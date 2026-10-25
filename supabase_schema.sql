-- ==============================================================================
-- TRIAL OF THE NINE REALMS: DATABASE SCHEMA (SUPABASE / POSTGRESQL)
-- Run this in the Supabase SQL Editor: https://supabase.com/dashboard/project/uspbxuhsxzwpevqdnysx/sql
-- ==============================================================================

-- 1. Enable pgvector extension for dense embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Runemark Documents Table (with pgvector + full-text search)
CREATE TABLE IF NOT EXISTS runemark_documents (
    doc_id TEXT PRIMARY KEY,
    title TEXT,
    content TEXT NOT NULL,
    country TEXT,
    sector TEXT,
    event_id TEXT,
    pub_date DATE NOT NULL,
    source_type TEXT,
    reliability_tier INT CHECK (reliability_tier BETWEEN 1 AND 4),
    
    -- Status and quarantine flags (Deliberate Traps defense)
    is_retracted BOOLEAN DEFAULT FALSE,
    retracted_by TEXT,
    is_corrected BOOLEAN DEFAULT FALSE,
    corrected_by TEXT,
    is_damaged BOOLEAN DEFAULT FALSE,
    damage_type TEXT, -- 'empty', 'truncated', 'encoding'
    is_duplicate BOOLEAN DEFAULT FALSE,
    duplicate_of TEXT,
    is_injection_attempt BOOLEAN DEFAULT FALSE,
    
    -- Embeddings (Gemini text-embedding-004 is 768 dimensions)
    embedding vector(768),
    
    -- Postgres Full-Text Search tsvector (for BM25 hybrid search)
    fts tsvector GENERATED ALWAYS AS (
        to_tsvector('english', coalesce(title, '') || ' ' || coalesce(content, ''))
    ) STORED,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for HNSW vector search
CREATE INDEX IF NOT EXISTS idx_runemark_docs_embedding 
ON runemark_documents USING hnsw (embedding vector_cosine_ops);

-- Index for Full-Text Search
CREATE INDEX IF NOT EXISTS idx_runemark_docs_fts 
ON runemark_documents USING gin (fts);

-- Index for As-Of Date filtering
CREATE INDEX IF NOT EXISTS idx_runemark_docs_pub_date 
ON runemark_documents (pub_date);

-- 3. Trade Tables (Metadata)
CREATE TABLE IF NOT EXISTS trade_tables (
    table_id TEXT PRIMARY KEY,
    country_pair TEXT,
    sector TEXT,
    unit TEXT,
    period TEXT,
    event_id TEXT,
    status TEXT DEFAULT 'ok',
    source_file TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Trade Table Rows (Granular calculation and citation level: TABLE-ID#row)
CREATE TABLE IF NOT EXISTS trade_rows (
    id BIGSERIAL PRIMARY KEY,
    table_id TEXT REFERENCES trade_tables(table_id) ON DELETE CASCADE,
    row_no INT NOT NULL,
    month DATE NOT NULL,
    value NUMERIC,
    volume NUMERIC,
    row_status TEXT DEFAULT 'ok', -- 'ok', 'missing', 'bad_number', 'repeated', 'cut_off'
    flag_reason TEXT,
    UNIQUE(table_id, row_no)
);

CREATE INDEX IF NOT EXISTS idx_trade_rows_lookup 
ON trade_rows (table_id, month);

-- 5. Case File Store (Blackboard Persistence)
CREATE TABLE IF NOT EXISTS case_files (
    case_id TEXT PRIMARY KEY,
    question TEXT NOT NULL,
    as_of DATE NOT NULL,
    status TEXT DEFAULT 'open', -- 'open', 'rejected', 'closed', 'closed_incomplete'
    scope JSONB,
    verification JSONB,
    ingest_report JSONB,
    runs JSONB DEFAULT '[]'::jsonb,
    limits JSONB,
    briefing TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. Private Agent Memories (Acceptance Check 9)
CREATE TABLE IF NOT EXISTS agent_memories (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL, -- 'heimdall', 'thor', 'loki', 'odin'
    memory_type TEXT NOT NULL,
    content TEXT NOT NULL,
    scope TEXT,
    basis_refs JSONB DEFAULT '[]'::jsonb,
    confidence NUMERIC DEFAULT 1.0,
    created_run INT,
    last_used_run INT,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS memory_events (
    id BIGSERIAL PRIMARY KEY,
    case_id TEXT,
    run_no INT,
    agent_id TEXT NOT NULL,
    event_type TEXT NOT NULL, -- 'memory_written', 'memory_read', 'query_changed_by_memory', etc.
    memory_id TEXT,
    previous_query TEXT,
    new_query TEXT,
    previous_filters JSONB,
    new_filters JSONB,
    reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ==============================================================================
-- 7. Hybrid Search Function (Vector + BM25 FTS merged via Reciprocal Rank Fusion)
-- ==============================================================================
CREATE OR REPLACE FUNCTION hybrid_search_docs(
    query_text TEXT,
    query_embedding vector(768),
    as_of_limit DATE,
    match_count INT DEFAULT 20,
    full_text_weight FLOAT DEFAULT 1.0,
    vector_weight FLOAT DEFAULT 1.0,
    filter_country TEXT DEFAULT NULL,
    filter_sector TEXT DEFAULT NULL,
    max_tier INT DEFAULT 4
)
RETURNS TABLE (
    doc_id TEXT,
    title TEXT,
    content TEXT,
    country TEXT,
    sector TEXT,
    event_id TEXT,
    pub_date DATE,
    source_type TEXT,
    reliability_tier INT,
    is_retracted BOOLEAN,
    is_corrected BOOLEAN,
    is_damaged BOOLEAN,
    is_injection_attempt BOOLEAN,
    combined_score FLOAT
)
LANGUAGE sql
AS $$
    WITH vector_matches AS (
        SELECT 
            d.doc_id,
            ROW_NUMBER() OVER (ORDER BY d.embedding <=> query_embedding) AS vector_rank
        FROM runemark_documents d
        WHERE d.pub_date <= as_of_limit
          AND d.is_damaged = FALSE
          AND d.is_injection_attempt = FALSE
          AND d.is_retracted = FALSE
          AND (filter_country IS NULL OR d.country = filter_country)
          AND (filter_sector IS NULL OR d.sector = filter_sector)
          AND d.reliability_tier <= max_tier
        LIMIT match_count * 2
    ),
    fts_matches AS (
        SELECT 
            d.doc_id,
            ROW_NUMBER() OVER (ORDER BY ts_rank_cd(d.fts, plainto_tsquery('english', query_text)) DESC) AS fts_rank
        FROM runemark_documents d
        WHERE d.pub_date <= as_of_limit
          AND d.is_damaged = FALSE
          AND d.is_injection_attempt = FALSE
          AND d.is_retracted = FALSE
          AND (filter_country IS NULL OR d.country = filter_country)
          AND (filter_sector IS NULL OR d.sector = filter_sector)
          AND d.reliability_tier <= max_tier
          AND d.fts @@ plainto_tsquery('english', query_text)
        LIMIT match_count * 2
    )
    SELECT 
        d.doc_id,
        d.title,
        d.content,
        d.country,
        d.sector,
        d.event_id,
        d.pub_date,
        d.source_type,
        d.reliability_tier,
        d.is_retracted,
        d.is_corrected,
        d.is_damaged,
        d.is_injection_attempt,
        (
            coalesce(1.0 / (60 + vm.vector_rank), 0.0) * vector_weight +
            coalesce(1.0 / (60 + fm.fts_rank), 0.0) * full_text_weight
        )::FLOAT AS combined_score
    FROM runemark_documents d
    LEFT JOIN vector_matches vm ON d.doc_id = vm.doc_id
    LEFT JOIN fts_matches fm ON d.doc_id = fm.doc_id
    WHERE vm.doc_id IS NOT NULL OR fm.doc_id IS NOT NULL
    ORDER BY combined_score DESC
    LIMIT match_count;
$$;

-- ==============================================================================
-- 8. Trial Events Table (append-only audit trail for all agents)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS trial_events (
    id BIGSERIAL PRIMARY KEY,
    case_id TEXT,
    event_type TEXT NOT NULL,   -- e.g. 'heimdall_started', 'citation_verified', 'memory_written'
    agent TEXT NOT NULL,        -- 'heimdall', 'thor', 'loki', 'odin', 'runner'
    run_no INT DEFAULT 1,
    details JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for efficient querying by case
CREATE INDEX IF NOT EXISTS idx_trial_events_case_id ON trial_events (case_id);
CREATE INDEX IF NOT EXISTS idx_trial_events_agent    ON trial_events (agent, run_no);

-- Row Level Security: trial_events are append-only by design.
-- No UPDATE or DELETE should be permitted on this table.
-- (Enforce via Supabase RLS policies in the dashboard.)

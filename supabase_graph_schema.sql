-- ==============================================================================
-- TRIAL OF THE NINE REALMS: KNOWLEDGE GRAPH SCHEMA (SUPABASE / POSTGRESQL)
-- Run this in the Supabase SQL Editor: https://supabase.com/dashboard/project/uspbxuhsxzwpevqdnysx/sql
-- ==============================================================================

-- 1. Graph Entities (Nodes)
CREATE TABLE IF NOT EXISTS graph_nodes (
    node_id TEXT PRIMARY KEY,               -- e.g., 'nation:midgard', 'port:orvan_grain'
    name TEXT NOT NULL,                     -- e.g., 'Midgard', 'Orvan Grain Port'
    entity_type TEXT NOT NULL,              -- 'NATION', 'COMMODITY', 'CHOKEPOINT', etc.
    country TEXT,                           -- Associated country (if applicable)
    sector TEXT,                            -- Associated sector (if applicable)
    description TEXT,
    source_doc_id TEXT REFERENCES runemark_documents(doc_id),
    pub_date DATE NOT NULL,
    reliability_tier INT DEFAULT 1,
    properties JSONB DEFAULT '{}'::jsonb,   -- e.g., {"capacity_pct": 95, "status": "active"}
    embedding vector(768),                  -- For semantic entity matching
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_graph_nodes_type ON graph_nodes (entity_type);
CREATE INDEX IF NOT EXISTS idx_graph_nodes_pub_date ON graph_nodes (pub_date);
CREATE INDEX IF NOT EXISTS idx_graph_nodes_country_sector ON graph_nodes (country, sector);

-- 2. Graph Relations (Edges)
CREATE TABLE IF NOT EXISTS graph_edges (
    edge_id TEXT PRIMARY KEY,               -- e.g., 'edge:orvan_to_midgard:wheat'
    source_id TEXT REFERENCES graph_nodes(node_id) ON DELETE CASCADE,
    target_id TEXT REFERENCES graph_nodes(node_id) ON DELETE CASCADE,
    relation_type TEXT NOT NULL,            -- 'EXPORTS_TO', 'BOTTLENECKED_AT', 'SUBSTITUTES_WITH'
    weight FLOAT DEFAULT 1.0,
    description TEXT,
    citation TEXT NOT NULL,                 -- Strict grounding: e.g., 'ORV-0018#P3'
    pub_date DATE NOT NULL,
    as_of_limit DATE NOT NULL,              -- Enforces Simulated Clock (NFR2)
    reliability_tier INT DEFAULT 1,
    is_retracted BOOLEAN DEFAULT FALSE,
    properties JSONB DEFAULT '{}'::jsonb,   -- Metrics: {"baseline_vol": 120000, "drop_pct": 55}
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_graph_edges_st ON graph_edges (source_id, target_id);
CREATE INDEX IF NOT EXISTS idx_graph_edges_rel ON graph_edges (relation_type);
CREATE INDEX IF NOT EXISTS idx_graph_edges_pub ON graph_edges (pub_date);
CREATE INDEX IF NOT EXISTS idx_graph_edges_citation ON graph_edges (citation);

-- 3. Recursive Graph Traversal RPC (Temporal-Gated 2-Hop / 3-Hop Walk)
CREATE OR REPLACE FUNCTION graph_traverse_subgraph(
    root_node_ids TEXT[],
    as_of_cutoff DATE,
    max_depth INT DEFAULT 2,
    max_tier INT DEFAULT 4
)
RETURNS TABLE (
    depth INT,
    source_id TEXT,
    source_name TEXT,
    relation_type TEXT,
    target_id TEXT,
    target_name TEXT,
    citation TEXT,
    properties JSONB
) LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    WITH RECURSIVE graph_walk AS (
        -- Base Case: 1-Hop direct connections from root nodes
        SELECT 
            1 AS depth,
            e.source_id,
            ns.name AS source_name,
            e.relation_type,
            e.target_id,
            nt.name AS target_name,
            e.citation,
            e.properties,
            ARRAY[e.source_id, e.target_id] AS path_history
        FROM graph_edges e
        JOIN graph_nodes ns ON e.source_id = ns.node_id
        JOIN graph_nodes nt ON e.target_id = nt.node_id
        WHERE e.source_id = ANY(root_node_ids)
          AND e.pub_date <= as_of_cutoff
          AND e.reliability_tier <= max_tier
          AND e.is_retracted = FALSE

        UNION ALL

        -- Recursive Step: Traverse next hop avoiding cycles
        SELECT 
            gw.depth + 1,
            e.source_id,
            ns.name,
            e.relation_type,
            e.target_id,
            nt.name,
            e.citation,
            e.properties,
            gw.path_history || e.target_id
        FROM graph_edges e
        JOIN graph_walk gw ON e.source_id = gw.target_id
        JOIN graph_nodes ns ON e.source_id = ns.node_id
        JOIN graph_nodes nt ON e.target_id = nt.node_id
        WHERE gw.depth < max_depth
          AND NOT (e.target_id = ANY(gw.path_history)) -- Cycle prevention
          AND e.pub_date <= as_of_cutoff
          AND e.reliability_tier <= max_tier
          AND e.is_retracted = FALSE
    )
    SELECT gw.depth, gw.source_id, gw.source_name, gw.relation_type, 
           gw.target_id, gw.target_name, gw.citation, gw.properties
    FROM graph_walk gw;
END;
$$;

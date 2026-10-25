import os
from typing import List, Dict, Any, Optional
from google import genai
import cohere
from src.config import get_settings
from src.supabase_client import get_supabase_admin

settings = get_settings()

class RetrievalTools:
    """
    Handles hybrid document retrieval from Supabase:
    1. Generates query embeddings with Google Gemini (text-embedding-004).
    2. Calls Supabase hybrid_search_docs RPC (pgvector cosine + Postgres FTS RRF).
    3. Reranks candidates with Cohere Rerank API (rerank-v3.5).
    4. Enforces strict as-of date gating and exclusion of damaged/injection documents.
    """
    def __init__(self):
        # Gemini embedding client
        self.gemini_client = None
        if settings.GEMINI_API_KEY:
            try:
                self.gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
            except Exception as e:
                print(f"[Warning] Failed to initialize Gemini Client: {e}")

        # Cohere rerank client
        self.cohere_client = None
        if settings.COHERE_API_KEY:
            try:
                self.cohere_client = cohere.ClientV2(api_key=settings.COHERE_API_KEY)
            except Exception as e:
                print(f"[Warning] Failed to initialize Cohere Client: {e}")

        self.supabase = get_supabase_admin()

    def get_embedding(self, text: str) -> List[float]:
        """Generate 768-dimensional embedding using Gemini text-embedding-004."""
        if not self.gemini_client:
            # Fallback zero vector if no key is provided during offline setup
            return [0.0] * 768
        
        response = self.gemini_client.models.embed_content(
            model="text-embedding-004",
            contents=text,
        )
        return response.embeddings[0].values

    def search_docs(
        self,
        query: str,
        as_of_date: str,
        country: Optional[str] = None,
        sector: Optional[str] = None,
        max_tier: int = 4,
        match_count: int = 15,
        rerank_top_k: int = 6
    ) -> List[Dict[str, Any]]:
        """
        Executes hybrid search in Supabase with as-of date filtering,
        followed by Cohere reranking.
        """
        # 1. Embed query
        query_vector = self.get_embedding(query)

        # 2. Call Supabase RPC for Hybrid Search
        rpc_params = {
            "query_text": query,
            "query_embedding": query_vector,
            "as_of_limit": as_of_date,
            "match_count": match_count,
            "full_text_weight": 1.0,
            "vector_weight": 1.0,
            "filter_country": country,
            "filter_sector": sector,
            "max_tier": max_tier
        }

        try:
            res = self.supabase.rpc("hybrid_search_docs", rpc_params).execute()
            docs = res.data or []
        except Exception as e:
            print(f"[Retrieval] Supabase hybrid_search_docs failed: {e}")
            # Fallback to standard SELECT query if RPC is not loaded yet
            query_builder = self.supabase.table("runemark_documents") \
                .select("doc_id, title, content, country, sector, event_id, pub_date, source_type, reliability_tier") \
                .lte("pub_date", as_of_date) \
                .eq("is_damaged", False) \
                .eq("is_retracted", False) \
                .eq("is_injection_attempt", False) \
                .lte("reliability_tier", max_tier)
            
            if country:
                query_builder = query_builder.eq("country", country)
            if sector:
                query_builder = query_builder.eq("sector", sector)
                
            res = query_builder.limit(match_count).execute()
            docs = res.data or []

        if not docs:
            return []

        # 3. Optional Cohere Reranking
        if self.cohere_client and len(docs) > 1:
            try:
                doc_texts = [f"{d.get('title', '')}: {d.get('content', '')}" for d in docs]
                rerank_response = self.cohere_client.rerank(
                    model="rerank-v3.5",
                    query=query,
                    documents=doc_texts,
                    top_n=min(rerank_top_k, len(docs))
                )
                reranked_docs = []
                for item in rerank_response.results:
                    idx = item.index
                    doc_copy = docs[idx].copy()
                    doc_copy["rerank_score"] = item.relevance_score
                    reranked_docs.append(doc_copy)
                return reranked_docs
            except Exception as e:
                print(f"[Rerank] Cohere reranking failed, falling back to hybrid order: {e}")
                return docs[:rerank_top_k]

        return docs[:rerank_top_k]

    def get_doc(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Fetch full document content and metadata by ID."""
        try:
            res = self.supabase.table("runemark_documents") \
                .select("*") \
                .eq("doc_id", doc_id) \
                .single() \
                .execute()
            return res.data
        except Exception as e:
            print(f"[Retrieval] get_doc failed for {doc_id}: {e}")
            return None

    def search_graph(
        self,
        country: str,
        sector: Optional[str] = None,
        as_of_date: Optional[str] = None,
        max_depth: int = 2,
    ) -> Dict[str, Any]:
        """Query knowledge graph local ego-network around country and sector."""
        from datetime import date
        from src.retrieval.graph_retriever import get_graph_retriever
        as_of = date.fromisoformat(as_of_date) if as_of_date else None
        res = get_graph_retriever().retrieve_local_subgraph(
            country=country,
            sector=sector,
            as_of_date=as_of,
            max_depth=max_depth,
        )
        return res.model_dump(mode="json")

    def find_supply_chain_paths(
        self,
        target_country: str,
        source_event: Optional[str] = None,
        as_of_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Find causal supply-chain and disruption paths connecting event to nation."""
        from datetime import date
        from src.retrieval.graph_retriever import get_graph_retriever
        as_of = date.fromisoformat(as_of_date) if as_of_date else None
        paths = get_graph_retriever().retrieve_causal_paths(
            target_country=target_country,
            source_event=source_event,
            as_of_date=as_of,
        )
        return [p.model_dump(mode="json") for p in paths]

    def get_bottlenecks_and_substitutions(
        self,
        country: str,
        sector: Optional[str] = None,
        as_of_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Retrieve both capacity bottlenecks and active substitution routes."""
        from datetime import date
        from src.graph.store import get_graph_store
        as_of = date.fromisoformat(as_of_date) if as_of_date else None
        store = get_graph_store()
        return {
            "bottlenecks": store.detect_bottlenecks(target_country=country, sector=sector, as_of_date=as_of),
            "substitutions": store.detect_substitutions(target_country=country, sector=sector, as_of_date=as_of),
        }

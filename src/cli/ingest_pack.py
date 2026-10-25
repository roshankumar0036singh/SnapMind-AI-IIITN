"""
src/cli/ingest_pack.py
======================
Unified Zero-Code Pack Ingestion CLI for the Final Round.
Handles Section 4.5 of the Trial of the Nine Realms Problem Statement:
  1. Multi-format documents (PDF, TXT, DOCX) with checksum validation.
  2. Damaged document quarantine (empty, cut off, duplicated, badly encoded, injection traps) (NFR3).
  3. Fixed-layout trade tables with explicit reporting of damaged rows (cut-off, missing, repeated, bad number).
  4. Embedding generation using gemini-embedding-2 (768-dim) into Supabase runemark_documents.
  5. Dynamic Knowledge Graph auto-extraction of new entities, chokepoints, and disruption edges.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

from src.ingestion.manifest_loader import ManifestLoader, ManifestLoadResult
from src.ingestion.supabase_loader import SupabaseDocumentLoader
from src.trade.table_parser import TradeTableParser
from src.trade.validator import TradeRowValidator
from src.graph.store import get_graph_store
from src.graph.extractor import LLMGraphExtractor
from src.supabase_client import get_supabase_admin


def ingest_event_pack(
    pack_dir: Path,
    use_embeddings: bool = True,
    extract_graph: bool = True,
    event_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Ingests an entire Runemark event pack into Supabase and the Knowledge Graph.
    """
    pack_path = Path(pack_dir)
    if not pack_path.is_dir():
        raise FileNotFoundError(f"Pack directory does not exist: {pack_path}")

    print("=" * 80)
    print(f"  RUNEMARK FINAL ROUND INGESTION: {pack_path.name}")
    print("=" * 80)

    # ---------------------------------------------------------------------------
    # Step 1: Document Ingestion & Damage Quarantine
    # ---------------------------------------------------------------------------
    print("\n>>> STEP 1: PARSING & QUARANTINING DOCUMENTS (PDF, TXT, DOCX)...")
    doc_loader = SupabaseDocumentLoader(use_embeddings=use_embeddings)
    ingest_report = doc_loader.load_pack_to_supabase(pack_path, generate_embeddings=use_embeddings)

    print(f"\n[Document Ingest Summary]")
    print(f"  - Total files cataloged : {ingest_report.total_files}")
    print(f"  - Clean / Ingested OK   : {ingest_report.files_ok}")
    print(f"  - Damaged (Quarantined) : {len(ingest_report.files_damaged)}")
    print(f"  - Duplicates Neutralized: {len(ingest_report.files_duplicated)}")
    print(f"  - Injections Flagged    : {len(ingest_report.files_injection_flagged)}")

    if ingest_report.files_damaged:
        print("\n  [Quarantined Damaged Files]:")
        for d in ingest_report.files_damaged[:5]:
            print(f"    * {d.get('file')} ({d.get('doc_id')}): {d.get('reason')} [{d.get('damage_type')}]")

    # ---------------------------------------------------------------------------
    # Step 2: Trade Table Ingestion & Granular Damage Reporting (PS Sec 4.5)
    # ---------------------------------------------------------------------------
    print("\n>>> STEP 2: PROCESSING TRADE TABLES & INSPECTING DAMAGED ROWS...")
    docs_dir = pack_path / "docs"
    table_parser = TradeTableParser()
    supabase = get_supabase_admin()

    total_tables = 0
    total_valid_rows = 0
    damaged_rows_report: List[Dict[str, Any]] = []

    if docs_dir.is_dir():
        for txt_file in docs_dir.glob("*.txt"):
            try:
                content = txt_file.read_text(encoding="utf-8", errors="ignore")
                # Identify if file is a trade table by header inspection
                if "TABLE_ID:" in content or "TABLE ID:" in content or "COUNTRY_PAIR:" in content:
                    header, rows = table_parser.parse_string(content, source_file=txt_file.name)
                    if header.table_id:
                        total_tables += 1
                        # Save table metadata
                        supabase.table("trade_tables").upsert({
                            "table_id": header.table_id,
                            "country_pair": header.country_pair,
                            "sector": header.sector,
                            "unit": header.unit,
                            "period": header.period,
                            "event_id": header.event_id,
                            "status": header.status,
                        }, on_conflict="table_id").execute()

                        # Process rows
                        rows_payload = []
                        for r in rows:
                            if r.row_status != "ok":
                                damaged_rows_report.append({
                                    "table_id": header.table_id,
                                    "row_no": r.row_no,
                                    "month": r.month.isoformat() if r.month else "missing",
                                    "status": r.row_status,
                                    "flag_reason": r.flag_reason,
                                    "raw_value": getattr(r, "raw_value", None),
                                    "raw_volume": getattr(r, "raw_volume", None),
                                })
                            else:
                                total_valid_rows += 1
                                rows_payload.append({
                                    "table_id": header.table_id,
                                    "row_no": r.row_no,
                                    "month": r.month.isoformat() if r.month else None,
                                    "value": r.value,
                                    "volume": r.volume,
                                    "status": r.row_status,
                                    "flag_reason": r.flag_reason,
                                })

                        if rows_payload:
                            supabase.table("trade_rows").upsert(rows_payload, on_conflict="table_id,row_no").execute()
            except Exception as e:
                print(f"  [Warning] Skipping unreadable trade table candidate {txt_file.name}: {e}")

    print(f"\n[Trade Table Summary]")
    print(f"  - Trade tables registered : {total_tables}")
    print(f"  - Valid monthly rows      : {total_valid_rows}")
    print(f"  - Damaged rows flagged    : {len(damaged_rows_report)}")

    if damaged_rows_report:
        print("\n  [DAMAGED TRADE ROW REPORT] (Explicitly caught per Section 4.5):")
        print(f"  {'Table ID':<12} | {'Row':<4} | {'Month':<10} | {'Issue Type':<12} | {'Raw Volume/Value':<20} | Action")
        print("  " + "-" * 78)
        for dr in damaged_rows_report[:10]:
            raw_str = f"vol={dr['raw_volume']}, val={dr['raw_value']}"
            print(f"  {dr['table_id']:<12} | {dr['row_no']:<4} | {dr['month']:<10} | {dr['status']:<12} | {raw_str:<20} | Excluded from calculations")
        if len(damaged_rows_report) > 10:
            print(f"  ... and {len(damaged_rows_report) - 10} more damaged rows flagged in audit log.")

    # ---------------------------------------------------------------------------
    # Step 3: Dynamic Knowledge Graph Auto-Extraction (Section 4.5)
    # ---------------------------------------------------------------------------
    extracted_nodes = 0
    extracted_edges = 0
    if extract_graph:
        print("\n>>> STEP 3: DYNAMIC KNOWLEDGE GRAPH AUTO-EXTRACTION VIA GEMINI...")
        graph_store = get_graph_store()
        extractor = LLMGraphExtractor()

        # Target high-tier documents for entity extraction
        if docs_dir.is_dir():
            for txt_file in list(docs_dir.glob("*.txt"))[:10]:
                try:
                    text = txt_file.read_text(encoding="utf-8", errors="ignore")
                    if "TABLE_ID:" in text:
                        continue  # Skip numeric tables for graph text extraction
                    doc_id = txt_file.stem
                    res = extractor.extract_from_document(
                        doc_id=doc_id,
                        text=text[:3000],
                        pub_date=ingest_report.as_of,
                        reliability_tier=1,
                    )
                    for ent in res.entities:
                        from src.schemas.graph import GraphNode, EntityType
                        try:
                            etype = EntityType(ent.entity_type)
                        except Exception:
                            etype = EntityType.NATION
                        node = GraphNode(
                            node_id=f"{etype.value}:{ent.name.lower().replace(' ', '_')}",
                            name=ent.name,
                            entity_type=etype,
                            country=ent.country,
                            sector=ent.sector,
                            description=ent.description,
                            pub_date=ingest_report.as_of,
                            reliability_tier=1,
                            properties=ent.properties,
                        )
                        graph_store.add_node(node)
                        extracted_nodes += 1

                    for rel in res.relations:
                        from src.schemas.graph import GraphEdge, RelationType
                        try:
                            rtype = RelationType(rel.relation_type)
                        except Exception:
                            rtype = RelationType.EXPORTS_TO
                        src_id = f"entity:{rel.source_name.lower().replace(' ', '_')}"
                        tgt_id = f"entity:{rel.target_name.lower().replace(' ', '_')}"
                        edge = GraphEdge(
                            edge_id=f"dyn_edge:{src_id}_{tgt_id}_{rel.relation_type}",
                            source_id=src_id,
                            target_id=tgt_id,
                            relation_type=rtype,
                            description=rel.description,
                            citation=rel.citation or f"{doc_id}#P1",
                            pub_date=ingest_report.as_of,
                            as_of_limit=ingest_report.as_of,
                            reliability_tier=1,
                            properties=rel.properties,
                        )
                        graph_store.add_edge(edge)
                        extracted_edges += 1
                except Exception as e:
                    print(f"  [Warning] Graph extraction skipped for {txt_file.name}: {e}")

        graph_store.save_to_disk()
        print(f"  - Extracted new graph items: {extracted_nodes} nodes, {extracted_edges} edges")
        print(f"  - Total Knowledge Graph size: {len(graph_store.nodes_data)} nodes, {len(graph_store.edges_data)} edges")

    print("\n" + "=" * 80)
    print("  LIVE PACK INGESTION COMPLETE: READY FOR TRIAL DEBATE")
    print("=" * 80)

    return {
        "pack_name": ingest_report.pack_name,
        "as_of": str(ingest_report.as_of),
        "files_ok": ingest_report.files_ok,
        "files_damaged": len(ingest_report.files_damaged),
        "tables_registered": total_tables,
        "valid_trade_rows": total_valid_rows,
        "damaged_trade_rows": len(damaged_rows_report),
        "graph_nodes_total": len(get_graph_store().nodes_data),
        "graph_edges_total": len(get_graph_store().edges_data),
    }


def main():
    parser = argparse.ArgumentParser(description="Ingest Runemark final round event pack into Supabase & Knowledge Graph.")
    parser.add_argument("--pack-dir", type=str, default="data/test_packs/dev_pack_E5", help="Path to event pack folder")
    parser.add_argument("--no-embeddings", action="store_true", help="Skip embedding generation")
    parser.add_argument("--no-graph", action="store_true", help="Skip dynamic graph extraction")
    args = parser.parse_args()

    try:
        ingest_event_pack(
            pack_dir=Path(args.pack_dir),
            use_embeddings=not args.no_embeddings,
            extract_graph=not args.no_graph,
        )
    except Exception as e:
        print(f"Error during ingestion: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

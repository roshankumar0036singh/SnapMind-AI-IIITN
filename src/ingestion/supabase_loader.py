import argparse
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.supabase_client import get_supabase_admin
from src.llm.embeddings import get_embedding_client
from src.ingestion.manifest_loader import ManifestLoader, ManifestLoadResult
from src.schemas.ingest import IngestReport


class SupabaseDocumentLoader:
    """
    Loads parsed Runemark documents and Gemini 768-dim embeddings into Supabase.
    Fulfills Phase 6 of the data ingestion pipeline.
    """

    BATCH_SIZE = 20

    def __init__(self, use_embeddings: bool = True):
        self.use_embeddings = use_embeddings
        self.embedding_client = get_embedding_client() if use_embeddings else None
        self._admin = None

    @property
    def admin(self):
        if self._admin is None:
            self._admin = get_supabase_admin()
        return self._admin

    def load_pack_to_supabase(
        self,
        pack_dir: Path,
        generate_embeddings: bool = True,
    ) -> IngestReport:
        """
        Parses an event pack, generates embeddings, and upserts all documents into Supabase.
        """
        pack_path = Path(pack_dir)
        print(f"Loading pack from: {pack_path}")
        
        loader = ManifestLoader()
        load_result = loader.load_pack(pack_path)
        records = load_result.document_records

        print(f"Parsed {len(records)} valid documents ({load_result.ingest_report.files_ok} OK, "
              f"{len(load_result.ingest_report.files_damaged)} damaged, "
              f"{len(load_result.ingest_report.files_duplicated)} duplicated, "
              f"{len(load_result.ingest_report.files_injection_flagged)} injection-flagged)")

        # Prepare database rows
        rows_to_upsert: List[Dict[str, Any]] = []
        texts_to_embed: List[str] = []
        doc_indices: List[int] = []

        for idx, rec in enumerate(records):
            meta = rec["metadata"]
            damage = rec["damage_report"]
            body = rec["body_text"]

            # Document text for embedding includes title and body
            embed_text = f"{meta['title']}\n\n{body}"
            texts_to_embed.append(embed_text)
            doc_indices.append(idx)

            row = {
                "doc_id": meta["doc_id"],
                "title": meta["title"],
                "content": body,
                "country": meta["country"],
                "sector": meta["sector"],
                "event_id": meta["event_id"],
                "pub_date": meta["pub_date"].isoformat() if hasattr(meta["pub_date"], "isoformat") else str(meta["pub_date"]),
                "source_type": meta["source_type"],
                "reliability_tier": meta["reliability_tier"],
                "is_retracted": damage.get("is_retracted", False),
                "retracted_by": damage.get("retracted_by"),
                "is_corrected": damage.get("is_corrected", False),
                "corrected_by": damage.get("corrected_by"),
                "is_damaged": damage.get("is_damaged", False),
                "damage_type": damage.get("damage_type"),
                "is_duplicate": damage.get("is_duplicate", False),
                "duplicate_of": damage.get("duplicate_of"),
                "is_injection_attempt": damage.get("is_injection_attempt", False),
                "embedding": None,
            }
            rows_to_upsert.append(row)

        # Generate Gemini embeddings if requested and client available
        if generate_embeddings and self.embedding_client:
            print(f"Generating 768-dim embeddings via Gemini text-embedding-004 for {len(texts_to_embed)} documents...")
            try:
                embeddings = self.embedding_client.get_embeddings_batch(texts_to_embed, batch_size=self.BATCH_SIZE)
                for i, emb in enumerate(embeddings):
                    rows_to_upsert[i]["embedding"] = emb
                print("All embeddings generated successfully.")
            except Exception as e:
                print(f"Warning: Failed to generate embeddings ({e}). Uploading without embeddings.")

        # Batch upsert to Supabase
        print(f"Upserting {len(rows_to_upsert)} documents to Supabase 'runemark_documents'...")
        for i in range(0, len(rows_to_upsert), self.BATCH_SIZE):
            batch = rows_to_upsert[i : i + self.BATCH_SIZE]
            try:
                self.admin.table("runemark_documents").upsert(batch, on_conflict="doc_id").execute()
            except Exception as e:
                raise RuntimeError(f"Supabase upsert failed at batch {i}: {e}")

        print(f"Successfully ingested pack '{load_result.pack_name}' into Supabase.")
        return load_result.ingest_report


def main():
    parser = argparse.ArgumentParser(description="Ingest Runemark event pack into Supabase with Gemini embeddings.")
    parser.add_argument("--pack-dir", type=str, default="data/test_packs/dev_pack_E5", help="Path to event pack folder")
    parser.add_argument("--no-embeddings", action="store_true", help="Skip embedding generation")
    args = parser.parse_args()

    pack_path = Path(args.pack_dir)
    loader = SupabaseDocumentLoader(use_embeddings=not args.no_embeddings)
    try:
        report = loader.load_pack_to_supabase(pack_path, generate_embeddings=not args.no_embeddings)
        print("\n=== Ingest Report ===")
        print(f"Total Files: {report.total_files}")
        print(f"Files OK: {report.files_ok}")
        print(f"Files Damaged: {len(report.files_damaged)}")
        print(f"Files Duplicated: {len(report.files_duplicated)}")
        print(f"Files Injection Flagged: {len(report.files_injection_flagged)}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

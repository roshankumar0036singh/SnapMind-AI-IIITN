import json
import hashlib
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from pydantic import BaseModel, Field

from src.ingestion.parsers import parse_document
from src.ingestion.damage_detector import DamageDetector
from src.ingestion.injection_guard import get_injection_guard
from src.ingestion.chunker import get_chunker
from src.schemas.ingest import DocumentMetadata, DocumentDamageReport, ParagraphChunk, IngestReport


class ManifestLoadResult(BaseModel):
    """
    Complete output of manifest ingestion.
    """
    pack_name: str
    event_id: str
    as_of: date
    ingest_report: IngestReport
    chunks: List[ParagraphChunk] = Field(default_factory=list)
    document_records: List[Dict[str, Any]] = Field(default_factory=list)


class ManifestLoader:
    """
    Loads and coordinates ingestion of an entire Runemark event pack.
    Fulfills Acceptance Checks 1, 8, and 10.
    """

    def __init__(self):
        self.damage_detector = DamageDetector()
        self.injection_guard = get_injection_guard()
        self.chunker = get_chunker()

    def load_pack(self, pack_dir: Path) -> ManifestLoadResult:
        pack_path = Path(pack_dir)
        manifest_path = pack_path / "manifest.json"
        if not manifest_path.is_file():
            raise FileNotFoundError(f"manifest.json not found in pack directory: {pack_path}")

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)

        pack_name = manifest_data.get("pack", pack_path.name)
        event_id = manifest_data.get("event_id", "NONE")
        as_of_str = manifest_data.get("as_of", "2027-01-25")
        as_of = datetime.strptime(as_of_str, "%Y-%m-%d").date()

        # Optional checksum verification
        checksums: Dict[str, str] = {}
        hashes_file = pack_path / "hashes.sha256"
        if hashes_file.is_file():
            for line in hashes_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and "  " in line:
                    h, rel_path = line.split("  ", 1)
                    checksums[Path(rel_path).name] = h.strip()

        docs_list = manifest_data.get("documents", [])
        docs_dir = pack_path / "docs"

        all_chunks: List[ParagraphChunk] = []
        document_records: List[Dict[str, Any]] = []

        files_ok = 0
        files_damaged: List[Dict[str, Any]] = []
        files_duplicated: List[Dict[str, Any]] = []
        files_injection_flagged: List[Dict[str, Any]] = []

        for doc_entry in docs_list:
            file_name = doc_entry.get("file")
            doc_id = doc_entry.get("DOC_ID", "UNKNOWN")
            file_path = docs_dir / file_name if file_name else None

            # 1. Physical existence and 0-byte check
            if not file_path or not file_path.is_file():
                files_damaged.append({
                    "doc_id": doc_id,
                    "file": file_name,
                    "reason": "File missing on filesystem",
                    "damage_type": "missing",
                })
                continue

            file_size = file_path.stat().st_size
            if file_size == 0:
                damage_rep = self.damage_detector.inspect(file_path, metadata=None, raw_text="")
                files_damaged.append({
                    "doc_id": doc_id,
                    "file": file_name,
                    "reason": damage_rep.quarantine_reason,
                    "damage_type": "empty",
                })
                continue

            # 2. Checksum validation (if available)
            if file_name in checksums:
                calc_sha = hashlib.sha256(file_path.read_bytes()).hexdigest()
                if calc_sha != checksums[file_name]:
                    files_damaged.append({
                        "doc_id": doc_id,
                        "file": file_name,
                        "reason": f"Checksum mismatch: expected {checksums[file_name]}, got {calc_sha}",
                        "damage_type": "corrupted",
                    })
                    continue

            # 3. Document Parsing
            try:
                metadata, body_text = parse_document(file_path)
            except Exception as e:
                files_damaged.append({
                    "doc_id": doc_id,
                    "file": file_name,
                    "reason": f"Parse failure: {str(e)}",
                    "damage_type": "truncated",
                })
                continue

            # 4. Damage & Duplicate Inspection
            damage_report = self.damage_detector.inspect(file_path, metadata=metadata, raw_text=body_text)
            if damage_report.is_damaged:
                files_damaged.append({
                    "doc_id": doc_id,
                    "file": file_name,
                    "reason": damage_report.quarantine_reason,
                    "damage_type": damage_report.damage_type,
                })
                continue

            if damage_report.is_duplicate:
                files_duplicated.append({
                    "doc_id": doc_id,
                    "file": file_name,
                    "duplicate_of": damage_report.duplicate_of,
                    "reason": damage_report.quarantine_reason,
                })
                # We record duplicates for audit, but skip adding chunks to search
                continue

            # 5. Prompt-Injection Inspection
            injection_res = self.injection_guard.scan(body_text)
            if injection_res.is_injection_attempt:
                damage_report.is_injection_attempt = True
                damage_report.injection_spans = injection_res.matched_spans
                files_injection_flagged.append({
                    "doc_id": doc_id,
                    "file": file_name,
                    "rules": injection_res.rule_ids,
                    "spans": injection_res.matched_spans,
                })
                # Per Sec 15.2, injection items are excluded from evidence retrieval by default
                continue

            # 6. Paragraph Chunking
            chunks = self.chunker.chunk_document(metadata, body_text, damage_report)
            all_chunks.extend(chunks)
            files_ok += 1

            document_records.append({
                "doc_id": metadata.doc_id,
                "metadata": metadata.model_dump(),
                "body_text": body_text,
                "damage_report": damage_report.model_dump(),
                "chunk_count": len(chunks),
            })

        ingest_report = IngestReport(
            pack_name=pack_name,
            event_id=event_id,
            as_of=as_of,
            total_files=len(docs_list),
            files_ok=files_ok,
            files_damaged=files_damaged,
            files_duplicated=files_duplicated,
            files_injection_flagged=files_injection_flagged,
        )

        return ManifestLoadResult(
            pack_name=pack_name,
            event_id=event_id,
            as_of=as_of,
            ingest_report=ingest_report,
            chunks=all_chunks,
            document_records=document_records,
        )

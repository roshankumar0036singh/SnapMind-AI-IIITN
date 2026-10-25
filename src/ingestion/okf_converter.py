import re
from pathlib import Path
from typing import Dict, Any, List, Optional
import yaml

from src.schemas.ingest import DocumentMetadata, DocumentDamageReport
from src.schemas.memory import MemoryRecord
from src.ingestion.manifest_loader import ManifestLoader


class OKFConverter:
    """
    Open Knowledge Format (OKF) Converter.
    Fulfills CONTEXT_UPDATED.md Section 7:
    - Normalizes heterogeneous documents (PDF, TXT, DOCX) into uniform Markdown with YAML frontmatter.
    - Explicitly surfaces deliberate trap flags (retractions, corrections, damage, injection attempts).
    - Generates bidirectional wiki-links [[DOC-ID]] between corrections and originals.
    - Exports agent private memories into visual OKF note cards for Acceptance Check 9.
    """

    DEFAULT_OKF_DOCS_DIR = Path("data/runemark_processed/okf_docs")
    DEFAULT_OKF_MEMORY_DIR = Path("data/runemark_processed/okf_memories")

    @staticmethod
    def format_document_as_okf(
        metadata: Dict[str, Any],
        damage_report: Dict[str, Any],
        body_text: str,
        links: Optional[List[str]] = None,
    ) -> str:
        """
        Converts parsed document data into an OKF Markdown string with YAML frontmatter.
        """
        frontmatter = {
            "doc_id": metadata.get("doc_id"),
            "title": metadata.get("title"),
            "country": metadata.get("country"),
            "sector": metadata.get("sector"),
            "event_id": metadata.get("event_id"),
            "pub_date": metadata.get("pub_date").isoformat() if hasattr(metadata.get("pub_date"), "isoformat") else str(metadata.get("pub_date")),
            "reliability_tier": metadata.get("reliability_tier"),
            "source_type": metadata.get("source_type"),
            "format": metadata.get("format", "unknown"),
            "is_retracted": damage_report.get("is_retracted", False),
            "retracted_by": damage_report.get("retracted_by"),
            "is_corrected": damage_report.get("is_corrected", False),
            "corrected_by": damage_report.get("corrected_by"),
            "is_damaged": damage_report.get("is_damaged", False),
            "damage_type": damage_report.get("damage_type"),
            "is_duplicate": damage_report.get("is_duplicate", False),
            "duplicate_of": damage_report.get("duplicate_of"),
            "is_injection_attempt": damage_report.get("is_injection_attempt", False),
            "links": links or [],
        }

        # Dump YAML header safely
        yaml_str = yaml.dump(frontmatter, sort_keys=False, default_flow_style=False).strip()
        cleaned_body = (body_text or "").replace("\x00", "").strip()

        return f"---\n{yaml_str}\n---\n\n{cleaned_body}\n"

    @classmethod
    def convert_and_save_pack(
        cls,
        pack_dir: Path,
        output_dir: Optional[Path] = None,
    ) -> List[Path]:
        """
        Loads an event pack and writes each parsed document as an OKF Markdown file.
        """
        out_path = Path(output_dir or cls.DEFAULT_OKF_DOCS_DIR)
        out_path.mkdir(parents=True, exist_ok=True)

        loader = ManifestLoader()
        result = loader.load_pack(Path(pack_dir))
        saved_paths: List[Path] = []

        for rec in result.document_records:
            meta = rec["metadata"]
            damage = rec["damage_report"]
            body = rec["body_text"]
            doc_id = meta["doc_id"]

            # Derive cross-document links
            links = []
            if damage.get("corrected_by"):
                links.append(f"[[{damage['corrected_by']}]]")
            if damage.get("retracted_by"):
                links.append(f"[[{damage['retracted_by']}]]")
            if damage.get("duplicate_of"):
                links.append(f"[[{damage['duplicate_of']}]]")

            okf_content = cls.format_document_as_okf(meta, damage, body, links=links)
            file_path = out_path / f"{doc_id}.md"
            file_path.write_text(okf_content, encoding="utf-8")
            saved_paths.append(file_path)

        return saved_paths

    @classmethod
    def format_memory_as_okf(cls, memory: MemoryRecord) -> str:
        """
        Formats an agent's private lasting memory record into an OKF Markdown card.
        """
        frontmatter = {
            "id": memory.id,
            "agent_id": memory.agent_id,
            "memory_type": memory.memory_type.value if hasattr(memory.memory_type, "value") else str(memory.memory_type),
            "scope": memory.scope.value if hasattr(memory.scope, "value") else str(memory.scope),
            "scope_value": memory.scope_value,
            "confidence": memory.confidence,
            "status": memory.status,
            "created_run": memory.created_run,
            "last_used_run": memory.last_used_run,
            "basis_refs": memory.basis_refs,
        }

        yaml_str = yaml.dump(frontmatter, sort_keys=False, default_flow_style=False).strip()
        body = f"# Actionable Lesson ({memory.memory_type})\n\n{memory.content}\n"
        if memory.basis_refs:
            body += "\n## Basis References\n" + "\n".join(f"- [[{ref}]]" for ref in memory.basis_refs) + "\n"

        return f"---\n{yaml_str}\n---\n\n{body}"

    @classmethod
    def export_agent_memories_to_okf(
        cls,
        memories: List[MemoryRecord],
        output_dir: Optional[Path] = None,
    ) -> List[Path]:
        """
        Exports a list of MemoryRecords into individual OKF Markdown cards.
        """
        out_path = Path(output_dir or cls.DEFAULT_OKF_MEMORY_DIR)
        out_path.mkdir(parents=True, exist_ok=True)
        saved_paths: List[Path] = []

        for mem in memories:
            agent_dir = out_path / mem.agent_id.lower()
            agent_dir.mkdir(parents=True, exist_ok=True)

            card_content = cls.format_memory_as_okf(mem)
            card_path = agent_dir / f"{mem.id}.md"
            card_path.write_text(card_content, encoding="utf-8")
            saved_paths.append(card_path)

        return saved_paths

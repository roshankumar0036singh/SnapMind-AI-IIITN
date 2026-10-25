import re
from datetime import date
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import yaml

from src.schemas.ingest import DocumentMetadata, DocumentDamageReport
from src.schemas.memory import MemoryRecord, MemoryType, MemoryScope
from src.ingestion.manifest_loader import ManifestLoader


class OKFConverter:
    """
    Open Knowledge Format (OKF) Converter.
    Fulfills CONTEXT_UPDATED.md Section 7:
    - Normalizes heterogeneous documents (PDF, TXT, DOCX) into uniform Markdown with YAML frontmatter.
    - Explicitly surfaces deliberate trap flags (retractions, corrections, damage, injection attempts).
    - Generates and extracts bidirectional wiki-links [[DOC-ID]] between documents and memories.
    - Exports and imports agent private memories into visual OKF note cards for Acceptance Check 9.
    - Provides resilient local document retrieval fallback for citation verification and exhibit inspection.
    """

    DEFAULT_OKF_DOCS_DIR = Path("data/runemark_processed/okf_docs")
    DEFAULT_OKF_MEMORY_DIR = Path("data/runemark_processed/okf_memories")
    WIKI_LINK_PATTERN = re.compile(r"\[\[([A-Z0-9_\-#]+)\]\]", re.IGNORECASE)

    @staticmethod
    def extract_wiki_links(text: str) -> List[str]:
        """Extracts [[DOC-ID]] or [[REF]] wiki links from text."""
        if not text:
            return []
        matches = OKFConverter.WIKI_LINK_PATTERN.findall(text)
        return list(dict.fromkeys(f"[[{m}]]" for m in matches))

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
        # Discover any wiki links inside the body text
        discovered_links = OKFConverter.extract_wiki_links(body_text)
        all_links = list(dict.fromkeys((links or []) + discovered_links))

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
            "links": all_links,
        }

        # Dump YAML header safely
        yaml_str = yaml.dump(frontmatter, sort_keys=False, default_flow_style=False).strip()
        cleaned_body = (body_text or "").replace("\x00", "").strip()

        return f"---\n{yaml_str}\n---\n\n{cleaned_body}\n"

    @classmethod
    def parse_okf_document(cls, content_or_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Parses an OKF Markdown file or string into a structured document dictionary.
        Extracts YAML frontmatter, trap flags, wiki links, and clean markdown body.
        """
        raw_text = ""
        if isinstance(content_or_path, Path) or (isinstance(content_or_path, str) and "\n" not in content_or_path and Path(content_or_path).is_file()):
            raw_text = Path(content_or_path).read_text(encoding="utf-8")
        else:
            raw_text = str(content_or_path)

        match = re.match(r"^---\r?\n([\s\S]*?)\r?\n---\r?\n?([\s\S]*)$", raw_text)
        if not match:
            # Fallback if no frontmatter found
            return {"content": raw_text.strip(), "body_text": raw_text.strip(), "links": cls.extract_wiki_links(raw_text)}

        yaml_text, body = match.group(1), match.group(2).strip()
        frontmatter = yaml.safe_load(yaml_text) or {}

        # Resolve pub_date
        raw_pub = frontmatter.get("pub_date")
        pub_date = None
        if isinstance(raw_pub, date):
            pub_date = raw_pub
        elif isinstance(raw_pub, str) and raw_pub.strip():
            try:
                pub_date = date.fromisoformat(raw_pub.strip()[:10])
            except ValueError:
                pub_date = None

        # Collect links
        links = frontmatter.get("links") or []
        body_links = cls.extract_wiki_links(body)
        combined_links = list(dict.fromkeys(links + body_links))

        return {
            "doc_id": frontmatter.get("doc_id"),
            "title": frontmatter.get("title"),
            "country": frontmatter.get("country"),
            "sector": frontmatter.get("sector"),
            "event_id": frontmatter.get("event_id"),
            "pub_date": pub_date,
            "publication_date": pub_date,
            "reliability_tier": frontmatter.get("reliability_tier"),
            "source_type": frontmatter.get("source_type"),
            "format": frontmatter.get("format", "unknown"),
            "is_retracted": bool(frontmatter.get("is_retracted", False)),
            "retracted_by": frontmatter.get("retracted_by"),
            "is_corrected": bool(frontmatter.get("is_corrected", False)),
            "corrected_by": frontmatter.get("corrected_by"),
            "is_damaged": bool(frontmatter.get("is_damaged", False)),
            "damage_type": frontmatter.get("damage_type"),
            "is_duplicate": bool(frontmatter.get("is_duplicate", False)),
            "duplicate_of": frontmatter.get("duplicate_of"),
            "is_injection_attempt": bool(frontmatter.get("is_injection_attempt", False)),
            "links": combined_links,
            "content": body,
            "body_text": body,
        }

    @classmethod
    def load_okf_document(cls, doc_id: str, docs_dir: Optional[Path] = None) -> Optional[Dict[str, Any]]:
        """
        Loads a document directly from the OKF document directory on disk.
        Provides robust fallback for citation verification and full doc exhibit view.
        """
        dir_path = Path(docs_dir or cls.DEFAULT_OKF_DOCS_DIR)
        if not dir_path.exists():
            return None

        clean_id = doc_id.strip()
        candidates = [
            dir_path / f"{clean_id}.md",
            dir_path / f"{clean_id.upper()}.md",
            dir_path / f"{clean_id.lower()}.md",
        ]
        for p in candidates:
            if p.is_file():
                return cls.parse_okf_document(p)

        # Case-insensitive scan
        clean_lower = clean_id.lower()
        for p in dir_path.glob("*.md"):
            if p.stem.lower() == clean_lower:
                return cls.parse_okf_document(p)

        return None

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
        body = f"# Actionable Lesson ({memory.memory_type.value if hasattr(memory.memory_type, 'value') else memory.memory_type})\n\n{memory.content}\n"
        if memory.basis_refs:
            body += "\n## Basis References\n" + "\n".join(f"- [[{ref}]]" for ref in memory.basis_refs) + "\n"

        return f"---\n{yaml_str}\n---\n\n{body}"

    @classmethod
    def parse_okf_memory(cls, content_or_path: Union[str, Path]) -> MemoryRecord:
        """
        Parses an OKF memory card file or string back into a Pydantic MemoryRecord.
        """
        raw_text = ""
        if isinstance(content_or_path, Path) or (isinstance(content_or_path, str) and "\n" not in content_or_path and Path(content_or_path).is_file()):
            raw_text = Path(content_or_path).read_text(encoding="utf-8")
        else:
            raw_text = str(content_or_path)

        match = re.match(r"^---\r?\n([\s\S]*?)\r?\n---\r?\n?([\s\S]*)$", raw_text)
        if not match:
            raise ValueError("Invalid OKF memory card: missing YAML frontmatter delimiters.")

        yaml_text, body = match.group(1), match.group(2).strip()
        frontmatter = yaml.safe_load(yaml_text) or {}

        # Extract content from body
        clean_body = re.sub(r"^#\s+Actionable Lesson[^\n]*\n*", "", body, flags=re.IGNORECASE).strip()
        parts = re.split(r"\n##\s+Basis References", clean_body, flags=re.IGNORECASE)
        content = parts[0].strip()

        # Basis refs from frontmatter or body
        basis_refs = frontmatter.get("basis_refs") or []
        if len(parts) > 1 and not basis_refs:
            wiki_matches = cls.WIKI_LINK_PATTERN.findall(parts[1])
            basis_refs = list(dict.fromkeys(wiki_matches))

        return MemoryRecord(
            id=frontmatter.get("id"),
            agent_id=frontmatter.get("agent_id"),
            memory_type=MemoryType(frontmatter.get("memory_type")),
            content=content or frontmatter.get("content", "General strategy rule"),
            scope=MemoryScope(frontmatter.get("scope", "global")),
            scope_value=frontmatter.get("scope_value"),
            confidence=float(frontmatter.get("confidence", 1.0)),
            status=frontmatter.get("status", "active"),
            created_run=int(frontmatter.get("created_run", 1)),
            last_used_run=frontmatter.get("last_used_run"),
            basis_refs=basis_refs,
        )

    @classmethod
    def load_agent_memories_from_okf(
        cls,
        agent_id: str,
        memory_dir: Optional[Path] = None,
    ) -> List[MemoryRecord]:
        """
        Loads all OKF memory cards for a specific agent from disk.
        """
        base_dir = Path(memory_dir or cls.DEFAULT_OKF_MEMORY_DIR) / agent_id.lower()
        if not base_dir.exists():
            return []

        memories: List[MemoryRecord] = []
        for p in base_dir.glob("*.md"):
            try:
                memories.append(cls.parse_okf_memory(p))
            except Exception:
                pass
        return memories

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

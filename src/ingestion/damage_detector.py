import hashlib
import re
from pathlib import Path
from typing import Dict, Optional, Tuple, Set, List

from src.schemas.ingest import DocumentMetadata, DocumentDamageReport


class DamageDetector:
    """
    Deterministic trap and damage detector.
    Evaluates file integrity BEFORE chunking or vector embedding.
    Fulfills CONTEXT_UPDATED.md Section 8 and Acceptance Check 10.
    """

    MIN_TEXT_LENGTH = 20
    DUPLICATE_SIMILARITY_THRESHOLD = 0.90
    TERMINAL_PUNCTUATION = {".", "!", "?", '"', "'", "”", "’", "\n"}

    def __init__(self):
        # Maps SHA256 -> doc_id for exact copy detection
        self._exact_hashes: Dict[str, str] = {}
        # Maps doc_id -> set of 3-word shingles for near-duplicate detection
        self._doc_shingles: Dict[str, Set[Tuple[str, ...]]] = {}
        # Tracks known retractions and corrections: {target_subject_or_id: correcting_doc_id}
        self._corrections_map: Dict[str, str] = {}
        self._retractions_map: Dict[str, str] = {}

    def inspect(
        self,
        file_path: Path,
        metadata: Optional[DocumentMetadata] = None,
        raw_text: Optional[str] = None,
    ) -> DocumentDamageReport:
        """
        Inspects raw file bytes and parsed content to produce a DocumentDamageReport.
        """
        report = DocumentDamageReport()
        path = Path(file_path)

        # 1. Empty File Check (bytes & stripped length)
        if not path.is_file():
            report.is_damaged = True
            report.damage_type = "empty"
            report.quarantine_reason = f"File not found: {path.name}"
            return report

        file_size = path.stat().st_size
        if file_size == 0:
            report.is_damaged = True
            report.damage_type = "empty"
            report.quarantine_reason = "File has 0 bytes (empty file trap)"
            return report

        if raw_text is None:
            # If parser couldn't even extract text
            report.is_damaged = True
            report.damage_type = "empty"
            report.quarantine_reason = "No extractable text extracted from file"
            return report

        body = raw_text.strip()
        if len(body) < self.MIN_TEXT_LENGTH:
            report.is_damaged = True
            report.damage_type = "empty"
            report.quarantine_reason = f"Stripped text length ({len(body)} chars) is below minimum threshold (20 chars)"
            return report

        # 2. Corrupted Encoding Check
        if "\ufffd" in raw_text:
            report.is_damaged = True
            report.damage_type = "encoding"
            report.quarantine_reason = "Contains unrecoverable replacement characters (Unicode \ufffd)"
            return report

        # 3. Truncation Check
        if metadata is None:
            report.is_damaged = True
            report.damage_type = "truncated"
            report.quarantine_reason = "Header missing or invalid; publication date cannot be verified"
            return report

        # Check if text abruptly cuts off mid-sentence without terminal punctuation
        last_char = body[-1] if body else ""
        if last_char not in self.TERMINAL_PUNCTUATION:
            # Check if last word is a dangling preposition/conjunction or incomplete
            words = body.split()
            if words and len(words[-1]) > 1:
                last_word = words[-1].lower()
                dangling_markers = {"and", "the", "with", "at", "in", "of", "to", "or", "for", "as"}
                if last_word in dangling_markers or not last_char.isalnum():
                    report.is_damaged = True
                    report.damage_type = "truncated"
                    report.quarantine_reason = "Text abruptly ends mid-sentence without terminal punctuation"

        # 4. Duplicate Detection (Exact & Near-Duplicates)
        doc_id = metadata.doc_id if metadata else path.stem
        norm_text = re.sub(r"\W+", " ", body.lower()).strip()
        text_hash = hashlib.sha256(norm_text.encode("utf-8")).hexdigest()

        if text_hash in self._exact_hashes:
            canonical_id = self._exact_hashes[text_hash]
            report.is_duplicate = True
            report.duplicate_of = canonical_id
            report.quarantine_reason = f"Exact duplicate of canonical document {canonical_id}"
        else:
            # Near-duplicate shingle comparison (3-word shingles)
            words = norm_text.split()
            shingles = set(zip(words, words[1:], words[2:])) if len(words) >= 3 else set()

            if shingles:
                for existing_id, existing_shingles in self._doc_shingles.items():
                    intersection = len(shingles & existing_shingles)
                    union = len(shingles | existing_shingles)
                    if union > 0:
                        jaccard = intersection / union
                        if jaccard >= self.DUPLICATE_SIMILARITY_THRESHOLD:
                            report.is_duplicate = True
                            report.duplicate_of = existing_id
                            report.quarantine_reason = f"Near-duplicate of {existing_id} (Jaccard similarity {jaccard:.2f})"
                            break

            if not report.is_duplicate:
                self._exact_hashes[text_hash] = doc_id
                if shingles:
                    self._doc_shingles[doc_id] = shingles

        # 5. Retraction and Correction Metadata Tracking
        if metadata:
            source_type = metadata.source_type.lower()
            title = metadata.title.lower()

            if "retraction" in source_type or "retraction:" in title:
                report.is_retracted = False  # The notice itself is not retracted
                # Register retraction relationship
                match = re.search(r"\b([A-Z]{3}-\d{4})\b", metadata.title)
                if match:
                    target_id = match.group(1)
                    self._retractions_map[target_id] = doc_id

            if "correction" in source_type or "correction:" in title:
                report.is_corrected = False  # The notice itself is not corrected
                # Register correction relationship
                match = re.search(r"\b([A-Z]{3}-\d{4})\b", metadata.title)
                if match:
                    target_id = match.group(1)
                    self._corrections_map[target_id] = doc_id

            # Apply registered relationships
            if doc_id in self._retractions_map:
                report.is_retracted = True
                report.retracted_by = self._retractions_map[doc_id]
                report.quarantine_reason = f"Retracted by notice {report.retracted_by}"

            if doc_id in self._corrections_map:
                report.is_corrected = True
                report.corrected_by = self._corrections_map[doc_id]

        return report

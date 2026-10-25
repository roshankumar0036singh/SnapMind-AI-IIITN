from pathlib import Path
from typing import Tuple

from src.ingestion.parsers.base import BaseParser
from src.schemas.ingest import DocumentMetadata


class TxtParser(BaseParser):
    """
    Parser for plaintext (.txt) Runemark documents.
    Supports automatic encoding fallback (UTF-8, UTF-16, Latin-1, CP1252).
    """

    CANDIDATE_ENCODINGS = ["utf-8", "utf-8-sig", "latin-1", "cp1252", "utf-16"]

    def parse(self, file_path: Path) -> Tuple[DocumentMetadata, str]:
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")

        raw_bytes = path.read_bytes()
        text: str = ""
        decoded = False

        for enc in self.CANDIDATE_ENCODINGS:
            try:
                text = raw_bytes.decode(enc)
                decoded = True
                break
            except (UnicodeDecodeError, LookupError):
                continue

        if not decoded:
            text = raw_bytes.decode("utf-8", errors="replace")

        return self.extract_header_and_body(text, path, "TXT")

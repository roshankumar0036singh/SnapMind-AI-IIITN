from pathlib import Path
from typing import Tuple
import pypdf

from src.ingestion.parsers.base import BaseParser
from src.schemas.ingest import DocumentMetadata


class PdfParser(BaseParser):
    """
    Parser for PDF (.pdf) Runemark documents using pure-Python pypdf.
    """

    def parse(self, file_path: Path) -> Tuple[DocumentMetadata, str]:
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            reader = pypdf.PdfReader(str(path))
        except Exception as e:
            raise ValueError(f"Corrupted or unreadable PDF {path.name}: {e}")

        if len(reader.pages) == 0:
            raise ValueError(f"Empty PDF with 0 pages: {path.name}")

        page_texts = []
        for i, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text()
                if page_text:
                    page_texts.append(page_text.strip())
            except Exception as e:
                # Log error or skip corrupt page
                continue

        full_text = "\n\n".join(page_texts)
        if not full_text.strip():
            raise ValueError(f"PDF {path.name} contains no extractable text.")

        return self.extract_header_and_body(full_text, path, "PDF")

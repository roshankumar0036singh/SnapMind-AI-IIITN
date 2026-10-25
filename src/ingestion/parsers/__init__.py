from pathlib import Path
from typing import Tuple, Union, Dict, Type

from src.ingestion.parsers.base import BaseParser
from src.ingestion.parsers.txt_parser import TxtParser
from src.ingestion.parsers.pdf_parser import PdfParser
from src.ingestion.parsers.docx_parser import DocxParser
from src.schemas.ingest import DocumentMetadata

_PARSERS: Dict[str, Type[BaseParser]] = {
    ".txt": TxtParser,
    ".pdf": PdfParser,
    ".docx": DocxParser,
}


def parse_document(file_path: Union[str, Path]) -> Tuple[DocumentMetadata, str]:
    """
    Main entry point for parsing any Runemark document (PDF, TXT, DOCX).
    Automatically selects the correct parser based on file extension.
    Returns (DocumentMetadata, body_text).
    """
    path = Path(file_path)
    suffix = path.suffix.lower()

    parser_cls = _PARSERS.get(suffix)
    if not parser_cls:
        raise ValueError(f"Unsupported document format '{suffix}' for file: {path.name}")

    parser = parser_cls()
    return parser.parse(path)


__all__ = [
    "BaseParser",
    "TxtParser",
    "PdfParser",
    "DocxParser",
    "parse_document",
]

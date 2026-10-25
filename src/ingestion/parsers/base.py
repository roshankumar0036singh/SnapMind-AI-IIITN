import re
from abc import ABC, abstractmethod
from datetime import date, datetime
from pathlib import Path
from typing import Tuple, Dict, Any, Optional

from src.schemas.ingest import DocumentMetadata


class BaseParser(ABC):
    """
    Abstract base parser for Runemark documents.
    Extracts the 11-field metadata header and separates it from the body text.
    """

    HEADER_SEPARATOR = "---"

    @abstractmethod
    def parse(self, file_path: Path) -> Tuple[DocumentMetadata, str]:
        """
        Parses the document file and returns (metadata, body_text).
        Raises ValueError if header is missing or unparseable.
        """
        pass

    def extract_header_and_body(
        self, full_text: str, file_path: Path, doc_format: str
    ) -> Tuple[DocumentMetadata, str]:
        """
        Splits text by the '---' line, parses header key-values, and builds DocumentMetadata.
        """
        if self.HEADER_SEPARATOR not in full_text:
            raise ValueError(
                f"Document {file_path.name} is missing the mandatory '{self.HEADER_SEPARATOR}' header separator."
            )

        parts = full_text.split(self.HEADER_SEPARATOR, 1)
        header_text = parts[0].strip()
        body_text = parts[1].strip()

        header_dict: Dict[str, str] = {}
        for line in header_text.splitlines():
            line = line.strip()
            if not line or ":" not in line:
                continue
            key, val = line.split(":", 1)
            header_dict[key.strip().upper()] = val.strip()

        # Mandatory fields check
        required_keys = ["DOC_ID", "TITLE", "SOURCE_NAME", "SOURCE_TYPE", "RELIABILITY", "PUB_DATE", "COUNTRY", "SECTOR"]
        missing_keys = [k for k in required_keys if k not in header_dict]
        if missing_keys:
            raise ValueError(f"Document {file_path.name} header missing required fields: {missing_keys}")

        # Parse publication date
        pub_date_str = header_dict["PUB_DATE"]
        try:
            pub_date = datetime.strptime(pub_date_str, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError(f"Invalid date format in {file_path.name}: '{pub_date_str}' (expected YYYY-MM-DD)")

        # Parse reliability tier (1 to 4)
        try:
            tier = int(header_dict["RELIABILITY"])
            if tier < 1 or tier > 4:
                raise ValueError()
        except ValueError:
            raise ValueError(f"Invalid reliability tier in {file_path.name}: '{header_dict['RELIABILITY']}' (must be 1-4)")

        metadata = DocumentMetadata(
            doc_id=header_dict["DOC_ID"],
            event_id=header_dict.get("EVENT_ID", "NONE"),
            title=header_dict["TITLE"],
            source_name=header_dict["SOURCE_NAME"],
            source_type=header_dict["SOURCE_TYPE"].lower(),
            reliability_tier=tier,
            pub_date=pub_date,
            pub_time=header_dict.get("PUB_TIME"),
            country=header_dict["COUNTRY"],
            sector=header_dict["SECTOR"],
            language=header_dict.get("LANGUAGE", "en").lower(),
            file_name=file_path.name,
            format=doc_format.upper(),
        )

        return metadata, body_text

import re
from typing import List, Tuple
from src.schemas.ingest import DocumentMetadata, DocumentDamageReport, ParagraphChunk


class ParagraphChunker:
    """
    Structure-aware chunker for Runemark documents.
    Preserves exact paragraph markers ([P1], [P2], etc.) for granular citations (DOC_ID#Pn).
    Fulfills CONTEXT_UPDATED.md Section 6.
    """

    PARAGRAPH_TAG_REGEX = re.compile(r"\[P(\d+)\]\s*", re.IGNORECASE)

    def chunk_document(
        self,
        metadata: DocumentMetadata,
        body_text: str,
        damage_report: DocumentDamageReport,
    ) -> List[ParagraphChunk]:
        """
        Splits document body into ParagraphChunks keyed by DOC_ID#Pn.
        """
        body = body_text.strip()
        if not body:
            return []

        chunks: List[ParagraphChunk] = []

        # Find all [Pn] tags and their positions
        matches = list(self.PARAGRAPH_TAG_REGEX.finditer(body))

        if matches:
            preamble = body[: matches[0].start()].strip()

            for i, match in enumerate(matches):
                p_no = int(match.group(1))
                start_idx = match.end()
                end_idx = matches[i + 1].start() if i + 1 < len(matches) else len(body)
                p_text = body[start_idx:end_idx].strip()

                # If there was a preamble title before [P1], include it with [P1]
                if i == 0 and preamble:
                    p_text = f"{preamble}\n\n{p_text}"

                if p_text:
                    chunk = ParagraphChunk(
                        chunk_id=f"{metadata.doc_id}#P{p_no}",
                        doc_id=metadata.doc_id,
                        paragraph_no=p_no,
                        text=p_text,
                        metadata=metadata,
                        damage_report=damage_report,
                    )
                    chunks.append(chunk)
        else:
            # Fallback for documents without explicit [Pn] tags
            # If short (< 1500 chars), keep whole as [P1]
            if len(body) < 1500:
                chunks.append(
                    ParagraphChunk(
                        chunk_id=f"{metadata.doc_id}#P1",
                        doc_id=metadata.doc_id,
                        paragraph_no=1,
                        text=body,
                        metadata=metadata,
                        damage_report=damage_report,
                    )
                )
            else:
                # Split along double newlines
                paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
                for idx, p_text in enumerate(paragraphs, start=1):
                    chunks.append(
                        ParagraphChunk(
                            chunk_id=f"{metadata.doc_id}#P{idx}",
                            doc_id=metadata.doc_id,
                            paragraph_no=idx,
                            text=p_text,
                            metadata=metadata,
                            damage_report=damage_report,
                        )
                    )

        return chunks


_chunker = ParagraphChunker()

def get_chunker() -> ParagraphChunker:
    return _chunker

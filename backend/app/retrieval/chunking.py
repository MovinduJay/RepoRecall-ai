from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.models.raw_document import RawDocument


@dataclass
class DocumentChunk:
    raw_document_id: str
    chunk_index: int
    text: str
    metadata: dict[str, Any]


def chunk_raw_document(
    document: RawDocument,
    max_characters: int = 1200,
) -> list[DocumentChunk]:
    """
    Convert one GitHub RawDocument into smaller searchable chunks.

    This first version:
    1. Combines the title and body.
    2. Splits the body using paragraphs.
    3. Keeps each chunk below max_characters.
    """

    title = document.title.strip()
    body = document.body.strip()

    paragraphs = [
        paragraph.strip()
        for paragraph in body.split("\n\n")
        if paragraph.strip()
    ]

    chunks: list[DocumentChunk] = []
    current_parts: list[str] = []
    current_length = 0

    for paragraph in paragraphs:
        paragraph_length = len(paragraph)

        would_exceed_limit = (
            current_parts
            and current_length + paragraph_length > max_characters
        )

        if would_exceed_limit:
            chunks.append(
                _create_chunk(
                    document=document,
                    title=title,
                    body_parts=current_parts,
                    chunk_index=len(chunks),
                )
            )

            current_parts = []
            current_length = 0

        current_parts.append(paragraph)
        current_length += paragraph_length

    if current_parts or not body:
        chunks.append(
            _create_chunk(
                document=document,
                title=title,
                body_parts=current_parts,
                chunk_index=len(chunks),
            )
        )

    return chunks


def _create_chunk(
    document: RawDocument,
    title: str,
    body_parts: list[str],
    chunk_index: int,
) -> DocumentChunk:
    body_text = "\n\n".join(body_parts)

    text_parts = [
        f"Source type: {document.source_type}",
        f"Title: {title}",
    ]

    if body_text:
        text_parts.append(f"Content:\n{body_text}")

    text = "\n\n".join(text_parts)

    metadata = {
        "repository_id": str(document.repository_id),
        "source_type": document.source_type,
        "source_id": document.source_id,
        "source_number": document.source_number,
        "title": document.title,
        "html_url": document.html_url,
        "author": document.author,
        "state": document.state,
        "chunk_index": chunk_index,
    }

    return DocumentChunk(
        raw_document_id=str(document.id),
        chunk_index=chunk_index,
        text=text,
        metadata=metadata,
    )
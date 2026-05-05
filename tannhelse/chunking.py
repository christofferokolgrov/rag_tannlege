import hashlib
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    document: str
    source_path: str
    content_hash: str
    chunk_index: int
    section_path: str
    section_label: str
    page_start: int
    page_end: int
    text: str


def _make_chunk_id(content_hash: str, chunk_index: int) -> str:
    return hashlib.sha256(f"{content_hash}:{chunk_index}".encode()).hexdigest()[:32]


def chunk_spans(
    spans, *, document: str, source_path: str, content_hash: str
) -> Iterable[Chunk]:
    """Tracer-bullet chunker: one Chunk per span, no token windowing."""
    for index, span in enumerate(spans):
        yield Chunk(
            chunk_id=_make_chunk_id(content_hash, index),
            document=document,
            source_path=source_path,
            content_hash=content_hash,
            chunk_index=index,
            section_path=span.section_path,
            section_label=span.section_label,
            page_start=span.page,
            page_end=span.page,
            text=span.text,
        )

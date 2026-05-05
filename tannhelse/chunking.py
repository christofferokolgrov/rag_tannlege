import hashlib
import re
from dataclasses import dataclass
from typing import Iterable

import tiktoken

from tannhelse.config import (
    CHUNK_MAX_TOKENS,
    CHUNK_OVERLAP_TOKENS,
    CHUNK_SIZE_TOKENS,
)

_SENTENCE_BREAK_RE = re.compile(r"(?<=[.?!])\s+(?=[A-ZÆØÅ])")
_ABBREVIATIONS = ("f.eks.", "bl.a.", "pkt.", "dvs.", "mv.")
_ENCODER = tiktoken.get_encoding("cl100k_base")


def split_sentences(text):
    parts = [p.strip() for p in _SENTENCE_BREAK_RE.split(text) if p.strip()]
    merged: list[str] = []
    for part in parts:
        if merged and merged[-1].endswith(_ABBREVIATIONS):
            merged[-1] = f"{merged[-1]} {part}"
        else:
            merged.append(part)
    return merged


def count_tokens(text: str) -> int:
    return len(_ENCODER.encode(text))


@dataclass(frozen=True)
class SectionGroup:
    section_path: str
    section_label: str
    text: str
    page_start: int
    page_end: int


def group_spans_by_section(spans):
    groups: list[SectionGroup] = []
    buffer_texts: list[str] = []
    cur_path = cur_label = None
    cur_start = cur_end = None

    def flush():
        if buffer_texts:
            groups.append(
                SectionGroup(
                    section_path=cur_path,
                    section_label=cur_label,
                    text="\n".join(buffer_texts),
                    page_start=cur_start,
                    page_end=cur_end,
                )
            )

    for span in spans:
        if span.section_path != cur_path:
            flush()
            buffer_texts = [span.text]
            cur_path = span.section_path
            cur_label = span.section_label
            cur_start = span.page
            cur_end = span.page
        else:
            buffer_texts.append(span.text)
            cur_end = span.page
    flush()
    return groups


def window_section(text, target=600, max_=900, overlap=100):
    sentences = split_sentences(text)
    if not sentences:
        return []
    sizes = [count_tokens(s) for s in sentences]
    if sum(sizes) <= target:
        return [" ".join(sentences)]

    chunks: list[str] = []
    i = 0
    while i < len(sentences):
        running = 0
        j = i
        while j < len(sentences) and running + sizes[j] <= target:
            running += sizes[j]
            j += 1
        if j == i:
            j = i + 1
        chunks.append(" ".join(sentences[i:j]))
        if j >= len(sentences):
            break

        back = j
        back_tokens = 0
        while back > i + 1 and back_tokens < overlap:
            back -= 1
            back_tokens += sizes[back]
        i = back
    return chunks


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
    groups = group_spans_by_section(list(spans))
    chunk_index = 0
    for group in groups:
        windows = window_section(
            group.text,
            target=CHUNK_SIZE_TOKENS,
            max_=CHUNK_MAX_TOKENS,
            overlap=CHUNK_OVERLAP_TOKENS,
        )
        for window_text in windows:
            yield Chunk(
                chunk_id=_make_chunk_id(content_hash, chunk_index),
                document=document,
                source_path=source_path,
                content_hash=content_hash,
                chunk_index=chunk_index,
                section_path=group.section_path,
                section_label=group.section_label,
                page_start=group.page_start,
                page_end=group.page_end,
                text=window_text,
            )
            chunk_index += 1

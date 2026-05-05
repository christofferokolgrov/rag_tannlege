from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import fitz


@dataclass(frozen=True)
class ParsedSpan:
    text: str
    page: int
    section_path: str
    section_label: str


def parse_pdf(path: Path) -> Iterable[ParsedSpan]:
    """Tracer-bullet parser: one span per page, no heading detection."""
    with fitz.open(path) as doc:
        for page_index, page in enumerate(doc, start=1):
            text = page.get_text("text").strip()
            if not text:
                continue
            yield ParsedSpan(
                text=text,
                page=page_index,
                section_path="",
                section_label=f"s. {page_index}",
            )

import re
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import fitz

_NUMERIC_HEADING_RE = re.compile(r"^(\d+(?:\.\d+)*)\s+\S")
_TOC_DOT_LEADER_RE = re.compile(r"\.{3,}")
_BOLD_SHORT_MAX_WORDS = 8
_FONT_HEADING_RATIO = 1.15
_FITZ_BOLD_FLAG = 16
_SENTENCE_TERMINATORS = (".", "!", "?")
_TOC_PAGE_HEADING_FRACTION = 0.6
_TOC_PAGE_MIN_LINES = 8

_NO_HEADING_LABEL = "(uten kapitteltittel)"


def numeric_heading_path(text):
    match = _NUMERIC_HEADING_RE.match(text)
    if not match:
        return None
    parts = match.group(1).split(".")
    return [".".join(parts[: i + 1]) for i in range(len(parts))]


_HAS_ALPHA_RE = re.compile(r"[A-Za-zÆØÅæøå]")


def is_heading(text, font_size, bold, page_median):
    if _TOC_DOT_LEADER_RE.search(text):
        return False
    if not _HAS_ALPHA_RE.search(text):
        return False
    # Hyphen-terminated lines are mid-word continuations, not section labels.
    if text.rstrip().endswith("-"):
        return False
    if numeric_heading_path(text) is not None:
        # Footnote bodies (smaller font) start with a digit too; only treat
        # numeric-prefixed lines as headings when they're at least as large
        # as the page's median text size.
        return font_size >= page_median
    if font_size > page_median * _FONT_HEADING_RATIO:
        return True
    if (
        bold
        and len(text.split()) <= _BOLD_SHORT_MAX_WORDS
        and not text.rstrip().endswith(_SENTENCE_TERMINATORS)
    ):
        return True
    return False


def section_for_heading(text):
    path = numeric_heading_path(text)
    if path is not None:
        return "/".join(path), f"Kap. {text}"
    return text, text


def is_toc_page(lines: list[tuple[str, float, bool]], page_median: float) -> bool:
    """A TOC page has many heading-shaped lines and few body-text lines.

    Used to suppress heading detection on TOC pages, where wrapped entries
    like "Utvalgets mandat," and "finansering av tannhelse-" otherwise
    trigger the font heuristic and produce hundreds of spurious sections.
    """
    if len(lines) < _TOC_PAGE_MIN_LINES:
        return False
    candidates = sum(
        1 for text, size, bold in lines if is_heading(text, size, bold, page_median)
    )
    return candidates / len(lines) >= _TOC_PAGE_HEADING_FRACTION


@dataclass(frozen=True)
class ParsedSpan:
    text: str
    page: int
    section_path: str
    section_label: str


def _extract_lines(page) -> list[tuple[str, float, bool]]:
    """Return (text, max_font_size, any_bold) per line on the page."""
    out: list[tuple[str, float, bool]] = []
    for block in page.get_text("dict")["blocks"]:
        if block.get("type", 0) != 0:
            continue
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            text = "".join(s["text"] for s in spans).strip()
            if not text:
                continue
            sizes = [s["size"] for s in spans] or [0.0]
            bold = any(s.get("flags", 0) & _FITZ_BOLD_FLAG for s in spans)
            out.append((text, max(sizes), bold))
    return out


def parse_pdf(path: Path) -> Iterable[ParsedSpan]:
    section_path = ""
    section_label = _NO_HEADING_LABEL
    saw_any_text = False

    with fitz.open(path) as doc:
        for page_index, page in enumerate(doc, start=1):
            lines = _extract_lines(page)
            if not lines:
                continue
            saw_any_text = True

            page_median = statistics.median(size for _, size, _ in lines)
            buffer: list[str] = []

            def flush() -> Iterable[ParsedSpan]:
                if buffer:
                    yield ParsedSpan(
                        text="\n".join(buffer),
                        page=page_index,
                        section_path=section_path,
                        section_label=section_label,
                    )

            if is_toc_page(lines, page_median):
                # TOC pages: keep text as body under the current section,
                # don't promote any line to a heading.
                for text, _size, _bold in lines:
                    buffer.append(text)
            else:
                for text, size, bold in lines:
                    if is_heading(text, size, bold, page_median):
                        yield from flush()
                        buffer.clear()
                        section_path, section_label = section_for_heading(text)
                    else:
                        buffer.append(text)

            yield from flush()

    if not saw_any_text:
        raise ValueError(
            f"No extractable text in {path.name} — image-only PDF? "
            "Run OCR (e.g. tesseract with Norwegian language pack) before ingesting."
        )

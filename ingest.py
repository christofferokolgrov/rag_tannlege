import hashlib
import json
import re
import sys
from pathlib import Path

import fitz

from tannhelse.chunking import chunk_spans
from tannhelse.config import DB_PATH, DOCS_DIR, DOCS_YAML
from tannhelse.docs_yaml import load_overrides
from tannhelse.embedding import embed_texts
from tannhelse.parsing import parse_pdf
from tannhelse.store import Store

_FILENAME_CLEAN_RE = re.compile(r"[_\-]+")
_WHITESPACE_RE = re.compile(r"\s+")


def _clean_filename_stem(stem: str) -> str:
    cleaned = _FILENAME_CLEAN_RE.sub(" ", stem)
    return _WHITESPACE_RE.sub(" ", cleaned).strip()


def _pdf_metadata_title(path: Path) -> str:
    try:
        with fitz.open(path) as doc:
            return (doc.metadata.get("title") or "").strip()
    except Exception:
        return ""


def _document_title(path: Path, override: dict[str, str]) -> str:
    """Resolve the `short_title` (stored in chunks.document).

    Order: docs.yaml short_title → PDF metadata title → cleaned filename stem.
    """
    short = (override.get("short_title") or "").strip()
    if short:
        return short
    meta = _pdf_metadata_title(path)
    if meta:
        return meta
    return _clean_filename_stem(path.stem)


def _content_hash(path: Path, override: dict[str, str]) -> str:
    file_bytes = path.read_bytes()
    entry_blob = json.dumps(override, sort_keys=True).encode("utf-8")
    return hashlib.sha256(file_bytes + b"\n" + entry_blob).hexdigest()


def _ingest_one(
    path: Path, store: Store, override: dict[str, str], chash: str
) -> int:
    document = _document_title(path, override)
    language = override.get("language", "no")
    spans = list(parse_pdf(path))
    chunks = list(
        chunk_spans(
            spans,
            document=document,
            source_path=str(path),
            content_hash=chash,
            language=language,
        )
    )
    if not chunks:
        store.replace_for_source_path(str(path), [], [])
        return 0
    texts = [
        f"{c.document} — {c.section_label}\n\n{c.text}" for c in chunks
    ]
    embeddings = embed_texts(texts)
    store.replace_for_source_path(str(path), chunks, embeddings)
    return len(chunks)


def _prune_orphans(store: Store, on_disk: set[str]) -> None:
    for _document, source_path in store.list_documents():
        if source_path not in on_disk:
            store.delete_by_source_path(source_path)
            print(f"  removed (orphaned): {Path(source_path).name}")


def main() -> int:
    if not DOCS_DIR.exists():
        print(f"docs dir not found: {DOCS_DIR}", file=sys.stderr)
        return 1

    # Load overrides up front so a malformed docs.yaml fails before we touch
    # any PDFs (per spec: clear error, not silent skip).
    overrides = load_overrides(DOCS_YAML)

    pdfs = sorted(DOCS_DIR.rglob("*.pdf"))
    on_disk = {str(p) for p in pdfs}

    store = Store(DB_PATH)
    try:
        _prune_orphans(store, on_disk)

        if not pdfs:
            print(f"no PDFs in {DOCS_DIR}")
            return 0

        for pdf in pdfs:
            try:
                entry = overrides.get(pdf.name, {})
                chash = _content_hash(pdf, entry)
                if store.existing_content_hash(str(pdf)) == chash:
                    print(f"  skipped (unchanged): {pdf.name}")
                    continue
                n = _ingest_one(pdf, store, entry, chash)
                print(f"  {pdf.name}: {n} chunks")
            except Exception as e:
                print(f"  {pdf.name}: FAILED ({e})", file=sys.stderr)
    finally:
        store.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

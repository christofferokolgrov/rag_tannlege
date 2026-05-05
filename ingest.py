import hashlib
import sys
from pathlib import Path

from tannhelse.chunking import chunk_spans
from tannhelse.config import DB_PATH, DOCS_DIR
from tannhelse.embedding import embed_texts
from tannhelse.parsing import parse_pdf
from tannhelse.store import Store


def _document_title(path: Path) -> str:
    return path.stem


def _content_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ingest_one(path: Path, store: Store) -> int:
    document = _document_title(path)
    chash = _content_hash(path)
    spans = list(parse_pdf(path))
    chunks = list(
        chunk_spans(
            spans,
            document=document,
            source_path=str(path),
            content_hash=chash,
        )
    )
    if not chunks:
        return 0
    texts = [
        f"{c.document} — {c.section_label}\n\n{c.text}" for c in chunks
    ]
    embeddings = embed_texts(texts)
    store.upsert_chunks(chunks, embeddings)
    return len(chunks)


def main() -> int:
    if not DOCS_DIR.exists():
        print(f"docs dir not found: {DOCS_DIR}", file=sys.stderr)
        return 1

    pdfs = sorted(DOCS_DIR.rglob("*.pdf"))
    if not pdfs:
        print(f"no PDFs in {DOCS_DIR}")
        return 0

    store = Store(DB_PATH)
    try:
        for pdf in pdfs:
            try:
                n = _ingest_one(pdf, store)
                print(f"  {pdf.name}: {n} chunks")
            except Exception as e:
                print(f"  {pdf.name}: FAILED ({e})", file=sys.stderr)
    finally:
        store.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

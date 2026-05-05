import sqlite3
import struct
from pathlib import Path
from typing import Iterable

import sqlite_vec

from tannhelse.chunking import Chunk
from tannhelse.config import EMBEDDING_DIM


def _serialize_vector(vec: list[float]) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec)


def _build_fts_query(query: str) -> str:
    tokens = []
    for word in query.split():
        cleaned = "".join(c for c in word if c.isalnum() or c == "-")
        if cleaned:
            tokens.append(f'"{cleaned}"')
    return " OR ".join(tokens)


class Store:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.enable_load_extension(True)
        sqlite_vec.load(self._conn)
        self._conn.enable_load_extension(False)
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.executescript(
            f"""
            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id TEXT PRIMARY KEY,
                document TEXT NOT NULL,
                source_path TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                section_path TEXT NOT NULL,
                section_label TEXT NOT NULL,
                page_start INTEGER NOT NULL,
                page_end INTEGER NOT NULL,
                text TEXT NOT NULL
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS vec_chunks USING vec0(
                chunk_id TEXT PRIMARY KEY,
                embedding float[{EMBEDDING_DIM}]
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                chunk_id UNINDEXED,
                text,
                tokenize = 'unicode61 remove_diacritics 0'
            );
            """
        )
        self._conn.commit()

    def upsert_chunks(
        self, chunks: Iterable[Chunk], embeddings: list[list[float]]
    ) -> None:
        chunk_list = list(chunks)
        assert len(chunk_list) == len(embeddings)
        with self._conn:
            for chunk, vec in zip(chunk_list, embeddings):
                self._conn.execute(
                    """
                    INSERT OR REPLACE INTO chunks
                    (chunk_id, document, source_path, content_hash, chunk_index,
                     section_path, section_label, page_start, page_end, text)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        chunk.chunk_id,
                        chunk.document,
                        chunk.source_path,
                        chunk.content_hash,
                        chunk.chunk_index,
                        chunk.section_path,
                        chunk.section_label,
                        chunk.page_start,
                        chunk.page_end,
                        chunk.text,
                    ),
                )
                self._conn.execute(
                    "INSERT OR REPLACE INTO vec_chunks (chunk_id, embedding) VALUES (?, ?)",
                    (chunk.chunk_id, _serialize_vector(vec)),
                )
                self._conn.execute(
                    "DELETE FROM chunks_fts WHERE chunk_id = ?",
                    (chunk.chunk_id,),
                )
                self._conn.execute(
                    "INSERT INTO chunks_fts (chunk_id, text) VALUES (?, ?)",
                    (chunk.chunk_id, chunk.text),
                )

    def dense_search(self, query_vec: list[float], k: int) -> list[Chunk]:
        rows = self._conn.execute(
            """
            SELECT c.chunk_id, c.document, c.source_path, c.content_hash, c.chunk_index,
                   c.section_path, c.section_label, c.page_start, c.page_end, c.text
            FROM vec_chunks v
            JOIN chunks c ON c.chunk_id = v.chunk_id
            WHERE v.embedding MATCH ? AND k = ?
            ORDER BY v.distance
            """,
            (_serialize_vector(query_vec), k),
        ).fetchall()
        return [Chunk(*row) for row in rows]

    def bm25_search(self, query: str, k: int) -> list[Chunk]:
        fts_query = _build_fts_query(query)
        if not fts_query:
            return []
        rows = self._conn.execute(
            """
            SELECT c.chunk_id, c.document, c.source_path, c.content_hash, c.chunk_index,
                   c.section_path, c.section_label, c.page_start, c.page_end, c.text
            FROM chunks_fts f
            JOIN chunks c ON c.chunk_id = f.chunk_id
            WHERE f.text MATCH ?
            ORDER BY bm25(chunks_fts)
            LIMIT ?
            """,
            (fts_query, k),
        ).fetchall()
        return [Chunk(*row) for row in rows]

    def fts_count(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM chunks_fts").fetchone()[0]

    def list_documents(self) -> list[tuple[str, str]]:
        rows = self._conn.execute(
            "SELECT DISTINCT document, source_path FROM chunks ORDER BY document"
        ).fetchall()
        return [(d, p) for d, p in rows]

    def count_chunks(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]

    def close(self) -> None:
        self._conn.close()

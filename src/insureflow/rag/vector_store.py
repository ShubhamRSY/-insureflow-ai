from __future__ import annotations

import logging
import math
import re
from abc import ABC, abstractmethod
from typing import Any

from insureflow.rag.guidelines import Guideline

logger = logging.getLogger(__name__)

_DEFAULT_COLLECTION = "guideline_embeddings"


def _sql_ident(name: str) -> str:
    cleaned = "".join(c for c in (name or "") if c.isalnum() or c == "_")
    return cleaned or _DEFAULT_COLLECTION


class VectorStore(ABC):
    @abstractmethod
    def index_guidelines(self, guidelines: list[Guideline]) -> None: ...

    @abstractmethod
    def search(self, query: str, top_k: int = 5) -> list[tuple[Guideline, float]]: ...

    @abstractmethod
    def clear(self) -> None: ...


class InMemoryVectorStore(VectorStore):
    def __init__(self) -> None:
        self._guidelines: list[Guideline] = []
        self._vectors: dict[str, list[float]] = {}

    def index_guidelines(self, guidelines: list[Guideline]) -> None:
        self._guidelines = guidelines
        for g in guidelines:
            self._vectors[g.id] = self._embed(g)

    def search(self, query: str, top_k: int = 5) -> list[tuple[Guideline, float]]:
        if not self._guidelines:
            return []
        query_vec = self._embed_query(query)
        scored: list[tuple[Guideline, float]] = []
        for g in self._guidelines:
            vec = self._vectors.get(g.id, self._embed(g))
            sim = self._cosine_similarity(query_vec, vec)
            scored.append((g, sim))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def clear(self) -> None:
        self._guidelines.clear()
        self._vectors.clear()

    def _embed(self, guideline: Guideline) -> list[float]:
        return self._tfidf_vector(f"{guideline.title} {guideline.content} {' '.join(guideline.keywords)}")

    def _embed_query(self, query: str) -> list[float]:
        return self._tfidf_vector(query)

    def _tfidf_vector(self, text: str) -> list[float]:
        cleaned = re.sub(r"[^a-z0-9]", "", text.lower())
        ngrams: list[str] = []
        for i in range(len(cleaned) - 2):
            ngrams.append(cleaned[i : i + 3])
        vec = [0.0] * 512
        for ng in ngrams:
            hashed = hash(ng) % 512
            vec[hashed] = vec[hashed] + 1.0
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(x * x for x in b))
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)


class PgVectorStore(VectorStore):
    def __init__(
        self,
        connection_string: str,
        collection_name: str = _DEFAULT_COLLECTION,
    ) -> None:
        self._conn_str = connection_string
        self._collection = _sql_ident(collection_name)
        self._conn: Any = None
        self._openai_client: Any = None

    def _ensure_connected(self) -> None:
        if self._conn is not None:
            return
        try:
            import psycopg2
            from pgvector.psycopg2 import register_vector

            self._conn = psycopg2.connect(self._conn_str, connect_timeout=3)
            register_vector(self._conn)
            cur = self._conn.cursor()
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {self._collection} (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    category TEXT NOT NULL,
                    source TEXT NOT NULL,
                    keywords TEXT[] NOT NULL,
                    risk_impact TEXT NOT NULL,
                    version TEXT NOT NULL DEFAULT '1.0',
                    status TEXT NOT NULL DEFAULT 'active',
                    effective_date TIMESTAMPTZ,
                    expiration_date TIMESTAMPTZ,
                    supersedes TEXT NOT NULL DEFAULT '',
                    states TEXT[] NOT NULL DEFAULT '{{}}',
                    pricing_rule_codes TEXT[] NOT NULL DEFAULT '{{}}',
                    embedding vector(1536)
                )
            """)
            for col, ddl in (
                ("version", "TEXT NOT NULL DEFAULT '1.0'"),
                ("status", "TEXT NOT NULL DEFAULT 'active'"),
                ("effective_date", "TIMESTAMPTZ"),
                ("expiration_date", "TIMESTAMPTZ"),
                ("supersedes", "TEXT NOT NULL DEFAULT ''"),
                ("states", "TEXT[] NOT NULL DEFAULT '{}'"),
                ("pricing_rule_codes", "TEXT[] NOT NULL DEFAULT '{}'"),
            ):
                cur.execute(f"ALTER TABLE {self._collection} ADD COLUMN IF NOT EXISTS {col} {ddl}")
            self._conn.commit()
            try:
                cur.execute(
                    f"CREATE INDEX IF NOT EXISTS {self._collection}_hnsw "
                    f"ON {self._collection} USING hnsw (embedding vector_cosine_ops)"
                )
                self._conn.commit()
            except Exception as exc:
                logger.debug("HNSW index skipped: %s", exc)
                self._conn.rollback()
            cur.close()
        except Exception as exc:
            logger.error("PgVectorStore connection failed: %s", exc)
            raise

    def index_guidelines(self, guidelines: list[Guideline]) -> None:
        self._ensure_connected()
        cur = self._conn.cursor()
        for g in guidelines:
            emb = self._get_embedding(f"{g.title} {g.content}")
            cur.execute(
                f"""
                INSERT INTO {self._collection} (
                    id, title, content, category, source, keywords, risk_impact,
                    version, status, effective_date, expiration_date, supersedes,
                    states, pricing_rule_codes, embedding
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    title = EXCLUDED.title,
                    content = EXCLUDED.content,
                    version = EXCLUDED.version,
                    status = EXCLUDED.status,
                    effective_date = EXCLUDED.effective_date,
                    expiration_date = EXCLUDED.expiration_date,
                    supersedes = EXCLUDED.supersedes,
                    states = EXCLUDED.states,
                    pricing_rule_codes = EXCLUDED.pricing_rule_codes,
                    embedding = EXCLUDED.embedding
            """,
                (
                    g.id,
                    g.title,
                    g.content,
                    g.category.value,
                    g.source.value,
                    g.keywords,
                    g.risk_impact,
                    g.version,
                    g.status.value,
                    g.effective_date,
                    g.expiration_date,
                    g.supersedes,
                    g.states,
                    g.pricing_rule_codes,
                    emb,
                ),
            )
        self._conn.commit()
        cur.close()

    def search(self, query: str, top_k: int = 5) -> list[tuple[Guideline, float]]:
        self._ensure_connected()
        query_vec = self._get_embedding(query)
        cur = self._conn.cursor()
        cur.execute(
            f"""
            SELECT id, title, content, category, source, keywords, risk_impact,
                   version, status, effective_date, expiration_date, supersedes,
                   states, pricing_rule_codes,
                   1 - (embedding <=> %s::vector) AS similarity
            FROM {self._collection}
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """,
            (query_vec, query_vec, top_k),
        )
        results: list[tuple[Guideline, float]] = []
        for row in cur.fetchall():
            g = Guideline(
                id=row[0],
                title=row[1],
                content=row[2],
                category=row[3],
                source=row[4],
                keywords=list(row[5]),
                risk_impact=row[6],
                version=row[7],
                status=row[8],
                effective_date=row[9],
                expiration_date=row[10],
                supersedes=row[11],
                states=list(row[12] or []),
                pricing_rule_codes=list(row[13] or []),
            )
            results.append((g, float(row[14])))
        cur.close()
        return results

    def clear(self) -> None:
        self._ensure_connected()
        cur = self._conn.cursor()
        cur.execute(f"DELETE FROM {self._collection}")
        self._conn.commit()
        cur.close()

    def _get_embedding(self, text: str) -> list[float]:
        from insureflow.llm.embeddings import embed_text

        return embed_text(text)


def get_vector_store(database_url: str | None = None) -> VectorStore:
    """Postgres + pgvector when DATABASE_URL is set; otherwise in-memory.

    This is the product vector DB — not Pinecone, Weaviate, or Qdrant.
    """
    import os

    url = (database_url if database_url is not None else os.getenv("DATABASE_URL", "")).strip()
    if not url.lower().startswith("postgres"):
        return InMemoryVectorStore()
    try:
        store = PgVectorStore(url)
        store._ensure_connected()
        return store
    except Exception as exc:
        logger.warning("pgvector unavailable (%s) — in-memory guideline vectors", exc)
        return InMemoryVectorStore()

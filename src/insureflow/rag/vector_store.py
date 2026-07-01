from __future__ import annotations

import logging
import math
import re
from abc import ABC, abstractmethod
from typing import Any

from insureflow.rag.guidelines import Guideline

logger = logging.getLogger(__name__)


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
        return self._tfidf_vector(
            f"{guideline.title} {guideline.content} {' '.join(guideline.keywords)}"
        )

    def _embed_query(self, query: str) -> list[float]:
        return self._tfidf_vector(query)

    def _tfidf_vector(self, text: str) -> list[float]:
        cleaned = re.sub(r"[^a-z0-9]", "", text.lower())
        ngrams: list[str] = []
        for i in range(len(cleaned) - 2):
            ngrams.append(cleaned[i:i+3])
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
        collection_name: str = "underwriting_guidelines",
    ) -> None:
        self._conn_str = connection_string
        self._collection = collection_name
        self._conn: Any = None
        self._openai_client: Any = None

    def _ensure_connected(self) -> None:
        if self._conn is not None:
            return
        try:
            import psycopg2
            from pgvector.psycopg2 import register_vector

            self._conn = psycopg2.connect(self._conn_str)
            register_vector(self._conn)
            cur = self._conn.cursor()
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {self._collection} (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    category TEXT NOT NULL,
                    source TEXT NOT NULL,
                    keywords TEXT[] NOT NULL,
                    risk_impact TEXT NOT NULL,
                    embedding vector(1536)
                )
            """)
            self._conn.commit()
            cur.close()
        except Exception as exc:
            logger.error("PgVectorStore connection failed: %s", exc)
            raise

    def index_guidelines(self, guidelines: list[Guideline]) -> None:
        self._ensure_connected()
        cur = self._conn.cursor()
        for g in guidelines:
            emb = self._get_embedding(f"{g.title} {g.content}")
            cur.execute(f"""
                INSERT INTO {self._collection} (id, title, content, category, source, keywords, risk_impact, embedding)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    title = EXCLUDED.title,
                    content = EXCLUDED.content,
                    embedding = EXCLUDED.embedding
            """, (
                g.id, g.title, g.content, g.category.value, g.source.value,
                g.keywords, g.risk_impact, emb,
            ))
        self._conn.commit()
        cur.close()

    def search(self, query: str, top_k: int = 5) -> list[tuple[Guideline, float]]:
        self._ensure_connected()
        query_vec = self._get_embedding(query)
        cur = self._conn.cursor()
        cur.execute(f"""
            SELECT id, title, content, category, source, keywords, risk_impact,
                   1 - (embedding <=> %s::vector) AS similarity
            FROM {self._collection}
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """, (query_vec, query_vec, top_k))
        results: list[tuple[Guideline, float]] = []
        for row in cur.fetchall():
            g = Guideline(
                id=row[0], title=row[1], content=row[2],
                category=row[3], source=row[4], keywords=list(row[5]),
                risk_impact=row[6],
            )
            results.append((g, float(row[7])))
        cur.close()
        return results

    def clear(self) -> None:
        self._ensure_connected()
        cur = self._conn.cursor()
        cur.execute(f"DELETE FROM {self._collection}")
        self._conn.commit()
        cur.close()

    def _get_embedding(self, text: str) -> list[float]:
        try:
            from openai import OpenAI
            client = OpenAI()
            resp = client.embeddings.create(
                model="text-embedding-3-small",
                input=text[:8000],
            )
            return resp.data[0].embedding
        except Exception:
            return [0.0] * 1536

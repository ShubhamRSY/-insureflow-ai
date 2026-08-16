from __future__ import annotations

import logging
import math
import os
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
                cur.execute(f"CREATE INDEX IF NOT EXISTS {self._collection}_hnsw ON {self._collection} USING hnsw (embedding vector_cosine_ops)")
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


class ChromaVectorStore(VectorStore):
    """ChromaDB backend — enabled when ``CHROMA_PERSIST_DIR`` is set.

    Uses a local ``PersistentClient`` (EphemeralClient when the dir is empty)
    with cosine space. Guidelines are serialized as JSON metadata so every
    field survives a round trip.
    """

    def __init__(self, persist_dir: str, collection_name: str = _DEFAULT_COLLECTION) -> None:
        self._persist_dir = persist_dir
        self._collection_name = _sql_ident(collection_name)
        self._client: Any = None
        self._collection: Any = None
        self._ids: set[str] = set()

    def _ensure_collection(self) -> Any:
        if self._collection is not None:
            return self._collection
        import chromadb

        if self._persist_dir:
            self._client = chromadb.PersistentClient(path=self._persist_dir)
        else:
            self._client = chromadb.EphemeralClient()
        self._collection = self._client.get_or_create_collection(
            name=self._collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        return self._collection

    def index_guidelines(self, guidelines: list[Guideline]) -> None:
        if not guidelines:
            return
        col = self._ensure_collection()
        col.upsert(
            ids=[g.id for g in guidelines],
            embeddings=[self._embed(f"{g.title} {g.content}") for g in guidelines],
            documents=[g.content for g in guidelines],
            metadatas=[self._meta(g) for g in guidelines],
        )
        self._ids.update(g.id for g in guidelines)

    def search(self, query: str, top_k: int = 5) -> list[tuple[Guideline, float]]:
        col = self._ensure_collection()
        try:
            result = col.query(query_embeddings=[self._embed(query)], n_results=max(top_k, 1))
        except Exception:
            count = col.count()
            if count == 0:
                return []
            result = col.query(query_embeddings=[self._embed(query)], n_results=count)
        scored: list[tuple[Guideline, float]] = []
        for meta, distance in zip(result.get("metadatas", [[]])[0] or [], result.get("distances", [[]])[0] or []):
            raw = meta.get("json") if meta else None
            if not raw:
                continue
            g = Guideline.model_validate_json(raw)
            sim = 1.0 - float(distance)
            scored.append((g, max(0.0, min(sim, 1.0))))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def clear(self) -> None:
        col = self._ensure_collection()
        if self._ids:
            col.delete(ids=list(self._ids))
            self._ids.clear()

    @staticmethod
    def _meta(g: Guideline) -> dict[str, Any]:
        return {"json": g.model_dump_json()}

    @staticmethod
    def _embed(text: str) -> list[float]:
        from insureflow.llm.embeddings import embed_text

        return embed_text(text)


class WeaviateVectorStore(VectorStore):
    """Weaviate backend — enabled when ``WEAVIATE_URL`` is set.

    Best-effort: supports the v4 client (``connect_to_custom``) and falls back
    to the v3 ``weaviate.Client``. Never raises at selection time; any failure
    degrades to in-memory.
    """

    def __init__(self, url: str, collection_name: str = _DEFAULT_COLLECTION) -> None:
        self._url = url
        self._collection_name = _sql_ident(collection_name)
        self._client: Any = None
        self._v4 = False

    def _connect(self) -> Any:
        if self._client is not None:
            return self._client
        import weaviate

        auth = None
        if os.getenv("WEAVIATE_API_KEY"):
            from weaviate.auth import AuthApiKey

            auth = AuthApiKey(os.getenv("WEAVIATE_API_KEY"))
        try:  # v4 client
            from weaviate.config import ConnectionConfig

            params = ConnectionConfig.from_url(self._url)
            self._client = weaviate.connect_to_custom(params, auth_client_secret=auth)
            self._v4 = True
        except Exception:
            self._client = weaviate.Client(url=self._url)  # v3 client
        return self._client

    def _ensure_collection(self) -> Any:
        client = self._connect()
        if self._v4:
            if client.collections.exists(self._collection_name):
                return client.collections.get(self._collection_name)
            return client.collections.create(self._collection_name)
        try:
            client.schema.get(self._collection_name)
        except Exception:
            client.schema.create_class({"class": self._collection_name})
        return client

    @staticmethod
    def _embed(text: str) -> list[float]:
        from insureflow.llm.embeddings import embed_text

        return embed_text(text)

    def index_guidelines(self, guidelines: list[Guideline]) -> None:
        if not guidelines:
            return
        col = self._ensure_collection()
        if self._v4:
            col.data.insert_many([{**_properties(g), "vector": self._embed(f"{g.title} {g.content}")} for g in guidelines])
        else:
            for g in guidelines:
                col.data_object.create(**_properties(g), vector=self._embed(f"{g.title} {g.content}"))

    def search(self, query: str, top_k: int = 5) -> list[tuple[Guideline, float]]:
        col = self._ensure_collection()
        vec = self._embed(query)
        if self._v4:
            response = col.query.near_vector(near_vector=vec, limit=top_k, return_metadata=["distance"])
            items = response.objects
            scored = []
            for obj in items:
                g = Guideline.model_validate_json(obj.properties["json"])
                scored.append((g, max(0.0, 1.0 - float(getattr(obj.metadata, "distance", 0.0)))))
        else:
            query_result = col.query.get(self._collection_name, _FIELDS).with_near_vector({"vector": vec}).with_limit(top_k).do()
            data = query_result.get("data", {}).get("Get", {}).get(self._collection_name, [])
            scored = []
            for item in data:
                g = Guideline.model_validate_json(item.pop("json"))
                scored.append((g, 1.0 - float(item.get("_additional", {}).get("distance", 0.0))))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def clear(self) -> None:
        col = self._ensure_collection()
        if self._v4:
            col.data.delete_many(where={})
        else:
            col.data_object.delete_by_id(id="*")


_FIELDS = "title content category source risk_impact version status json"


def _properties(g: Guideline) -> dict[str, Any]:
    return {
        "title": g.title,
        "content": g.content,
        "category": g.category.value,
        "source": g.source.value,
        "risk_impact": g.risk_impact,
        "version": g.version,
        "status": g.status.value,
        "json": g.model_dump_json(),
    }


def get_vector_store(database_url: str | None = None) -> VectorStore:
    """Vector backend selection: Chroma → Weaviate → Postgres/pgvector → in-memory.

    This is the product vector DB — Chroma/Weaviate only when explicitly
    configured via ``CHROMA_PERSIST_DIR`` / ``WEAVIATE_URL``, otherwise pgvector
    on ``DATABASE_URL``, otherwise in-memory.
    """
    import os

    chroma_dir = os.getenv("CHROMA_PERSIST_DIR", "").strip()
    if chroma_dir:
        try:
            return ChromaVectorStore(chroma_dir)
        except Exception as exc:
            logger.warning("Chroma unavailable (%s) — falling through", exc)

    weaviate_url = os.getenv("WEAVIATE_URL", "").strip()
    if weaviate_url:
        try:
            return WeaviateVectorStore(weaviate_url)
        except Exception as exc:
            logger.warning("Weaviate unavailable (%s) — falling through", exc)

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

"""
Pure-Python vector database for VeloC agent RAG (Retrieval-Augmented Generation).

Implements a lightweight TF-IDF + cosine similarity retrieval system using only
the Python standard library (no numpy, no scipy, no external dependencies).

Storage
-------
Entries are persisted as a JSON file at ``<BUILD_DIR>/knowledge_db/knowledge.json``.
The database starts empty; the LLM fills it organically through ``store_insight``
calls during real sessions.

Enable/Disable
--------------
Controlled by the ``VELOC_RAG_ENABLED`` environment variable / ``.env`` setting
(via ``agents.veloc.config.Settings``).  When disabled, all three tool functions
return immediately with ``rag_enabled: false`` and make no reads or writes.

Tool functions (exposed to the LLM)
------------------------------------
- ``query_knowledge_base(query, category, top_k)``
- ``store_insight(category, title, content, tags, confidence)``
- ``update_insight(insight_id, content, confidence, verified)``

Each function returns a JSON string suitable for the LLM tool-calling protocol.
"""

from __future__ import annotations

import json
import math
import os
import re
import time
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DB_FILENAME = "knowledge.json"
_DB_VERSION = 1

VALID_CATEGORIES = frozenset({
    "best_practice",
    "api_usage",
    "error_solution",
    "state_identification",
    "checkpoint_timing",
    "code_pattern",
})


# ---------------------------------------------------------------------------
# Helpers: TF-IDF + cosine similarity (pure Python)
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> List[str]:
    """Lowercase, strip punctuation, split into tokens."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9_\s]", " ", text)
    return [t for t in text.split() if len(t) > 1]


def _tf(tokens: List[str]) -> Dict[str, float]:
    """Term frequency: count / total."""
    if not tokens:
        return {}
    counts = Counter(tokens)
    total = len(tokens)
    return {term: count / total for term, count in counts.items()}


def _idf(corpus_tokens: List[List[str]]) -> Dict[str, float]:
    """Inverse document frequency over a corpus of token lists."""
    n = len(corpus_tokens)
    if n == 0:
        return {}
    df: Dict[str, int] = {}
    for tokens in corpus_tokens:
        for term in set(tokens):
            df[term] = df.get(term, 0) + 1
    return {term: math.log((n + 1) / (count + 1)) + 1.0 for term, count in df.items()}


def _tfidf_vector(tokens: List[str], idf: Dict[str, float]) -> Dict[str, float]:
    """Compute TF-IDF vector for a token list given a pre-computed IDF table."""
    tf = _tf(tokens)
    return {term: tf_val * idf.get(term, 1.0) for term, tf_val in tf.items()}


def _cosine_similarity(vec_a: Dict[str, float], vec_b: Dict[str, float]) -> float:
    """Cosine similarity between two sparse TF-IDF vectors."""
    if not vec_a or not vec_b:
        return 0.0
    dot = sum(vec_a.get(t, 0.0) * v for t, v in vec_b.items())
    norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
    norm_b = math.sqrt(sum(v * v for v in vec_b.values()))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


# ---------------------------------------------------------------------------
# VectorDB class
# ---------------------------------------------------------------------------

class VectorDB:
    """
    Lightweight persistent knowledge base backed by a JSON file.

    Thread-safety: not thread-safe; the agent runs single-threaded tool calls
    so this is acceptable.  File is read on every query and written on every
    store/update to ensure durability without a background process.
    """

    def __init__(self, db_path: Path) -> None:
        self._path = db_path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._write({"version": _DB_VERSION, "entries": []})

    # ── I/O ──────────────────────────────────────────────────────────────────

    def _read(self) -> Dict[str, Any]:
        try:
            with open(self._path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if not isinstance(data, dict) or "entries" not in data:
                return {"version": _DB_VERSION, "entries": []}
            return data
        except (OSError, json.JSONDecodeError):
            return {"version": _DB_VERSION, "entries": []}

    def _write(self, data: Dict[str, Any]) -> None:
        tmp = self._path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
        tmp.replace(self._path)

    # ── Query ─────────────────────────────────────────────────────────────────

    def query(
        self,
        query: str,
        category: Optional[str] = None,
        top_k: int = 5,
        min_similarity: float = 0.05,
    ) -> List[Dict[str, Any]]:
        """
        Return the top-k entries most similar to *query*.

        Optionally filter by *category*.  Entries with cosine similarity below
        *min_similarity* are excluded.
        """
        data = self._read()
        entries: List[Dict[str, Any]] = data.get("entries", [])

        # Apply category filter.
        if category and category in VALID_CATEGORIES:
            entries = [e for e in entries if e.get("category") == category]

        if not entries:
            return []

        # Build corpus: each entry's searchable text = title + content + tags.
        def _entry_text(e: Dict[str, Any]) -> str:
            tags = " ".join(e.get("tags") or [])
            return f"{e.get('title', '')} {e.get('content', '')} {tags}"

        corpus_tokens = [_tokenize(_entry_text(e)) for e in entries]
        query_tokens = _tokenize(query)

        # Compute IDF over corpus + query.
        all_token_lists = corpus_tokens + [query_tokens]
        idf = _idf(all_token_lists)

        query_vec = _tfidf_vector(query_tokens, idf)

        # Score each entry.
        scored: List[tuple[float, Dict[str, Any]]] = []
        for tokens, entry in zip(corpus_tokens, entries):
            entry_vec = _tfidf_vector(tokens, idf)
            sim = _cosine_similarity(query_vec, entry_vec)
            if sim >= min_similarity:
                scored.append((sim, entry))

        # Sort descending by similarity, take top-k.
        scored.sort(key=lambda x: x[0], reverse=True)
        results = []
        for sim, entry in scored[:top_k]:
            result = dict(entry)
            result["similarity"] = round(sim, 4)
            # Truncate content for display (full content is in the entry).
            results.append(result)
        return results

    # ── Store ─────────────────────────────────────────────────────────────────

    def store(
        self,
        category: str,
        title: str,
        content: str,
        tags: Optional[List[str]] = None,
        confidence: float = 0.5,
        source: str = "unknown",
    ) -> Dict[str, Any]:
        """Add a new entry and return it."""
        now = datetime.now(timezone.utc).isoformat()
        entry: Dict[str, Any] = {
            "id": str(uuid.uuid4()),
            "category": category if category in VALID_CATEGORIES else "best_practice",
            "title": title.strip(),
            "content": content.strip(),
            "tags": [t.strip() for t in (tags or []) if t.strip()],
            "source": source,
            "created_at": now,
            "updated_at": now,
            "confidence": max(0.0, min(1.0, float(confidence))),
            "verified": False,
        }
        data = self._read()
        data.setdefault("entries", []).append(entry)
        self._write(data)
        return entry

    # ── Update ────────────────────────────────────────────────────────────────

    def update(
        self,
        insight_id: str,
        content: Optional[str] = None,
        confidence: Optional[float] = None,
        verified: Optional[bool] = None,
        title: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Update an existing entry by ID.  Returns the updated entry or None."""
        data = self._read()
        entries: List[Dict[str, Any]] = data.get("entries", [])
        for entry in entries:
            if entry.get("id") == insight_id:
                if title is not None:
                    entry["title"] = title.strip()
                if category is not None and category in VALID_CATEGORIES:
                    entry["category"] = category
                if content is not None:
                    entry["content"] = content.strip()
                if tags is not None:
                    entry["tags"] = [t.strip() for t in tags if t.strip()]
                if confidence is not None:
                    entry["confidence"] = max(0.0, min(1.0, float(confidence)))
                if verified is not None:
                    entry["verified"] = bool(verified)
                entry["updated_at"] = datetime.now(timezone.utc).isoformat()
                self._write(data)
                return entry
        return None

    # ── Delete ────────────────────────────────────────────────────────────────

    def delete(self, insight_id: str) -> bool:
        """Delete an entry by ID.  Returns True if found and deleted."""
        data = self._read()
        entries: List[Dict[str, Any]] = data.get("entries", [])
        new_entries = [e for e in entries if e.get("id") != insight_id]
        if len(new_entries) == len(entries):
            return False
        data["entries"] = new_entries
        self._write(data)
        return True

    # ── List all ──────────────────────────────────────────────────────────────

    def list_all(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return all entries, optionally filtered by category."""
        data = self._read()
        entries = data.get("entries", [])
        if category:
            entries = [e for e in entries if e.get("category") == category]
        return entries

    def stats(self) -> Dict[str, Any]:
        """Return summary statistics about the knowledge base."""
        data = self._read()
        entries = data.get("entries", [])
        by_cat: Dict[str, int] = {}
        for e in entries:
            cat = e.get("category", "unknown")
            by_cat[cat] = by_cat.get(cat, 0) + 1
        latest = max((e.get("updated_at", "") for e in entries), default=None)
        return {
            "total_entries": len(entries),
            "by_category": by_cat,
            "latest_update": latest,
            "db_path": str(self._path),
        }


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_db_instance: Optional[VectorDB] = None


def _get_db() -> VectorDB:
    """Return the module-level VectorDB singleton, creating it if needed."""
    global _db_instance
    if _db_instance is None:
        from agents.veloc.config import get_project_root
        db_path = Path(get_project_root()) / "knowledge_db" / _DB_FILENAME
        _db_instance = VectorDB(db_path)
    return _db_instance


def _is_rag_enabled() -> bool:
    """Return True if RAG is enabled (checked at call time, not import time)."""
    from agents.veloc.config import get_settings
    return get_settings().veloc_rag_enabled


# ---------------------------------------------------------------------------
# LLM Tool functions
# ---------------------------------------------------------------------------

def query_knowledge_base(
    query: str,
    category: str = "",
    top_k: int = 5,
) -> str:
    """
    Search the VeloC knowledge base for insights relevant to *query*.

    Args:
        query: Natural-language description of what you are looking for
               (e.g. "MPI checkpoint state identification", "VeloC Init error").
        category: Optional category filter.  One of: best_practice, api_usage,
                  error_solution, state_identification, checkpoint_timing, code_pattern.
                  Leave empty to search all categories.
        top_k: Maximum number of results to return (default 5).

    Returns:
        JSON string with keys:
          - ``results``: list of matching entries (each has id, category, title,
            content, tags, confidence, verified, similarity).
          - ``count``: number of results returned.
          - ``rag_enabled``: whether the RAG system is active.
    """
    if not _is_rag_enabled():
        return json.dumps({
            "results": [],
            "count": 0,
            "rag_enabled": False,
            "note": "RAG is disabled (VELOC_RAG_ENABLED=false). No knowledge base access.",
        })

    t0 = time.monotonic()
    try:
        db = _get_db()
        cat = category.strip() if category else None
        results = db.query(query, category=cat, top_k=max(1, int(top_k)))
        elapsed = time.monotonic() - t0
        return json.dumps({
            "results": results,
            "count": len(results),
            "rag_enabled": True,
            "elapsed_s": round(elapsed, 3),
        })
    except Exception as exc:
        return json.dumps({"error": str(exc), "results": [], "count": 0, "rag_enabled": True})


def store_insight(
    category: str,
    title: str,
    content: str,
    tags: Optional[List[str]] = None,
    confidence: float = 0.5,
    source: str = "",
) -> str:
    """
    Store a new insight in the VeloC knowledge base.

    Args:
        category: One of: best_practice, api_usage, error_solution,
                  state_identification, checkpoint_timing, code_pattern.
        title: Short descriptive title (1–2 sentences).
        content: Full text of the insight.  Include context, code snippets,
                 and explanation.  Be specific and actionable.
        tags: Optional list of keyword tags (e.g. ["veloc", "mpi", "memory-based"]).
        confidence: Confidence level 0.0–1.0 (default 0.5).  Use higher values
                    for insights that have been validated by successful runs.
        source: Optional session ID or label for provenance tracking.

    Returns:
        JSON string with keys:
          - ``stored``: True if stored successfully.
          - ``id``: UUID of the new entry.
          - ``rag_enabled``: whether the RAG system is active.
    """
    if not _is_rag_enabled():
        return json.dumps({
            "stored": False,
            "rag_enabled": False,
            "note": "RAG is disabled (VELOC_RAG_ENABLED=false). Insight not stored.",
        })

    try:
        db = _get_db()
        entry = db.store(
            category=category,
            title=title,
            content=content,
            tags=tags or [],
            confidence=confidence,
            source=source or "unknown",
        )
        return json.dumps({
            "stored": True,
            "id": entry["id"],
            "category": entry["category"],
            "title": entry["title"],
            "rag_enabled": True,
        })
    except Exception as exc:
        return json.dumps({"stored": False, "error": str(exc), "rag_enabled": True})


def update_insight(
    insight_id: str,
    content: Optional[str] = None,
    confidence: Optional[float] = None,
    verified: Optional[bool] = None,
) -> str:
    """
    Update an existing insight in the VeloC knowledge base.

    Call this when a solution from the knowledge base was applied but did not
    work as expected — update the content with the correct information and set
    ``verified=false`` so future sessions know to treat it with caution.

    Args:
        insight_id: UUID of the entry to update (from a previous store_insight
                    or query_knowledge_base result).
        content: New full text content (replaces existing content if provided).
        confidence: New confidence level 0.0–1.0 (replaces existing if provided).
        verified: Set to True if the insight has been validated by a successful
                  run, False if it failed or needs re-verification.

    Returns:
        JSON string with keys:
          - ``updated``: True if the entry was found and updated.
          - ``id``: UUID of the updated entry.
          - ``rag_enabled``: whether the RAG system is active.
    """
    if not _is_rag_enabled():
        return json.dumps({
            "updated": False,
            "rag_enabled": False,
            "note": "RAG is disabled (VELOC_RAG_ENABLED=false). No update made.",
        })

    try:
        db = _get_db()
        entry = db.update(
            insight_id=insight_id,
            content=content,
            confidence=confidence,
            verified=verified,
        )
        if entry is None:
            return json.dumps({
                "updated": False,
                "error": f"No entry found with id '{insight_id}'.",
                "rag_enabled": True,
            })
        return json.dumps({
            "updated": True,
            "id": entry["id"],
            "title": entry["title"],
            "confidence": entry["confidence"],
            "verified": entry["verified"],
            "rag_enabled": True,
        })
    except Exception as exc:
        return json.dumps({"updated": False, "error": str(exc), "rag_enabled": True})


def get_knowledge_db_stats() -> Dict[str, Any]:
    """Return stats about the knowledge base (for the /knowledge web endpoint)."""
    if not _is_rag_enabled():
        return {"rag_enabled": False, "total_entries": 0, "by_category": {}, "latest_update": None}
    try:
        db = _get_db()
        stats = db.stats()
        stats["rag_enabled"] = True
        return stats
    except Exception as exc:
        return {"rag_enabled": True, "error": str(exc), "total_entries": 0}


def get_knowledge_db_entries(category: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return all entries from the knowledge base (for the /knowledge web endpoint)."""
    if not _is_rag_enabled():
        return []
    try:
        db = _get_db()
        return db.list_all(category=category)
    except Exception:
        return []


def add_knowledge_db_entry(
    category: str,
    title: str,
    content: str,
    tags: Optional[List[str]] = None,
    confidence: float = 0.5,
    source: str = "webui",
) -> Dict[str, Any]:
    """Add a new entry via the web UI."""
    db = _get_db()
    return db.store(
        category=category,
        title=title,
        content=content,
        tags=tags or [],
        confidence=confidence,
        source=source,
    )


def update_knowledge_db_entry(
    insight_id: str,
    title: Optional[str] = None,
    category: Optional[str] = None,
    content: Optional[str] = None,
    tags: Optional[List[str]] = None,
    confidence: Optional[float] = None,
    verified: Optional[bool] = None,
) -> Optional[Dict[str, Any]]:
    """Update an existing entry via the web UI."""
    db = _get_db()
    return db.update(
        insight_id=insight_id,
        title=title,
        category=category,
        content=content,
        tags=tags,
        confidence=confidence,
        verified=verified,
    )


def delete_knowledge_db_entry(insight_id: str) -> bool:
    """Delete an entry by ID via the web UI."""
    db = _get_db()
    return db.delete(insight_id)

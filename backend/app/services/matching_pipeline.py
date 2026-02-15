"""Multi-stage BoQ matching pipeline (Stages 2-3)."""
from __future__ import annotations

from typing import Any

from rank_bm25 import BM25Plus

from app.services.text_preprocessor import preprocess, tokenize, extract_unit


# ── Helper functions ────────────────────────────────────────────────


def _char_trigrams(text: str) -> set[str]:
    if len(text) < 3:
        return {text} if text else set()
    return {text[i : i + 3] for i in range(len(text) - 2)}


def trigram_jaccard(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    set_a = _char_trigrams(a)
    set_b = _char_trigrams(b)
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def unit_match_score(unit_a: str | None, unit_b: str | None) -> float:
    norm_a = extract_unit(unit_a)
    norm_b = extract_unit(unit_b)
    if not norm_a or not norm_b:
        return 0.5
    return 1.0 if norm_a == norm_b else 0.0


def code_similarity_score(code_a: str | None, code_b: str | None) -> float:
    if not code_a or not code_b:
        return 0.0
    parts_a = code_a.rstrip(".").split(".")
    parts_b = code_b.rstrip(".").split(".")
    match_depth = 0
    for pa, pb in zip(parts_a, parts_b):
        if pa == pb:
            match_depth += 1
        else:
            break
    if match_depth == 0:
        return 0.0
    max_depth = max(len(parts_a), len(parts_b))
    return min(1.0, match_depth / (max_depth - 1)) if max_depth > 1 else 1.0


# ── MatchingPipeline ────────────────────────────────────────────────


class MatchingPipeline:
    """BM25 + structural re-ranking pipeline for BoQ description matching."""

    def __init__(self) -> None:
        self._bm25: BM25Plus | None = None
        self._items: list[dict[str, Any]] = []
        self._preprocessed: list[str] = []
        self._tokenized: list[list[str]] = []

    @property
    def is_indexed(self) -> bool:
        return self._bm25 is not None and len(self._items) > 0

    @property
    def corpus_size(self) -> int:
        return len(self._items)

    def build_index(self, items: list[dict[str, Any]]) -> None:
        """Build BM25 index from historical items.

        Uses fullDescription if available and longer, else description.
        """
        if not items:
            self._bm25 = None
            self._items = []
            self._preprocessed = []
            self._tokenized = []
            return

        self._items = list(items)
        self._preprocessed = []
        self._tokenized = []

        for item in self._items:
            desc = item.get("description", "")
            full_desc = item.get("fullDescription", "")
            text = full_desc if full_desc and len(full_desc) > len(desc) else desc
            pp = preprocess(text)
            self._preprocessed.append(pp)
            self._tokenized.append(tokenize(pp))

        self._bm25 = BM25Plus(self._tokenized)

    def _retrieve_candidates(
        self, query: str, top_k: int = 20
    ) -> list[dict[str, Any]]:
        """Stage 2: Retrieve top-k candidates using BM25."""
        if not self.is_indexed:
            return []
        query_tokens = tokenize(preprocess(query))
        if not query_tokens:
            return []
        scores = self._bm25.get_scores(query_tokens)
        scored = [
            (idx, float(score)) for idx, score in enumerate(scores) if score > 0
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [
            {
                **self._items[idx],
                "_bm25_score": score,
                "_preprocessed": self._preprocessed[idx],
            }
            for idx, score in scored[:top_k]
        ]

    def search(
        self,
        query: str,
        max_results: int = 20,
        threshold: float = 0.3,
        query_unit: str | None = None,
        query_code: str | None = None,
    ) -> list[dict[str, Any]]:
        """Stage 3: Search with BM25 retrieval + structural re-ranking.

        Scoring formula:
            final = 0.4 * bm25_norm + 0.35 * trigram + 0.15 * unit + 0.1 * code
        """
        if not query or not self.is_indexed:
            return []

        candidates = self._retrieve_candidates(
            query, top_k=max(max_results * 3, 60)
        )
        if not candidates:
            return []

        max_bm25 = max(c["_bm25_score"] for c in candidates)
        if max_bm25 > 0:
            for c in candidates:
                c["_bm25_norm"] = c["_bm25_score"] / max_bm25
        else:
            for c in candidates:
                c["_bm25_norm"] = 0.0

        query_pp = preprocess(query)

        for c in candidates:
            tri = trigram_jaccard(query_pp, c["_preprocessed"])
            unit_sc = unit_match_score(query_unit, c.get("unit"))
            code_sc = code_similarity_score(query_code, c.get("itemNumber"))
            c["similarity"] = round(
                0.4 * c["_bm25_norm"]
                + 0.35 * tri
                + 0.15 * unit_sc
                + 0.1 * code_sc,
                4,
            )
            c["matchedQuery"] = query

        results = sorted(
            [c for c in candidates if c["similarity"] >= threshold],
            key=lambda x: x["similarity"],
            reverse=True,
        )

        for r in results:
            for key in ("_bm25_score", "_bm25_norm", "_preprocessed"):
                r.pop(key, None)

        return results[:max_results]

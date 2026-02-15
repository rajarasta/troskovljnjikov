from app.services.matching_pipeline import (
    MatchingPipeline,
    trigram_jaccard,
    unit_match_score,
    code_similarity_score,
)


def _make_items() -> list[dict]:
    return [
        {
            "id": "1",
            "description": "podložni beton C12/15",
            "fullDescription": "betonski radovi podložni beton C12/15",
            "unit": "m3",
            "itemNumber": "3.1.1",
        },
        {
            "id": "2",
            "description": "armiranobetonska ploča d=20cm",
            "fullDescription": "",
            "unit": "m3",
            "itemNumber": "3.1.2",
        },
        {
            "id": "3",
            "description": "čelična konstrukcija IPE 200",
            "fullDescription": "čelični radovi čelična konstrukcija IPE 200",
            "unit": "kg",
            "itemNumber": "5.1.1",
        },
        {
            "id": "4",
            "description": "dobava i ugradnja keramičkih pločica",
            "fullDescription": "",
            "unit": "m2",
            "itemNumber": "7.2.1",
        },
        {
            "id": "5",
            "description": "podložni beton C15/20",
            "fullDescription": "betonski radovi podložni beton C15/20",
            "unit": "m3",
            "itemNumber": "3.1.3",
        },
    ]


# ── Index tests ─────────────────────────────────────────────────────


def test_build_index():
    pipeline = MatchingPipeline()
    pipeline.build_index(_make_items())
    assert pipeline.is_indexed
    assert pipeline.corpus_size == 5


def test_build_index_empty():
    pipeline = MatchingPipeline()
    pipeline.build_index([])
    assert not pipeline.is_indexed
    assert pipeline.corpus_size == 0


# ── Retrieval tests ─────────────────────────────────────────────────


def test_retrieve_beton():
    pipeline = MatchingPipeline()
    pipeline.build_index(_make_items())
    candidates = pipeline._retrieve_candidates("podložni beton", top_k=3)
    assert len(candidates) <= 3
    descriptions = [c["description"] for c in candidates]
    assert any("podložni beton" in d for d in descriptions)


def test_retrieve_unindexed():
    pipeline = MatchingPipeline()
    assert pipeline._retrieve_candidates("anything", top_k=5) == []


def test_retrieve_returns_bm25_score():
    pipeline = MatchingPipeline()
    pipeline.build_index(_make_items())
    candidates = pipeline._retrieve_candidates("podložni beton C12/15", top_k=3)
    assert all("_bm25_score" in c for c in candidates)
    assert all(c["_bm25_score"] > 0 for c in candidates)


# ── Trigram tests ───────────────────────────────────────────────────


def test_trigram_identical():
    assert trigram_jaccard("podložni beton", "podložni beton") == 1.0


def test_trigram_similar():
    score = trigram_jaccard("podložni beton C12/15", "podložni beton C15/20")
    assert 0.5 < score < 1.0


def test_trigram_different():
    score = trigram_jaccard("betoniranje temelja", "krovopokrivački radovi")
    assert score < 0.3


def test_trigram_empty():
    assert trigram_jaccard("", "anything") == 0.0
    assert trigram_jaccard("anything", "") == 0.0


def test_trigram_short():
    assert trigram_jaccard("ab", "ab") == 1.0
    assert trigram_jaccard("ab", "cd") == 0.0


# ── Unit match tests ───────────────────────────────────────────────


def test_unit_match_same():
    assert unit_match_score("m3", "m3") == 1.0


def test_unit_match_normalized():
    assert unit_match_score("m³", "m3") == 1.0


def test_unit_match_different():
    assert unit_match_score("m3", "kg") == 0.0


def test_unit_match_missing():
    assert unit_match_score("m3", "") == 0.5
    assert unit_match_score("", "") == 0.5


# ── Code similarity tests ──────────────────────────────────────────


def test_code_same_parent():
    assert code_similarity_score("3.1.1", "3.1.2") > 0.5


def test_code_different_chapter():
    assert code_similarity_score("3.1.1", "5.2.1") == 0.0


def test_code_same_chapter():
    score = code_similarity_score("3.1.1", "3.2.1")
    assert 0.0 < score < code_similarity_score("3.1.1", "3.1.2")


def test_code_missing():
    assert code_similarity_score("3.1.1", "") == 0.0
    assert code_similarity_score("", "") == 0.0


# ── Search tests ────────────────────────────────────────────────────


def test_search_sorted():
    pipeline = MatchingPipeline()
    pipeline.build_index(_make_items())
    results = pipeline.search(
        "podložni beton C12/15", max_results=5, threshold=0.1
    )
    assert len(results) > 0
    scores = [r["similarity"] for r in results]
    assert scores == sorted(scores, reverse=True)


def test_search_best_match():
    pipeline = MatchingPipeline()
    pipeline.build_index(_make_items())
    results = pipeline.search("podložni beton C12/15", max_results=5)
    assert results[0]["description"] == "podložni beton C12/15"


def test_search_threshold():
    pipeline = MatchingPipeline()
    pipeline.build_index(_make_items())
    results = pipeline.search("podložni beton", max_results=20, threshold=0.8)
    for r in results:
        assert r["similarity"] >= 0.8


def test_search_with_unit_boost():
    pipeline = MatchingPipeline()
    pipeline.build_index(_make_items())
    results = pipeline.search(
        "podložni beton C12/15",
        max_results=5,
        query_unit="m3",
        query_code="3.1.1",
    )
    assert len(results) > 0


def test_search_empty():
    pipeline = MatchingPipeline()
    pipeline.build_index(_make_items())
    assert pipeline.search("") == []


def test_search_unindexed():
    pipeline = MatchingPipeline()
    assert pipeline.search("anything") == []


def test_search_clean_internal_fields():
    pipeline = MatchingPipeline()
    pipeline.build_index(_make_items())
    results = pipeline.search("podložni beton", max_results=1)
    assert "id" in results[0]
    assert "similarity" in results[0]
    assert "matchedQuery" in results[0]
    assert "_bm25_score" not in results[0]
    assert "_preprocessed" not in results[0]

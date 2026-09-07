from __future__ import annotations
import pytest
from app.retrieval.embedder import embed_chunks, embed_query, compute_dense_vector, compute_sparse_vector
from app.retrieval.vectorstore import InMemoryVectorStore, get_store, SearchResult
from app.retrieval.hybrid import reciprocal_rank_fusion
from app.retrieval.reranker import rerank
from app.retrieval.decompose import decompose
from app.retrieval.policy import decide, Route
from app.core.schemas import SectionPlan


class TestRagPipeline:
    def test_embedder_semantic_discrimination(self):
        t1 = "Threat actor SILVER CYCLONE exploiting CVE-2026-8819 on supervisory gateway port 44818"
        t2 = "Routine maintenance schedule for administrative cafeteria heating and ventilation"
        q = "What CVE is SILVER CYCLONE attacking on port 44818?"

        chunks = [("c1", t1), ("c2", t2)]
        results = embed_chunks(chunks)
        assert len(results) == 2

        q_emb = embed_query(q)

        # Dot product with normalized dense vectors = cosine similarity
        sim1 = sum(a * b for a, b in zip(q_emb.dense, results[0].dense))
        sim2 = sum(a * b for a, b in zip(q_emb.dense, results[1].dense))

        # Relevant chunk must have significantly higher similarity than irrelevant chunk
        assert sim1 > sim2
        assert sim1 > 0.35
        assert sim2 < 0.20

    def test_vectorstore_dense_sparse_hybrid(self):
        store = InMemoryVectorStore()
        chunks = [
            ("c1", "State-sponsored cyber threat group SILVER CYCLONE compromised 14 supervisory nodes."),
            ("c2", "Critical vulnerability CVE-2026-8819 with CVSS 9.8 allows remote code execution."),
            ("c3", "Mandatory mitigation: emergency patch deployment and block port 44818 immediately."),
        ]
        emb_results = embed_chunks(chunks)
        payloads = [
            {"chunk_id": cid, "text": text, "page": 1}
            for cid, text in chunks
        ]
        store.upsert(emb_results, payloads)
        assert store.size() == 3

        # Hybrid query for mitigation and patch
        res = store.search_hybrid("What are the mandatory mitigation actions and patch instructions?", top_k=2)
        assert len(res) > 0
        top = res[0]
        assert top.chunk_id == "c3"
        assert "patch" in top.payload["text"].lower()

        # Hybrid query for vulnerability and CVSS
        res_vuln = store.search_hybrid("CVSS 9.8 remote code execution CVE-2026-8819", top_k=1)
        assert len(res_vuln) > 0
        assert res_vuln[0].chunk_id == "c2"

    def test_reciprocal_rank_fusion(self):
        dense_results = [
            SearchResult(chunk_id="c2", score=0.9),
            SearchResult(chunk_id="c1", score=0.7),
        ]
        sparse_results = [
            SearchResult(chunk_id="c1", score=4.5),
            SearchResult(chunk_id="c3", score=3.0),
        ]

        fused = reciprocal_rank_fusion(dense_results, sparse_results, k=60)
        assert len(fused) == 3
        # c1 appeared in both lists, so its RRF score must be highest
        assert fused[0].chunk_id == "c1"

    def test_reranker_identifier_boost(self):
        q = "Investigate malicious telemetry targeting port 44818 CVE-2026-8819"
        candidates = [
            SearchResult(chunk_id="cand_generic", score=0.03, payload={"text": "Network telemetry monitoring report."}),
            SearchResult(chunk_id="cand_exact", score=0.025, payload={"text": "Adversary exploiting CVE-2026-8819 on gateway port 44818."}),
        ]
        from app.retrieval.hybrid import FusedResult
        fused = [
            FusedResult(chunk_id="cand_generic", rrf_score=0.03),
            FusedResult(chunk_id="cand_exact", rrf_score=0.025),
        ]
        chunk_texts = {
            "cand_generic": "Network telemetry monitoring report.",
            "cand_exact": "Adversary exploiting CVE-2026-8819 on gateway port 44818.",
        }

        reranked = rerank(q, fused, chunk_texts, top_k=2)
        # Even though cand_generic had slightly higher initial RRF, cand_exact has exact identifier matches
        assert reranked[0].chunk_id == "cand_exact"
        assert reranked[0].rerank_score > reranked[1].rerank_score

    def test_query_decomposition(self):
        sections = [
            SectionPlan(section_key="key_findings", required=True),
            SectionPlan(section_key="affected_systems", required=True),
            SectionPlan(section_key="recommended_actions", required=True),
        ]
        subqueries = decompose(sections, sot_context="SILVER CYCLONE CVE-2026-8819", target_format="advisory")
        assert len(subqueries) == 3
        assert any("finding" in sq.query_text.lower() for sq in subqueries)
        assert any("affected" in sq.query_text.lower() or "system" in sq.query_text.lower() for sq in subqueries)
        assert any("mitigation" in sq.query_text.lower() or "patch" in sq.query_text.lower() for sq in subqueries)

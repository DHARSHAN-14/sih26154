"""
api/routes_retrieval.py — RAG hybrid retrieval API endpoints.
Provides:
- POST /api/sessions/{session_id}/retrieval/query: Execute hybrid search (Dense + BM25 + RRF + Rerank)
- GET /api/sessions/{session_id}/retrieval/status: Check RAG vector store and index status
- Flat router alternatives for flexible frontend access
"""
from __future__ import annotations
import json
import pathlib
import re
from typing import Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.deps import DbDep, SettingsDep
from app.retrieval.vectorstore import get_store, InMemoryVectorStore
from app.retrieval.embedder import embed_chunks, tokenize, _STOP_WORDS
from app.retrieval.policy import decide
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/sessions/{session_id}/retrieval", tags=["RAG / Retrieval"])
flat_router = APIRouter(prefix="/retrieval", tags=["RAG / Retrieval"])


class RetrievalQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Search query or question")
    top_k: int = Field(default=5, ge=1, le=50, description="Max passages to retrieve")
    format: str | None = Field(default=None, description="Optional output format context")


class RetrievalPassageOut(BaseModel):
    chunk_id: str
    text: str
    page: int = 1
    paragraph: int = 1
    doc_id: str = ""
    dense_score: float = 0.0
    sparse_score: float = 0.0
    rrf_score: float = 0.0
    rerank_score: float = 0.0
    matched_terms: list[str] = []


class RetrievalResponse(BaseModel):
    session_id: str
    query: str
    route: str
    total_indexed_chunks: int
    results: list[RetrievalPassageOut]


async def _ensure_store_indexed(session_id: str, db: Any) -> InMemoryVectorStore:
    """Ensure the session's vector store has all chunks indexed."""
    store = get_store(session_id)
    if store.size() > 0:
        return store

    # Load from DB SourceDocument and FactRecords
    from sqlalchemy import select
    from app.db.models import SourceDocument, FactRecord
    from app.ingest import docling_adapter

    doc_res = await db.execute(
        select(SourceDocument).where(SourceDocument.session_id == session_id)
    )
    docs = doc_res.scalars().all()

    chunks_to_index: list[tuple[str, str, dict[str, Any]]] = []

    for doc in docs:
        # Check parsed json
        if doc.parsed_path:
            json_p = pathlib.Path(doc.parsed_path).parent / f"{doc.id}_parsed.json"
            if json_p.exists():
                try:
                    pages = json.loads(json_p.read_text(encoding="utf-8"))
                    for p_data in pages:
                        p_num = p_data.get("page", 1)
                        paragraphs = p_data.get("paragraphs", [p_data.get("text", "")])
                        for idx, p_txt in enumerate(paragraphs):
                            if p_txt and len(p_txt.strip()) > 15:
                                cid = f"{doc.id}-p{p_num}-s{idx}"
                                chunks_to_index.append((cid, p_txt.strip(), {
                                    "chunk_id": cid,
                                    "text": p_txt.strip(),
                                    "doc_id": doc.id,
                                    "page": p_num,
                                    "paragraph": idx + 1,
                                }))
                except Exception:
                    pass

        # If still empty, parse raw file if available
        if not chunks_to_index and doc.file_path and pathlib.Path(doc.file_path).exists():
            try:
                internal_doc = docling_adapter.convert(
                    doc_id=doc.id,
                    file_path=pathlib.Path(doc.file_path),
                    mime_type=doc.mime_type or "",
                )
                for c in internal_doc.chunks:
                    p = c.provenance[0].page if c.provenance else 1
                    para = c.provenance[0].paragraph if c.provenance else 1
                    chunks_to_index.append((c.chunk_id, c.text, {
                        "chunk_id": c.chunk_id,
                        "text": c.text,
                        "doc_id": doc.id,
                        "page": p,
                        "paragraph": para,
                    }))
            except Exception:
                pass

    # Fallback to FactRecords if document files aren't directly chunked
    if not chunks_to_index:
        facts_res = await db.execute(
            select(FactRecord).where(FactRecord.session_id == session_id)
        )
        facts = facts_res.scalars().all()
        for f in facts:
            cid = f"fact-{f.id}"
            page = 1
            if f.provenance_json:
                try:
                    pj = json.loads(f.provenance_json)
                    if pj and isinstance(pj, list):
                        page = pj[0].get("page", 1)
                except Exception:
                    pass
            chunks_to_index.append((cid, f.canonical_text, {
                "chunk_id": cid,
                "text": f.canonical_text,
                "doc_id": "sot-facts",
                "page": page,
                "paragraph": 1,
            }))

    if chunks_to_index:
        pairs = [(cid, text) for cid, text, _ in chunks_to_index]
        emb_results = embed_chunks(pairs)
        payloads = [payload for _, _, payload in chunks_to_index]
        store.upsert(emb_results, payloads)
        logger.info("Initialized RAG vector store on demand", session_id=session_id, chunks=len(emb_results))

    return store


@router.post("/query", summary="Query RAG hybrid vector store", response_model=RetrievalResponse)
async def query_retrieval(
    session_id: str,
    body: RetrievalQueryRequest,
    db: DbDep,
    settings: SettingsDep,
) -> RetrievalResponse:
    store = await _ensure_store_indexed(session_id, db)
    search_results = store.search_hybrid(body.query, top_k=body.top_k)

    # Route decision
    from sqlalchemy import select
    from app.db.models import SourceDocument
    doc_res = await db.execute(select(SourceDocument).where(SourceDocument.session_id == session_id))
    db_docs = doc_res.scalars().all()
    file_count = len(db_docs) or len(set(p.get("doc_id") for _, p in store._store.values() if p.get("doc_id"))) or 1
    total_tokens = sum(len(txt.split()) for txt in store.all_chunk_texts().values()) * 4 // 3
    decision = decide(token_count=total_tokens, threshold=settings.retrieval_token_threshold, file_count=file_count)

    q_tokens = set(tokenize(body.query)) - _STOP_WORDS

    passages: list[RetrievalPassageOut] = []
    for r in search_results:
        p_text = r.payload.get("text", "")
        p_tokens = set(tokenize(p_text))
        matched = sorted(list(q_tokens.intersection(p_tokens)))

        passages.append(RetrievalPassageOut(
            chunk_id=r.chunk_id,
            text=p_text,
            page=r.payload.get("page", 1),
            paragraph=r.payload.get("paragraph", 1),
            doc_id=r.payload.get("doc_id", ""),
            dense_score=r.dense_score,
            sparse_score=r.sparse_score,
            rrf_score=r.rrf_score,
            rerank_score=r.rerank_score,
            matched_terms=matched,
        ))

    return RetrievalResponse(
        session_id=session_id,
        query=body.query,
        route=decision.route.value,
        total_indexed_chunks=store.size(),
        results=passages,
    )


@router.get("/status", summary="Get RAG vector store status")
async def retrieval_status(
    session_id: str,
    db: DbDep,
    settings: SettingsDep,
) -> dict[str, Any]:
    from sqlalchemy import select
    from app.db.models import SourceDocument
    store = await _ensure_store_indexed(session_id, db)
    doc_res = await db.execute(select(SourceDocument).where(SourceDocument.session_id == session_id))
    db_docs = doc_res.scalars().all()
    file_count = len(db_docs) or len(set(p.get("doc_id") for _, p in store._store.values() if p.get("doc_id"))) or 1
    total_tokens = sum(len(txt.split()) for txt in store.all_chunk_texts().values()) * 4 // 3
    decision = decide(token_count=total_tokens, threshold=settings.retrieval_token_threshold, file_count=file_count)

    return {
        "session_id": session_id,
        "indexed_chunks": store.size(),
        "route": decision.route.value,
        "route_reason": decision.reason,
        "token_count": total_tokens,
        "token_threshold": settings.retrieval_token_threshold,
        "hybrid_ready": True,
        "components": {
            "dense_embedder": "n-gram-l2-normalized",
            "sparse_search": "bm25-inverted-index",
            "fusion": "reciprocal_rank_fusion_k60",
            "reranker": "cross_matching_identifier_aware",
        }
    }


# ─── Flat Routes ───────────────────────────────────────────────────────────────

@flat_router.post("/query", summary="Query RAG hybrid vector store (flat endpoint)")
async def flat_query_retrieval(
    session_id: str,
    body: RetrievalQueryRequest,
    db: DbDep,
    settings: SettingsDep,
) -> RetrievalResponse:
    return await query_retrieval(session_id=session_id, body=body, db=db, settings=settings)


@flat_router.get("/{session_id}/status", summary="Get RAG status (flat endpoint)")
async def flat_retrieval_status(
    session_id: str,
    db: DbDep,
    settings: SettingsDep,
) -> dict[str, Any]:
    return await retrieval_status(session_id=session_id, db=db, settings=settings)

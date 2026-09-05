"""
ingest/chunker.py — Text chunking with provenance preservation.
INVARIANT: every emitted chunk carries at least one valid Provenance.
Do NOT write a custom character splitter — it destroys page/bbox mappings.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from app.core.schemas import Provenance
from app.core.ids import generate_chunk_id

DEFAULT_CHUNK_TOKENS = 512
DEFAULT_OVERLAP_TOKENS = 64
AVG_CHARS_PER_TOKEN = 4


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    text: str
    provenance: list[Provenance] = field(default_factory=list)
    token_estimate: int = 0

    def __post_init__(self):
        self.token_estimate = len(self.text) // AVG_CHARS_PER_TOKEN


def chunk_text(
    doc_id: str,
    text: str,
    page: int | None = None,
    locator: str = "",
    chunk_size_chars: int = DEFAULT_CHUNK_TOKENS * AVG_CHARS_PER_TOKEN,
    overlap_chars: int = DEFAULT_OVERLAP_TOKENS * AVG_CHARS_PER_TOKEN,
) -> list[Chunk]:
    """
    Split text into overlapping chunks, attaching provenance to each.
    In production this is replaced by docling-core HybridChunker.
    """
    chunks: list[Chunk] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size_chars, len(text))
        span = text[start:end]
        cid = generate_chunk_id()
        prov = Provenance(
            doc_id=doc_id,
            locator=locator or (f"p{page}" if page else "p0"),
            page=page,
            chunk_id=cid,
            snippet=span[:300],
            char_start=start,
            char_end=end,
        )
        chunks.append(Chunk(chunk_id=cid, doc_id=doc_id, text=span,
                            provenance=[prov]))
        if end == len(text):
            break
        start = end - overlap_chars
    return chunks


def assert_provenance(chunks: list[Chunk]) -> None:
    """Raise AssertionError if any chunk lacks provenance."""
    for c in chunks:
        assert c.provenance, (
            f"Chunk {c.chunk_id} has no Provenance — ingest pipeline invariant violated"
        )

"""
ingest/store.py — Immutable, content-addressed artifact storage.
v2 never overwrites v1; version diffs have real data to compare.
"""
from __future__ import annotations
import pathlib
import shutil
from app.core.hashing import hash_bytes


class ArtifactStore:
    def __init__(self, root: pathlib.Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, data: bytes, filename: str) -> tuple[str, pathlib.Path]:
        """
        Store data content-addressed by SHA-256.
        Returns (file_hash, absolute_path).
        """
        file_hash = hash_bytes(data)
        dest = self.root / file_hash[:2] / file_hash
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            dest.write_bytes(data)
        return file_hash, dest

    def save_file(self, src: pathlib.Path) -> tuple[str, pathlib.Path]:
        data = src.read_bytes()
        return self.save(data, src.name)

    def get(self, file_hash: str) -> pathlib.Path | None:
        p = self.root / file_hash[:2] / file_hash
        return p if p.exists() else None

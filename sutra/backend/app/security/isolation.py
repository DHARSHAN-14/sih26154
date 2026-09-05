"""
security/isolation.py — Per-session path jail and DB isolation guard.
"""
from __future__ import annotations
import pathlib


def jail_path(session_dir: pathlib.Path, rel: str) -> pathlib.Path:
    """
    Resolve a relative path inside the session directory.
    Raises ValueError if the resolved path would escape the jail.
    """
    resolved = (session_dir / rel).resolve()
    jail = session_dir.resolve()
    if not str(resolved).startswith(str(jail)):
        raise ValueError(
            f"Path escape attempt: '{rel}' resolves outside session jail"
        )
    return resolved


def check_session_filter(session_id: str, query_session_id: str) -> None:
    """Raise if a DB query is scoped to a different session."""
    if session_id != query_session_id:
        raise PermissionError(
            f"Cross-session access denied: "
            f"requested {query_session_id}, active session {session_id}"
        )

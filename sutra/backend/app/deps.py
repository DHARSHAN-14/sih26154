from __future__ import annotations
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.session import get_db

# ── Annotated dependency shortcuts ────────────────────────────────────────────
# Usage in route handlers:
#   async def my_route(settings: SettingsDep, db: DbDep) -> ...:

SettingsDep = Annotated[Settings, Depends(get_settings)]
DbDep = Annotated[AsyncSession, Depends(get_db)]

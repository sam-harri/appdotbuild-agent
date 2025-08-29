from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from app.db.session import get_session

router = APIRouter()

# DO NOT CHANGE, THE DOCKER CONTAINER HEALTHCHECK USES THIS ENDPOINT
@router.get("/healthcheck")
async def healthcheck():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}

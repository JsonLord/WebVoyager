import uuid
from fastapi import APIRouter, HTTPException
from app.models.session import SessionResponse
from app.services.browser_service import browser_service

router = APIRouter()

@router.post("/", response_model=SessionResponse)
async def create_session():
    session_id = str(uuid.uuid4())
    # Driver is initialized lazily in browser_service
    return SessionResponse(session_id=session_id, status="initialized")

@router.delete("/{session_id}")
async def close_session(session_id: str):
    browser_service.close_session(session_id)
    return {"status": "closed"}

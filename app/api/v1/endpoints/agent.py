from fastapi import APIRouter, HTTPException
from app.models.session import TaskRequest
from app.services.agent_service import agent_service

router = APIRouter()

@router.post("/{session_id}/task")
async def execute_task(session_id: str, request: TaskRequest):
    try:
        result = await agent_service.execute_task(session_id, request.task)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

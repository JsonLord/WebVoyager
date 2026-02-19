import os
from fastapi import FastAPI, Depends, HTTPException
from app.core.session_manager import SessionManager
from app.services.agent_service import AgentService
from app.services.scraper_service import ScraperService
from app.services.planner_service import PlannerService
from openai import OpenAI
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(title="Web-Agent-Internal API")

# Setup dependencies
openai_api_key = os.getenv("OPENAI_API_KEY", "your-key")
client = OpenAI(api_key=openai_api_key)
session_manager = SessionManager()
scraper_service = ScraperService(openai_client=client)
planner_service = PlannerService()
agent_service = AgentService(
    session_manager=session_manager,
    scraper_service=scraper_service,
    planner_service=planner_service,
    openai_client=client,
    api_model="gpt-4o"
)

class TaskRequest(BaseModel):
    query: str
    max_iter: Optional[int] = 15

class SessionRequest(BaseModel):
    session_id: Optional[str] = None

class ScrapeRequest(BaseModel):
    query: str
    schema_dict: Optional[dict] = None

@app.post("/sessions")
async def create_session(request: SessionRequest):
    session_id = session_manager.create_session(request.session_id)
    return {"session_id": session_id}

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    session_manager.delete_session(session_id)
    return {"status": "deleted"}

@app.post("/sessions/{session_id}/execute")
async def execute_task(session_id: str, request: TaskRequest):
    try:
        result = await agent_service.run_task(session_id, request.query, request.max_iter)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/sessions/{session_id}/scrape")
async def scrape_page(session_id: str, request: ScrapeRequest):
    driver = session_manager.get_driver(session_id)
    if not driver:
        raise HTTPException(status_code=404, detail="Session not found")

    html = driver.page_source
    result = scraper_service.scrape_structured(html, request.query, request.schema_dict)
    return {"result": result}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

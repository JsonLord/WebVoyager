from fastapi import APIRouter
from app.api.v1.endpoints import agent, session, scraper

api_router = APIRouter()
api_router.include_router(agent.router, prefix="/agent", tags=["agent"])
api_router.include_router(session.router, prefix="/sessions", tags=["sessions"])
api_router.include_router(scraper.router, prefix="/scraper", tags=["scraper"])

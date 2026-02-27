from fastapi import APIRouter, HTTPException
from app.models.session import ScrapeRequest
from app.services.scraper_service import scraper_service
from app.services.browser_service import browser_service

router = APIRouter()

@router.post("/")
async def scrape_stateless(request: ScrapeRequest):
    # For stateless scraping, we create a temporary session
    import uuid
    session_id = f"temp_{uuid.uuid4()}"
    try:
        if request.url:
            browser_service.navigate(session_id, request.url)

        result = await scraper_service.scrape_page(session_id, request.schema_dict, request.query)
        return result
    finally:
        browser_service.close_session(session_id)

@router.post("/{session_id}")
async def scrape_session(session_id: str, request: ScrapeRequest):
    # Scraping within an existing session
    result = await scraper_service.scrape_page(session_id, request.schema_dict, request.query)
    return result

import pytest
import os
from app.services.browser_service import browser_service
from app.core.config import settings

@pytest.mark.asyncio
async def test_browser_initialization():
    session_id = "test_session"
    try:
        driver = browser_service.get_driver(session_id)
        assert driver is not None
        assert os.path.exists(os.path.join(settings.SESSIONS_DIR, session_id))

        # Test navigation
        browser_service.navigate(session_id, "https://www.google.com")
        assert "google" in driver.current_url.lower()
    finally:
        browser_service.close_session(session_id)

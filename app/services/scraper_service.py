import json
import logging
from openai import OpenAI
from app.core.config import settings
from app.services.browser_service import browser_service

class ScraperService:
    def __init__(self):
        self.client = None
        # Prioritize Blablador
        if settings.BLABLADOR_API_KEY:
            self.client = OpenAI(
                api_key=settings.BLABLADOR_API_KEY,
                base_url=settings.BLABLADOR_BASE_URL
            )
        elif settings.OPENAI_API_KEY:
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    async def scrape_page(self, session_id: str, schema: dict = None, query: str = None):
        driver = browser_service.get_driver(session_id)
        # Get page source or innerText
        page_text = driver.execute_script("return document.body.innerText")

        if not self.client:
            return {"error": "LLM API key not configured for scraping"}

        system_prompt = "You are a specialized web scraping agent. Your goal is to extract structured information from web page text."
        user_prompt = f"Extract data from the following text:\n\n{page_text[:10000]}\n\n"

        if schema:
            user_prompt += f"Use this JSON schema: {json.dumps(schema)}"
        elif query:
            user_prompt += f"Focus on this request: {query}"
        else:
            user_prompt += "Extract all relevant information into a structured JSON format."

        try:
            response = self.client.chat.completions.create(
                model=settings.MODEL_FAST,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logging.error(f"Scraping failed: {e}")
            return {"error": str(e)}

scraper_service = ScraperService()

import json
from typing import Any, Dict, Optional
from openai import OpenAI

class ScraperService:
    def __init__(self, openai_client: OpenAI, model: str = "gpt-4-1106-preview"):
        self.client = openai_client
        self.model = model

    def scrape_structured(self, html: str, query: str, schema: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Extract structured data from HTML based on a query and optional schema.
        Inspired by CyberScraper-2077 logic.
        """
        system_prompt = "You are a specialized web scraping assistant. Extract the requested information from the provided HTML and return it as valid JSON."

        user_prompt = f"HTML Content (truncated if too long):\n{html[:10000]}\n\nTask: {query}"
        if schema:
            user_prompt += f"\n\nPlease follow this JSON schema for the output:\n{json.dumps(schema, indent=2)}"

        user_prompt += "\n\nReturn ONLY the JSON object."

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"} if "1106" in self.model or "gpt-4-turbo" in self.model else None
            )

            result_text = response.choices[0].message.content
            return json.loads(result_text)
        except Exception as e:
            return {"error": str(e), "raw_response": getattr(response.choices[0].message, 'content', None) if 'response' in locals() else None}

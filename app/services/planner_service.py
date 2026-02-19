import json
import logging
from openai import OpenAI
from app.core.config import settings

class PlannerService:
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

    async def create_plan(self, goal: str, current_url: str = "Not started"):
        if not self.client:
            return {"plan": [{"title": "Initial Step", "description": "Navigate to the site and begin exploration."}]}

        system_prompt = "You are an expert web automation planner. Your job is to break down complex user goals into high-level navigational steps."
        user_prompt = f"""
        Goal: {goal}
        Current URL: {current_url}

        Create a hierarchical plan to achieve this goal.
        Return a JSON object with a 'plan' list.
        Each item should have:
        - 'step_number': integer
        - 'goal': a concise goal for this step
        - 'description': detailed instructions for the agent
        """

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
            logging.error(f"Planning failed: {e}")
            return {"error": str(e), "plan": []}

planner_service = PlannerService()

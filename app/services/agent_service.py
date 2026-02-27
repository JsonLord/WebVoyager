import json
import logging
import os
import time
from openai import OpenAI
from app.core.config import settings
from app.services.browser_service import browser_service
from app.services.scraper_service import scraper_service
from app.services.planner_service import planner_service
from app.services.vision_service import vision_service
from app.utils.mcp_tools import WEB_AGENT_TOOLS

logger = logging.getLogger(__name__)

class AgentService:
    def __init__(self):
        self.client = None
        if settings.BLABLADOR_API_KEY:
            self.client = OpenAI(
                api_key=settings.BLABLADOR_API_KEY,
                base_url=settings.BLABLADOR_BASE_URL
            )
        elif settings.OPENAI_API_KEY:
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    async def execute_task(self, session_id: str, task: str):
        if not self.client:
            return {"error": "LLM client not configured."}

        logger.info(f"Task: {task}")

        driver = browser_service.get_driver(session_id)
        current_url = driver.current_url
        plan_response = await planner_service.create_plan(task, current_url)
        plan = plan_response.get("plan", [])

        history = [
            {"role": "system", "content": f"You are an autonomous web agent. Use tools to achieve the goal. Plan: {json.dumps(plan)}"},
            {"role": "user", "content": f"Task: {task}"}
        ]

        max_iterations = 10
        for i in range(max_iterations):
            logger.info(f"Iteration {i+1}")

            # Observe DOM
            rects, web_eles, web_text = browser_service.get_web_elements(session_id)

            # Observe Vision
            screenshot_path = f"screenshots/{session_id}_step_{i}.png"
            os.makedirs("screenshots", exist_ok=True)
            browser_service.capture_screenshot(session_id, screenshot_path)

            logger.info("Requesting Visual Analysis...")
            visual_description = await vision_service.describe_screenshot(screenshot_path)

            # Forward ONLY TEXT to Helmholtz as requested
            obs_msg = (
                f"URL: {driver.current_url}\n"
                f"Visual (Florence-2): {visual_description}\n"
                f"Interactive Elements:\n{web_text}"
            )
            history.append({"role": "user", "content": obs_msg})

            try:
                response = self.client.chat.completions.create(
                    model=settings.MODEL_LARGE,
                    messages=history,
                    tools=WEB_AGENT_TOOLS,
                    tool_choice="auto"
                )
            except Exception as e:
                logger.error(f"LLM API Error: {e}")
                return {"error": str(e)}

            response_message = response.choices[0].message
            history.append(response_message)

            if not response_message.tool_calls:
                return {"status": "completed", "final_answer": response_message.content}

            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)
                result = ""
                try:
                    if function_name == "navigate":
                        browser_service.navigate(session_id, args["url"])
                        result = f"Navigated to {args['url']}"
                    elif function_name == "click_element":
                        browser_service.click(session_id, args["element_id"], web_eles)
                        result = "Clicked"
                    elif function_name == "type_text":
                        browser_service.type_text(session_id, args["element_id"], args["text"], web_eles)
                        result = "Typed"
                    elif function_name == "scroll":
                        browser_service.scroll(session_id, args["direction"])
                        result = "Scrolled"
                    elif function_name == "scrape_page":
                        scrape_res = await scraper_service.scrape_page(session_id, args.get("schema"), args.get("query"))
                        result = f"Data: {json.dumps(scrape_res)}"

                    browser_service.remove_rects(session_id, rects)
                except Exception as e:
                    result = f"Error: {str(e)}"

                history.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": result,
                })

        return {"status": "timeout", "history": "..."}

agent_service = AgentService()

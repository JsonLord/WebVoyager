import json
import logging
import os
import time
from openai import OpenAI
from app.core.config import settings
from app.services.browser_service import browser_service
from app.services.scraper_service import scraper_service
from app.services.planner_service import planner_service
from app.utils.mcp_tools import WEB_AGENT_TOOLS

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
            return {"error": "LLM API key not configured"}

        # 1. Initial Planning
        driver = browser_service.get_driver(session_id)
        current_url = driver.current_url
        plan_response = await planner_service.create_plan(task, current_url)
        plan = plan_response.get("plan", [])

        history = [
            {"role": "system", "content": "You are an autonomous web agent. Use the provided tools to achieve the user's goal. Current Plan: " + json.dumps(plan)},
            {"role": "user", "content": f"Task: {task}"}
        ]

        max_iterations = 10
        for i in range(max_iterations):
            # Observe state
            rects, web_eles, web_text = browser_service.get_web_elements(session_id)

            # Prepare observation message
            obs_msg = f"Current URL: {driver.current_url}\nVisible Elements:\n{web_text}"
            history.append({"role": "user", "content": obs_msg})

            # Call LLM
            try:
                response = self.client.chat.completions.create(
                    model=settings.MODEL_LARGE,
                    messages=history,
                    tools=WEB_AGENT_TOOLS,
                    tool_choice="auto"
                )
            except Exception as e:
                logging.error(f"LLM call failed: {e}")
                return {"error": str(e)}

            response_message = response.choices[0].message
            history.append(response_message)

            if not response_message.tool_calls:
                # Agent finished or gave up
                return {"status": "completed", "final_answer": response_message.content}

            # Handle tool calls
            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)

                logging.info(f"Executing {function_name} with {args}")

                result = ""
                try:
                    if function_name == "navigate":
                        browser_service.navigate(session_id, args["url"])
                        result = f"Navigated to {args['url']}"
                    elif function_name == "click_element":
                        browser_service.click(session_id, args["element_id"], web_eles)
                        result = f"Clicked element {args['element_id']}"
                    elif function_name == "type_text":
                        browser_service.type_text(session_id, args["element_id"], args["text"], web_eles)
                        result = f"Typed text into element {args['element_id']}"
                    elif function_name == "scroll":
                        browser_service.scroll(session_id, args["direction"])
                        result = f"Scrolled {args['direction']}"
                    elif function_name == "scrape_page":
                        scrape_res = await scraper_service.scrape_page(session_id, args.get("schema"), args.get("query"))
                        result = f"Scraped data: {json.dumps(scrape_res)}"

                    # Clean up rects after action
                    browser_service.remove_rects(session_id, rects)

                except Exception as e:
                    logging.error(f"Error executing {function_name}: {e}")
                    result = f"Error: {str(e)}"

                history.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": result,
                })

        return {"status": "max_iterations_reached", "history": "..."}

agent_service = AgentService()

import os
import re
import time
import logging
import base64
import json
from typing import List, Dict, Any, Optional
from openai import OpenAI
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

from app.core.session_manager import SessionManager
from app.services.scraper_service import ScraperService
from app.services.planner_service import PlannerService
from app.services.mcp_tools import get_mcp_tool_definitions
from app.utils.utils import get_web_element_rect, encode_image, extract_information, clip_message_and_obs
from app.utils.prompts import SYSTEM_PROMPT

class AgentService:
    def __init__(
        self,
        session_manager: SessionManager,
        scraper_service: ScraperService,
        planner_service: PlannerService,
        openai_client: OpenAI,
        api_model: str = "gpt-4o"
    ):
        self.session_manager = session_manager
        self.scraper_service = scraper_service
        self.planner_service = planner_service
        self.client = openai_client
        self.api_model = api_model

    async def run_task(self, session_id: str, task_query: str, max_iter: int = 15):
        driver = self.session_manager.get_driver(session_id)
        if not driver:
            raise ValueError(f"Session {session_id} not found")

        # Initial setup
        messages = [{'role': 'system', 'content': SYSTEM_PROMPT}]

        # Add planning context if available
        plan_context = self.planner_service.format_plan_for_prompt(session_id)
        init_msg = f"Task: {task_query}\n\n{plan_context}\n\nPlease begin by analyzing the current page."

        it = 0
        while it < max_iter:
            it += 1
            logging.info(f"Iteration {it} for session {session_id}")

            # 1. Observe
            rects, web_eles, web_eles_text = get_web_element_rect(driver)

            img_path = f"sessions/{session_id}/screenshot_{it}.png"
            os.makedirs(os.path.dirname(img_path), exist_ok=True)
            driver.save_screenshot(img_path)
            b64_img = encode_image(img_path)

            # 2. Format Message
            curr_msg = {
                'role': 'user',
                'content': [
                    {'type': 'text', 'text': f"Observation (Iter {it}): Here is the current view and interactive elements.\n{web_eles_text}"},
                    {'type': 'image_url', 'image_url': {"url": f"data:image/png;base64,{b64_img}"}}
                ]
            }
            if it == 1:
                curr_msg['content'][0]['text'] = init_msg + "\n" + curr_msg['content'][0]['text']

            messages.append(curr_msg)
            messages = clip_message_and_obs(messages, 3)

            # 3. Call LLM with Tool definitions
            tools = get_mcp_tool_definitions()
            response = self.client.chat.completions.create(
                model=self.api_model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                max_tokens=1000
            )

            assistant_message = response.choices[0].message
            messages.append(assistant_message)

            if assistant_message.content:
                logging.info(f"Assistant Thought: {assistant_message.content}")

            # 4. Handle Tool Calls
            if assistant_message.tool_calls:
                for tool_call in assistant_message.tool_calls:
                    action_key = tool_call.function.name
                    args = json.loads(tool_call.function.arguments)

                    logging.info(f"Executing tool call: {action_key} with {args}")

                    try:
                        result = await self._execute_tool(session_id, driver, action_key, args, web_eles)
                        messages.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": action_key,
                            "content": str(result),
                        })
                    except Exception as e:
                        logging.error(f"Tool execution error: {e}")
                        messages.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": action_key,
                            "content": f"Error: {str(e)}",
                        })
            else:
                # Fallback to text extraction if no tool calls (for backward compatibility with SYSTEM_PROMPT)
                action_key, info = extract_information(assistant_message.content or "")
                if action_key == 'answer':
                    return info['content']
                if action_key:
                    self._execute_selenium_action(driver, action_key, info, web_eles)

            # Cleanup rects
            for rect in rects:
                try:
                    driver.execute_script("arguments[0].remove()", rect)
                except:
                    pass

            time.sleep(2)

    async def _execute_tool(self, session_id, driver, action_key, args, web_eles):
        if action_key == "click_element":
            label = args["label"]
            web_eles[label].click()
            return "Clicked element."
        elif action_key == "type_text":
            label = args["label"]
            text = args["text"]
            ele = web_eles[label]
            ele.clear()
            ele.send_keys(text)
            ele.send_keys(Keys.ENTER)
            return "Typed text and pressed Enter."
        elif action_key == "scrape_structured_data":
            query = args["query"]
            schema = args.get("schema")
            html = driver.page_source
            result = self.scraper_service.scrape_structured(html, query, schema)
            return json.dumps(result)
        elif action_key == "update_plan":
            steps = args["steps"]
            self.planner_service.create_plan(session_id, steps)
            return "Plan updated."
        else:
            raise ValueError(f"Unknown tool: {action_key}")

    def _execute_selenium_action(self, driver, action_key, info, web_eles):
        # Legacy action execution
        if action_key == 'click':
            idx = int(info[0])
            web_eles[idx].click()
        elif action_key == 'type':
            idx = int(info['number'])
            content = info['content']
            ele = web_eles[idx]
            ele.clear()
            ele.send_keys(content)
            ele.send_keys(Keys.ENTER)
        elif action_key == 'scroll':
            direction = info['content']
            amount = 500 if direction == 'down' else -500
            driver.execute_script(f"window.scrollBy(0, {amount});")
        elif action_key == 'wait':
            time.sleep(5)
        elif action_key == 'goback':
            driver.back()
        elif action_key == 'google':
            driver.get('https://www.google.com')
        else:
            raise NotImplementedError(f"Action {action_key} not implemented")

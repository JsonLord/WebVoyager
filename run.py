import platform
import argparse
import time
import json
import re
import os
import shutil
import logging

from PIL import Image, ImageDraw
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

from prompts import SYSTEM_PROMPT, SYSTEM_PROMPT_TEXT_ONLY, PERSONA_SYSTEM_PROMPT
from openai import OpenAI, APIError
import httpx
from utils import get_web_element_rect, encode_image, extract_information, print_message,\
    get_webarena_accessibility_tree, get_pdf_retrieval_ans_from_assistant, clip_message_and_obs, clip_message_and_obs_text_only


def setup_logger(folder_path):
    log_file_path = os.path.join(folder_path, 'agent.log')

    logger = logging.getLogger()
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()

    handler = logging.FileHandler(log_file_path)
    formatter = logging.Formatter('%(message)s') # Keep logs clean
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def driver_config(args):
    options = webdriver.ChromeOptions()

    if args.save_accessibility_tree:
        args.force_device_scale = True

    if args.force_device_scale:
        options.add_argument("--force-device-scale-factor=1")
    if args.headless:
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument(
            "--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )
    options.add_experimental_option(
        "prefs", {
            "download.default_directory": args.download_dir,
            "plugins.always_open_pdf_externally": True
        }
    )
    return options


def format_msg(it, init_msg, pdf_obs, warn_obs, web_img_b64, web_text):
    if it == 1:
        init_msg += f"I've provided the tag name of each element and the text it contains (if text exists). Note that <textarea> or <input> may be textbox, but not exactly. Please focus more on the screenshot and then refer to the textual information.\n{web_text}"
        init_msg_format = {
            'role': 'user',
            'content': [
                {'type': 'text', 'text': init_msg},
            ]
        }
        init_msg_format['content'].append({"type": "image_url",
                                           "image_url": {"url": f"data:image/png;base64,{web_img_b64}"}})
        return init_msg_format
    else:
        # Similar formatting for subsequent messages
        content = f"Observation:{warn_obs} please analyze the attached screenshot and give the Thought and Action. I've provided the tag name of each element and the text it contains (if text exists). Note that <textarea> or <input> may be textbox, but not exactly. Please focus more on the screenshot and then refer to the textual information.\n{web_text}"
        if pdf_obs:
            content = f"Observation: {pdf_obs} Please analyze the response given by Assistant, then consider whether to continue iterating or not. The screenshot of the current page is also attached, give the Thought and Action.\n{web_text}"
        
        return {
            'role': 'user',
            'content': [
                {'type': 'text', 'text': content},
                {'type': 'image_url', 'image_url': {"url": f"data:image/png;base64,{web_img_b64}"}}
            ]
        }

def call_gpt4v_api(args, client_blablador, client_openai, messages):
    retry_times = 0
    wait_time = 5  # Initial wait time
    while True:
        try:
            if not args.text_only:
                logging.info('Calling gpt4v API...')
                openai_response = client_openai.chat.completions.create(
                    model="gpt-4-turbo", messages=messages, max_tokens=1000, seed=args.seed
                )
            else:
                logging.info('Calling gpt4 API...')
                openai_response = client_blablador.chat.completions.create(
                    model='alias-large', messages=messages, max_tokens=1000, seed=args.seed, timeout=30
                )

            prompt_tokens = openai_response.usage.prompt_tokens
            completion_tokens = openai_response.usage.completion_tokens

            logging.info(f'Prompt Tokens: {prompt_tokens}; Completion Tokens: {completion_tokens}')

            gpt_call_error = False
            yield "result", (prompt_tokens, completion_tokens, gpt_call_error, openai_response)
            return

        except APIError as e:
            if e.status_code == 501:
                logging.info(f'APIError with status code 501 occurred. Retrying in {wait_time} seconds...')
                yield "status", "observing"
                time.sleep(wait_time)
                wait_time *= 2  # Exponential backoff
            else:
                logging.info(f'Error occurred, retrying. Error type: {type(e).__name__}')
                time.sleep(15)

        except Exception as e:
            logging.info(f'Error occurred, retrying. Error type: {type(e).__name__}')

            if type(e).__name__ == 'RateLimitError':
                time.sleep(10)

            elif type(e).__name__ == 'InvalidRequestError':
                gpt_call_error = True
                yield "result", (None, None, gpt_call_error, None)
                return

            else:
                gpt_call_error = True
                yield "result", (None, None, gpt_call_error, None)
                return

        retry_times += 1
        if retry_times == 10:
            logging.info('Retrying too many times')
            yield "result", (None, None, True, None)
            return


def exec_action_click(info, web_ele, driver_task, task_dir, it_action):
    driver_task.execute_script("arguments[0].setAttribute('target', '_self')", web_ele)
    web_ele.click()
    time.sleep(3)
    img_path = os.path.join(task_dir, f'screenshot{it_action}.png')
    driver_task.save_screenshot(img_path)
    try:
        location = web_ele.location
        size = web_ele.size
        img = Image.open(img_path)
        draw = ImageDraw.Draw(img)
        draw.rectangle([location['x'], location['y'], location['x'] + size['width'], location['y'] + size['height']], outline="red", width=3)
        img.save(img_path)
    except Exception as e:
        logging.error(f"Error highlighting element: {e}")


def exec_action_type(info, web_ele, driver_task, task_dir, it_action):
    warn_obs = ""
    type_content = info['content']

    ele_tag_name = web_ele.tag_name.lower()
    ele_type = web_ele.get_attribute("type")
    # outer_html = web_ele.get_attribute("outerHTML")
    if (ele_tag_name != 'input' and ele_tag_name != 'textarea') or (ele_tag_name == 'input' and ele_type not in ['text', 'search', 'password', 'email', 'tel']):
        warn_obs = f"note: The web element you're trying to type may not be a textbox, and its tag name is <{web_ele.tag_name}>, type is {ele_type}."
    try:
        # Not always work to delete
        web_ele.clear()
        # Another way to delete
        if platform.system() == 'Darwin':
            web_ele.send_keys(Keys.COMMAND + "a")
        else:
            web_ele.send_keys(Keys.CONTROL + "a")
        web_ele.send_keys(" ")
        web_ele.send_keys(Keys.BACKSPACE)
    except:
        pass

    actions = ActionChains(driver_task)
    actions.click(web_ele).perform()
    actions.pause(1)

    try:
        driver_task.execute_script("""window.onkeydown = function(e) {if(e.keyCode == 32 && e.target.type != 'text' && e.target.type != 'textarea' && e.target.type != 'search') {e.preventDefault();}};""")
    except:
        pass

    actions.send_keys(type_content)
    actions.pause(2)

    actions.send_keys(Keys.ENTER)
    actions.perform()
    time.sleep(10)
    img_path = os.path.join(task_dir, f'screenshot{it_action}.png')
    driver_task.save_screenshot(img_path)
    try:
        location = web_ele.location
        size = web_ele.size
        img = Image.open(img_path)
        draw = ImageDraw.Draw(img)
        draw.rectangle([location['x'], location['y'], location['x'] + size['width'], location['y'] + size['height']], outline="red", width=3)
        img.save(img_path)
    except Exception as e:
        logging.error(f"Error highlighting element: {e}")
    return warn_obs


def exec_action_scroll(info, web_eles, driver_task, args, obs_info, task_dir, it_action):
    scroll_ele_number = info['number']
    scroll_content = info['content']
    web_ele = None
    if scroll_ele_number == "WINDOW":
        if scroll_content == 'down':
            driver_task.execute_script(f"window.scrollBy(0, {args.window_height*2//3});")
        else:
            driver_task.execute_script(f"window.scrollBy(0, {-args.window_height*2//3});")
    else:
        if not args.text_only:
            scroll_ele_number = int(scroll_ele_number)
            web_ele = web_eles[scroll_ele_number]
        else:
            element_box = obs_info[scroll_ele_number]['union_bound']
            element_box_center = (element_box[0] + element_box[2] // 2, element_box[1] + element_box[3] // 2)
            web_ele = driver_task.execute_script("return document.elementFromPoint(arguments[0], arguments[1]);", element_box_center[0], element_box_center[1])
        actions = ActionChains(driver_task)
        driver_task.execute_script("arguments[0].focus();", web_ele)
        if scroll_content == 'down':
            actions.key_down(Keys.ALT).send_keys(Keys.ARROW_DOWN).key_up(Keys.ALT).perform()
        else:
            actions.key_down(Keys.ALT).send_keys(Keys.ARROW_UP).key_up(Keys.ALT).perform()
    time.sleep(3)
    img_path = os.path.join(task_dir, f'screenshot{it_action}.png')
    driver_task.save_screenshot(img_path)
    if web_ele:
        try:
            location = web_ele.location
            size = web_ele.size
            img = Image.open(img_path)
            draw = ImageDraw.Draw(img)
            draw.rectangle([location['x'], location['y'], location['x'] + size['width'], location['y'] + size['height']], outline="red", width=3)
            img.save(img_path)
        except Exception as e:
            logging.error(f"Error highlighting element: {e}")


def webvoyager_run(args, task, task_dir, persona=None):
    """
    A generator function that yields log messages for each step of the WebVoyager run.
    """
    client_blablador = OpenAI(api_key=args.api_key, base_url=args.api_base_url, http_client=httpx.Client(trust_env=False))
    client_openai = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"), http_client=httpx.Client(trust_env=False))
    options = driver_config(args)
    setup_logger(task_dir)
    
    driver_task = webdriver.Chrome(options=options)
    driver_task.set_window_size(args.window_width, args.window_height)
    
    yield json.dumps({"status": f"Navigating to URL: {task['web']}..."})
    driver_task.get(task['web'])
    time.sleep(5)

    if persona:
        logging.info(f"Applying persona to system prompt: {persona.get('name', 'Unknown')}")
        persona_name = persona.get('name', 'a helpful assistant')
        background = persona.get('background', 'web browsing agent')
        goal = persona.get('goal', persona.get('goals', 'completing the task'))
        tone = persona.get('tone', 'professional')
        syntax_style = persona.get('syntax_style', persona.get('syntax', 'clear'))

        logging.info(f"Persona Name: {persona_name}")
        logging.info(f"Background: {background}")
        logging.info(f"Goal: {goal}")
        logging.info(f"Tone: {tone}")
        logging.info(f"Syntax Style: {syntax_style}")

        system_prompt = PERSONA_SYSTEM_PROMPT.format(
            persona_name=persona_name,
            background=background,
            goal=goal,
            tone=tone,
            syntax_style=syntax_style,
            base_prompt=SYSTEM_PROMPT
        )
    else:
        logging.info("No persona provided. Using default system prompt.")
        system_prompt = SYSTEM_PROMPT

    messages = [{'role': 'system', 'content': system_prompt}]
    init_msg = f"Now given a task: {task['ques']} Please interact with {task['web']} and get the answer."

    for it in range(1, args.max_iter + 1):
        yield json.dumps({"status": f"Taking screenshot (Step {it})..."})
        img_path = os.path.join(task_dir, f'screenshot{it}.png')
        driver_task.save_screenshot(img_path)
        b64_img = encode_image(img_path)
        
        yield json.dumps({"status": f"Extracting web elements (Step {it})..."})
        rects, web_eles, web_eles_text = get_web_element_rect(driver_task, fix_color=args.fix_box_color)
        
        curr_msg = format_msg(it, init_msg, "", "", b64_img, web_eles_text)
        messages.append(curr_msg)
        
        # Log the user message
        yield json.dumps(curr_msg)

        yield json.dumps({"status": f"Sending request to LLM (Step {it})..."})
        for status, result in call_gpt4v_api(args, client_blablador, client_openai, messages):
            if status == "status":
                yield json.dumps({"status": result})
            elif status == "result":
                _, _, _, openai_response = result
                break
        
        if not openai_response:
            yield json.dumps({"error": "API call failed"})
            break
            
        yield json.dumps({"status": f"Processing LLM response (Step {it})..."})
        gpt_4v_res = openai_response.choices[0].message.content
        messages.append({'role': 'assistant', 'content': gpt_4v_res})
        
        # Log the assistant message
        yield json.dumps({'role': 'assistant', 'content': gpt_4v_res})

        if 'rects' in locals() and rects:
            for rect_ele in rects:
                driver_task.execute_script("arguments[0].remove()", rect_ele)

        action_key, info = extract_information(gpt_4v_res.split('Action:')[1].strip())
        
        
        if action_key == 'click':
            click_ele_number = int(info[0])
            web_ele = web_eles[click_ele_number]
            yield json.dumps({"status": f"Executing action: Clicking (Step {it})..."})
            exec_action_click(info, web_ele, driver_task, task_dir, f"{it}_action")

        elif action_key == 'type':
            type_ele_number = int(info['number'])
            web_ele = web_eles[type_ele_number]
            yield json.dumps({"status": f"Executing action: Typing (Step {it})..."})
            exec_action_type(info, web_ele, driver_task, task_dir, f"{it}_action")

        elif action_key == 'scroll':
            yield json.dumps({"status": f"Executing action: Scrolling (Step {it})..."})
            exec_action_scroll(info, web_eles, driver_task, args, None, task_dir, f"{it}_action")

        
        if action_key == 'answer':
            break

    driver_task.quit()

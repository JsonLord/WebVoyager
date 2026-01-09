import platform
import argparse
import time
import json
import re
import os
import shutil
import logging

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

from prompts import SYSTEM_PROMPT, SYSTEM_PROMPT_TEXT_ONLY
from openai import OpenAI
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

# ... (rest of the helper functions remain the same)

def webvoyager_run(args, task, task_dir):
    """
    A generator function that yields log messages for each step of the WebVoyager run.
    """
    client = OpenAI(api_key=args.api_key, http_client=httpx.Client(trust_env=False))
    options = driver_config(args)
    setup_logger(task_dir)

    driver_task = webdriver.Chrome(options=options)
    driver_task.set_window_size(args.window_width, args.window_height)
    driver_task.get(task['web'])
    time.sleep(5)

    messages = [{'role': 'system', 'content': SYSTEM_PROMPT}]
    init_msg = f"Now given a task: {task['ques']} Please interact with {task['web']} and get the answer."

    for it in range(1, args.max_iter + 1):
        img_path = os.path.join(task_dir, f'screenshot{it}.png')
        driver_task.save_screenshot(img_path)
        b64_img = encode_image(img_path)

        rects, web_eles, web_eles_text = get_web_element_rect(driver_task, fix_color=args.fix_box_color)

        curr_msg = format_msg(it, init_msg, "", "", b64_img, web_eles_text)
        messages.append(curr_msg)

        # Log the user message
        yield json.dumps(curr_msg)

        _, _, _, openai_response = call_gpt4v_api(args, client, messages)

        if not openai_response:
            yield json.dumps({"error": "API call failed"})
            break

        gpt_4v_res = openai_response.choices[0].message.content
        messages.append({'role': 'assistant', 'content': gpt_4v_res})

        # Log the assistant message
        yield json.dumps({'role': 'assistant', 'content': gpt_4v_res})

        if 'rects' in locals() and rects:
            for rect_ele in rects:
                driver_task.execute_script("arguments[0].remove()", rect_ele)

        action_key, info = extract_information(gpt_4v_res.split('Action:')[1].strip())

        # ... (action execution logic remains the same)
        if action_key == 'answer':
            break

    driver_task.quit()

import gradio as gr
from fastapi import FastAPI
import argparse
import os
import sys
import tempfile
import threading
import json
import traceback
import concurrent.futures
import time
import base64
from run import webvoyager_run
from utils import generate_persona
import re
import logging
from gradio_logsview import LogsView

# Set up FastAPI for health checks
app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

def format_log_for_gradio(log_content):
    """
    Formats the raw log content into a more readable format for the Gradio UI.
    """
    try:
        # The log content may or may not be a valid JSON string.
        # It could be a simple string like "Observing...".
        log_data = json.loads(log_content)
    except (json.JSONDecodeError, TypeError):
        return log_content

    formatted_output = ""
    
    if log_data.get('role') == 'user':
        # This is the initial prompt
        formatted_output += "--- Starting Task ---\n"
        content = log_data['content'][0]['text']
        task_match = re.search(r'Now given a task: (.*?)\s+Please interact with', content)
        if task_match:
            formatted_output += f"Task: {task_match.group(1)}\n"
        
        # Check for image URL and replace it with a placeholder
        if len(log_data['content']) > 1 and log_data['content'][1].get('type') == 'image_url':
            formatted_output += "Processing screenshot...\n"

    elif log_data.get('role') == 'assistant':
        # This is the agent's response
        content = log_data['content']
        thought_match = re.search(r'Thought: (.*?)\nAction:', content, re.DOTALL)
        action_match = re.search(r'Action: (.*)', content, re.DOTALL)
        
        if thought_match:
            formatted_output += f"Thought: {thought_match.group(1).strip()}\n"
        if action_match:
            action = action_match.group(1).strip()
            # Make action more human-readable
            action = action.replace("click", "Clicking element").replace("type", "Typing into element").replace("scroll", "Scrolling")
            formatted_output += f"Action: {action}\n"

    elif 'error' in log_data:
        formatted_output += f"An error occurred: {log_data['error']}. Please check the container logs for more details."

    return formatted_output


def run_script_for_gradio(url, task, persona_criteria=None):
    """
    A wrapper to run the webvoyager script for Gradio, capturing output and screenshots.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        task_file_path = os.path.join(temp_dir, 'task.jsonl')
        with open(task_file_path, 'w') as f:
            f.write(f'{{"id": "custom_task", "web": "{url}", "ques": "{task}"}}')

        args = argparse.Namespace(
            test_file=task_file_path,
            max_iter=5,
            api_key=os.environ.get("BLABLADOR_API_KEY"),
            api_base_url="https://api.helmholtz-blablador.fz-juelich.de/v1",
            api_model="alias-fast",
            output_dir=os.path.join(temp_dir, 'results'),
            seed=None,
            max_attached_imgs=1,
            temperature=1.0,
            download_dir=os.path.join(temp_dir, 'downloads'),
            text_only=False,
            headless=True,
            save_accessibility_tree=False,
            force_device_scale=False,
            window_width=1024,
            window_height=768,
            fix_box_color=False
        )

        os.makedirs(args.output_dir, exist_ok=True)
        os.makedirs(args.download_dir, exist_ok=True)
        
        task_dir = os.path.join(args.output_dir, 'taskcustom_task')
        os.makedirs(task_dir, exist_ok=True)

        # Import run here to avoid circular dependency if any, but mainly to use its setup_logger
        from run import setup_logger
        setup_logger(task_dir)

        full_log = ""
        last_screenshot_html = "" # Keep track of the last image to ensure we always show something
        debug_log = ""
        raw_log_file_path = os.path.join(task_dir, "raw_log.txt")
        # Ensure the raw_log file exists
        with open(raw_log_file_path, "w") as f:
            f.write("")

        persona = None
        if persona_criteria:
            full_log += "--- Initializing TinyTroupe Persona ---\n"
            yield last_screenshot_html, full_log, debug_log, "--- Initializing TinyTroupe Persona ---"

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(generate_persona, persona_criteria)

                # Poll for log updates while persona is being generated
                while not future.done():
                    try:
                        with open(os.path.join(task_dir, 'agent.log'), 'r') as f:
                            new_debug_log = f.read()
                            if new_debug_log != debug_log:
                                # Extract last few lines as status update
                                status_lines = [l for l in new_debug_log[len(debug_log):].split('\n') if l.strip()]
                                if status_lines:
                                    last_status = status_lines[-1]
                                    yield last_screenshot_html, full_log, new_debug_log, f"Status: {last_status}"
                                debug_log = new_debug_log
                    except Exception:
                        pass
                    time.sleep(1.0)

                persona = future.result()

            # Final debug log read after persona generation
            try:
                with open(os.path.join(task_dir, 'agent.log'), 'r') as f:
                    debug_log = f.read()
            except Exception:
                pass

            if persona:
                full_log += f"Persona generated: {persona.get('name', 'Unknown')}\n"
                yield last_screenshot_html, full_log, debug_log, "Raw log will be available here."
            else:
                full_log += "Failed to generate persona. STOPPING execution as requested.\n"
                yield last_screenshot_html, full_log, debug_log, "Task stopped due to persona generation failure."
                return

        try:
            # We'll get real-time updates by iterating through the run function
            with open(raw_log_file_path, "w") as raw_log_file:
                for i, log_entry in enumerate(webvoyager_run(args, {"id": "custom_task", "web": url, "ques": task}, task_dir, persona=persona)):
                    
                    raw_log_file.write(log_entry + '\n')
                    raw_log_file.flush()

                    try:
                        log_data = json.loads(log_entry)
                        if log_data.get("status"):
                            full_log += f"{log_data['status']}\n"
                            yield last_screenshot_html, full_log, debug_log, f"Log file: {raw_log_file_path}"
                            continue
                    except (json.JSONDecodeError, AttributeError):
                        pass # Not a status update, proceed as normal

                    formatted_log = format_log_for_gradio(log_entry)
                    if formatted_log:
                        full_log += f"--- Step {i+1} ---\n{formatted_log}\n"
                    
                    # Read agent.log for debug info
                    try:
                        with open(os.path.join(task_dir, 'agent.log'), 'r') as f:
                            debug_log = f.read()
                    except FileNotFoundError:
                        debug_log = "agent.log not found."

                    current_screenshot = None
                    try:
                        # Get all png files starting with 'screenshot'
                        files = [f for f in os.listdir(task_dir) if f.startswith('screenshot') and f.endswith('.png')]
                        if files:
                            # Sort by number (e.g. screenshot1, screenshot1_action, screenshot2)
                            files.sort(key=lambda x: [int(c) if c.isdigit() else c for c in re.split(r'(\d+)', x)])
                            current_screenshot = os.path.join(task_dir, files[-1])
                    except Exception:
                        pass # If directory read fails momentarily, just skip update

                    if current_screenshot and os.path.exists(current_screenshot):
                        with open(current_screenshot, "rb") as img_file:
                            b64_data = base64.b64encode(img_file.read()).decode('utf-8')
                            last_screenshot_html = f"<img src='data:image/png;base64,{b64_data}' style='max-width: 100%;'>"
                    
                    yield last_screenshot_html, full_log, debug_log, f"Log file: {raw_log_file_path}"

        except Exception as e:
            tb = traceback.format_exc()
            full_log += f"An error occurred: {e}\n\nFull Traceback:\n{tb}"
            yield last_screenshot_html, full_log, debug_log, f"Error: {e}"

with gr.Blocks() as iface:
    gr.Markdown("# WebVoyager")
    gr.Markdown("An LMM-powered web agent that can complete user instructions end-to-end.")

    with gr.Row():
        with gr.Column():
            url_input = gr.Textbox(label="URL", placeholder="Enter the URL of the website")
            task_input = gr.Textbox(label="Task", placeholder="Describe the task to perform")
            criteria_input = gr.Textbox(label="Persona Criteria (TinyTroupe)", placeholder="Describe the persona you want (e.g. salesman for CRM)")
            submit_btn = gr.Button("Submit")

        with gr.Column():
            screenshot_output = gr.HTML(label="Agent's View")
            agent_output = gr.Textbox(label="Agent Output", lines=20, interactive=False)

    with gr.Row():
        debug_output = gr.Textbox(label="Debug Log", lines=10, interactive=False)
        raw_log_status = gr.Markdown(label="Raw Log Status")

    logs_view = LogsView(label="Internal Process Logs")

    submit_btn.click(
        run_script_for_gradio,
        inputs=[url_input, task_input, criteria_input],
        outputs=[screenshot_output, agent_output, debug_output, raw_log_status]
    )

# Mount Gradio to FastAPI
app = gr.mount_gradio_app(app, iface, path="/")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)

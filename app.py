import gradio as gr
import argparse
import os
import sys
import tempfile
import threading
import json
import traceback
from run import webvoyager_run
from utils import generate_persona
import re

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


def run_script_for_gradio(url, task, business_description=None, customer_profile=None):
    """
    A wrapper to run the webvoyager script for Gradio, capturing output and screenshots.
    """
    persona = None
    if business_description and customer_profile:
        yield None, "Generating persona from TinyTroupe...", "", None
        persona = generate_persona(business_description, customer_profile)
        if persona:
            yield None, f"Persona generated: {persona.get('name', 'Unknown')}\n", "", None
        else:
            yield None, "Failed to generate persona. Proceeding with default persona.\n", "", None

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

        full_log = ""
        last_screenshot = None # Keep track of the last image to ensure we always show something
        debug_log = ""
        raw_log_file_path = os.path.join(task_dir, "raw_log.txt")

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
                            yield last_screenshot, full_log, debug_log, raw_log_file_path
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
                        last_screenshot = current_screenshot
                    
                    yield last_screenshot, full_log, debug_log, raw_log_file_path

        except Exception as e:
            tb = traceback.format_exc()
            full_log += f"An error occurred: {e}\n\nFull Traceback:\n{tb}"
            yield last_screenshot, full_log, debug_log, raw_log_file_path

iface = gr.Interface(
    fn=run_script_for_gradio,
    inputs=[
        gr.Textbox(label="URL", placeholder="Enter the URL of the website"),
        gr.Textbox(label="Task", placeholder="Describe the task to perform"),
        gr.Textbox(label="Business Description (TinyTroupe)", placeholder="What is your business about?"),
        gr.Textbox(label="Customer Profile (TinyTroupe)", placeholder="Information about your customer profile"),
    ],
    outputs=[
        gr.Image(label="Agent's View", type="filepath"),
        gr.Textbox(label="Agent Output", lines=20, interactive=False),
        gr.Textbox(label="Debug Log", lines=10, interactive=False),
        gr.File(label="Raw Log File"),
    ],
    title="WebVoyager",
    description="An LMM-powered web agent that can complete user instructions end-to-end.",
)

if __name__ == "__main__":
    iface.launch()
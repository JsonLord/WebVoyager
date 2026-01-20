import gradio as gr
import argparse
import os
import sys
import tempfile
import threading
import json
import traceback
from run import webvoyager_run
import re

def format_log_for_gradio(log_content):
    """
    Formats the raw log content into a more readable format for the Gradio UI.
    """
    # Extract the JSON part of the log
    json_match = re.search(r'\[(\{.*?\})\]', log_content, re.DOTALL)
    if not json_match:
        return log_content

    try:
        log_data = json.loads(json_match.group(1))
        formatted_output = ""
        
        if 'role' in log_data and log_data['role'] == 'user':
            # This is the initial prompt, let's summarize it
            formatted_output += "--- Initial Prompt ---\n"
            content = log_data['content'][0]['text']
            task_match = re.search(r'Now given a task: (.*?)\s+Please interact with', content)
            if task_match:
                formatted_output += f"Task: {task_match.group(1)}\n\n"

        elif 'role' in log_data and log_data['role'] == 'assistant':
            # This is the agent's response
            content = log_data['content']
            thought_match = re.search(r'Thought: (.*?)\nAction:', content, re.DOTALL)
            action_match = re.search(r'Action: (.*)', content, re.DOTALL)
            
            if thought_match:
                formatted_output += f"Thought: {thought_match.group(1).strip()}\n"
            if action_match:
                formatted_output += f"Action: {action_match.group(1).strip()}\n"

        return formatted_output

    except json.JSONDecodeError:
        return log_content # Return raw log if JSON parsing fails

def run_script_for_gradio(url, task):
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
            api_key=os.environ.get("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY"),
            api_model="gpt-4-turbo",
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

        try:
            # We'll get real-time updates by iterating through the run function
            for i, log_entry in enumerate(webvoyager_run(args, {"id": "custom_task", "web": url, "ques": task}, task_dir)):
                
                formatted_log = format_log_for_gradio(log_entry)
                if formatted_log:
                    full_log += f"--- Step {i+1} ---\n{formatted_log}\n"
                
                # --- FIX START: robustly find the latest screenshot ---
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

                # If we found a new screenshot, update our tracker. 
                # If not, we keep yielding the old one so the image doesn't vanish.
                if current_screenshot and os.path.exists(current_screenshot):
                    last_screenshot = current_screenshot
                
                yield last_screenshot, full_log
                # --- FIX END ---

        except Exception as e:
            tb = traceback.format_exc()
            full_log += f"An error occurred: {e}\n\nFull Traceback:\n{tb}"
            yield last_screenshot, full_log

iface = gr.Interface(
    fn=run_script_for_gradio,
    inputs=[
        gr.Textbox(label="URL", placeholder="Enter the URL of the website"),
        gr.Textbox(label="Task", placeholder="Describe the task to perform"),
    ],
    outputs=[
        gr.Image(label="Agent's View", type="filepath"),
        gr.Textbox(label="Agent Output", lines=20, interactive=False),
    ],
    title="WebVoyager",
    description="An LMM-powered web agent that can complete user instructions end-to-end.",
)

if __name__ == "__main__":
    iface.launch()
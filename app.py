import gradio as gr
import argparse
import os
import sys
import tempfile
import threading
import json
import traceback
from run import webvoyager_run

def run_script_for_gradio(url, task):
    """
    A wrapper to run the webvoyager script for Gradio, capturing output.
    """
    # Create a temporary directory for this run
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a temporary file for the task
        task_file_path = os.path.join(temp_dir, 'task.jsonl')
        with open(task_file_path, 'w') as f:
            f.write(f'{{"id": "custom_task", "web": "{url}", "ques": "{task}"}}')

        # Setup arguments
        args = argparse.Namespace(
            test_file=task_file_path,
            max_iter=5,
            api_key=os.environ.get("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY"),
            api_model="gpt-4-vision-preview",
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

        # Create necessary directories
        os.makedirs(args.output_dir, exist_ok=True)
        os.makedirs(args.download_dir, exist_ok=True)

        # Capture stdout
        original_stdout = sys.stdout
        sys.stdout = captured_output = threading.local()
        captured_output.value = ""

        def stream_catcher():
            while True:
                try:
                    # This is a bit of a hack to get real-time output
                    # A better solution would be to modify the logger to write to a queue
                    with open(os.path.join(args.output_dir, 'taskcustom_task', 'agent.log'), 'r') as f:
                        captured_output.value = f.read()
                except FileNotFoundError:
                    pass # Log file might not be created yet

        stream_thread = threading.Thread(target=stream_catcher)
        stream_thread.daemon = True
        stream_thread.start()

        output = ""
        try:
            with open(task_file_path, 'r', encoding='utf-8') as f:
                task_data = [json.loads(line) for line in f]

            for task_item in task_data:
                task_dir = os.path.join(args.output_dir, f'task{task_item["id"]}')
                os.makedirs(task_dir, exist_ok=True)
                webvoyager_run(args, task_item, task_dir)

                # Read the final log
                with open(os.path.join(task_dir, 'agent.log'), 'r') as f:
                    output = f.read()
                yield output

        except Exception as e:
            tb = traceback.format_exc()
            output = f"An error occurred: {e}\n\nFull Traceback:\n{tb}"
            yield output
        finally:
            sys.stdout = original_stdout


iface = gr.Interface(
    fn=run_script_for_gradio,
    inputs=[
        gr.Textbox(label="URL", placeholder="Enter the URL of the website"),
        gr.Textbox(label="Task", placeholder="Describe the task to perform"),
    ],
    outputs=gr.Textbox(label="Agent Output", lines=20, interactive=False),
    title="WebVoyager",
    description="An LMM-powered web agent that can complete user instructions end-to-end.",
)

if __name__ == "__main__":
    iface.launch()

import os
import sys
from huggingface_hub import HfApi

def upload_to_space():
    api = HfApi()
    token = os.environ.get("HF_TOKEN")
    if not token:
        print("Error: HF_TOKEN environment variable not set.")
        sys.exit(1)

    repo_id = "AUXteam/Web-Agent-Internal"

    print(f"Uploading current directory to {repo_id}...")

    try:
        api.upload_folder(
            folder_path=".",
            repo_id=repo_id,
            repo_type="space",
            token=token,
            ignore_patterns=["*.pyc", "__pycache__", "sessions_data", ".pytest_cache", ".git", "hf_upload.py"]
        )
        print("Upload successful!")
    except Exception as e:
        print(f"Upload failed: {e}")

if __name__ == "__main__":
    upload_to_space()

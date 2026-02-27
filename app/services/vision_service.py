import logging
import time
import traceback
import asyncio
import os
from gradio_client import Client, handle_file
from huggingface_hub import login

logger = logging.getLogger(__name__)

class VisionService:
    def __init__(self):
        self.client = None
        self.repo_id = "MinhDS/Florence-2-Demo"
        self._initialize_client()

    def _initialize_client(self):
        logger.info(f"[VisionService] Initializing for {self.repo_id}...")
        try:
            hf_token = os.environ.get("HF_TOKEN")
            if hf_token:
                try:
                    login(token=hf_token)
                    logger.info("[VisionService] Logged in to Hugging Face.")
                except Exception as le:
                    logger.warning(f"[VisionService] HF login failed: {le}")

            # Initialize client.
            # Using clean URL as Client initialization with repo_id was failing with JSONDecodeError in some environments.
            space_url = "https://minhds-florence-2-demo.hf.space"
            logger.info(f"[VisionService] Attempting Client('{space_url}')...")
            self.client = Client(space_url)
            logger.info(f"[VisionService] Client initialized.")
        except Exception as e:
            logger.error(f"[VisionService] Client init error: {e}")

    async def describe_screenshot(self, image_path: str):
        if not self.client:
            self._initialize_client()

        if not self.client:
            return "Visual Analysis Error: Vision service client not initialized."

        # Configuration as requested for cascaded tasks
        task_prompt = "More Detailed Caption + Grounding"
        text_input = "SEE THE WEBSITE CONTENT AND IDENTIFY AREAS TO CLICK"
        model_id = "microsoft/Florence-2-base"

        try:
            logger.info(f"[VisionService] Requesting '{task_prompt}'...")

            # Use asyncio.to_thread for blocking call
            result = await asyncio.to_thread(
                self.client.predict,
                image=handle_file(image_path),
                task_prompt=task_prompt,
                text_input=text_input,
                model_id=model_id,
                api_name="/process_image"
            )

            # Florence-2 returns (text_output, image_output)
            # Forward ONLY the text as requested
            if isinstance(result, (list, tuple)) and len(result) > 0:
                return str(result[0])
            return str(result)

        except Exception as e:
            logger.error(f"[VisionService] Predict failed: {e}")
            return f"Visual Analysis Error: {str(e)}"

vision_service = VisionService()

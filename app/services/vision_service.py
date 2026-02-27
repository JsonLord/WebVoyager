import logging
import time
import traceback
import asyncio
import os
import httpx
from gradio_client import Client, handle_file
from app.core.config import settings

# Configure logging to be more verbose for this service
logger = logging.getLogger(__name__)

class VisionService:
    def __init__(self):
        self.client = None
        self.repo_id = "MinhDS/Florence-2-Demo"
        self._initialize_client()

    def _initialize_client(self):
        hf_token = os.environ.get("HF_TOKEN")
        logger.info(f"[VisionService] Initializing Florence-2 client. Repo: {self.repo_id}")
        logger.info(f"[VisionService] HF_TOKEN detected: {bool(hf_token)}")

        try:
            # Try initializing with hf_token if available
            # Note: The parameter name in gradio_client >= 0.5.0 is hf_token
            if hf_token:
                logger.info("[VisionService] Using HF_TOKEN for initialization...")
                self.client = Client(self.repo_id, hf_token=hf_token)
            else:
                logger.info("[VisionService] No HF_TOKEN found, attempting public access...")
                self.client = Client(self.repo_id)

            logger.info(f"[VisionService] Client successfully connected to {self.repo_id}")
        except Exception as e:
            logger.error(f"[VisionService] ERROR during client initialization: {str(e)}")
            logger.error(traceback.format_exc())

            # Fallback attempt with direct URL if repo_id fails
            try:
                direct_url = f"https://{self.repo_id.replace('/', '-').lower()}.hf.space/"
                logger.info(f"[VisionService] Attempting fallback to direct URL: {direct_url}")
                if hf_token:
                    self.client = Client(direct_url, hf_token=hf_token)
                else:
                    self.client = Client(direct_url)
                logger.info("[VisionService] Fallback client initialized.")
            except Exception as fe:
                logger.error(f"[VisionService] Fallback also failed: {str(fe)}")

    async def describe_screenshot(self, image_path: str):
        if not self.client:
            logger.warning("[VisionService] Client not available. Attempting re-initialization...")
            self._initialize_client()
            if not self.client:
                return "Vision analysis unavailable: Client initialization failed."

        if not os.path.exists(image_path):
            logger.error(f"[VisionService] Screenshot file not found: {image_path}")
            return "Vision analysis unavailable: Screenshot missing."

        # As requested: Cascased task with More Detailed Caption + Grounding
        # Based on user documentation, we'll try the task prompt directly if supported
        # or follow the logic of a cascaded job.
        task_prompt = "More Detailed Caption" # Default fallback
        # The user's example output showed grounding data too.
        # Let's try "More Detailed Caption + Grounding" as requested.
        requested_prompt = "More Detailed Caption + Grounding"

        try:
            logger.info(f"[VisionService] Sending request to Florence-2 API...")
            logger.info(f"[VisionService] Image Path: {image_path}")
            logger.info(f"[VisionService] Requested Prompt: {requested_prompt}")

            start_time = time.time()

            # We wrap the blocking predict call in asyncio.to_thread
            # result[0] is the text output
            result = await asyncio.to_thread(
                self.client.predict,
                image=handle_file(image_path),
                task_prompt=requested_prompt,
                text_input="SEE THE WEBSITE CONTENT AND IDENTIFY AREAS TO CLICK",
                model_id="microsoft/Florence-2-base",
                api_name="/process_image"
            )

            end_time = time.time()
            logger.info(f"[VisionService] API call completed in {end_time - start_time:.2f} seconds.")

            if isinstance(result, (list, tuple)) and len(result) > 0:
                text_output = str(result[0])
            else:
                text_output = str(result)

            logger.info(f"[VisionService] Successfully received visual analysis (Length: {len(text_output)} chars)")
            logger.debug(f"[VisionService] Analysis Output: {text_output}")

            return text_output

        except Exception as e:
            logger.error(f"[VisionService] ERROR during API call: {str(e)}")
            logger.error(traceback.format_exc())

            # If the specific prompt fails, try a simpler fallback
            logger.info("[VisionService] Attempting fallback to 'More Detailed Caption'...")
            try:
                result = await asyncio.to_thread(
                    self.client.predict,
                    image=handle_file(image_path),
                    task_prompt="More Detailed Caption",
                    text_input=None,
                    model_id="microsoft/Florence-2-base",
                    api_name="/process_image"
                )
                if isinstance(result, (list, tuple)) and len(result) > 0:
                    return str(result[0])
                return str(result)
            except Exception as e2:
                logger.error(f"[VisionService] Fallback also failed: {str(e2)}")
                return f"Visual Analysis Error: {str(e)}"

vision_service = VisionService()

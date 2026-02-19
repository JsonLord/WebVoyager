import logging
import time
import traceback
from gradio_client import Client, handle_file
from app.core.config import settings

class VisionService:
    def __init__(self):
        self.client = None
        self.endpoint = "MinhDS/Florence-2-Demo"
        try:
            logging.info(f"[VisionService] Initializing client for {self.endpoint}...")
            self.client = Client(self.endpoint)
            logging.info(f"[VisionService] Client initialized successfully.")
        except Exception as e:
            logging.error(f"[VisionService] Failed to initialize client: {e}")
            logging.error(traceback.format_exc())

    async def describe_screenshot(self, image_path: str):
        if not self.client:
            logging.warning("[VisionService] describe_screenshot called but client is not available.")
            return "Vision service not available."

        task_prompt = "More Detailed Caption"
        model_id = "microsoft/Florence-2-base"

        try:
            logging.info(f"[VisionService] Starting description for {image_path}...")
            logging.info(f"[VisionService] Task: {task_prompt}, Model: {model_id}")

            start_time = time.time()

            # Note: client.predict is synchronous in gradio_client,
            # but we are in an async function. For now keeping it simple as it was.
            result = self.client.predict(
                image=handle_file(image_path),
                task_prompt=task_prompt,
                text_input=None,
                model_id=model_id,
                api_name="/process_image"
            )

            duration = time.time() - start_time
            logging.info(f"[VisionService] API call completed in {duration:.2f} seconds.")

            # Log result type and structure for debugging
            logging.info(f"[VisionService] Result type: {type(result)}")

            description = ""
            if isinstance(result, (list, tuple)) and len(result) > 0:
                description = str(result[0])
                logging.info(f"[VisionService] Description extracted (length: {len(description)}).")
            else:
                description = str(result)
                logging.info(f"[VisionService] Result was not a list/tuple, using string representation.")

            logging.debug(f"[VisionService] Description snippet: {description[:200]}...")
            return description

        except Exception as e:
            logging.error(f"[VisionService] Vision API call failed for {image_path}: {e}")
            logging.error(traceback.format_exc())
            return f"Error describing screenshot: {str(e)}"

vision_service = VisionService()

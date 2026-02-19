import logging
from gradio_client import Client, handle_file
from app.core.config import settings

class VisionService:
    def __init__(self):
        self.client = None
        try:
            self.client = Client("MinhDS/Florence-2-Demo")
        except Exception as e:
            logging.error(f"Failed to initialize Florence-2 client: {e}")

    async def describe_screenshot(self, image_path: str):
        if not self.client:
            return "Vision service not available."

        try:
            logging.info(f"Calling Florence-2 vision API for {image_path}...")
            # Using 'More Detailed Caption' for rich textual description
            # We use a long timeout as vision tasks can be slow
            result = self.client.predict(
                image=handle_file(image_path),
                task_prompt="More Detailed Caption",
                text_input=None,
                model_id="microsoft/Florence-2-base",
                api_name="/process_image"
            )
            # result[0] is the text output, result[1] is the output image (which we ignore)
            if isinstance(result, (list, tuple)) and len(result) > 0:
                return str(result[0])
            return str(result)
        except Exception as e:
            logging.error(f"Vision API call failed: {e}")
            return f"Error describing screenshot: {str(e)}"

vision_service = VisionService()

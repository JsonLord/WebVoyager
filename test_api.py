from gradio_client import Client

client = Client("https://auxteam-webvoyager-vision-enhancement.hf.space/")
result = client.predict(
    "https://www.google.com",
    "test",
    api_name="/run_script_for_gradio"
)
print(result)

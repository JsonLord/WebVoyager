import logging
from gradio_client import Client
import sys

logging.basicConfig(level=logging.INFO)

def test_init():
    repo_id = "MinhDS/Florence-2-Demo"
    print(f"Testing Client('{repo_id}')...")
    try:
        client = Client(repo_id)
        print("Success!")
        print(f"API Info: {client.view_api(all_endpoints=True)}")
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    test_init()

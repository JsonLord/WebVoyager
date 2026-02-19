import httpx
import time
import pytest
import os

BASE_URL = "http://127.0.0.1:8000"

def test_session_lifecycle():
    print("Testing session lifecycle...")
    with httpx.Client(timeout=30.0) as client:
        response = client.post(f"{BASE_URL}/sessions", json={})
        assert response.status_code == 200
        session_id = response.json()["session_id"]
        assert session_id is not None

        # 2. Check session exists in directory
        assert os.path.exists(f"sessions/{session_id}")

        # 3. Delete session
        response = client.delete(f"{BASE_URL}/sessions/{session_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "deleted"
    print("Session lifecycle test passed!")

def test_scrape_endpoint():
    print("Testing scrape endpoint...")
    with httpx.Client(timeout=60.0) as client:
        # Create session
        resp = client.post(f"{BASE_URL}/sessions", json={"session_id": "test_scrape"})
        session_id = resp.json()["session_id"]

        try:
            # Scrape
            scrape_resp = client.post(
                f"{BASE_URL}/sessions/{session_id}/scrape",
                json={"query": "what is the title of this page?"}
            )
            print(f"Scrape response status: {scrape_resp.status_code}")
            if scrape_resp.status_code == 200:
                print(f"Scrape result: {scrape_resp.json()}")
            else:
                print(f"Scrape failed: {scrape_resp.text}")
        finally:
            client.delete(f"{BASE_URL}/sessions/{session_id}")
    print("Scrape endpoint test completed!")

def test_execute_endpoint():
    print("Testing execute endpoint...")
    with httpx.Client(timeout=120.0) as client:
        # Create session
        resp = client.post(f"{BASE_URL}/sessions", json={"session_id": "test_execute"})
        session_id = resp.json()["session_id"]

        try:
            # Execute task
            exec_resp = client.post(
                f"{BASE_URL}/sessions/{session_id}/execute",
                json={"query": "go to google.com", "max_iter": 1}
            )
            print(f"Execute response status: {exec_resp.status_code}")
            if exec_resp.status_code == 200:
                print(f"Execute result: {exec_resp.json()}")
            else:
                print(f"Execute failed (expected if no API key): {exec_resp.text}")
        finally:
            client.delete(f"{BASE_URL}/sessions/{session_id}")
    print("Execute endpoint test completed!")

if __name__ == "__main__":
    test_session_lifecycle()
    test_scrape_endpoint()
    test_execute_endpoint()

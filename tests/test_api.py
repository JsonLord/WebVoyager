import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to Web-Agent-Internal API"}

def test_create_session():
    response = client.post("/api/v1/sessions/")
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert data["status"] == "initialized"

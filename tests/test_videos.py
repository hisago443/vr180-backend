import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_create_video():
    response = client.post("/videos/", json={"title": "Test Video", "description": "A test video"})
    assert response.status_code == 200
    assert response.json() == {"message": "Video created successfully"}
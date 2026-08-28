"""Unit tests for Pydantic models, request validation, and API authentication."""
import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient
from app.main import app
from app.models import GenerateRequest
from app.config import settings

client = TestClient(app)

def test_generate_request_validation_valid():
    req = GenerateRequest(prompt="A cinematic sunset over Paris", count=4, aspect_ratio="16:9")
    assert req.prompt == "A cinematic sunset over Paris"
    assert req.count == 4
    assert req.aspect_ratio == "16:9"

def test_generate_request_validation_empty_prompt():
    with pytest.raises(ValidationError):
        GenerateRequest(prompt="   ", count=4)

def test_generate_request_validation_non_four_count():
    with pytest.raises(ValidationError):
        GenerateRequest(prompt="Valid prompt", count=1)
    with pytest.raises(ValidationError):
        GenerateRequest(prompt="Valid prompt", count=2)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_status_endpoint():
    response = client.get("/status")
    assert response.status_code == 200
    data = response.json()
    assert "browser_running" in data
    assert "model" in data
    assert data["model"] == "Nano Banana 2"

def test_generate_endpoint_validation_error():
    response = client.post("/generate", json={"prompt": "test", "count": 2})
    assert response.status_code == 422
    data = response.json()
    assert data["success"] is False
    assert data["error"] == "ONLY_FOUR_OUTPUTS_SUPPORTED"

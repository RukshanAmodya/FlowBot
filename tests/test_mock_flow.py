"""Mocked flow tests verifying generation locking, response formats, and error handling."""
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.services.session_manager import session_manager
from app.services.flow_adapter import FlowAutomationException

client = TestClient(app)

@pytest.mark.asyncio
async def test_mock_successful_generation(tmp_path):
    mock_files = []
    for i in range(1, 5):
        f = tmp_path / f"image_{i}.png"
        f.write_bytes(b"\x89PNG\r\n\x1a\nfakeimage")
        mock_files.append(f)

    with patch("app.services.flow_browser.GoogleFlowBrowser.generate_images", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_files

        response = client.post(
            "/generate",
            json={"prompt": "Realistic landscape", "count": 4, "aspect_ratio": "16:9"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["count"] == 4
        assert data["model"] == "Nano Banana 2"
        assert len(data["images"]) == 4
        assert "zip_url" in data

@pytest.mark.asyncio
async def test_mock_concurrency_lock():
    await session_manager.lock.acquire()
    try:
        response = client.post(
            "/generate",
            json={"prompt": "Second request while locked", "count": 4}
        )
        assert response.status_code == 409
        data = response.json()["detail"]
        assert data["success"] is False
        assert data["error"] == "GENERATION_IN_PROGRESS"
    finally:
        session_manager.lock.release()

@pytest.mark.asyncio
async def test_mock_model_unavailable_error():
    with patch("app.services.flow_browser.GoogleFlowBrowser.generate_images", new_callable=AsyncMock) as mock_gen:
        mock_gen.side_effect = FlowAutomationException(
            "NANO_BANANA_2_UNAVAILABLE",
            "Nano Banana 2 could not be selected in the current Google Flow session."
        )

        response = client.post(
            "/generate",
            json={"prompt": "Prompt needing model", "count": 4}
        )
        assert response.status_code == 400
        data = response.json()["detail"]
        assert data["success"] is False
        assert data["error"] == "NANO_BANANA_2_UNAVAILABLE"

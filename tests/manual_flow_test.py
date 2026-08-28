"""Manual real Google Flow integration test."""
import os
import pytest
from app.services.flow_browser import GoogleFlowBrowser

@pytest.mark.skipif(
    os.getenv("REAL_FLOW_TEST") != "true",
    reason="Requires active browser profile and REAL_FLOW_TEST=true"
)
@pytest.mark.asyncio
async def test_live_google_flow_generation():
    prompt = "A majestic glowing crystal tree on a mountain top, photorealistic volumetric lighting"
    files = await GoogleFlowBrowser.generate_images(
        prompt=prompt,
        generation_id="live_test_001",
        count=4,
        aspect_ratio="16:9"
    )
    assert len(files) == 4
    for f in files:
        assert f.exists()
        assert f.stat().st_size > 0

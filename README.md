# Google Flow Nano Banana 2 Image Generation API Bot

A local-first Python backend and browser automation service that exposes an HTTP API endpoint to generate, download, and serve 4 photorealistic images from Google Flow using the **Nano Banana 2** model.

The bot utilizes Playwright with a persistent browser profile. The user logs into their Google account manually once, avoiding password storage or security bypasses.

---

## Architecture Overview

`
Client (HTTP POST /generate)
       │
       ▼
 FastAPI Server (run.py)
       │  (asyncio.Lock: single generation at a time)
       ▼
 GoogleFlowBrowser / SessionManager
       │  (Persistent Playwright Context: ./browser_profile)
       ▼
 Google Flow Web UI (https://labs.google/fx/tools/flow)
       ├── 1. Ensure Image Mode
       ├── 2. Select Model: Nano Banana 2
       ├── 3. Set Aspect Ratio (16:9 / 1:1 / 9:16)
       ├── 4. Set Output Count: 4
       ├── 5. Insert Exact User Prompt & Click Generate
       ├── 6. State & Progress Detection (non-busy, asset count)
       └── 7. Download & Save 4 Generated Image Assets
       │
       ▼
 Static File Serving & Zip Archiving (/generated/{id}/...)
`

---

## Features

- **Zero Credential Storage**: Uses persistent browser profiles (rowser_profile/). Never stores passwords or tokens.
- **Explicit Model Targeting**: Guarantees selection of Nano Banana 2 or returns a structured error NANO_BANANA_2_UNAVAILABLE.
- **Exact 4-Output Guarantee**: Rejects non-4 counts and verifies 4 genuine downloaded image assets.
- **Non-blocking State Detection**: Robust generation monitoring via UI state, progress bars, and DOM asset diffing (no arbitrary sleep(30)).
- **Diagnostics & Error Handling**: Captures full-page screenshots and HTML DOM snapshots under screenshots/ on any timeout or failure.
- **Concurrent Request Protection**: Enforces single generation concurrency using syncio.Lock(), returning HTTP 409 GENERATION_IN_PROGRESS on conflicting calls.
- **Zip Download Endpoint**: Easily retrieve all 4 generated images in a single archive (/generation/{id}/download.zip).
- **UI Discovery Mode**: Built-in inspector (python scripts/inspect_flow.py) to easily maintain DOM selectors if Google updates Flow's UI.

---

## Installation

### Prerequisites
- Python 3.11+
- Playwright & Chromium

### Step 1: Clone and Set Up Virtual Environment

`ash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
`

### Step 2: Install Dependencies

`ash
pip install -r requirements.txt
playwright install chromium
`

### Step 3: Configure Environment

Copy .env.example to .env:
`ash
cp .env.example .env
`

---

## First-Run Experience (Authentication)

1. Launch the interactive login helper:
   `ash
   python scripts/login.py
   `
2. A Chromium window will open with Google Flow.
3. Sign into your Google account manually.
4. Once Google Flow is loaded and your profile avatar is visible, return to your terminal and press **ENTER**.
5. The session is now saved in ./browser_profile and will be reused automatically.

---

## Running the API Server

Start the API server on 127.0.0.1:8000:
`ash
python run.py
`

---

## API Documentation

### 1. Generate Images
**Endpoint:** POST /generate  
**Headers:** Content-Type: application/json (Optional: Authorization: Bearer <API_KEY>)

**Request Body:**
`json
{
  prompt: Create a highly realistic cinematic image of a catastrophic meteor impact near a beautiful French landmark, dramatic sky, physically realistic destruction, detailed architecture, volumetric lighting, photorealistic photography.,
  count: 4,
  aspect_ratio: 16:9
}
`

**Response (200 OK):**
`json
{
  success: true,
  generation_id: a1b2c3d4e5f6,
  model: Nano Banana 2,
  count: 4,
  aspect_ratio: 16:9,
  images: [
    /generated/a1b2c3d4e5f6/image_1.png,
    /generated/a1b2c3d4e5f6/image_2.png,
    /generated/a1b2c3d4e5f6/image_3.png,
    /generated/a1b2c3d4e5f6/image_4.png
  ],
  zip_url: /generation/a1b2c3d4e5f6/download.zip
}
`

### 2. Download Image File
**Endpoint:** GET /generated/{generation_id}/{filename}  
Serves individual image files directly (e.g. /generated/a1b2c3d4e5f6/image_1.png).

### 3. Download All as ZIP
**Endpoint:** GET /generation/{generation_id}/download.zip  
Downloads a zip archive containing image_1.png, image_2.png, image_3.png, and image_4.png.

### 4. Health & Status
- GET /health -> {status: ok}
- GET /status -> Reports browser execution state, authentication status, and active generation lock.

---

## Error Handling

Standardized JSON error responses are returned:

| Error Code | HTTP Status | Description |
|---|---|---|
| GOOGLE_FLOW_AUTHENTICATION_REQUIRED | 400 | Session expired or signed out; run login.py. |
| NANO_BANANA_2_UNAVAILABLE | 400 | Model could not be found/selected in the current Flow UI. |
| ONLY_FOUR_OUTPUTS_SUPPORTED | 422 | Output count was not 4. |
| GENERATION_IN_PROGRESS | 409 | Another generation job is currently holding the browser lock. |
| FLOW_RATE_LIMITED | 429 | Google Flow rate limit or quota exceeded. |
| GENERATION_TIMEOUT | 500 | Generation did not complete within configured timeout. |

---

## Testing & Diagnostics

### Running Unit Tests
`ash
pytest -v
`

### UI Discovery Tool
If Google updates Flow's DOM, run the discovery script to inspect visible elements and save full DOM/screenshots:
`ash
python scripts/inspect_flow.py
`

### Selector Maintenance
All DOM selectors are centrally defined in [pp/services/flow_selectors.py](app/services/flow_selectors.py).

---

## VPS Deployment Considerations

1. **Persistent Profile Setup**: Run scripts/login.py in a desktop environment or via X11/VNC forwarding to establish the initial session in ./browser_profile.
2. **Headless Execution**: Set HEADLESS=true in .env.
3. **Security**:
   - Set API_KEY=your-secret-token in .env.
   - Bind to 127.0.0.1 and place behind a reverse proxy (e.g., Nginx or Caddy) with HTTPS.

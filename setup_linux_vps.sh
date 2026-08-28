#!/usr/bin/env bash
# FlowBot Linux VPS 1-Click Setup Script
set -e

echo "=================================================="
echo "🚀 Setting up FlowBot on Linux VPS..."
echo "=================================================="

# Update and install system dependencies
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv git curl

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate venv & install python dependencies
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Install Playwright browser and system binaries
echo "Installing Chromium and Playwright system dependencies..."
playwright install chromium
playwright install-deps chromium

# Create necessary directories
mkdir -p browser_profile generated temp screenshots logs

echo "=================================================="
echo "✅ FlowBot Setup Complete!"
echo "To run the API server in background on VPS:"
echo "  nohup ./venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 > logs/server.log 2>&1 &"
echo "Or use Docker:"
echo "  docker compose up -d --build"
echo "=================================================="

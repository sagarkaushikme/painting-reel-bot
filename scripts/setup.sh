#!/bin/bash
# ============================================================
# Painting Reel Bot — One-Command Local Setup
# ============================================================
# Usage: bash scripts/setup.sh
# ============================================================

set -e

echo "🎨 Setting up Painting Reel Bot..."
echo ""

# Check Python version
PYTHON_CMD=""
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ Python not found. Please install Python 3.11+"
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
echo "✅ Python found: $PYTHON_VERSION"

# Check FFmpeg
if command -v ffmpeg &> /dev/null; then
    FFMPEG_VERSION=$(ffmpeg -version 2>&1 | head -1)
    echo "✅ FFmpeg found: $FFMPEG_VERSION"
else
    echo "❌ FFmpeg not found!"
    echo "   Install it:"
    echo "   macOS:  brew install ffmpeg"
    echo "   Ubuntu: sudo apt-get install ffmpeg"
    exit 1
fi

# Create virtual environment
if [ ! -d "venv" ]; then
    echo ""
    echo "📦 Creating virtual environment..."
    $PYTHON_CMD -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate venv
source venv/bin/activate

# Install dependencies
echo ""
echo "📥 Installing dependencies..."
pip install -r requirements.txt --quiet
echo "✅ Dependencies installed"

# Copy .env if not exists
if [ ! -f ".env" ]; then
    echo ""
    echo "📝 Creating .env from template..."
    cp .env.example .env
    echo "✅ .env created — please fill in your API keys!"
    echo "   Open .env and add:"
    echo "   - GEMINI_API_KEY"
    echo "   - INSTAGRAM_ACCESS_TOKEN"
    echo "   - INSTAGRAM_USER_ID"
    echo "   - GITHUB_TOKEN"
    echo "   - GITHUB_REPO"
else
    echo "✅ .env already exists"
fi

echo ""
echo "🚀 Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Fill in .env with your API keys"
echo "  2. Activate venv:  source venv/bin/activate"
echo "  3. Run pipeline:   python main.py"
echo "  4. Run tests:      pytest tests/ -v"

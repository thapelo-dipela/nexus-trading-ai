#!/bin/bash
# 🏢 NEXUS Dashboard + Pixel Office Launcher
# Starts the dashboard server with pixel office tab integration

set -e

WORKSPACE_DIR="/Users/thapelodipela/Desktop/nexus-trading-ai"
PORT=${PORT:-3000}

cd "$WORKSPACE_DIR"

echo "🚀 NEXUS Dashboard Launcher"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📁 Workspace: $WORKSPACE_DIR"
echo "🔌 Port: $PORT"
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3."
    exit 1
fi

# Check if Flask is installed
if ! python3 -c "import flask" 2>/dev/null; then
    echo "⚠️  Flask not installed. Installing dependencies..."
    pip install flask flask-cors python-dotenv requests
fi

# Syntax check
echo "🔍 Checking dashboard_server.py syntax..."
python3 -m py_compile dashboard_server.py
echo "✅ Syntax check passed"
echo ""

# Check required files
echo "📋 Verifying required files..."
REQUIRED_FILES=("dashboard.html" "pixel_office.html" "dashboard_server.py")
for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file NOT FOUND"
        exit 1
    fi
done
echo ""

# Verify Office tab integration
echo "🔗 Verifying Office tab integration..."
if grep -q "tab-office" dashboard.html; then
    echo "  ✅ Office tab panel found in dashboard.html"
else
    echo "  ❌ Office tab panel not found"
    exit 1
fi

if grep -q "def pixel_office" dashboard_server.py; then
    echo "  ✅ /office endpoint found in dashboard_server.py"
else
    echo "  ❌ /office endpoint not found"
    exit 1
fi
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "✨ All checks passed! Starting dashboard server..."
echo ""
echo "📊 Dashboard: http://localhost:$PORT"
echo "🏢 Office:    http://localhost:$PORT/?tab=office"
echo ""
echo "📡 Available Endpoints:"
echo "   • /api/market      - Market data"
echo "   • /api/agents      - Agent performance"
echo "   • /api/sentiment   - Sentiment analysis"
echo "   • /api/positions   - Current positions"
echo "   • /api/equity      - Equity curve"
echo "   • /api/risk        - Risk metrics"
echo "   • /api/health      - Health check"
echo "   • /office          - Pixel office iframe"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Start the server
export FLASK_APP=dashboard_server.py
PORT=$PORT python3 dashboard_server.py

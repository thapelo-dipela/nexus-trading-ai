#!/bin/bash
set -e

PROJECT_ROOT="/Users/thapelodipela/Desktop/nexus-trading-ai"

echo "🚀 Starting Nexus Trading AI Services..."
echo ""

# Start Dashboard Server (Python, port 3000)
echo "Starting Dashboard Server on http://localhost:3000..."
cd "$PROJECT_ROOT"
python3 dashboard_server.py &
DASHBOARD_PID=$!
sleep 2

# Start Nanopay Service (Node, port 3001)
echo "Starting Nanopay Service on http://localhost:3001..."
cd "$PROJECT_ROOT/payments/circle_nanopay"
export AGENT_WALLET_KEY='0x076f5d64a7ad0b7f5b5bba0cc191ae017faad45cc2bea74ab68936c1b58b2b04'
export ARC_USDC_ADDRESS='0x3600000000000000000000000000000000000000'
export ARC_RPC_URL='https://rpc.testnet.arc.network'
export PORT='3001'
node dist/index.js &
NANOPAY_PID=$!
sleep 2

echo ""
echo "✓ All services started!"
echo "  Dashboard: http://localhost:3000"
echo "  Nanopay:   http://localhost:3001/api"
echo ""
echo "Process IDs: Dashboard=$DASHBOARD_PID, Nanopay=$NANOPAY_PID"
echo ""
echo "To stop services, run: kill $DASHBOARD_PID $NANOPAY_PID"
echo ""

# Keep script running
wait

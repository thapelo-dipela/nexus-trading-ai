#!/bin/bash

# NEXUS Live Trading Start Script
# Usage: ./run_live.sh [--verbose] [--dry-run]

set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                    NEXUS Trading System                        ║"
echo "║                  Live Trading Mode Launcher                    ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 not found. Please install Python 3.9+"
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    echo "❌ Error: main.py not found. Please run this script from the nexus-trading-ai directory"
    exit 1
fi

# Parse arguments
VERBOSE=""
DRY_RUN=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --verbose)
            VERBOSE="--verbose"
            shift
            ;;
        --dry-run)
            DRY_RUN="--dry-run"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: ./run_live.sh [--verbose] [--dry-run]"
            exit 1
            ;;
    esac
done

# Determine mode
if [ -n "$DRY_RUN" ]; then
    MODE="[yellow]DRY-RUN[/yellow] (simulated trades)"
    ARGS="--dry-run"
else
    MODE="[bold red]LIVE[/bold red] (real trades)"
    ARGS="--live"
fi

echo "Mode: $MODE"
echo "Verbose: $([ -n "$VERBOSE" ] && echo 'Enabled' || echo 'Disabled')"
echo ""
echo "Starting trading loop in 3 seconds..."
echo "(Press Ctrl+C to stop)"
sleep 3
echo ""

# Run the trading system
python3 main.py $ARGS $VERBOSE


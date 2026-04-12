#!/bin/bash

# NEXUS Live Decisions Monitor
# Better than 'tail -f' because it avoids partial JSON reads

while true; do
  clear
  echo "╔════════════════════════════════════════════════════════════════╗"
  echo "║         NEXUS LIVE AGENT DECISIONS MONITOR                    ║"
  echo "║         Press Ctrl+C to stop                                  ║"
  echo "╚════════════════════════════════════════════════════════════════╝"
  echo ""
  
  # Display the JSON nicely
  if [ -f nexus_live_decisions.json ]; then
    cat nexus_live_decisions.json | jq '.' 2>/dev/null
    if [ $? -ne 0 ]; then
      echo "⚠️  JSON Parse Error - waiting for valid data..."
    fi
  else
    echo "❌ nexus_live_decisions.json not found"
  fi
  
  echo ""
  echo "⏳ Refreshing in 5 seconds..."
  sleep 5
done

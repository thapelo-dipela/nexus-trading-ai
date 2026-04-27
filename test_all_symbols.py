#!/usr/bin/env python3
"""
Test script to verify all tradeable symbols are visible on the dashboard.
"""
import requests
import json
import sys
import config

print("=" * 80)
print("NEXUS TRADING AI — SYMBOL VISIBILITY CHECK")
print("=" * 80)

# Check 1: Verify config has all symbols
print("\n[1] CONFIG SYMBOLS:")
print(f"Total symbols in SUPPORTED_SYMBOLS: {len(config.SUPPORTED_SYMBOLS)}")
for sym, meta in config.SUPPORTED_SYMBOLS.items():
    status = "✅ Active" if meta['active'] else "⚪ Inactive"
    print(f"  {sym:6} → {meta['name']:25} ({meta['category']:10}) {status}")

# Check 2: Verify free_market has mappings for all symbols
print("\n[2] FREE MARKET CLIENT COVERAGE:")
from data.free_market import COINGECKO_IDS, BINANCE_PAIRS

config_syms = set(config.SUPPORTED_SYMBOLS.keys())
coingecko_syms = set(COINGECKO_IDS.keys())
binance_syms = set(BINANCE_PAIRS.keys())

print(f"Symbols in COINGECKO_IDS: {len(coingecko_syms)}")
missing_gecko = config_syms - coingecko_syms
if missing_gecko:
    print(f"  ❌ Missing from CoinGecko: {missing_gecko}")
else:
    print(f"  ✅ All symbols covered")

print(f"Symbols in BINANCE_PAIRS: {len(binance_syms)}")
missing_binance = config_syms - binance_syms
if missing_binance:
    print(f"  ❌ Missing from Binance: {missing_binance}")
else:
    print(f"  ✅ All symbols covered")

# Check 3: Test API endpoint
print("\n[3] DASHBOARD API TEST:")
try:
    resp = requests.get("http://localhost:3000/api/market-overview", timeout=5)
    if resp.status_code == 200:
        data = resp.json()
        print(f"  ✅ API responded (status {resp.status_code})")
        
        currencies = data.get('currencies', [])
        print(f"  Total symbols returned: {len(currencies)}")
        print(f"  Expected: {len(config.SUPPORTED_SYMBOLS)}")
        
        returned_syms = {c['symbol'] for c in currencies}
        missing_from_api = config_syms - returned_syms
        extra_in_api = returned_syms - config_syms
        
        if missing_from_api:
            print(f"  ❌ Missing from API response: {missing_from_api}")
        if extra_in_api:
            print(f"  ⚠️  Extra symbols in API: {extra_in_api}")
        if not missing_from_api and not extra_in_api:
            print(f"  ✅ All symbols present in API response")
        
        # Show details
        print("\n  Symbol Details:")
        for curr in sorted(currencies, key=lambda x: x['symbol']):
            price_str = f"${curr['price']:.2f}" if curr.get('price') else "N/A"
            status = "🟢" if curr.get('active') else "⚪"
            print(f"    {status} {curr['symbol']:6} {price_str:>10} ({curr.get('category', 'unknown'):10})")
    else:
        print(f"  ❌ API error: status {resp.status_code}")
        print(f"  Response: {resp.text[:200]}")
except requests.exceptions.ConnectionError:
    print(f"  ❌ Cannot connect to API at http://localhost:3000")
    print(f"  Please ensure dashboard_server.py is running")
except Exception as e:
    print(f"  ❌ Error testing API: {e}")

# Check 4: Verify dashboard files are set up
print("\n[4] DASHBOARD FILES:")
import os
files_to_check = [
    'dashboard.html',
    'streamlit_app.py',
    'dashboard_server.py',
    'data/free_market.py',
    'config.py',
]
for f in files_to_check:
    path = f"/Users/thapelodipela/Desktop/nexus-trading-ai/{f}"
    if os.path.exists(path):
        print(f"  ✅ {f}")
    else:
        print(f"  ❌ {f} NOT FOUND")

print("\n" + "=" * 80)
print("SUMMARY:")
print("=" * 80)
print(f"""
Total symbols available for trading: {len(config.SUPPORTED_SYMBOLS)}
  - Active: {sum(1 for m in config.SUPPORTED_SYMBOLS.values() if m['active'])}
  - Inactive: {sum(1 for m in config.SUPPORTED_SYMBOLS.values() if not m['active'])}

All symbols should be visible in:
  1. Streamlit "Currencies" tab (http://localhost:8501)
  2. HTML Dashboard "Currencies" tab (http://localhost:3000)
  3. API endpoint /api/market-overview (http://localhost:3000/api/market-overview)

To view the Streamlit dashboard:
  streamlit run streamlit_app.py

To view the HTML dashboard:
  Open http://localhost:3000 in browser
""")

#!/usr/bin/env python3
"""PRISM API Diagnostic Script"""

import sys
import requests
import json
from typing import Dict, Any

def test_prism_api() -> None:
    """Test PRISM API connectivity and endpoints"""
    
    api_key = "prism_sk_C8ZTr-AEX6IkDGfLmdm7RXa5ZOIG29H5xc57pUCPGRQ"
    base_url = "https://api.prismapi.ai"
    
    print("\n" + "="*70)
    print("NEXUS — PRISM API Diagnostic")
    print("="*70)
    
    print(f"\nAPI Configuration:")
    print(f"  Key: {api_key[:20]}...{api_key[-10:]}")
    print(f"  Base URL: {base_url}")
    print(f"  Symbol: BTC")
    
    # Test various endpoints
    endpoints = [
        ("/crypto/BTC/price", "Price endpoint (v1)"),
        ("/resolve/BTC", "Resolve endpoint"),
        ("/crypto/BTC/ohlc", "OHLC endpoint"),
        ("/signals/BTC", "Signals endpoint"),
    ]
    
    headers = {"X-API-Key": api_key}
    
    print(f"\nTesting {len(endpoints)} endpoints:\n")
    
    for endpoint, description in endpoints:
        url = base_url + endpoint
        print(f"  [{description}]")
        print(f"    URL: {url}")
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            status = response.status_code
            
            if status == 200:
                try:
                    data = response.json()
                    print(f"    ✅ Status 200 (OK)")
                    print(f"    Response keys: {list(data.keys())}")
                except:
                    print(f"    ✅ Status 200 (OK) - Not JSON")
                    print(f"    Response: {response.text[:100]}")
            elif status == 401:
                print(f"    ❌ Status 401 (Unauthorized)")
                print(f"    → API key may be invalid or expired")
            elif status == 404:
                print(f"    ❌ Status 404 (Not Found)")
                print(f"    → Endpoint may not exist")
            else:
                print(f"    ❌ Status {status}")
                print(f"    Response: {response.text[:100]}")
                
        except requests.exceptions.Timeout:
            print(f"    ⏱️  Timeout (10s) - API unreachable or slow")
        except requests.exceptions.ConnectionError as e:
            print(f"    🔌 Connection Error: {str(e)[:60]}")
        except Exception as e:
            print(f"    ⚠️  Error: {str(e)[:60]}")
        
        print()
    
    print("="*70)
    print("\nDiagnostic Summary:")
    print("  • If endpoints return 401: API key is invalid or expired")
    print("  • If endpoints return 404: Check endpoint format or API version")
    print("  • If connection times out: Check network/firewall or API is down")
    print("  • If working: NEXUS can now fetch real market data")
    print("="*70 + "\n")

if __name__ == "__main__":
    test_prism_api()

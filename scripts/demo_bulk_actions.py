#!/usr/bin/env python3
"""Demo script to create many micropayments by calling the local nanopay wrapper via PayerAgent.

Usage: python scripts/demo_bulk_actions.py --count 60
"""
import argparse
import json
import time
import sys
from pathlib import Path
from pathlib import Path as _P

# Ensure project root is on sys.path so 'agents' package can be imported when running this script directly
_ROOT = str(_P(__file__).resolve().parents[1])
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

try:
    # prefer internal agent if available
    from agents.payer_agent import PayerAgent
    _HAS_AGENT = True
except Exception:
    _HAS_AGENT = False
    import urllib.request
    import urllib.error
    import urllib.parse



def main(count: int, out_file: str):
    agent = PayerAgent() if _HAS_AGENT else None
    logp = Path(out_file)
    results = []
    for i in range(count):
        action_id = f"demo-action-{int(time.time()*1000)}-{i}"
        try:
            if _HAS_AGENT:
                resp = agent.pay_for_action(action_id, 0.05, {'demo': True, 'index': i})
                results.append({'action_id': action_id, 'resp': resp})
            else:
                # fallback: POST directly to nanopay wrapper
                payload = json.dumps({'channelId': action_id, 'amountUSDC': 0.05, 'metadata': {'demo': True, 'index': i}}).encode('utf8')
                req = urllib.request.Request('http://localhost:3001/api/charge-action', data=payload, headers={'Content-Type': 'application/json'})
                with urllib.request.urlopen(req, timeout=5) as r:
                    body = r.read().decode('utf8')
                    results.append({'action_id': action_id, 'resp': json.loads(body)})
            print(f"[{i+1}/{count}] charged {action_id}")
        except Exception as e:
            print(f"[{i+1}/{count}] failed {action_id}: {e}")
            results.append({'action_id': action_id, 'error': str(e)})
        time.sleep(0.05)

    # persist
    existing = []
    if logp.exists():
        try:
            existing = json.loads(logp.read_text())
        except Exception:
            existing = []
    existing.extend(results)
    logp.write_text(json.dumps(existing, indent=2))
    print(f"Wrote {len(results)} entries to {out_file}")


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--count', type=int, default=60)
    p.add_argument('--out', default='nexus_txlog.json')
    args = p.parse_args()
    main(args.count, args.out)

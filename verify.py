#!/usr/bin/env python3
"""
NEXUS Trading AI — Hackathon Submission Verifier
Run from project root: python verify.py
"""

import os, sys, json, importlib, urllib.request, urllib.error

# ── Colours ────────────────────────────────────────────────────────────────
G = "\033[92m"; R = "\033[91m"; Y = "\033[93m"; B = "\033[94m"; RESET = "\033[0m"; BOLD = "\033[1m"
OK  = f"{G}✓{RESET}"
FAIL = f"{R}✗{RESET}"
WARN = f"{Y}⚠{RESET}"

passes = fails = warns = 0

def ok(msg):
    global passes; passes += 1; print(f"  {OK}  {msg}")

def fail(msg):
    global fails; fails += 1; print(f"  {FAIL}  {R}{msg}{RESET}")

def warn(msg):
    global warns; warns += 1; print(f"  {WARN}  {Y}{msg}{RESET}")

def section(title):
    print(f"\n{BOLD}{B}{'─'*55}{RESET}")
    print(f"{BOLD}{B}  {title}{RESET}")
    print(f"{BOLD}{B}{'─'*55}{RESET}")

# ── Load .env without python-dotenv ────────────────────────────────────────
def load_env(path=".env"):
    env = {}
    if not os.path.exists(path):
        return env
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip()
    return env

ENV = load_env()

def env(key):
    return ENV.get(key) or os.environ.get(key, "")

# ══════════════════════════════════════════════════════════════════════════
# 1. CRITICAL ENV VARS
# ══════════════════════════════════════════════════════════════════════════
section("1. Critical Environment Variables")

REQUIRED_KEYS = {
    # On-chain / Arc
    "ARC_RPC_URL":              "Arc RPC URL",
    "ARC_CHAIN_ID":             "Arc Chain ID",
    "ARC_USDC_ADDRESS":         "USDC contract on Arc",
    "AGENT_WALLET_KEY":         "Agent wallet private key",
    # ERC-8004 contracts
    "AGENT_REGISTRY_ADDRESS":   "ERC-8004 Agent Registry",
    "HACKATHON_VAULT_ADDRESS":  "Hackathon Capital Sandbox Vault",
    "RISK_ROUTER_ADDRESS":      "On-chain Risk Router",
    "REPUTATION_REGISTRY_ADDRESS": "Reputation Registry",
    "VALIDATION_REGISTRY_ADDRESS": "Validation Registry",
    "AGENT_ID":                 "Registered Agent ID",
    # Circle
    "CIRCLE_API_KEY":           "Circle API Key",
    "NANOPAY_SERVICE_URL":      "Circle Nanopayments service URL",
    # Kraken
    "KRAKEN_API_KEY":           "Kraken API Key",
    "KRAKEN_API_SECRET":        "Kraken API Secret",
    # PRISM
    "PRISM_API_KEY":            "PRISM API Key",
}

for key, label in REQUIRED_KEYS.items():
    val = env(key)
    if val:
        ok(f"{label} ({key})")
    else:
        fail(f"MISSING: {label} ({key})")

# ══════════════════════════════════════════════════════════════════════════
# 2. CORE PROJECT FILES
# ══════════════════════════════════════════════════════════════════════════
section("2. Core Project Files")

FILES = [
    ("main.py",                         "Main entry point"),
    ("config.py",                       "Config module"),
    ("requirements.txt",                "Requirements file"),
    ("agents/momentum.py",              "Momentum agent"),
    ("agents/sentiment.py",             "Sentiment agent"),
    ("agents/risk_guardian.py",         "Risk Guardian agent"),
    ("agents/mean_reversion.py",        "Mean Reversion agent"),
    ("agents/payer_agent.py",           "Payer agent (nanopayments)"),
    ("agents/receiver_agent.py",        "Receiver agent (nanopayments)"),
    ("consensus/engine.py",             "Consensus engine"),
    ("execution/kraken.py",             "Kraken execution"),
    ("execution/risk_router.py",        "Risk router"),
    ("execution/sandbox_capital.py",    "Sandbox Capital integration"),
    ("onchain/reputation.py",           "On-chain reputation module"),
    ("middleware/x402_middleware.py",   "x402 payment middleware"),
    ("payments/circle_nanopay/src/nanopay.ts", "Circle Nanopay service"),
    ("dashboard_server.py",             "FastAPI dashboard server"),
    ("dashboard.html",                  "Dashboard HTML"),
    ("compliance.py",                   "Compliance module"),
    ("validation.py",                   "Validation module"),
]

for path, label in FILES:
    if os.path.exists(path):
        ok(f"{label} → {path}")
    else:
        fail(f"MISSING: {label} → {path}")

# ══════════════════════════════════════════════════════════════════════════
# 3. ON-CHAIN / ERC-8004 ARTEFACTS
# ══════════════════════════════════════════════════════════════════════════
section("3. On-Chain / ERC-8004 Artefacts")

CONTRACTS = [
    "ai-trading-agent-template/contracts/AgentRegistry.sol",
    "ai-trading-agent-template/contracts/HackathonVault.sol",
    "ai-trading-agent-template/contracts/ReputationRegistry.sol",
    "ai-trading-agent-template/contracts/RiskRouter.sol",
    "ai-trading-agent-template/contracts/ValidationRegistry.sol",
]
for c in CONTRACTS:
    if os.path.exists(c):
        ok(f"Contract: {os.path.basename(c)}")
    else:
        fail(f"MISSING contract: {c}")

# deployed.json
deployed_path = "ai-trading-agent-template/deployed.json"
if os.path.exists(deployed_path):
    try:
        with open(deployed_path) as f:
            deployed = json.load(f)
        if deployed:
            ok(f"deployed.json present ({len(deployed)} entries)")
        else:
            warn("deployed.json exists but is empty — contracts not deployed yet?")
    except json.JSONDecodeError:
        fail("deployed.json is malformed JSON")
else:
    fail("deployed.json missing — have you run the deploy script?")

# agent-id.json
agent_id_path = "ai-trading-agent-template/agent-id.json"
if os.path.exists(agent_id_path):
    try:
        with open(agent_id_path) as f:
            aid = json.load(f)
        if aid:
            ok(f"agent-id.json present: {list(aid.keys())}")
        else:
            warn("agent-id.json is empty")
    except json.JSONDecodeError:
        fail("agent-id.json is malformed JSON")
else:
    fail("agent-id.json missing — agent not registered on-chain yet")

# checkpoints
ckpt_path = "ai-trading-agent-template/checkpoints.jsonl"
if os.path.exists(ckpt_path):
    with open(ckpt_path) as f:
        lines = [l for l in f if l.strip()]
    if len(lines) >= 1:
        ok(f"EIP-712 checkpoints: {len(lines)} entries")
    else:
        warn("checkpoints.jsonl exists but has no entries")
else:
    warn("checkpoints.jsonl missing — no EIP-712 signed checkpoints yet")

# ══════════════════════════════════════════════════════════════════════════
# 4. NANOPAYMENTS / CIRCLE INTEGRATION
# ══════════════════════════════════════════════════════════════════════════
section("4. Circle Nanopayments Integration")

receipts_path = "payments/.nanopay_data/receipts.json"
if os.path.exists(receipts_path):
    try:
        with open(receipts_path) as f:
            receipts = json.load(f)
        count = len(receipts) if isinstance(receipts, list) else len(receipts.get("receipts", []))
        if count >= 50:
            ok(f"Nanopay receipts: {count} transactions (≥50 ✓)")
        elif count > 0:
            warn(f"Nanopay receipts: {count} transactions — need 50+ for submission")
        else:
            fail("Receipts file exists but is empty — no transactions recorded")
    except (json.JSONDecodeError, KeyError):
        warn("receipts.json present but could not parse transaction count")
else:
    fail("payments/.nanopay_data/receipts.json missing — no nanopay receipts logged")

nanopay_service = "payments/circle_nanopay/src/nanopay.ts"
if os.path.exists(nanopay_service):
    with open(nanopay_service) as f:
        content = f.read()
    if "ARC" in content or "arc" in content:
        ok("nanopay.ts references Arc settlement")
    else:
        warn("nanopay.ts — Arc settlement reference not detected, verify manually")
    if "USDC" in content or "usdc" in content:
        ok("nanopay.ts references USDC")
    else:
        warn("nanopay.ts — USDC reference not detected")
else:
    fail("nanopay.ts not found")

# ══════════════════════════════════════════════════════════════════════════
# 5. TRANSACTION LOG (50+ on-chain txns requirement)
# ══════════════════════════════════════════════════════════════════════════
section("5. On-Chain Transaction Log (50+ required)")

txlog_path = "nexus_txlog.json"
if os.path.exists(txlog_path):
    try:
        with open(txlog_path) as f:
            txlog = json.load(f)
        count = len(txlog) if isinstance(txlog, list) else 0
        if count >= 50:
            ok(f"nexus_txlog.json: {count} transactions (≥50 ✓)")
        elif count > 0:
            warn(f"nexus_txlog.json: {count} transactions — need 50+ for submission")
        else:
            fail("nexus_txlog.json has no entries")
    except json.JSONDecodeError:
        fail("nexus_txlog.json is malformed")
else:
    fail("nexus_txlog.json not found — no on-chain tx log")

# ══════════════════════════════════════════════════════════════════════════
# 6. PYTHON MODULE IMPORTS
# ══════════════════════════════════════════════════════════════════════════
section("6. Python Module Imports")

MODULES = [
    "fastapi", "uvicorn", "web3", "requests",
    "anthropic", "numpy", "aiohttp",
]
for mod in MODULES:
    try:
        importlib.import_module(mod)
        ok(f"import {mod}")
    except ImportError:
        fail(f"Cannot import {mod} — run: pip install {mod}")

# ══════════════════════════════════════════════════════════════════════════
# 7. NETWORK REACHABILITY
# ══════════════════════════════════════════════════════════════════════════
section("7. Network Reachability")

def ping(label, url, timeout=5):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "nexus-verify/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            ok(f"{label} reachable (HTTP {r.status})")
    except urllib.error.HTTPError as e:
        # 4xx still means server is up
        ok(f"{label} reachable (HTTP {e.code})")
    except Exception as e:
        fail(f"{label} unreachable — {e}")

arc_rpc = env("ARC_RPC_URL")
def warn_ping(label, url, timeout=5):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "nexus-verify/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            ok(f"{label} reachable (HTTP {r.status})")
    except urllib.error.HTTPError as e:
        ok(f"{label} reachable (HTTP {e.code})")
    except Exception as e:
        warn(f"{label} unreachable (external endpoint) — {e}")

if arc_rpc:
    warn_ping("Arc RPC", arc_rpc)
else:
    warn("ARC_RPC_URL not set — skipping Arc reachability check")

nanopay_url = env("NANOPAY_SERVICE_URL")
if nanopay_url:
    ping("Nanopay service", nanopay_url)
else:
    warn("NANOPAY_SERVICE_URL not set — skipping nanopay reachability check")

warn_ping("PRISM API", "https://api.prismapi.ai")

# ══════════════════════════════════════════════════════════════════════════
# 8. SUBMISSION ASSETS
# ══════════════════════════════════════════════════════════════════════════
section("8. Submission Assets")

SUBMISSION_ASSETS = [
    ("README.md",           "README / project description"),
    ("HACKATHON_SUBMISSION.md", "Hackathon submission doc"),
    ("DELIVERABLES.md",     "Deliverables doc"),
]
for path, label in SUBMISSION_ASSETS:
    if os.path.exists(path):
        ok(f"{label} → {path}")
    else:
        warn(f"MISSING: {label} → {path}")

# ══════════════════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════════════════
print(f"\n{BOLD}{'═'*55}{RESET}")
print(f"{BOLD}  NEXUS VERIFICATION SUMMARY{RESET}")
print(f"{BOLD}{'═'*55}{RESET}")
print(f"  {G}Passed : {passes}{RESET}")
print(f"  {Y}Warnings: {warns}{RESET}")
print(f"  {R}Failed : {fails}{RESET}")

if fails == 0 and warns == 0:
    print(f"\n  {G}{BOLD}🚀 ALL CHECKS PASSED — SUBMISSION READY{RESET}\n")
elif fails == 0:
    print(f"\n  {Y}{BOLD}⚠  Passed with warnings — review above before submitting{RESET}\n")
else:
    print(f"\n  {R}{BOLD}✗  {fails} critical issue(s) — fix before submitting{RESET}\n")

sys.exit(0 if fails == 0 else 1)

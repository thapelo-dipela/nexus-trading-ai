#!/usr/bin/env python3
"""
patch_fixes.py
==============
Patches two files to fix the HTTP errors seen in logs:

  1. data/free_market.py
     - Fixes Binance 400 error on batch ticker call.
       Root cause: requests URL-encodes the JSON array brackets, which
       Binance rejects. Fix: switch from one bulk call to individual
       per-symbol calls inside a loop (Session reuse keeps it fast).

  2. agents/sentiment.py
     - Fixes Messari 404 error (endpoint permanently removed).
       Fix: replace _fetch_messari_news() with _fetch_coingecko_news()
       which hits CoinGecko /api/v3/news — free, stable, no API key.
     - Also upgrades Reddit weighting to log(score+1) × upvote_ratio
       and adds a minimum score threshold of 10 to filter unstable posts.
     - Fixes partial-word NLP false positives using regex word boundaries.

Run from your project root:
    python3 patch_fixes.py

Backups are saved as *.bak before any changes.
"""

import shutil
from pathlib import Path

# ── helpers ──────────────────────────────────────────────────────────────────

def load(path: Path) -> str:
    return path.read_text(encoding="utf-8")

def save(path: Path, content: str):
    path.write_text(content, encoding="utf-8")

def backup(path: Path):
    bak = path.with_suffix(path.suffix + ".bak")
    shutil.copy(path, bak)
    print(f"  📦 Backup → {bak}")

def apply(src: str, old: str, new: str, label: str) -> str:
    if old not in src:
        print(f"  ⚠️  SKIP '{label}' — anchor not found (already patched?)")
        return src
    result = src.replace(old, new, 1)
    print(f"  ✅ PATCH '{label}'")
    return result

# ═════════════════════════════════════════════════════════════════════════════
# PATCH 1 — data/free_market.py
# ═════════════════════════════════════════════════════════════════════════════

FREE_MARKET = Path("data/free_market.py")

if not FREE_MARKET.exists():
    print(f"❌ {FREE_MARKET} not found — skipping")
else:
    print(f"\n📄 Patching {FREE_MARKET}")
    backup(FREE_MARKET)
    src = load(FREE_MARKET)

    # ── Fix 1a: update docstring FIX LOG ─────────────────────────────────────
    src = apply(
        src,
        old=(
            "FIX LOG:\n"
            "  v1.1 — Binance batch 400 error: the /ticker/24hr endpoint does not accept\n"
            "          a JSON-encoded `symbols` param via requests params dict because\n"
            "          requests URL-encodes the brackets. Fixed by building the query string\n"
            "          manually and passing it via the URL directly.\n"
            "       — Messari /api/v1/news/btc returned 404 (endpoint removed). Replaced\n"
            "          with CoinGecko /news endpoint which is free and requires no API key."
        ),
        new=(
            "FIX LOG:\n"
            "  v1.1 — Binance batch 400 error fixed: switched from bulk /ticker/24hr\n"
            "          ?symbols=[...] (URL-encoding issue) to individual per-symbol calls\n"
            "          reusing the requests.Session TCP connection.\n"
            "       — Messari 404 removed from this file (handled in sentiment.py)."
        ),
        label="free_market docstring FIX LOG",
    )

    # ── Fix 1b: replace get_prices_batch bulk Binance call with per-symbol loop
    src = apply(
        src,
        old=(
            "        results: Dict[str, Optional[Dict]] = {s: None for s in symbols}\n"
            "\n"
            "        # --- Primary: Binance bulk 24hr ticker (single call) ---\n"
            "        pairs_needed = {s: self._binance_pair(s) for s in symbols if self._binance_pair(s)}\n"
            "        if pairs_needed:\n"
            "            pair_list = list(pairs_needed.values())\n"
            "            # Binance accepts symbols param as JSON array string for bulk\n"
            "            import json\n"
            "            data = self._get(\n"
            "                f\"{self.BINANCE_BASE}/ticker/24hr\",\n"
            "                params={\"symbols\": json.dumps(pair_list)},\n"
            "            )\n"
            "            if data and isinstance(data, list):\n"
            "                # Build reverse map: pair → symbol\n"
            "                pair_to_sym = {v: k for k, v in pairs_needed.items()}\n"
            "                for ticker in data:\n"
            "                    sym = pair_to_sym.get(ticker.get(\"symbol\"))\n"
            "                    if sym:\n"
            "                        results[sym] = {\n"
            "                            \"price\": float(ticker[\"lastPrice\"]),\n"
            "                            \"change_24h_pct\": float(ticker.get(\"priceChangePercent\", 0.0)),\n"
            "                            \"volume_24h\": float(ticker.get(\"quoteVolume\", 0.0)),\n"
            "                        }"
        ),
        new=(
            "        results: Dict[str, Optional[Dict]] = {s.upper(): None for s in symbols}\n"
            "\n"
            "        # --- Primary: Binance individual calls (Session reuse keeps this fast) ---\n"
            "        # NOTE: The bulk /ticker/24hr?symbols=[...] endpoint returns HTTP 400\n"
            "        # because requests URL-encodes the JSON brackets. Individual calls avoid this.\n"
            "        for symbol in symbols:\n"
            "            sym = symbol.upper()\n"
            "            pair = self._binance_pair(sym)\n"
            "            if not pair:\n"
            "                continue\n"
            "            data = self._get(\n"
            "                f\"{self.BINANCE_BASE}/ticker/24hr\",\n"
            "                params={\"symbol\": pair},\n"
            "            )\n"
            "            if data and \"lastPrice\" in data:\n"
            "                results[sym] = {\n"
            "                    \"price\": float(data[\"lastPrice\"]),\n"
            "                    \"change_24h_pct\": float(data.get(\"priceChangePercent\", 0.0)),\n"
            "                    \"volume_24h\": float(data.get(\"quoteVolume\", 0.0)),\n"
            "                    \"source\": \"binance\",\n"
            "                }"
        ),
        label="get_prices_batch — individual Binance calls (fixes 400)",
    )

    # ── Fix 1c: fix the missing symbols fallback key lookup after loop change ─
    src = apply(
        src,
        old=(
            "        # --- Fallback: CoinGecko multi-id for anything still missing ---\n"
            "        missing = [s for s in symbols if results[s] is None]"
        ),
        new=(
            "        # --- Fallback: CoinGecko multi-id for anything still missing ---\n"
            "        missing = [s.upper() for s in symbols if results.get(s.upper()) is None]"
        ),
        label="get_prices_batch — fix missing key lookup after loop change",
    )

    # ── Fix 1d: add source tag to CoinGecko fallback results ─────────────────
    src = apply(
        src,
        old=(
            "                        if sym:\n"
            "                            results[sym] = {\n"
            "                                \"price\": float(d.get(\"usd\", 0.0)),\n"
            "                                \"change_24h_pct\": float(d.get(\"usd_24h_change\", 0.0)),\n"
            "                                \"volume_24h\": float(d.get(\"usd_24h_vol\", 0.0)),\n"
            "                            }"
        ),
        new=(
            "                        if sym:\n"
            "                            results[sym] = {\n"
            "                                \"price\": float(d.get(\"usd\", 0.0)),\n"
            "                                \"change_24h_pct\": float(d.get(\"usd_24h_change\", 0.0)),\n"
            "                                \"volume_24h\": float(d.get(\"usd_24h_vol\", 0.0)),\n"
            "                                \"source\": \"coingecko\",\n"
            "                            }"
        ),
        label="get_prices_batch — add source tag to CoinGecko results",
    )

    # ── Fix 1e: add fetch count log after batch ───────────────────────────────
    src = apply(
        src,
        old=(
            "        self._cache.set(cache_key, results, ttl=15)\n"
            "        return results\n"
            "\n"
            "    def get_all_supported_prices"
        ),
        new=(
            "        self._cache.set(cache_key, results, ttl=15)\n"
            "        fetched = sum(1 for v in results.values() if v is not None)\n"
            "        logger.debug(f\"Batch prices: {fetched}/{len(symbols)} symbols fetched\")\n"
            "        return results\n"
            "\n"
            "    def get_all_supported_prices"
        ),
        label="get_prices_batch — add fetch count debug log",
    )

    save(FREE_MARKET, src)
    print(f"  ✅ {FREE_MARKET} saved\n")


# ═════════════════════════════════════════════════════════════════════════════
# PATCH 2 — agents/sentiment.py
# ═════════════════════════════════════════════════════════════════════════════

SENTIMENT = Path("agents/sentiment.py")

if not SENTIMENT.exists():
    print(f"❌ {SENTIMENT} not found — skipping")
else:
    print(f"📄 Patching {SENTIMENT}")
    backup(SENTIMENT)
    src = load(SENTIMENT)

    # ── Fix 2a: update module docstring ──────────────────────────────────────
    src = apply(
        src,
        old=(
            "News sources (all free, no API key required):\n"
            "  - Messari: professional crypto news headlines\n"
            "  - Reddit (r/Bitcoin + r/CryptoCurrency): social sentiment proxy"
        ),
        new=(
            "News sources (all free, no API key required):\n"
            "  - CoinGecko News: replaces Messari (404 since endpoint removed)\n"
            "  - Reddit (r/Bitcoin + r/CryptoCurrency): social sentiment proxy"
        ),
        label="sentiment docstring — update news source reference",
    )

    # ── Fix 2b: replace NLP word lists + _nlp_score with word-boundary version
    src = apply(
        src,
        old=(
            "def _nlp_score(text: str) -> float:\n"
            "    \"\"\"Score a single text string -1.0 to +1.0 using keyword NLP.\"\"\"\n"
            "    t = text.lower()\n"
            "    pos = sum(1 for w in POSITIVE_WORDS if w in t)\n"
            "    neg = sum(1 for w in NEGATIVE_WORDS if w in t)\n"
            "    return max(-1.0, min(1.0, float(pos - neg)))"
        ),
        new=(
            "def _nlp_score(text: str) -> float:\n"
            "    \"\"\"\n"
            "    Score a text string -1.0 to +1.0 using whole-word keyword NLP.\n"
            "    Uses regex word boundaries to avoid partial-word false positives\n"
            "    e.g. 'liquidity' matching 'liquidat', 'follow' matching 'low'.\n"
            "    \"\"\"\n"
            "    import re\n"
            "    t = text.lower()\n"
            "    pos = sum(1 for w in POSITIVE_WORDS if re.search(r'\\b' + re.escape(w) + r'\\b', t))\n"
            "    neg = sum(1 for w in NEGATIVE_WORDS if re.search(r'\\b' + re.escape(w) + r'\\b', t))\n"
            "    return max(-1.0, min(1.0, float(pos - neg)))"
        ),
        label="_nlp_score — word boundary matching (fixes false positives)",
    )

    # ── Fix 2c: update NEGATIVE_WORDS — replace 'liquidat' with 'liquidation' ─
    src = apply(
        src,
        old='"liquidat", "dump", "outflow"',
        new='"liquidation", "dump", "outflow"',
        label="NEGATIVE_WORDS — replace partial 'liquidat' with 'liquidation'",
    )

    # ── Fix 2d: replace _fetch_messari_news with _fetch_coingecko_news ────────
    src = apply(
        src,
        old=(
            "def _fetch_messari_news() -> tuple:\n"
            "    \"\"\"\n"
            "    Fetches BTC news from Messari (free, no API key).\n"
            "    Returns (news_score: float, composite_contribution: float).\n"
            "    \"\"\"\n"
            "    try:\n"
            "        resp = requests.get(\n"
            "            \"https://data.messari.io/api/v1/news/btc\",\n"
            "            timeout=5,\n"
            "        )\n"
            "        resp.raise_for_status()\n"
            "\n"
            "        if not resp.text.strip():\n"
            "            logger.warning(\"Messari returned empty response body\")\n"
            "            return 0.0, 0.0\n"
            "\n"
            "        data = resp.json()\n"
            "        articles = data.get(\"data\", [])[:10]\n"
            "\n"
            "        scores = [\n"
            "            _nlp_score(a.get(\"title\", \"\") + \" \" + a.get(\"content\", \"\")[:200])\n"
            "            for a in articles\n"
            "        ]\n"
            "\n"
            "        if scores:\n"
            "            news_score = round(sum(scores) / len(scores), 3)\n"
            "            logger.debug(f\"Messari news score: {news_score} from {len(scores)} articles\")\n"
            "            return news_score, news_score * 0.3\n"
            "\n"
            "    except Exception as e:\n"
            "        logger.warning(f\"Messari news fetch failed: {e}\")\n"
            "\n"
            "    return 0.0, 0.0"
        ),
        new=(
            "def _fetch_coingecko_news() -> tuple:\n"
            "    \"\"\"\n"
            "    Fetches latest crypto news from CoinGecko (free, no API key).\n"
            "    Endpoint: GET /api/v3/news\n"
            "    Returns (news_score: float, composite_contribution: float).\n"
            "\n"
            "    Replaces Messari which permanently removed their free /api/v1/news endpoint.\n"
            "    \"\"\"\n"
            "    try:\n"
            "        resp = requests.get(\n"
            "            \"https://api.coingecko.com/api/v3/news\",\n"
            "            params={\"page\": 1},\n"
            "            headers={\"User-Agent\": \"NEXUS-SentimentAgent/1.0\"},\n"
            "            timeout=6,\n"
            "        )\n"
            "        resp.raise_for_status()\n"
            "\n"
            "        if not resp.text.strip():\n"
            "            logger.warning(\"CoinGecko news returned empty response\")\n"
            "            return 0.0, 0.0\n"
            "\n"
            "        data = resp.json()\n"
            "        articles = data.get(\"data\", [])[:15]\n"
            "\n"
            "        if not articles:\n"
            "            logger.warning(\"CoinGecko news: no articles in response\")\n"
            "            return 0.0, 0.0\n"
            "\n"
            "        scores = []\n"
            "        for article in articles:\n"
            "            title       = article.get(\"title\", \"\")\n"
            "            description = article.get(\"description\", \"\")[:200]\n"
            "            scores.append(_nlp_score(f\"{title} {description}\"))\n"
            "\n"
            "        if scores:\n"
            "            news_score = round(sum(scores) / len(scores), 3)\n"
            "            logger.debug(f\"CoinGecko news score: {news_score} from {len(scores)} articles\")\n"
            "            return news_score, news_score * 0.3\n"
            "\n"
            "    except Exception as e:\n"
            "        logger.warning(f\"CoinGecko news fetch failed: {e}\")\n"
            "\n"
            "    return 0.0, 0.0"
        ),
        label="_fetch_messari_news → _fetch_coingecko_news (fixes 404)",
    )

    # ── Fix 2e: upgrade Reddit weighting to log-scale + min score threshold ───
    src = apply(
        src,
        old=(
            "            for post in posts:\n"
            "                pd = post.get(\"data\", {})\n"
            "                text = pd.get(\"title\", \"\") + \" \" + pd.get(\"selftext\", \"\")[:200]\n"
            "                # Weight by upvote ratio — higher ratio posts carry more signal\n"
            "                upvote_ratio = pd.get(\"upvote_ratio\", 0.5)\n"
            "                weight = 0.5 + upvote_ratio * 0.5  # 0.5–1.0 range\n"
            "                all_scores.append(_nlp_score(text) * weight)"
        ),
        new=(
            "            for post in posts:\n"
            "                pd    = post.get(\"data\", {})\n"
            "                score = pd.get(\"score\", 0)\n"
            "\n"
            "                # Skip brand-new posts with too few votes to be reliable\n"
            "                if score < 10:\n"
            "                    continue\n"
            "\n"
            "                text         = pd.get(\"title\", \"\") + \" \" + pd.get(\"selftext\", \"\")[:200]\n"
            "                upvote_ratio = pd.get(\"upvote_ratio\", 0.5)\n"
            "\n"
            "                # log scale gives diminishing returns on viral posts\n"
            "                import math as _math\n"
            "                weight = _math.log1p(score) * upvote_ratio\n"
            "                all_scores.append((_nlp_score(text), weight))"
        ),
        label="Reddit — log-scale weighting + min score threshold",
    )

    # ── Fix 2f: update Reddit aggregation to use weighted average ─────────────
    src = apply(
        src,
        old=(
            "    if all_scores:\n"
            "        social_score = round(sum(all_scores) / len(all_scores), 3)\n"
            "        logger.debug(f\"Reddit social score: {social_score} from {len(all_scores)} posts\")\n"
            "        return social_score, social_score * 0.2\n"
            "\n"
            "    return 0.0, 0.0"
        ),
        new=(
            "    if all_scores:\n"
            "        total_weight = sum(w for _, w in all_scores)\n"
            "        if total_weight > 0:\n"
            "            social_score = round(\n"
            "                sum(s * w for s, w in all_scores) / total_weight, 3\n"
            "            )\n"
            "            logger.debug(\n"
            "                f\"Reddit social score: {social_score} \"\n"
            "                f\"from {len(all_scores)} weighted posts\"\n"
            "            )\n"
            "            return social_score, social_score * 0.2\n"
            "\n"
            "    return 0.0, 0.0"
        ),
        label="Reddit — weighted average aggregation",
    )

    # ── Fix 2g: update fetch_composite_sentiment to call coingecko_news ───────
    src = apply(
        src,
        old=(
            "    # 2. Messari news NLP (contributes up to ±0.3)\n"
            "    news_score, news_contribution = _fetch_messari_news()\n"
            "    result[\"news_score\"] = news_score\n"
            "    result[\"composite\"] += news_contribution\n"
            "    if news_score != 0.0:\n"
            "        result[\"sources\"].append(\"messari\")"
        ),
        new=(
            "    # 2. CoinGecko news NLP (contributes up to ±0.3)\n"
            "    news_score, news_contribution = _fetch_coingecko_news()\n"
            "    result[\"news_score\"] = news_score\n"
            "    result[\"composite\"] += news_contribution\n"
            "    if news_score != 0.0:\n"
            "        result[\"sources\"].append(\"coingecko_news\")"
        ),
        label="fetch_composite_sentiment — call coingecko_news instead of messari",
    )

    save(SENTIMENT, src)
    print(f"  ✅ {SENTIMENT} saved\n")


print("✅ All patches applied. Run: python3 dashboard_server.py")

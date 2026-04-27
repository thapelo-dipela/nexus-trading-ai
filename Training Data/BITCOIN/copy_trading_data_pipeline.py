"""
=============================================================
 COPY TRADING SIGNAL REPLICATION — AI TRAINING DATA PIPELINE
=============================================================
 Collects two data streams from Binance public APIs:

 STREAM 1 — Leaderboard Position Snapshots
   - Polls top traders' open/closed positions every N seconds
   - Reconstructs entry/exit signals (BUY/SELL, price, size, leverage)
   - Saves labelled signal events for supervised training

 STREAM 2 — Tick-by-Tick Aggrades
   - Streams every aggregated trade on the chosen symbol(s)
   - Captures price, volume, side (maker/taker = buy/sell)
   - Timestamps aligned with signal events for context window

 OUTPUT FORMAT (per session):
   data/
   ├── ticks/          BTCUSDT_ticks_YYYYMMDD_HHMMSS.csv
   ├── signals/        leaderboard_signals_YYYYMMDD_HHMMSS.csv
   └── merged/         merged_BTCUSDT_YYYYMMDD_HHMMSS.csv

 HOW TO RUN:
   pip install requests websocket-client pandas
   python copy_trading_data_pipeline.py

 CONFIGURATION:
   Edit the CONFIG block below before running.
=============================================================
"""

import os, time, json, csv, threading, logging
from datetime import datetime
from pathlib import Path

import requests
import pandas as pd

# ─────────────────────────────────────────────
#  CONFIGURATION — edit before running
# ─────────────────────────────────────────────
CONFIG = {
    # Symbols to collect tick data for
    "symbols": ["BTCUSDT", "ETHUSDT"],

    # How many top leaderboard traders to track (by all-time PnL)
    "top_n_traders": 20,

    # How often (seconds) to snapshot leaderboard positions
    "snapshot_interval_sec": 30,

    # How long to run the collection session (seconds). 0 = run forever.
    "session_duration_sec": 3600,  # 1 hour default

    # Output directory
    "output_dir": "./data",

    # Leaderboard filter
    "leaderboard_trade_type": "PERPETUAL",  # or "DELIVERY"
    "leaderboard_period": "ALL",            # ALL, MONTHLY, WEEKLY, DAILY
    "leaderboard_sort": "PNL",              # PNL or ROI

    # Only include traders who share positions publicly
    "only_position_sharers": True,

    # Request delay to avoid rate limiting (seconds)
    "request_delay_sec": 0.5,
}

# ─────────────────────────────────────────────
#  LOGGING
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("pipeline.log"),
    ]
)
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────
#  BINANCE API HELPERS
# ─────────────────────────────────────────────
BINANCE_FAPI    = "https://fapi.binance.com"
BINANCE_BAPI    = "https://www.binance.com/bapi/futures/v3/public/future/leaderboard"

HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (compatible; TrainingDataCollector/1.0)"
}


def get_leaderboard_top_traders(n: int = 20) -> list[dict]:
    """Fetch top N traders from Binance Futures Leaderboard by PnL/ROI."""
    url = f"{BINANCE_BAPI}/getLeaderboardRank"
    payload = {
        "statisticsType": CONFIG["leaderboard_sort"],
        "tradeType": CONFIG["leaderboard_trade_type"],
        "periodType": CONFIG["leaderboard_period"],
        "isShared": CONFIG["only_position_sharers"],
        "isTrader": False,
    }
    try:
        r = requests.post(url, json=payload, headers=HEADERS, timeout=10)
        r.raise_for_status()
        data = r.json().get("data", [])
        log.info(f"Fetched {len(data)} traders from leaderboard")
        return data[:n]
    except Exception as e:
        log.error(f"Leaderboard fetch error: {e}")
        return []


def get_trader_positions(encrypted_uid: str) -> list[dict]:
    """Fetch open positions for a single trader (if they share publicly)."""
    url = f"https://www.binance.com/bapi/futures/v1/public/future/leaderboard/getOtherPosition"
    payload = {
        "encryptedUid": encrypted_uid,
        "tradeType": CONFIG["leaderboard_trade_type"],
    }
    try:
        r = requests.post(url, json=payload, headers=HEADERS, timeout=10)
        r.raise_for_status()
        positions = r.json().get("data", {}).get("otherPositionRetList", [])
        return positions
    except Exception as e:
        log.warning(f"Position fetch error for {encrypted_uid[:12]}...: {e}")
        return []


def get_agg_trades(symbol: str, limit: int = 1000, from_id: int = None) -> list[dict]:
    """Fetch aggregated trades (tick-by-tick) from Binance Futures."""
    url = f"{BINANCE_FAPI}/fapi/v1/aggTrades"
    params = {"symbol": symbol, "limit": limit}
    if from_id:
        params["fromId"] = from_id
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log.error(f"AggTrades fetch error for {symbol}: {e}")
        return []


def get_klines(symbol: str, interval: str = "1m", limit: int = 500) -> list:
    """Fetch OHLCV candles as context enrichment."""
    url = f"{BINANCE_FAPI}/fapi/v1/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log.error(f"Klines fetch error: {e}")
        return []


# ─────────────────────────────────────────────
#  DATA STORAGE
# ─────────────────────────────────────────────
class DataStore:
    def __init__(self, output_dir: str):
        self.session_ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        self.base = Path(output_dir)
        for folder in ["ticks", "signals", "merged"]:
            (self.base / folder).mkdir(parents=True, exist_ok=True)

        # CSV writers
        self._tick_files   = {}
        self._tick_writers = {}
        self._signal_file   = open(self.base / "signals" / f"leaderboard_signals_{self.session_ts}.csv", "w", newline="")
        self._signal_writer = csv.DictWriter(self._signal_file, fieldnames=[
            "timestamp_utc", "trader_nick", "encrypted_uid", "all_time_pnl",
            "all_time_roi", "symbol", "side", "entry_price", "amount",
            "notional_usdt", "leverage", "unrealized_pnl", "snapshot_event"
        ])
        self._signal_writer.writeheader()
        self._prev_positions = {}  # uid -> set of position keys

    def get_tick_writer(self, symbol: str):
        if symbol not in self._tick_writers:
            f = open(self.base / "ticks" / f"{symbol}_ticks_{self.session_ts}.csv", "w", newline="")
            w = csv.DictWriter(f, fieldnames=[
                "agg_trade_id", "timestamp_utc", "timestamp_ms",
                "symbol", "price", "quantity", "side", "is_buyer_maker"
            ])
            w.writeheader()
            self._tick_files[symbol] = f
            self._tick_writers[symbol] = w
        return self._tick_writers[symbol]

    def write_ticks(self, symbol: str, trades: list[dict]):
        w = self.get_tick_writer(symbol)
        for t in trades:
            w.writerow({
                "agg_trade_id": t["a"],
                "timestamp_ms": t["T"],
                "timestamp_utc": datetime.utcfromtimestamp(t["T"] / 1000).isoformat(),
                "symbol": symbol,
                "price": float(t["p"]),
                "quantity": float(t["q"]),
                "side": "SELL" if t["m"] else "BUY",   # maker = sell pressure
                "is_buyer_maker": t["m"],
            })
        log.info(f"  Wrote {len(trades)} ticks for {symbol}")

    def write_signal(self, trader: dict, position: dict, event: str):
        side = "LONG" if float(position.get("amount", 0)) > 0 else "SHORT"
        notional = abs(float(position.get("amount", 0))) * float(position.get("entryPrice", 0))
        self._signal_writer.writerow({
            "timestamp_utc": datetime.utcnow().isoformat(),
            "trader_nick": trader.get("nickName", ""),
            "encrypted_uid": trader.get("encryptedUid", ""),
            "all_time_pnl": trader.get("pnl", ""),
            "all_time_roi": trader.get("roi", ""),
            "symbol": position.get("symbol", ""),
            "side": side,
            "entry_price": position.get("entryPrice", ""),
            "amount": position.get("amount", ""),
            "notional_usdt": round(notional, 2),
            "leverage": position.get("leverage", ""),
            "unrealized_pnl": position.get("pnl", ""),
            "snapshot_event": event,  # OPEN, CLOSE, UNCHANGED
        })
        self._signal_file.flush()

    def detect_signal_events(self, trader: dict, current_positions: list[dict]):
        """Compare to previous snapshot and emit OPEN/CLOSE events."""
        uid = trader.get("encryptedUid", "")
        curr_keys = {p["symbol"]: p for p in current_positions}
        prev_keys  = self._prev_positions.get(uid, {})

        for sym, pos in curr_keys.items():
            if sym not in prev_keys:
                self.write_signal(trader, pos, "OPEN")
                log.info(f"  🟢 OPEN  {trader.get('nickName','?')} -> {sym} {pos.get('amount','')}")
            else:
                self.write_signal(trader, pos, "UNCHANGED")

        for sym, pos in prev_keys.items():
            if sym not in curr_keys:
                self.write_signal(trader, pos, "CLOSE")
                log.info(f"  🔴 CLOSE {trader.get('nickName','?')} -> {sym}")

        self._prev_positions[uid] = curr_keys

    def merge_and_save(self, symbol: str):
        """Merge tick data with signals for a symbol and save for training."""
        tick_path   = self.base / "ticks" / f"{symbol}_ticks_{self.session_ts}.csv"
        signal_path = self.base / "signals" / f"leaderboard_signals_{self.session_ts}.csv"
        out_path    = self.base / "merged" / f"merged_{symbol}_{self.session_ts}.csv"

        if not tick_path.exists() or not signal_path.exists():
            return

        ticks   = pd.read_csv(tick_path, parse_dates=["timestamp_utc"])
        signals = pd.read_csv(signal_path, parse_dates=["timestamp_utc"])
        signals_sym = signals[signals["symbol"] == symbol].copy()

        if signals_sym.empty:
            log.info(f"No signals found for {symbol}, skipping merge.")
            return

        # Merge: for each tick, find the most recent signal before it
        ticks = ticks.sort_values("timestamp_utc")
        signals_sym = signals_sym.sort_values("timestamp_utc")
        merged = pd.merge_asof(ticks, signals_sym, on="timestamp_utc", suffixes=("", "_signal"))
        merged.to_csv(out_path, index=False)
        log.info(f"  Saved merged dataset: {out_path} ({len(merged)} rows)")

    def close(self):
        self._signal_file.close()
        for f in self._tick_files.values():
            f.close()


# ─────────────────────────────────────────────
#  COLLECTION THREADS
# ─────────────────────────────────────────────
def tick_collection_loop(symbol: str, store: DataStore, stop_event: threading.Event):
    """Continuously poll tick-by-tick trade data for a symbol."""
    last_id = None
    log.info(f"Starting tick collection for {symbol}")
    while not stop_event.is_set():
        trades = get_agg_trades(symbol, limit=1000, from_id=last_id)
        if trades:
            store.write_ticks(symbol, trades)
            last_id = trades[-1]["a"] + 1  # continue from last trade id
        time.sleep(CONFIG["request_delay_sec"])


def leaderboard_snapshot_loop(store: DataStore, stop_event: threading.Event):
    """Poll leaderboard and each trader's positions on a fixed interval."""
    log.info("Starting leaderboard snapshot loop")
    traders = []

    while not stop_event.is_set():
        # Refresh trader list every 10 snapshots
        if not traders:
            traders = get_leaderboard_top_traders(CONFIG["top_n_traders"])
            log.info(f"Loaded {len(traders)} traders to track")

        log.info(f"--- Snapshot at {datetime.utcnow().isoformat()} ---")
        for trader in traders:
            uid  = trader.get("encryptedUid", "")
            nick = trader.get("nickName", uid[:8])
            positions = get_trader_positions(uid)
            log.info(f"  {nick}: {len(positions)} open positions")
            store.detect_signal_events(trader, positions)
            time.sleep(CONFIG["request_delay_sec"])

        # Sleep until next snapshot
        for _ in range(CONFIG["snapshot_interval_sec"]):
            if stop_event.is_set():
                break
            time.sleep(1)


# ─────────────────────────────────────────────
#  MAIN ENTRY POINT
# ─────────────────────────────────────────────
def main():
    log.info("=" * 60)
    log.info("  COPY TRADING AI TRAINING DATA PIPELINE")
    log.info(f"  Session start: {datetime.utcnow().isoformat()} UTC")
    log.info(f"  Symbols: {CONFIG['symbols']}")
    log.info(f"  Top traders: {CONFIG['top_n_traders']}")
    log.info(f"  Duration: {CONFIG['session_duration_sec']}s")
    log.info("=" * 60)

    store = DataStore(CONFIG["output_dir"])
    stop  = threading.Event()

    threads = []

    # One tick thread per symbol
    for sym in CONFIG["symbols"]:
        t = threading.Thread(target=tick_collection_loop, args=(sym, store, stop), daemon=True)
        t.start()
        threads.append(t)

    # Leaderboard snapshot thread
    lb = threading.Thread(target=leaderboard_snapshot_loop, args=(store, stop), daemon=True)
    lb.start()
    threads.append(lb)

    # Run for configured duration
    try:
        duration = CONFIG["session_duration_sec"]
        if duration == 0:
            log.info("Running indefinitely. Press Ctrl+C to stop.")
            while True:
                time.sleep(60)
        else:
            log.info(f"Running for {duration} seconds...")
            time.sleep(duration)
    except KeyboardInterrupt:
        log.info("Interrupted by user.")

    # Shutdown
    log.info("Stopping threads...")
    stop.set()
    for t in threads:
        t.join(timeout=5)

    # Merge datasets
    log.info("Merging tick + signal data...")
    for sym in CONFIG["symbols"]:
        store.merge_and_save(sym)

    store.close()
    log.info("Pipeline complete. Check ./data/ for output files.")


if __name__ == "__main__":
    main()

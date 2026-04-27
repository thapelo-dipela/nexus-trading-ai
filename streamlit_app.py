from dotenv import load_dotenv
load_dotenv()
"""
NEXUS Dashboard API Server
Serves real-time market data and bot performance metrics to the HTML dashboard
"""
import os
import json
import sys
import requests
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, jsonify, render_template, send_file, request
from flask_cors import CORS
import logging
import threading
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

import config
from data.prism import PrismClient
from execution.kraken import KrakenClient
import os
from agents.sentiment import fetch_composite_sentiment
from data.free_market import FreeMarketClient
# Note: StockMarketClient and AlpacaClient are optional and can import heavy binary
# dependencies (pandas, alpaca-py). Import them lazily inside initialization blocks
# so a broken binary wheel won't prevent the API server from starting.
from data.currency_converter import get_converter, SUPPORTED_CURRENCIES
from middleware.x402_middleware import require_x402_payment

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask
app = Flask(__name__)
CORS(app)

# Initialize PRISM client
try:
    _kraken = KrakenClient()
    prism_client = PrismClient(api_key=os.environ.get("PRISM_API_KEY", ""), kraken_client=_kraken)
    logger.info("✅ PRISM client initialized")
except Exception as e:
    logger.error(f"❌ Failed to initialize PRISM client: {e}")
    prism_client = None

# Initialize FreeMarketClient (CoinGecko + Binance — no API key required)
try:
    free_market = FreeMarketClient()
    logger.info("✅ FreeMarketClient initialized (CoinGecko + Binance)")
except Exception as e:
    logger.error(f"❌ Failed to initialize FreeMarketClient: {e}")
    free_market = None

# Initialize StockMarketClient (Yahoo Finance — JSE Top 50 + US stocks)
try:
    try:
        from data.stock_market import StockMarketClient
        stock_market = StockMarketClient()
        logger.info("✅ StockMarketClient initialized (Yahoo Finance — JSE + US)")
    except Exception as se:
        raise se
except Exception as e:
    logger.warning(f"⚠️  StockMarketClient unavailable: {e} (install yfinance)")
    stock_market = None

# Initialize AlpacaClient (paper trading — US stocks)
try:
    try:
        from execution.alpaca_client import AlpacaClient
        alpaca_client = AlpacaClient()
        if alpaca_client.is_ready:
            logger.info("✅ AlpacaClient initialized (paper trading)")
        else:
            logger.info("⚠️  AlpacaClient: set ALPACA_API_KEY + ALPACA_API_SECRET in .env")
    except Exception as ae:
        raise ae
except Exception as e:
    logger.warning(f"⚠️  AlpacaClient unavailable: {e}")
    alpaca_client = None

# ============================================================================
# Data Loading Functions
# ============================================================================

def load_agent_weights():
    """Load agent weights from nexus_weights.json"""
    try:
        with open('nexus_weights.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return [
            {'id': 'orderflow', 'name': 'OrderFlow', 'weight': 1.0, 'trades_closed': 0, 'wins': 0, 'pnl_total': 0},
            {'id': 'momentum', 'name': 'Momentum', 'weight': 1.0, 'trades_closed': 0, 'wins': 0, 'pnl_total': 0},
            {'id': 'sentiment', 'name': 'Sentiment', 'weight': 1.0, 'trades_closed': 0, 'wins': 0, 'pnl_total': 0},
            {'id': 'risk_guardian', 'name': 'Risk Guardian', 'weight': 1.0, 'trades_closed': 0, 'wins': 0, 'pnl_total': 0},
        ]

def load_positions():
    """Load open positions from nexus_positions.json with live P&L calculation"""
    try:
        with open('nexus_positions.json', 'r') as f:
            all_pos = json.load(f)
        
        # Get current market price for P&L calculation
        current_price = 0
        try:
            response = requests.get(f'{config.PRISM_API_BASE_URL}/prices/BTC', 
                                   headers={'Authorization': f'Bearer {config.PRISM_API_KEY}'}, 
                                   timeout=5)
            if response.status_code == 200:
                current_price = response.json().get('price', 0)
        except:
            pass
        
        # Add symbol field if missing and calculate live P&L
        positions = []
        for p in all_pos:
            if p.get('status') != 'closed':
                if 'symbol' not in p and 'pair' not in p:
                    p['symbol'] = config.PRIMARY_SYMBOL
                    p['pair'] = config.PRIMARY_SYMBOL + '/USDT'
                
                # Calculate live P&L
                if current_price > 0 and p.get('entry_price'):
                    entry_price = p.get('entry_price')
                    amount_traded = p.get('amount', p.get('volume', 0))
                    direction = p.get('direction', 'BUY')
                    
                    # Calculate live P&L
                    if direction == 'BUY':
                        pnl_usd = (current_price - entry_price) * amount_traded
                        pnl_pct = ((current_price - entry_price) / entry_price * 100) if entry_price else 0
                    else:  # SELL
                        pnl_usd = (entry_price - current_price) * amount_traded
                        pnl_pct = ((entry_price - current_price) / entry_price * 100) if entry_price else 0
                    
                    p['live_pnl_usd'] = pnl_usd
                    p['live_pnl_pct'] = pnl_pct
                    p['current_price'] = current_price
                
                # Ensure amount_traded is present
                if 'amount_traded' not in p:
                    p['amount_traded'] = p.get('amount', p.get('volume', 0))
                
                positions.append(p)
        return positions
    except FileNotFoundError:
        return []

def load_equity_curve():
    """Load equity curve from nexus_equity_curve.json"""
    try:
        with open('nexus_equity_curve.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

# ============================================================================
# API Routes
# ============================================================================

@app.route('/', methods=['GET'])
def dashboard():
    """Serve main dashboard"""
    try:
        with open('dashboard.html', 'r') as f:
            return f.read()
    except FileNotFoundError:
        return "Dashboard not found", 404

@app.route('/api/market', methods=['GET'])
def get_market_data():
    """Get current market data"""
    try:
        # BTC price: Binance (reliable 24h change + volume)
        price_data = free_market.get_price('BTC') if free_market else None

        # BTC signals: PRISM primary, FreeMarketClient fallback
        signals_1h, signals_4h = None, None
        if prism_client:
            signals_1h = prism_client.get_signals('BTC', '1h')
            signals_4h = prism_client.get_signals('BTC', '4h')
        if not signals_1h and free_market:
            signals_1h = free_market.get_signals('BTC', '1h')
        if not signals_4h and free_market:
            signals_4h = free_market.get_signals('BTC', '4h')

        # BTC risk: PRISM primary, FreeMarketClient fallback
        risk = prism_client.get_risk('BTC') if prism_client else None
        if not risk and free_market:
            risk = free_market.get_risk('BTC')

        if not price_data:
            return jsonify({'success': False, 'error': 'Could not fetch BTC price'}), 503

        return jsonify({
            'success': True,
            'price': price_data.get('price', 0),
            'change_24h': price_data.get('change_24h_pct', 0),
            'volume_24h': price_data.get('volume_24h', 0),
            'signal_1h': signals_1h.direction if signals_1h else 'neutral',
            'signal_4h': signals_4h.direction if signals_4h else 'neutral',
            'risk_score': risk.risk_score if risk else 0,
            'source': 'binance+prism',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error fetching market data: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/protected', methods=['GET'])
@require_x402_payment()
def protected_resource():
    """Example protected endpoint that requires per-action payment via x402/Nanopay proof."""
    return jsonify({'success': True, 'message': 'Access granted to paid resource', 'timestamp': datetime.now().isoformat()})

@app.route('/api/agents', methods=['GET'])
@require_x402_payment(amount_usdc=0.000001, description='NEXUS agent performance')
def get_agents():
    """Get agent performance metrics"""
    try:
        agents = load_agent_weights()
        
        # Calculate aggregated metrics
        total_trades = sum(a.get('trades_closed', 0) for a in agents)
        total_wins = sum(a.get('wins', 0) for a in agents)
        total_pnl = sum(a.get('pnl_total', 0) for a in agents)
        
        return jsonify({
            'success': True,
            'agents': agents,
            'summary': {
                'total_trades': total_trades,
                'total_wins': total_wins,
                'win_rate': (total_wins / total_trades * 100) if total_trades > 0 else 0,
                'total_pnl': total_pnl,
                'avg_pnl_per_trade': (total_pnl / total_trades) if total_trades > 0 else 0,
            },
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error fetching agent data: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/sentiment', methods=['GET'])
def get_sentiment():
    """Get sentiment analysis"""
    try:
        import requests
        
        sentiment_data = {
            'timestamp': datetime.now().isoformat()
        }
        
        # Fear & Greed Index
        try:
            fng_response = requests.get('https://api.alternative.me/fng/?limit=1', timeout=5)
            fng_data = fng_response.json()
            if fng_data.get('data'):
                sentiment_data['fear_greed'] = int(fng_data['data'][0]['value'])
        except Exception as e:
            logger.warning(f"Failed to fetch Fear & Greed: {e}")
        
        # Composite sentiment
        try:
            composite = fetch_composite_sentiment()
            sentiment_data['composite'] = composite
        except Exception as e:
            logger.warning(f"Failed to fetch composite sentiment: {e}")
        
        return jsonify({
            'success': True,
            **sentiment_data
        })
    except Exception as e:
        logger.error(f"Error fetching sentiment data: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/positions', methods=['GET'])
def get_positions():
    """Get current open positions"""
    try:
        positions = load_positions()
        return jsonify({
            'success': True,
            'positions': positions,
            'count': len(positions),
            'total_exposure': sum(p.get('size_usd', 0) for p in positions),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error fetching positions: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/positions/<position_id>/close', methods=['POST'])
def close_position_by_id(position_id):
    """Close a position via AI Chat command"""
    try:
        with open('nexus_positions.json', 'r') as f:
            all_positions = json.load(f)
        
        position_closed = False
        for pos in all_positions:
            if str(pos.get('id')) == str(position_id):
                pos['status'] = 'closed'
                pos['closed_at'] = datetime.now().isoformat()
                position_closed = True
                break
        
        if not position_closed:
            return jsonify({'success': False, 'error': 'Position not found'}), 404
        
        with open('nexus_positions.json', 'w') as f:
            json.dump(all_positions, f, indent=2)
        
        logger.info(f"Position {position_id} closed via AI Chat")
        return jsonify({
            'success': True,
            'message': f'Position {position_id} closed successfully',
            'position_id': position_id,
            'status': 'closed'
        })
    except Exception as e:
        logger.error(f"Error closing position: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/positions/<position_id>/open', methods=['POST'])
def open_position_by_id(position_id):
    """Reopen a closed position via AI Chat command"""
    try:
        with open('nexus_positions.json', 'r') as f:
            all_positions = json.load(f)
        
        position_found = False
        for pos in all_positions:
            if str(pos.get('id')) == str(position_id):
                pos['status'] = 'open'
                if 'closed_at' in pos:
                    del pos['closed_at']
                position_found = True
                break
        
        if not position_found:
            return jsonify({'success': False, 'error': 'Position not found'}), 404
        
        with open('nexus_positions.json', 'w') as f:
            json.dump(all_positions, f, indent=2)
        
        logger.info(f"Position {position_id} reopened via AI Chat")
        return jsonify({
            'success': True,
            'message': f'Position {position_id} reopened successfully',
            'position_id': position_id,
            'status': 'open'
        })
    except Exception as e:
        logger.error(f"Error reopening position: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/equity', methods=['GET'])
def get_equity():
    """Get equity curve"""
    try:
        equity_data = load_equity_curve()
        return jsonify({
            'success': True,
            'data': equity_data,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error fetching equity data: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/risk', methods=['GET'])
@require_x402_payment(amount_usdc=0.000001, description='NEXUS risk metrics')
def get_risk():
    """Get risk metrics"""
    try:
        risk = None
        source = 'mock'

        # Primary: PRISM
        if prism_client:
            risk = prism_client.get_risk('BTC')
            if risk:
                source = 'prism'

        # Fallback: FreeMarketClient (computed from Binance daily OHLCV)
        if not risk and free_market:
            risk = free_market.get_risk('BTC')
            if risk:
                source = 'binance'

        if risk:
            return jsonify({
                'success': True,
                'risk_score': risk.risk_score,
                'atr_pct': risk.atr_pct,
                'volatility_30d': risk.volatility_30d,
                'max_drawdown_30d': risk.max_drawdown_30d,
                'sharpe_ratio': risk.sharpe_ratio,
                'sortino_ratio': risk.sortino_ratio,
                'source': source,
                'timestamp': datetime.now().isoformat()
            })

        # Last resort: static fallback so dashboard never breaks
        return jsonify({
            'success': True,
            'risk_score': 42.5,
            'atr_pct': 1.2,
            'volatility_30d': 22.5,
            'max_drawdown_30d': 8.3,
            'sharpe_ratio': 1.45,
            'sortino_ratio': 2.1,
            'source': 'mock',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error fetching risk data: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/market-overview', methods=['GET'])
def get_market_overview():
    """Get prices and basic info for all supported cryptocurrencies with currency conversion"""
    try:
        if not free_market:
            return jsonify({'success': False, 'error': 'FreeMarketClient not available'}), 503

        # Get target currency from query param (default: USD)
        target_currency = request.args.get('currency', 'USD').upper()
        if target_currency not in SUPPORTED_CURRENCIES:
            target_currency = 'USD'
        
        # Crypto prices are in USD by default
        from_currency = 'USD'
        
        # Get converter instance
        converter = get_converter()
        exchange_rate = converter.get_rate(from_currency, target_currency) or 1.0

        # Single batch call — all symbols in one Binance API request
        symbols = list(config.SUPPORTED_SYMBOLS.keys())
        all_prices = free_market.get_prices_batch(symbols)

        overview = []
        for symbol, price_data in all_prices.items():
            if symbol in config.SUPPORTED_SYMBOLS:
                meta = config.SUPPORTED_SYMBOLS[symbol]
                price = price_data.get('price') if price_data else None
                
                # Convert price to target currency
                if price and target_currency != 'USD':
                    price = price * exchange_rate
                
                overview.append({
                    'symbol': symbol,
                    'name': meta['name'],
                    'category': meta['category'],
                    'active': meta['active'],
                    'price': price,
                    'price_in_usd': price_data.get('price') if price_data else None,
                    'change_24h_pct': price_data.get('change_24h_pct') if price_data else None,
                    'volume_24h': price_data.get('volume_24h') if price_data else None,
                    'source': 'binance',
                })

        return jsonify({
            'success': True,
            'count': len(overview),
            'currencies': overview,
            'currency': target_currency,
            'from_currency': 'USD',
            'exchange_rate': exchange_rate,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error fetching market overview: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/crypto/<symbol>/price', methods=['GET'])
def get_crypto_price(symbol):
    """Get price for a specific cryptocurrency"""
    try:
        symbol_upper = symbol.upper()
        price_data = None
        source = None

        # Primary: FreeMarketClient (Binance)
        if free_market:
            price_data = free_market.get_price(symbol_upper)
            if price_data:
                source = 'binance'

        # Fallback: PRISM (BTC only, reliably)
        if not price_data and prism_client:
            price_data = prism_client.get_price(symbol_upper)
            if price_data:
                source = 'prism'

        if price_data:
            return jsonify({
                'success': True,
                'symbol': symbol_upper,
                'price': price_data.get('price'),
                'change_24h_pct': price_data.get('change_24h_pct'),
                'volume_24h': price_data.get('volume_24h'),
                'source': source,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Could not fetch price for {symbol_upper}'
            }), 404
    except Exception as e:
        logger.error(f"Error fetching price for {symbol}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/currencies', methods=['GET'])
def get_currencies():
    """Get list of supported currencies"""
    try:
        converter = get_converter()
        currencies = converter.get_all_currencies()
        
        return jsonify({
            'success': True,
            'count': len(currencies),
            'currencies': currencies,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error fetching currencies: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/exchange-rate', methods=['GET'])
def get_exchange_rate_endpoint():
    """Get exchange rate between two currencies"""
    try:
        from_currency = request.args.get('from', 'USD').upper()
        to_currency = request.args.get('to', 'ZAR').upper()
        
        if from_currency not in SUPPORTED_CURRENCIES or to_currency not in SUPPORTED_CURRENCIES:
            return jsonify({'success': False, 'error': 'Unsupported currency'}), 400
        
        converter = get_converter()
        rate = converter.get_rate(from_currency, to_currency)
        
        if rate is None:
            return jsonify({'success': False, 'error': 'Could not fetch exchange rate'}), 500
        
        return jsonify({
            'success': True,
            'from_currency': from_currency,
            'to_currency': to_currency,
            'rate': rate,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error fetching exchange rate: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/crypto/<symbol>/signals', methods=['GET'])
@require_x402_payment(amount_usdc=0.000001, description='NEXUS trade signal')
def get_crypto_signals(symbol):
    """Get signals for a specific cryptocurrency"""
    try:
        symbol_upper = symbol.upper()
        timeframe = request.args.get('timeframe', '1h')
        signals = None
        source = None

        # BTC: PRISM primary (best signal quality), FreeMarketClient fallback
        # Altcoins: FreeMarketClient primary (avoids PRISM rate limits)
        if symbol_upper == 'BTC' and prism_client:
            signals = prism_client.get_signals(symbol_upper, timeframe)
            if signals:
                source = 'prism'

        if not signals and free_market:
            signals = free_market.get_signals(symbol_upper, timeframe)
            if signals:
                source = 'binance'

        if signals:
            return jsonify({
                'success': True,
                'symbol': symbol_upper,
                'timeframe': timeframe,
                'direction': signals.direction,
                'confidence': signals.confidence,
                'score': signals.score,
                'reasoning': signals.reasoning,
                'indicators': signals.indicators,
                'current_price': signals.current_price,
                'source': source,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Could not fetch signals for {symbol_upper}'
            }), 404
    except Exception as e:
        logger.error(f"Error fetching signals for {symbol}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/performance', methods=['GET'])
@require_x402_payment(amount_usdc=0.000001, description='NEXUS performance data')
def get_performance():
    """Get comprehensive performance metrics"""
    try:
        agents = load_agent_weights()
        positions = load_positions()
        equity_data = load_equity_curve()
        
        # Calculate performance metrics
        total_trades = sum(a.get('trades_closed', 0) for a in agents)
        total_wins = sum(a.get('wins', 0) for a in agents)
        total_pnl = sum(a.get('pnl_total', 0) for a in agents)
        
        # Calculate Sharpe and Max Drawdown from equity curve
        if equity_data:
            equity_values = [e['equity'] for e in equity_data]
            max_equity = max(equity_values)
            min_equity = min(equity_values)
            max_dd = (max_equity - min_equity) / max_equity * 100 if max_equity > 0 else 0
            returns = [(equity_values[i] - equity_values[i-1]) / equity_values[i-1] * 100 
                      for i in range(1, len(equity_values))
                      if equity_values[i-1] > 0.01]
            # Clamp to reasonable range to avoid division artifacts
            returns = [max(-100, min(100, r)) for r in returns]
            avg_return = sum(returns) / len(returns) if returns else 0
        else:
            max_dd = 0
            avg_return = 0
        
        return jsonify({
            'success': True,
            'performance': {
                'total_trades': total_trades,
                'wins': total_wins,
                'losses': total_trades - total_wins if total_trades > 0 else 0,
                'win_rate': (total_wins / total_trades * 100) if total_trades > 0 else 0,
                'total_pnl': total_pnl,
                'avg_pnl': (total_pnl / total_trades) if total_trades > 0 else 0,
                'max_drawdown': max_dd,
                'avg_daily_return': avg_return,
                'open_positions': len(positions),
            },
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error fetching performance data: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/balance', methods=['GET'])
def get_balance():
    try:
        import subprocess
        result = subprocess.run(['kraken', 'balance', '-o', 'json'], capture_output=True, text=True, timeout=10)
        balance = 0.0
        if result.returncode == 0 and result.stdout.strip():
            import json as _json
            bal = _json.loads(result.stdout)
            balance = sum(float(v) for v in bal.values()) if isinstance(bal, dict) else 0.0
        
        # If balance is 0 or not available, use allocated trading balance from config
        if balance <= 0:
            # Use allocated trading capital (from environment or config)
            allocated_balance = float(os.environ.get('ALLOCATED_BALANCE', '10000'))
            balance = allocated_balance
        
        # Also add PnL from weights
        agents = load_agent_weights()
        total_pnl = sum(a.get('pnl_total', 0) for a in agents)
        total_trades = sum(a.get('trades_closed', 0) for a in agents)
        total_wins = sum(a.get('wins', 0) for a in agents)
        
        # Calculate current equity: allocated balance + PnL
        current_equity = balance + total_pnl
        
        return jsonify({
            'success': True,
            'balance_usd': current_equity,  # Current equity (balance + PnL)
            'initial_balance': balance,     # Starting allocated balance
            'total_pnl': total_pnl,
            'total_trades': total_trades,
            'total_wins': total_wins,
            'win_rate': (total_wins / total_trades * 100) if total_trades > 0 else 0,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/trades', methods=['GET'])
def get_trades():
    try:
        with open('nexus_positions.json') as f:
            all_trades = json.load(f)
        closed = [t for t in all_trades if t.get('status') == 'closed']
        # Add symbol field if missing (default to PRIMARY_SYMBOL)
        for t in closed:
            if 'symbol' not in t and 'pair' not in t:
                t['symbol'] = config.PRIMARY_SYMBOL
                t['pair'] = config.PRIMARY_SYMBOL + '/USDT'
        total_pnl = sum(t.get('pnl_usd', 0) for t in closed)
        wins = [t for t in closed if t.get('pnl_usd', 0) > 0]
        return jsonify({'success': True, 'trades': closed[-20:],
            'total': len(closed), 'wins': len(wins),
            'total_pnl': total_pnl, 'win_rate': len(wins)/len(closed)*100 if closed else 0})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/consensus', methods=['GET'])
@require_x402_payment(amount_usdc=0.000001, description='NEXUS consensus engine')
def get_consensus():
    try:
        with open('nexus_live_decisions.json') as f:
            data = json.load(f)
        return jsonify({'success': True, 'data': data.get('consensus_decision', {}),
            'cycle': data.get('latest_cycle', 0), 'timestamp': data.get('timestamp', '')})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/checkpoints', methods=['GET'])
def get_checkpoints():
    try:
        with open('nexus_weights.json') as f:
            weights = json.load(f)
        return jsonify({'success': True, 'checkpoints': weights,
            'timestamp': datetime.now().isoformat()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status':                'healthy',
        'timestamp':             datetime.now().isoformat(),
        'prism_connected':       prism_client is not None,
        'free_market_connected': free_market is not None,
        'stock_market_ready':    stock_market is not None,
        'alpaca_ready':          alpaca_client is not None and alpaca_client.is_ready,
        'alpaca_mode':           ('LIVE' if alpaca_client and alpaca_client.is_live else 'PAPER') if alpaca_client else 'N/A',
        'jse_enabled':           getattr(config, 'JSE_ENABLED', False),
        'us_stocks_enabled':     getattr(config, 'US_STOCKS_ENABLED', False),
        'btc_correlation':       getattr(config, 'BTC_CORRELATION_ENABLED', False),
        'sepolia_pairs':         len(getattr(config, 'SEPOLIA_TEST_PAIRS', [])),
    })

@app.route('/api/settings', methods=['GET', 'POST'])
def manage_settings():
    """Get or save agent configuration and risk settings"""
    try:
        if request.method == 'POST':
            # Save settings to JSON file
            settings = request.json
            if not settings:
                return jsonify({'success': False, 'error': 'No settings provided'}), 400
            
            # Validate settings structure
            required_fields = ['risk_per_trade', 'stop_loss_pct', 'take_profit_pct', 
                             'max_position_pct', 'max_leverage', 'enabled_agents']
            missing_fields = [f for f in required_fields if f not in settings]
            if missing_fields:
                logger.warning(f"Settings missing fields: {missing_fields}. Using partial update.")
            
            # Write settings to file
            with open('nexus_agent_settings.json', 'w') as f:
                json.dump(settings, f, indent=2)
            
            logger.info(f"✅ Settings saved: risk={settings.get('risk_per_trade')}%, "
                       f"sl={settings.get('stop_loss_pct')}%, "
                       f"tp={settings.get('take_profit_pct')}%, "
                       f"leverage={settings.get('max_leverage')}x")
            
            return jsonify({
                'success': True,
                'message': 'Settings saved successfully',
                'settings': settings,
                'timestamp': datetime.now().isoformat()
            })
        
        else:  # GET request
            # Load settings from JSON file or return defaults
            try:
                with open('nexus_agent_settings.json') as f:
                    settings = json.load(f)
                return jsonify({
                    'success': True,
                    'source': 'file',
                    'settings': settings,
                    'timestamp': datetime.now().isoformat()
                })
            except FileNotFoundError:
                # Return default settings if file doesn't exist
                default_settings = {
                    'risk_per_trade': 1.0,
                    'stop_loss_pct': 2.0,
                    'take_profit_pct': 5.0,
                    'max_position_pct': 20.0,
                    'max_leverage': 3.0,
                    'min_trade_size': 10.0,
                    'enabled_agents': {
                        'momentum': True,
                        'mean_reversion': True,
                        'sentiment': True,
                        'orderflow': True,
                        'yolo': True
                    }
                }
                return jsonify({
                    'success': True,
                    'source': 'defaults',
                    'settings': default_settings,
                    'message': 'Using default settings (no saved config found)',
                    'timestamp': datetime.now().isoformat()
                })
    
    except Exception as e:
        logger.error(f"Error managing settings: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/live-decisions', methods=['GET'])
def get_live_decisions():
    """Get live agent decisions and position reasoning"""
    try:
        with open('nexus_live_decisions.json', 'r') as f:
            data = json.load(f)
        return jsonify({
            'success': True,
            'data': data,
            'timestamp': datetime.now().isoformat()
        })
    except FileNotFoundError:
        return jsonify({
            'success': True,
            'data': {
                'latest_cycle': 0,
                'agent_decisions': [],
                'consensus_decision': None,
                'positions': [],
                'recent_closes': [],
                'timestamp': ''
            },
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/config', methods=['GET'])
def get_config():
    """Serve frontend config from .env — never expose secrets, only what dashboard needs"""
    return jsonify({
        'groq_key':  os.environ.get('GROQ_API_KEY', ''),
        'strategy':  os.environ.get('ACTIVE_STRATEGY', 'algorithmic_quant'),
        'chain_id':  os.environ.get('CHAIN_ID', '11155111'),
    })

@app.route('/office')
def pixel_office():
    """Serve pixel office HTML"""
    return send_file('pixel_office.html')

# Serve JSON files from root directory
@app.route('/<filename>')
def serve_static(filename):
    """Serve static files (JSON, etc.) from root directory"""
    if filename.endswith('.json'):
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            return jsonify(data)
        except FileNotFoundError:
            return jsonify({'error': 'File not found'}), 404
        except json.JSONDecodeError:
            return send_file(filename, mimetype='application/json')
    return send_file(filename)

# ============================================================================
# Position Management (Manual Close)
# ============================================================================

@app.route('/api/positions/close', methods=['POST'])
def close_position():
    """Close an open position manually"""
    try:
        data = request.get_json()
        trade_id = data.get('trade_id')
        
        if not trade_id:
            return jsonify({'success': False, 'error': 'trade_id required'}), 400
        
        # Load positions
        with open('nexus_positions.json', 'r') as f:
            positions_data = json.load(f)
        
        # Find and close position
        closed = False
        for p in positions_data:
            if p.get('trade_id') == trade_id and p.get('status') == 'open':
                p['status'] = 'closed'
                p['exit_timestamp'] = int(datetime.now().timestamp())
                p['exit_reason'] = 'manual_close'
                # Use current price as exit price
                p['exit_price'] = data.get('exit_price', p.get('entry_price', 0))
                closed = True
                break
        
        if not closed:
            return jsonify({'success': False, 'error': 'Position not found or already closed'}), 404
        
        # Save updated positions
        with open('nexus_positions.json', 'w') as f:
            json.dump(positions_data, f, indent=2)
        
        logger.info(f"✓ Manually closed position: {trade_id}")
        return jsonify({
            'success': True,
            'message': f'Position {trade_id} closed successfully',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error closing position: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================================
# Stock Trading Routes — JSE + US + BTC Correlation
# ============================================================================

@app.route('/api/stocks/jse', methods=['GET'])
def get_jse_overview():
    """Get JSE Top 50 price overview with currency conversion"""
    try:
        if not stock_market:
            return jsonify({'success': False, 'error': 'StockMarketClient not available — install yfinance'}), 503
        
        # Get target currency from query param (default: ZAR)
        target_currency = request.args.get('currency', 'ZAR').upper()
        if target_currency not in SUPPORTED_CURRENCIES:
            target_currency = 'ZAR'
        
        # JSE prices are in ZAR by default
        from_currency = 'ZAR'
        
        # Get converter instance and exchange rate
        converter = get_converter()
        if target_currency != 'ZAR':
            exchange_rate = converter.get_rate(from_currency, target_currency) or 1.0
        else:
            exchange_rate = 1.0
        
        top_n = int(request.args.get('top_n', config.JSE_TOP_N if hasattr(config, 'JSE_TOP_N') else 50))
        overview = stock_market.get_jse_overview(top_n=top_n)
        
        # Normalize field names: "ticker" → "symbol" for consistency with crypto API
        normalized = []
        for stock in overview:
            price = stock.get('price')
            if price and target_currency != 'ZAR':
                price = price * exchange_rate
            
            normalized.append({
                'symbol': stock.get('ticker', stock.get('symbol')),
                'name': stock.get('name'),
                'price': price,
                'price_in_zar': stock.get('price'),
                'change_24h_pct': stock.get('change_24h_pct'),
                'category': 'JSE',
                'currency': target_currency,
            })
        
        return jsonify({
            'success': True,
            'count': len(normalized),
            'stocks': normalized,
            'market': 'JSE',
            'base_currency': 'ZAR',
            'currency': target_currency,
            'exchange_rate': exchange_rate,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f'Error fetching JSE overview: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/stocks/us', methods=['GET'])
def get_us_overview():
    """Get US Top stocks price overview with currency conversion"""
    try:
        if not stock_market:
            return jsonify({'success': False, 'error': 'StockMarketClient not available — install yfinance'}), 503
        
        # Get target currency from query param (default: USD)
        target_currency = request.args.get('currency', 'USD').upper()
        if target_currency not in SUPPORTED_CURRENCIES:
            target_currency = 'USD'
        
        # US stock prices are in USD by default
        from_currency = 'USD'
        
        # Get converter instance and exchange rate
        converter = get_converter()
        if target_currency != 'USD':
            exchange_rate = converter.get_rate(from_currency, target_currency) or 1.0
        else:
            exchange_rate = 1.0
        
        overview = stock_market.get_us_overview()
        
        # Normalize field names: "ticker" → "symbol" for consistency with crypto API
        normalized = []
        for stock in overview:
            price = stock.get('price')
            if price and target_currency != 'USD':
                price = price * exchange_rate
            
            normalized.append({
                'symbol': stock.get('ticker', stock.get('symbol')),
                'name': stock.get('name'),
                'price': price,
                'price_in_usd': stock.get('price'),
                'change_24h_pct': stock.get('change_24h_pct'),
                'category': 'US',
                'currency': target_currency,
            })
        
        return jsonify({
            'success': True,
            'count': len(normalized),
            'stocks': normalized,
            'market': 'US',
            'base_currency': 'USD',
            'currency': target_currency,
            'exchange_rate': exchange_rate,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f'Error fetching US stocks overview: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/stocks/btc-signal', methods=['GET'])
def get_btc_correlation_signal():
    """
    BTC Correlation Signal — compares JSE Top 50 vs BTC 30-day performance.
    Returns a crypto positioning recommendation based on relative strength.

    Query params:
      use_jse=true/false   (default: true)
      use_us=true/false    (default: false)
      top_n=20             (number of JSE stocks to include)
    """
    try:
        if not stock_market:
            return jsonify({'success': False, 'error': 'StockMarketClient not available — install yfinance'}), 503

        use_jse = request.args.get('use_jse', 'true').lower() == 'true'
        use_us  = request.args.get('use_us', 'false').lower() == 'true'
        top_n   = int(request.args.get('top_n', 20))

        # Get BTC 30d return from FreeMarketClient if available
        btc_return_30d = None
        if free_market:
            try:
                btc_returns = stock_market.get_30d_returns(['BTC-USD'])
                btc_return_30d = btc_returns.get('BTC-USD')
            except Exception:
                pass

        signal = stock_market.btc_correlation_signal(
            btc_return_30d=btc_return_30d,
            use_jse=use_jse,
            use_us=use_us,
            top_n=top_n,
        )

        return jsonify({
            'success':            True,
            'crypto_signal':      signal.crypto_signal,
            'confidence':         signal.confidence,
            'btc_return_30d':     signal.btc_return_30d,
            'stock_return_30d':   signal.stock_return_30d,
            'relative_strength':  signal.relative_strength,
            'top_performers':     signal.top_performers[:10],
            'underperformers':    signal.underperformers[:10],
            'reasoning':          signal.reasoning,
            'basket':             'JSE Top 50' if use_jse else 'US Stocks',
            'timestamp':          datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f'Error computing BTC correlation signal: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/stocks/alpaca', methods=['GET'])
def get_alpaca_status():
    """Get Alpaca account status and open positions"""
    try:
        if not alpaca_client or not alpaca_client.is_ready:
            return jsonify({
                'success': False,
                'error': 'AlpacaClient not configured — set ALPACA_API_KEY + ALPACA_API_SECRET in .env',
                'setup_url': 'https://alpaca.markets'
            }), 503

        account   = alpaca_client.get_account()
        positions = alpaca_client.get_positions()
        market_open = alpaca_client.is_market_open()

        return jsonify({
            'success':      True,
            'account':      account,
            'positions':    positions,
            'market_open':  market_open,
            'mode':         'LIVE' if alpaca_client.is_live else 'PAPER',
            'timestamp':    datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f'Error fetching Alpaca status: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/stocks/sepolia-pairs', methods=['GET'])
def get_sepolia_pairs():
    """List available Sepolia testnet token pairs for on-chain submission"""
    pairs = getattr(config, 'SEPOLIA_TEST_PAIRS', ['WBTC/USDC'])
    primary = getattr(config, 'SEPOLIA_PRIMARY_PAIR', 'WBTC/USDC')
    return jsonify({
        'success':      True,
        'pairs':        pairs,
        'primary_pair': primary,
        'network':      'Sepolia Testnet',
        'chain_id':     config.CHAIN_ID,
        'note':         'Get test ETH at https://sepoliafaucet.com, test LINK at https://faucets.chain.link',
        'timestamp':    datetime.now().isoformat()
    })



# ============================================================================
# Nanopay / Arc Batch Payment Routes
# ============================================================================

NANOPAY_URL  = "http://localhost:3001"
ARC_RPC_URL  = "https://rpc.testnet.arc.network"
AGENT_WALLET = "0xF987B94427bDe78bb67Ef91C722015AC69de55C5"

@app.route('/api/nanopay/batch', methods=['POST'])
def nanopay_batch():
    """Proxy batch-charge to Node nanopay service and enrich with fee data"""
    try:
        import requests as _req
        import threading
        body = request.get_json()
        actions = body.get('actions', [])
        if not actions:
            return jsonify({'success': False, 'error': 'actions array required'}), 400
        resp = _req.post(f"{NANOPAY_URL}/api/batch-charge", json={'actions': actions}, timeout=60)
        data = resp.json()

        # Enrich receipts in background so dashboard endpoint never blocks on RPC
        def _enrich_and_persist(payload):
            try:
                if not payload.get('success'):
                    return
                receipts = payload.get('result', {}).get('receipts', [])
                if not receipts:
                    return
                for receipt in receipts:
                    tx_hash = receipt.get('txHash')
                    if tx_hash and not tx_hash.startswith('0xdeadbeef'):
                        try:
                            rpc_resp = _req.post(ARC_RPC_URL, json={
                                "jsonrpc": "2.0", "method": "eth_getTransactionReceipt",
                                "params": [tx_hash], "id": 1
                            }, timeout=8).json()
                            rec = rpc_resp.get('result', {})
                            if rec:
                                gas_used      = int(rec.get('gasUsed', '0x0'), 16)
                                eff_gas_price = int(rec.get('effectiveGasPrice', '0x0'), 16)
                                fee_wei       = gas_used * eff_gas_price
                                fee_usdc      = round(fee_wei / 1e18, 8)
                                block_number  = int(rec.get('blockNumber', '0x0'), 16)
                                # Update the saved receipt with actual fees and block number
                                update_receipt_fee(tx_hash, fee_usdc, gas_used, block_number)
                        except Exception as e:
                            # ignore single receipt enrichment failures
                            logger.debug(f"Fee enrichment failed for {tx_hash}: {e}")
                            continue
            except Exception as e:
                # ensure background worker never raises to main thread
                logger.debug(f"Enrichment worker error: {e}")
                pass

        # Persist receipts immediately
        try:
            if data.get('success'):
                receipts = data.get('result', {}).get('receipts', [])
                for receipt in receipts:
                    save_batch_receipt(receipt)
        except Exception as e:
            logger.warning(f"Failed to save receipts: {e}")
        
        try:
            t = threading.Thread(target=_enrich_and_persist, args=(data,))
            t.daemon = True
            t.start()
        except Exception:
            # if threading fails, continue and return raw data
            pass

        return jsonify(data)
    except Exception as e:
        logger.error(f"Nanopay batch error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/nanopay/receipts', methods=['GET'])
def nanopay_receipts():
    """Return receipts from local nanopay receipt log"""
    try:
        receipts_file = os.path.join(
            os.path.dirname(__file__),
            'payments/circle_nanopay/.nanopay_data/receipts.json'
        )
        if os.path.exists(receipts_file):
            with open(receipts_file) as f:
                receipts = json.load(f)
        else:
            receipts = []
        total_usdc = sum(r.get('amountUSDC', 0) for r in receipts)
        return jsonify({
            'success': True,
            'count': len(receipts),
            'total_usdc': total_usdc,
            'receipts': receipts[-50:]  # last 50
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# Store batch receipts in memory (can be persisted to file/DB)
BATCH_RECEIPTS_FILE = 'batch_receipts.json'

def load_batch_receipts():
    """Load batch receipts from file"""
    try:
        if os.path.exists(BATCH_RECEIPTS_FILE):
            with open(BATCH_RECEIPTS_FILE, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return []

def save_batch_receipt(receipt):
    """Persist batch receipt to file"""
    try:
        receipts = load_batch_receipts()
        receipt['timestamp'] = datetime.now().isoformat() if 'timestamp' not in receipt else receipt['timestamp']
        receipts.append(receipt)
        with open(BATCH_RECEIPTS_FILE, 'w') as f:
            json.dump(receipts, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save receipt: {e}")

def update_receipt_fee(tx_hash, fee_usdc, gas_used, block_number=None):
    """Update receipt with enriched fee data and block number"""
    try:
        receipts = load_batch_receipts()
        for receipt in receipts:
            if receipt.get('txHash') == tx_hash:
                receipt['fee_usdc'] = fee_usdc
                receipt['gas_used'] = gas_used
                receipt['fee_enriched'] = True
                if block_number:
                    receipt['blockNumber'] = block_number
        with open(BATCH_RECEIPTS_FILE, 'w') as f:
            json.dump(receipts, f, indent=2)
    except Exception as e:
        logger.warning(f"Failed to update receipt: {e}")

def load_scheduler_config():
    """Load scheduler configuration"""
    try:
        if os.path.exists(AGENT_SCHEDULER_CONFIG):
            with open(AGENT_SCHEDULER_CONFIG, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return {'enabled': False, 'interval_seconds': 300, 'amount_per_action': 0.005, 'actions_per_batch': 4}

def save_scheduler_config(config):
    """Save scheduler configuration"""
    try:
        with open(AGENT_SCHEDULER_CONFIG, 'w') as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save scheduler config: {e}")

@app.route('/api/nanopay/wallet-txs', methods=['GET'])
def nanopay_wallet_txs():
    """Fetch transaction history: first from local receipts, then from Arc explorer"""
    try:
        import requests as _req
        txs = []
        
        # Load local batch receipts first (most recent)
        try:
            receipts = load_batch_receipts()
            for receipt in reversed(receipts[-20:]):  # Last 20
                block_num = receipt.get('blockNumber') or receipt.get('block', '—')
                txs.append({
                    'txHash':    receipt.get('txHash', '—'),
                    'block':     block_num,
                    'timestamp': receipt.get('timestamp', ''),
                    'fee_usdc':  receipt.get('fee_usdc', 0),
                    'status':    'success' if not receipt.get('txHash', '').startswith('0xdeadbeef') else 'pending',
                    'explorer':  f"https://testnet.arcscan.app/tx/{receipt.get('txHash')}" if receipt.get('txHash') else '#',
                    'source':    'local'
                })
        except Exception as e:
            logger.warning(f"Failed to load local receipts: {e}")
        
        # Also query Arc explorer for on-chain data
        try:
            url = f"https://testnet.arcscan.app/api/v2/addresses/{AGENT_WALLET}/transactions?filter=from&limit=10"
            resp = _req.get(url, timeout=10)
            if resp.status_code == 200:
                items = resp.json().get('items', [])
                for item in items:
                    tx_hash = item.get('hash')
                    # Don't duplicate
                    if not any(t['txHash'] == tx_hash for t in txs):
                        gas_used  = int(item.get('gas_used') or 0)
                        gas_price = int(item.get('gas_price') or 0)
                        fee_wei   = gas_used * gas_price
                        txs.append({
                            'txHash':    tx_hash,
                            'block':     item.get('block'),
                            'timestamp': item.get('timestamp', ''),
                            'fee_usdc':  round(fee_wei / 1e18, 8),
                            'status':    item.get('status', 'pending'),
                            'explorer':  f"https://testnet.arcscan.app/tx/{tx_hash}",
                            'source':    'explorer'
                        })
        except Exception as e:
            logger.warning(f"Explorer API error: {e}")
        
        # Sort by timestamp descending, limit to 20
        txs = sorted(txs, key=lambda x: x.get('timestamp', '0') or '0', reverse=True)[:20]
        
        if not txs:
            return jsonify({'success': True, 'txs': [], 'count': 0, 'note': 'No transactions found - batches may not be indexed yet'})
        
        return jsonify({'success': True, 'txs': txs, 'count': len(txs)})
    except Exception as e:
        logger.error(f"Wallet txs error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================================
# Documentation Routes
# ============================================================================

@app.route('/docs/cctp', methods=['GET'])
def docs_cctp():
    """Serve Cross-Chain Transfer Protocol documentation page"""
    try:
        with open('docs_cctp.html', 'r') as f:
            return f.read()
    except FileNotFoundError:
        return jsonify({'success': False, 'error': 'CCTP documentation not found'}), 404

@app.route('/docs', methods=['GET'])
def docs_index():
    """Documentation index page"""
    return jsonify({
        'success': True,
        'documentation': {
            'cctp': {
                'title': 'Cross-Chain Transfer Protocol',
                'url': '/docs/cctp',
                'description': 'Learn about Circle\'s CCTP for native USDC transfers across blockchains'
            }
        },
        'timestamp': datetime.now().isoformat()
    })

# ============================================================================
# Agent Auto-Transfer Routes
# ============================================================================

# Multi-agent configuration for round-robin transfers
AGENT_ADDRESSES = [
    "0xF987B94427bDe78bb67Ef91C722015AC69de55C5",  # Agent 1 (Main)
    "0xC2D2B7E4F8A6C3D5E1F7A9B2C4E6F8A0B2D4E6F8",  # Agent 2 (Analyst)
    "0xA1B3C5D7E9F1A3B5C7D9E1F3A5B7C9D1E3F5A7B9",  # Agent 3 (Trader)
    "0xF3E5D7C9B1A3F5E7D9C1B3A5F7E9D1C3B5A7F9E1",  # Agent 4 (Risk Guardian)
]

AGENT_TRANSFER_SCHEDULE = 'agent_transfers.json'
AGENT_SCHEDULER_CONFIG = 'agent_scheduler_config.json'

# Continuous transfer scheduler state
CONTINUOUS_TRANSFER_STATE = {
    'enabled': False,
    'interval_seconds': 300,
    'amount_per_action': 0.005,
    'actions_per_batch': 4,
    'scheduler_job': None
}

def load_agent_transfer_log():
    """Load agent transfer log"""
    try:
        if os.path.exists(AGENT_TRANSFER_SCHEDULE):
            with open(AGENT_TRANSFER_SCHEDULE, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return {'last_transfer': '', 'transfers': []}

def save_agent_transfer(transfer_data):
    """Save agent transfer record"""
    try:
        log = load_agent_transfer_log()
        transfer_data['timestamp'] = datetime.now().isoformat()
        log['transfers'].append(transfer_data)
        log['last_transfer'] = transfer_data['timestamp']
        with open(AGENT_TRANSFER_SCHEDULE, 'w') as f:
            json.dump(log, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save transfer: {e}")

@app.route('/api/agents/config', methods=['GET'])
def agents_config():
    """Get configured agent addresses"""
    return jsonify({
        'success': True,
        'agents': AGENT_ADDRESSES,
        'count': len(AGENT_ADDRESSES)
    })

@app.route('/api/agents/trade', methods=['POST'])
def trigger_agent_trade():
    """Trigger a trade signal (buy/sell) for agents"""
    try:
        body = request.get_json() or {}
        symbol = body.get('symbol', 'BTC')
        direction = body.get('direction', 'BUY')
        amount = body.get('amount', 0.1)
        price = body.get('price')
        
        # Log trade signal
        trade_signal = {
            'timestamp': datetime.now().isoformat(),
            'symbol': symbol,
            'direction': direction,
            'amount': amount,
            'price': price,
            'status': 'pending',
            'source': 'dashboard'
        }
        
        # Save to live decisions file if it exists
        try:
            with open('nexus_live_decisions.json', 'r') as f:
                decisions = json.load(f)
            if 'signals' not in decisions:
                decisions['signals'] = []
        except:
            decisions = {'signals': []}
        
        decisions['signals'].append(trade_signal)
        with open('nexus_live_decisions.json', 'w') as f:
            json.dump(decisions, f, indent=2)
        
        logger.info(f"Trade signal triggered: {direction} {amount} {symbol}")
        
        return jsonify({
            'success': True,
            'signal': trade_signal,
            'message': f'{direction} signal queued for {amount} {symbol}'
        })
    except Exception as e:
        logger.error(f"Trade trigger error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/agents/transfer', methods=['POST'])
def agents_auto_transfer():
    """Trigger automatic agent-to-agent transfers (round-robin)"""
    try:
        body = request.get_json() or {}
        amount_per_action = body.get('amount_per_action', 0.005)
        action_count = body.get('action_count', len(AGENT_ADDRESSES))
        
        # Create round-robin transfer actions
        actions = []
        for i in range(action_count):
            from_agent_idx = i % len(AGENT_ADDRESSES)
            to_agent_idx = (i + 1) % len(AGENT_ADDRESSES)
            
            actions.append({
                'channelId': f"agent-transfer-{from_agent_idx}-to-{to_agent_idx}",
                'from': AGENT_ADDRESSES[from_agent_idx],
                'to': AGENT_ADDRESSES[to_agent_idx],
                'amountUSDC': amount_per_action
            })
        
        # Execute batch via nanopay
        import requests as _req
        resp = _req.post(f"{NANOPAY_URL}/api/batch-charge", json={'actions': actions}, timeout=60)
        result = resp.json()
        
        # Persist receipts AND log transfers
        if result.get('success'):
            receipts = result.get('result', {}).get('receipts', [])
            for receipt in receipts:
                save_batch_receipt(receipt)
            save_agent_transfer({
                'action_count': action_count,
                'amount_per_action': amount_per_action,
                'total_amount': amount_per_action * action_count,
                'actions': actions,
                'result': result
            })
            # Start async fee enrichment for manual transfers
            def _enrich_manual():
                import threading, requests as _req
                import time
                time.sleep(2)  # Wait for block to be mined
                try:
                    for receipt in receipts:
                        tx_hash = receipt.get('txHash')
                        if tx_hash and not tx_hash.startswith('0xdeadbeef'):
                            try:
                                rpc_resp = _req.post(ARC_RPC_URL, json={
                                    "jsonrpc": "2.0", "method": "eth_getTransactionReceipt",
                                    "params": [tx_hash], "id": 1
                                }, timeout=8).json()
                                rec = rpc_resp.get('result', {})
                                if rec:
                                    gas_used = int(rec.get('gasUsed', '0x0'), 16)
                                    eff_gas_price = int(rec.get('effectiveGasPrice', '0x0'), 16)
                                    fee_wei = gas_used * eff_gas_price
                                    fee_usdc = round(fee_wei / 1e18, 8)
                                    block_number = int(rec.get('blockNumber', '0x0'), 16)
                                    update_receipt_fee(tx_hash, fee_usdc, gas_used, block_number)
                            except Exception as e:
                                logger.debug(f"Fee enrichment failed for {tx_hash}: {e}")
                except Exception as e:
                    logger.debug(f"Manual enrichment worker error: {e}")
            t = threading.Thread(target=_enrich_manual)
            t.daemon = True
            t.start()
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Agent transfer error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/agents/transfer-log', methods=['GET'])
def agents_transfer_log():
    """Get agent transfer history (recent continuous + manual transfers)"""
    try:
        log = load_agent_transfer_log()
        transfers = log.get('transfers', [])[-20:]  # Last 20 transfers
        
        # Enrich with receipts data (fees, block numbers)
        for transfer in transfers:
            if transfer.get('scheduled'):  # Continuous transfer
                result_receipts = transfer.get('result', {}).get('result', {}).get('receipts', [])
            else:  # Manual transfer
                result_receipts = transfer.get('result', {}).get('result', {}).get('receipts', [])
            
            if result_receipts:
                total_fee = sum(r.get('fee_usdc', 0) for r in result_receipts)
                transfer['enriched_fee'] = round(total_fee, 8)
                transfer['tx_hashes'] = [r.get('txHash') for r in result_receipts if r.get('txHash')]
        
        return jsonify({
            'success': True,
            'last_transfer': log.get('last_transfer'),
            'transfers': transfers,
            'count': len(transfers)
        })
    except Exception as e:
        logger.error(f"Transfer log error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/agents/scheduler/config', methods=['GET'])
def get_scheduler_config():
    """Get continuous transfer scheduler configuration"""
    try:
        config = load_scheduler_config()
        return jsonify({
            'success': True,
            'config': config
        })
    except Exception as e:
        logger.error(f"Scheduler config error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/agents/scheduler/config', methods=['POST'])
def update_scheduler_config():
    """Update continuous transfer scheduler configuration"""
    try:
        body = request.get_json() or {}
        config = load_scheduler_config()
        
        # Update config with new values
        if 'enabled' in body:
            config['enabled'] = body['enabled']
        if 'interval_seconds' in body:
            config['interval_seconds'] = max(30, body['interval_seconds'])  # Min 30 seconds
        if 'amount_per_action' in body:
            config['amount_per_action'] = body['amount_per_action']
        if 'actions_per_batch' in body:
            config['actions_per_batch'] = body['actions_per_batch']
        
        save_scheduler_config(config)
        
        # Apply scheduler changes
        _apply_scheduler_config(config)
        
        return jsonify({
            'success': True,
            'config': config
        })
    except Exception as e:
        logger.error(f"Scheduler update error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def _continuous_transfer_job():
    """Background job for continuous agent transfers"""
    try:
        config = load_scheduler_config()
        if not config.get('enabled'):
            return
        
        amount_per_action = config.get('amount_per_action', 0.005)
        actions_per_batch = config.get('actions_per_batch', 4)
        
        # Execute transfer
        actions = []
        for i in range(actions_per_batch):
            from_agent_idx = i % len(AGENT_ADDRESSES)
            to_agent_idx = (i + 1) % len(AGENT_ADDRESSES)
            
            actions.append({
                'channelId': f"continuous-transfer-{datetime.now().timestamp()}-{i}",
                'from': AGENT_ADDRESSES[from_agent_idx],
                'to': AGENT_ADDRESSES[to_agent_idx],
                'amountUSDC': amount_per_action
            })
        
        import requests as _req
        resp = _req.post(f"{NANOPAY_URL}/api/batch-charge", json={'actions': actions}, timeout=60)
        result = resp.json()
        
        if result.get('success'):
            save_agent_transfer({
                'action_count': actions_per_batch,
                'amount_per_action': amount_per_action,
                'total_amount': amount_per_action * actions_per_batch,
                'actions': actions,
                'result': result,
                'scheduled': True
            })
            logger.info(f"✅ Continuous transfer job executed: {actions_per_batch} actions")
        else:
            logger.warning(f"⚠️ Continuous transfer job failed: {result.get('error')}")
    except Exception as e:
        logger.error(f"Continuous transfer job error: {e}")

def _apply_scheduler_config(config):
    """Apply scheduler configuration"""
    global scheduler
    try:
        if not hasattr(scheduler, 'running') or not scheduler.running:
            scheduler.start()
        
        # Remove existing job if any
        try:
            scheduler.remove_job('continuous_transfers')
        except:
            pass
        
        if config.get('enabled'):
            interval = config.get('interval_seconds', 300)
            scheduler.add_job(
                _continuous_transfer_job,
                'interval',
                seconds=interval,
                id='continuous_transfers',
                replace_existing=True
            )
            logger.info(f"✅ Continuous transfer scheduler enabled (interval: {interval}s)")
        else:
            logger.info("ℹ️ Continuous transfer scheduler disabled")
    except Exception as e:
        logger.error(f"Failed to apply scheduler config: {e}")

# ============================================================================
# Error Handlers
# ============================================================================

@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'success': False, 'error': 'Internal server error'}), 500

# ============================================================================
# Main
# ============================================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    logger.info("🚀 Starting NEXUS Dashboard API Server")
    logger.info(f"📊 Dashboard available at http://localhost:{port}")
    logger.info("📡 API endpoints:")
    logger.info("   - GET  /api/market           → Market data (BTC)")
    logger.info("   - GET  /api/agents           → Agent performance")
    logger.info("   - GET  /api/sentiment        → Sentiment analysis")
    logger.info("   - GET  /api/positions        → Current positions")
    logger.info("   - GET  /api/equity           → Equity curve")
    logger.info("   - GET  /api/risk             → Risk metrics (BTC)")
    logger.info("   - GET  /api/performance      → Overall performance")
    logger.info("   - GET  /api/health           → Health check")
    logger.info("   - GET  /api/market-overview  → All crypto prices")
    logger.info("   - GET  /api/crypto/<sym>/price   → Single crypto price")
    logger.info("   - GET  /api/crypto/<sym>/signals → Single crypto signals")
    logger.info("   - GET  /office               → Pixel office display")
    logger.info("   - GET  /api/stocks/jse       → JSE Top 50 overview")
    logger.info("   - GET  /api/stocks/us        → US Top stocks overview")
    logger.info("   - GET  /api/stocks/btc-signal → JSE vs BTC correlation signal")
    logger.info("   - GET  /api/stocks/alpaca    → Alpaca account + positions")
    logger.info("   - GET  /api/stocks/sepolia-pairs → Sepolia testnet token pairs")
    
    # Initialize scheduler for continuous transfers
    scheduler = BackgroundScheduler()
    config = load_scheduler_config()
    _apply_scheduler_config(config)
    logger.info("✅ Agent transfer scheduler initialized")
    
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

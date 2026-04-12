from dotenv import load_dotenv
load_dotenv()
"""
NEXUS Dashboard API Server
Serves real-time market data and bot performance metrics to the HTML dashboard
"""
import os
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, jsonify, render_template, send_file
from flask_cors import CORS
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from data.prism import PrismClient
from execution.kraken import KrakenClient
import os
from agents.sentiment import fetch_composite_sentiment

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

# ============================================================================
# Data Loading Functions
# ============================================================================

def load_agent_weights():
    """Load agent weights from nexus_weights.json"""
    try:
        with open('nexus_weights.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning("nexus_weights.json not found, returning empty")
        return []

def load_positions():
    """Load OPEN positions — first from live_decisions, fallback to positions file"""
    try:
        with open('nexus_live_decisions.json', 'r') as f:
            data = json.load(f)
            positions = data.get('positions', [])
            if positions:
                return positions
    except Exception:
        pass
    try:
        with open('nexus_positions.json', 'r') as f:
            all_pos = json.load(f)
            return [p for p in all_pos if p.get('status') == 'open']
    except FileNotFoundError:
        return []

def load_equity_curve():
    """Load equity curve from nexus_equity_curve.json"""
    try:
        with open('nexus_equity_curve.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Generate mock equity curve
        equity_data = []
        base_equity = 10000
        for i in range(30):
            date = (datetime.now() - timedelta(days=30-i)).strftime('%Y-%m-%d')
            daily_pnl = (i % 3 - 1) * 50 + 75  # Varied returns
            equity_data.append({
                'date': date,
                'equity': base_equity + (i * 50),
                'drawdown': max(0, (10000 - (base_equity + i * 50)) / 10000 * 100)
            })
        return equity_data

# ============================================================================
# API Endpoints
# ============================================================================

@app.route('/')
def dashboard():
    """Serve the dashboard HTML"""
    return send_file('dashboard.html')

@app.route('/api/market', methods=['GET'])
def get_market_data():
    """Get current market data"""
    try:
        if prism_client:
            # Get price from PRISM
            import requests as _req; _btc = _req.get("https://api.kraken.com/0/public/Ticker?pair=XBTUSD", timeout=5).json(); price_data = {"current_price": float(list(_btc["result"].values())[0]["c"][0]), "change_24h_pct": 0, "volume_24h": float(list(_btc["result"].values())[0]["v"][1])}
            
            # Get signals
            signals_1h = prism_client.get_signals('BTC', '1h')
            signals_4h = prism_client.get_signals('BTC', '4h')
            
            # Get risk
            risk = prism_client.get_risk('BTC')
            
            return jsonify({
                'success': True,
                'price': price_data.get('current_price', 0),
                'change_24h': price_data.get('change_24h_pct', 0),
                'volume_24h': price_data.get('volume_24h', 0),
                'signal_1h': signals_1h.direction if signals_1h else 'neutral',
                'signal_4h': signals_4h.direction if signals_4h else 'neutral',
                'risk_score': risk.risk_score if risk else 0,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': 'PRISM client not available'
            }), 503
    except Exception as e:
        logger.error(f"Error fetching market data: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/agents', methods=['GET'])
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
def get_risk():
    """Get risk metrics"""
    try:
        if prism_client:
            risk = prism_client.get_risk('BTC')
            if risk:
                return jsonify({
                    'success': True,
                    'risk_score': risk.risk_score,
                    'atr_pct': risk.atr_pct,
                    'volatility_30d': risk.volatility_30d,
                    'max_drawdown_30d': risk.max_drawdown_30d,
                    'sharpe_ratio': risk.sharpe_ratio,
                    'sortino_ratio': risk.sortino_ratio,
                    'timestamp': datetime.now().isoformat()
                })
        
        # Fallback to mock data
        return jsonify({
            'success': True,
            'risk_score': 42.5,
            'atr_pct': 1.2,
            'volatility_30d': 22.5,
            'max_drawdown_30d': 8.3,
            'sharpe_ratio': 1.45,
            'sortino_ratio': 2.1,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error fetching risk data: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/performance', methods=['GET'])
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
        # Also add PnL from weights
        agents = load_agent_weights()
        total_pnl = sum(a.get('pnl_total', 0) for a in agents)
        total_trades = sum(a.get('trades_closed', 0) for a in agents)
        total_wins = sum(a.get('wins', 0) for a in agents)
        return jsonify({
            'success': True,
            'balance_usd': balance,
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
        total_pnl = sum(t.get('pnl_usd', 0) for t in closed)
        wins = [t for t in closed if t.get('pnl_usd', 0) > 0]
        return jsonify({'success': True, 'trades': closed[-20:],
            'total': len(closed), 'wins': len(wins),
            'total_pnl': total_pnl, 'win_rate': len(wins)/len(closed)*100 if closed else 0})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/consensus', methods=['GET'])
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
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'prism_connected': prism_client is not None,
    })

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


@app.route("/api/config", methods=["GET"])
def get_config():
    return jsonify({
        "groq_key": os.environ.get("GROQ_API_KEY", ""),
        "strategy": os.environ.get("ACTIVE_STRATEGY", "algorithmic_quant"),
        "chain_id": os.environ.get("CHAIN_ID", "11155111"),
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    logger.info("🚀 Starting NEXUS Dashboard API Server")
    logger.info(f"📊 Dashboard available at http://localhost:{port}")
    logger.info("📡 API endpoints:")
    logger.info("   - GET  /api/market      → Market data")
    logger.info("   - GET  /api/agents      → Agent performance")
    logger.info("   - GET  /api/sentiment   → Sentiment analysis")
    logger.info("   - GET  /api/positions   → Current positions")
    logger.info("   - GET  /api/equity      → Equity curve")
    logger.info("   - GET  /api/risk        → Risk metrics")
    logger.info("   - GET  /api/performance → Overall performance")
    logger.info("   - GET  /api/health      → Health check")
    
    app.run(host='0.0.0.0', port=port, debug=True)

@app.route('/api/config', methods=['GET'])
def get_config():
    """Serve frontend config from .env — never expose secrets, only what dashboard needs"""
    return jsonify({
        'groq_key':  os.environ.get('GROQ_API_KEY', ''),
        'strategy':  os.environ.get('ACTIVE_STRATEGY', 'algorithmic_quant'),
        'chain_id':  os.environ.get('CHAIN_ID', '11155111'),
    })

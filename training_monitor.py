#!/usr/bin/env python3
"""
NEXUS Training Monitor - Real-time training progress dashboard
"""
import json
import os
import time
import sys
from datetime import datetime
from typing import Dict, List

class TrainingMonitor:
    def __init__(self):
        self.weights_file = "nexus_weights.json"
        self.equity_file = "nexus_equity_curve.json"
        self.positions_file = "nexus_positions.json"
        self.start_time = time.time()
    
    def load_weights(self) -> List[Dict]:
        """Load current agent weights."""
        try:
            with open(self.weights_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return []
    
    def load_equity_curve(self) -> List[Dict]:
        """Load equity curve data."""
        try:
            with open(self.equity_file, 'r') as f:
                lines = f.readlines()
                return [json.loads(line) for line in lines[-100:] if line.strip()]
        except FileNotFoundError:
            return []
    
    def load_positions(self) -> List[Dict]:
        """Load position history."""
        try:
            with open(self.positions_file, 'r') as f:
                lines = f.readlines()
                return [json.loads(line) for line in lines[-50:] if line.strip()]
        except FileNotFoundError:
            return []
    
    def get_stats(self):
        """Calculate training statistics."""
        weights = self.load_weights()
        equity_curve = self.load_equity_curve()
        positions = self.load_positions()
        
        # Calculate total metrics
        total_pnl = sum(w['pnl_total'] for w in weights)
        total_trades = sum(w['trades_closed'] for w in weights)
        total_wins = sum(w['wins'] for w in weights)
        
        # Calculate equity stats
        initial_equity = 10000
        current_equity = initial_equity + total_pnl
        equity_change = current_equity - initial_equity
        roi_pct = (equity_change / initial_equity * 100) if initial_equity > 0 else 0
        
        # Calculate closed positions
        closed_positions = [p for p in positions if p.get('status') == 'closed']
        closed_pnl = sum(p.get('pnl_usd', 0) for p in closed_positions)
        closed_wins = sum(1 for p in closed_positions if p.get('pnl_usd', 0) > 0)
        
        return {
            'weights': weights,
            'equity_curve': equity_curve,
            'positions': positions,
            'total_pnl': total_pnl,
            'total_trades': total_trades,
            'total_wins': total_wins,
            'current_equity': current_equity,
            'roi_pct': roi_pct,
            'closed_positions': closed_positions,
            'closed_pnl': closed_pnl,
            'closed_wins': closed_wins,
        }
    
    def print_dashboard(self):
        """Print real-time training dashboard."""
        stats = self.get_stats()
        
        print("\n" + "=" * 80)
        print(" " * 20 + "🤖 NEXUS TRAINING MONITOR 🤖")
        print("=" * 80)
        
        # Session info
        elapsed = time.time() - self.start_time
        print(f"\n📊 SESSION INFO")
        print(f"  Time Elapsed:    {int(elapsed):,}s ({int(elapsed/60):,} min)")
        print(f"  Timestamp:       {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Equity performance
        print(f"\n💰 EQUITY PERFORMANCE")
        print(f"  Initial Capital: $10,000.00")
        print(f"  Current Equity:  ${stats['current_equity']:,.2f}")
        print(f"  Total PnL:       ${stats['total_pnl']:,.2f}")
        print(f"  ROI:             {stats['roi_pct']:+.2f}%")
        
        # Trading stats
        print(f"\n📈 TRADING STATS")
        print(f"  Total Trades:    {stats['total_trades']}")
        print(f"  Closed Positions: {len(stats['closed_positions'])}")
        print(f"  Wins:            {stats['closed_wins']}")
        print(f"  Closed PnL:      ${stats['closed_pnl']:,.2f}")
        
        if stats['closed_positions']:
            win_rate = (stats['closed_wins'] / len(stats['closed_positions']) * 100)
            print(f"  Win Rate:        {win_rate:.1f}%")
        
        # Agent performance
        print(f"\n🤖 AGENT PERFORMANCE")
        print(f"  {'Agent':<20} {'Weight':<10} {'Status':<10} {'Trades':<8} {'PnL':<12}")
        print(f"  {'-'*60}")
        
        for agent in stats['weights']:
            agent_id = agent['agent_id']
            weight = agent['weight']
            status = "RETIRED" if agent['retired'] else "ACTIVE"
            trades = agent['trades_closed']
            pnl = agent['pnl_total']
            
            print(f"  {agent_id:<20} {weight:<10.2f} {status:<10} {trades:<8} ${pnl:>10,.2f}")
        
        # Recent positions
        if stats['closed_positions']:
            print(f"\n📍 RECENT POSITIONS (last 10)")
            print(f"  {'Dir':<5} {'Entry':<12} {'Exit':<12} {'Volume':<10} {'PnL':<12} {'Reason':<15}")
            print(f"  {'-'*70}")
            
            for pos in stats['closed_positions'][-10:]:
                direction = pos.get('direction', '?')[:3]
                entry_price = pos.get('entry_price', 0)
                exit_price = pos.get('exit_price', 0)
                volume = pos.get('volume', 0)
                pnl = pos.get('pnl_usd', 0)
                reason = pos.get('exit_reason', 'N/A')[:12]
                
                print(f"  {direction:<5} ${entry_price:<11,.0f} ${exit_price:<11,.0f} {volume:<10.4f} ${pnl:>10,.2f} {reason:<15}")
        
        print("\n" + "=" * 80)
        print(f"Last Updated: {datetime.now().strftime('%H:%M:%S')}")
        print("=" * 80 + "\n")
    
    def watch(self, interval: int = 10, max_cycles: int = None):
        """Watch training progress in real-time."""
        cycle = 0
        try:
            while True:
                if max_cycles and cycle >= max_cycles:
                    print("\n✅ Monitoring complete!")
                    break
                
                self.print_dashboard()
                cycle += 1
                
                if max_cycles is None:
                    print(f"Press Ctrl+C to stop. Refreshing in {interval}s...")
                    time.sleep(interval)
                else:
                    if cycle < max_cycles:
                        time.sleep(interval)
        
        except KeyboardInterrupt:
            print("\n\n🛑 Monitoring stopped by user.")
            sys.exit(0)

if __name__ == "__main__":
    monitor = TrainingMonitor()
    print("\n🚀 Starting NEXUS Training Monitor...")
    print("   This will show real-time progress of the training loop.")
    print("   Make sure --dry-run is running in another terminal!\n")
    
    # Check if training is active
    if not os.path.exists("nexus_weights.json"):
        print("⚠️  No training data found!")
        print("   Run: python3 main.py --dry-run -v")
        print("   in another terminal to start training.\n")
        sys.exit(1)
    
    # Watch for 30 cycles (5-10 minutes depending on interval)
    monitor.watch(interval=10, max_cycles=30)

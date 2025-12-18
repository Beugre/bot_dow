"""
Backtest rapide sur 1 mois pour debugging
"""

import sys
sys.path.insert(0, '.')

from backtest_dow import BacktestEngine
from config_dow import PAIRS
from datetime import datetime, timedelta

# Backtest sur 1 mois seulement avec 2 paires pour debug rapide
end_date = datetime.now()
start_date = end_date - timedelta(days=60)  # 2 mois

backtest = BacktestEngine(
    initial_capital=10000,
    start_date=start_date.strftime("%Y-%m-%d"),
    end_date=end_date.strftime("%Y-%m-%d"),
    pairs=["BTC/USDC", "ETH/USDC"],  # Seulement 2 paires
    risk_percent=2.0,
    trigger_zero_r=1.0,
    lock_profit_r=0.2
)

results = backtest.run_backtest()

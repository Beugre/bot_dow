"""
Configuration pour le bot Dow Theory / Market Structure — Optimisé H1
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# API BINANCE
# ============================================================================
BINANCE_API_KEY = os.getenv('BINANCE_API_KEY')
BINANCE_API_SECRET = os.getenv('BINANCE_API_SECRET')

# ============================================================================
# FIREBASE (logs & dashboard)
# ============================================================================
FIREBASE_CREDENTIALS = os.getenv('FIREBASE_CREDENTIALS', 'firebase-credentials.json')

# ============================================================================
# TELEGRAM
# ============================================================================
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# ============================================================================
# UNIVERS DE TRADING
# ============================================================================
PAIRS = [
    "BTC/USDC",
    "ETH/USDC",
    "BNB/USDC",
    "SOL/USDC",
    "AVAX/USDC"
]

# ============================================================================
# TIMEFRAMES
# ============================================================================
TIMEFRAME_EXECUTION = "1h"     # Timeframe principal
TIMEFRAME_MACRO = "1h"         # Macro bias en H1 également

# Nombre de bougies
CANDLES_H1 = 1000   # Backtest ~42 jours par fetch
CANDLES_H4 = 6000   # Laisser pour compatibilité si besoin d'H4

# ============================================================================
# 🎯 DÉTECTION DES SWINGS — VERSION OPTIMISÉE POUR H1
# ============================================================================

# Nombre de bougies de chaque côté pour valider pivot (6 → optimum H1)
SWING_LOOKBACK = 6

# Taille minimale du swing (%). H1 = swings naturels ~0.3% à 1%.
MIN_SWING_SIZE_PCT = 0.35     # (au lieu de 1.2%)

# Distance minimale entre swings du même type (évite micro-bruits)
MIN_SWING_DISTANCE_PCT = 0.35 # (au lieu de 1.2%)

# Confirmation du pivot
SWING_CONFIRMATION_CANDLES = 1  # (au lieu de 2)

# ============================================================================
# 🔥 FILTRE ANTI-RANGE (H1)
# ============================================================================
# Range minimal sur 20 bougies H1. 1% était trop strict → ici optimum.
RANGE_MIN_PCT = 0.45

# ============================================================================
# MONEY MANAGEMENT
# ============================================================================
RISK_PERCENT = 2.0             # % du capital risqué par trade
MAX_OPEN_TRADES = 3            # Max trades en même temps
MAX_TRADES_PER_PAIR = 1        # 1 trade par paire
MAX_TRADES_PER_STRUCTURE = 1    # Empêche les doublons sur la même structure

# Stops adaptés H1
MIN_STOP_PCT = 0.25            # Min = 0.25% (avant 1.0%)
MAX_STOP_PCT = 5.0             # Max = 5% (avant 10%)

# ============================================================================
# ZERO RISK & TRAILING
# ============================================================================
TRIGGER_ZERO_R = 1.0   # Active Zero Risk à +1R
LOCK_PROFIT_R = 0.0    # Lock sur entry_price (zero risk pur)

TRAILING_ENABLED = True
TRAILING_STEPS = [
    (1.5, 0.5),    # +1.5R → SL à +0.5R
    (2.5, 1.0),    # +2.5R → SL à +1R
    (3.5, 2.0),    # +3.5R → SL à +2R
    (4.0, 2.5),    # +4R   → SL à +2.5R
]

# ============================================================================
# GESTION GLOBALE DU RISQUE
# ============================================================================
MAX_TOTAL_RISK_PCT = 6.0  # Max 6% du capital à risque total

# ============================================================================
# FRAIS & SLIPPAGE (Backtest)
# ============================================================================
TAKER_FEE = 0.0004
MAKER_FEE = 0.0002
SLIPPAGE_PCT = 0.05  # 0.05% de slippage par défaut

# ============================================================================
# PARAMÈTRES D’EXÉCUTION
# ============================================================================
CHECK_INTERVAL = 3600
DRY_RUN = False

# ============================================================================
# LOGS
# ============================================================================
LOG_LEVEL = "INFO"
LOG_FILE = "logs/dow_bot.log"

# ============================================================================
# BACKTEST
# ============================================================================
BACKTEST_START_DATE = "2023-01-01"
BACKTEST_END_DATE = "2025-12-13"
BACKTEST_INITIAL_CAPITAL = 10000  # USDC

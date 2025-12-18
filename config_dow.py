"""
Configuration pour le bot Dow Theory / Market Structure — Optimisé H4
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
TIMEFRAME_EXECUTION = "4h"     # Timeframe principal
TIMEFRAME_MACRO = "4h"         # Macro bias en H4 également

# Nombre de bougies
CANDLES_H1 = 1000   # Pour compatibilité (non utilisé en H4)
CANDLES_H4 = 6000   # Backtest ~1000 jours (2.7 ans)

# ============================================================================
# 🎯 DÉTECTION DES SWINGS — VERSION OPTIMISÉE POUR H4
# ============================================================================

# Nombre de bougies de chaque côté pour valider pivot (2 → optimum H4)
SWING_LOOKBACK = 2

# Taille minimale du swing (%). H4 = swings plus larges ~1% à 3%.
MIN_SWING_SIZE_PCT = 1.0

# Distance minimale entre swings du même type (évite micro-bruits)
MIN_SWING_DISTANCE_PCT = 1.0

# Confirmation du pivot (plus large en H4)
SWING_CONFIRMATION_CANDLES = 2

# ============================================================================
# 🔥 FILTRE ANTI-RANGE (H4)
# ============================================================================
# Range minimal sur 20 bougies H4. H4 = ranges plus larges.
RANGE_MIN_PCT = 1.5

# ============================================================================
# MONEY MANAGEMENT
# ============================================================================
RISK_PERCENT = 2.0             # % du capital risqué par trade
MAX_OPEN_TRADES = 3            # Max trades en même temps
MAX_TRADES_PER_PAIR = 1        # 1 trade par paire
MAX_TRADES_PER_STRUCTURE = 1    # Empêche les doublons sur la même structure

# Stops adaptés H4 (plus larges)
MIN_STOP_PCT = 1.0             # Min = 1% pour H4
MAX_STOP_PCT = 10.0            # Max = 10% pour H4

# ============================================================================
# ZERO RISK & TRAILING (H4 - plus doux)
# ============================================================================
TRIGGER_ZERO_R = 1.5   # Active Zero Risk à +1.5R (plus patient en H4)
LOCK_PROFIT_R = 0.5    # Lock à +0.5R (laisse respirer)

TRAILING_ENABLED = True
TRAILING_STEPS = [
    (2.0, 0.5),    # +2R   → SL à +0.5R
    (3.0, 1.5),    # +3R   → SL à +1.5R
    (4.0, 2.5),    # +4R   → SL à +2.5R
    (5.0, 3.5),    # +5R   → SL à +3.5R
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

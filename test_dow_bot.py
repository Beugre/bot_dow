"""
Test rapide du bot Dow Theory
Vérifie que tous les modules s'importent correctement
"""
import sys
from datetime import datetime

print("=" * 70)
print("🧪 TEST DU BOT DOW THEORY")
print("=" * 70)
print()

# Test imports
print("📦 Test des imports...")
try:
    import config_dow as config
    print("✅ config_dow")
except Exception as e:
    print(f"❌ config_dow: {e}")
    sys.exit(1)

try:
    from swing_detector import SwingDetector
    print("✅ swing_detector")
except Exception as e:
    print(f"❌ swing_detector: {e}")
    sys.exit(1)

try:
    from market_structure import MarketStructure
    print("✅ market_structure")
except Exception as e:
    print(f"❌ market_structure: {e}")
    sys.exit(1)

try:
    from risk_manager_dow import RiskManager
    print("✅ risk_manager_dow")
except Exception as e:
    print(f"❌ risk_manager_dow: {e}")
    sys.exit(1)

try:
    from data_fetcher_dow import DataFetcher
    print("✅ data_fetcher_dow")
except Exception as e:
    print(f"❌ data_fetcher_dow: {e}")
    sys.exit(1)

print()
print("=" * 70)
print("✅ TOUS LES MODULES ONT ÉTÉ IMPORTÉS AVEC SUCCÈS")
print("=" * 70)
print()

# Test configuration
print("📊 Configuration:")
print(f"   Paires: {', '.join(config.PAIRS)}")
print(f"   Risk%: {config.RISK_PERCENT}%")
print(f"   Max trades: {config.MAX_OPEN_TRADES}")
print(f"   Zero risk: {config.TRIGGER_ZERO_R}R → {config.LOCK_PROFIT_R}R")
print(f"   DRY RUN: {config.DRY_RUN}")
print()

# Test SwingDetector
print("🔍 Test SwingDetector...")
import pandas as pd
import numpy as np

# Créer des données de test
dates = pd.date_range(start='2024-01-01', periods=100, freq='H')
np.random.seed(42)
prices = 100 + np.cumsum(np.random.randn(100) * 0.5)

df_test = pd.DataFrame({
    'timestamp': dates,
    'open': prices,
    'high': prices + np.random.rand(100) * 0.5,
    'low': prices - np.random.rand(100) * 0.5,
    'close': prices + np.random.randn(100) * 0.2,
    'volume': np.random.randint(1000, 10000, 100)
})

detector = SwingDetector(lookback=1)
swings = detector.detect_swings(df_test)
swings = detector.classify_swings(swings)
trend = detector.get_trend(swings)
summary = detector.get_structure_summary(swings)

print(f"   Swings détectés: {len(swings)}")
print(f"   Highs: {summary['highs']}, Lows: {summary['lows']}")
print(f"   Tendance: {trend}")
print(f"   Dernier HH: {summary['last_HH']}")
print(f"   Dernier HL: {summary['last_HL']}")
print()

# Test RiskManager
print("💰 Test RiskManager...")
risk_mgr = RiskManager(initial_capital=10000)

# Simuler un calcul de position
entry_price = 100.0
stop_loss = 95.0
side = "LONG"

quantity = risk_mgr.calculate_position_size(entry_price, stop_loss, side)
risk_amount = 10000 * (config.RISK_PERCENT / 100)
stop_distance = entry_price - stop_loss

print(f"   Capital: {risk_mgr.current_capital} USDC")
print(f"   Entry: {entry_price}, SL: {stop_loss}")
print(f"   Stop distance: {stop_distance}")
print(f"   Risk amount: {risk_amount} USDC")
print(f"   Quantité calculée: {quantity:.4f}")
print()

# Test DataFetcher (nécessite API Binance)
print("🔌 Test DataFetcher (optionnel - nécessite API)...")
try:
    fetcher = DataFetcher()
    print("   ✅ Connexion Binance OK")
    
    # Test récupération données
    if config.BINANCE_API_KEY and config.BINANCE_API_KEY != 'your_api_key_here':
        print("   Test fetch BTC/USDC...")
        data = fetcher.fetch_multiple_timeframes("BTC/USDC")
        if "H1" in data and "H4" in data:
            print(f"   ✅ H1: {len(data['H1'])} bougies")
            print(f"   ✅ H4: {len(data['H4'])} bougies")
        else:
            print("   ⚠️ Données incomplètes")
    else:
        print("   ⚠️ API non configurée (normal en test)")
except Exception as e:
    print(f"   ⚠️ Erreur DataFetcher: {e}")

print()
print("=" * 70)
print("✅ TESTS TERMINÉS")
print("=" * 70)
print()
print("📝 Prochaines étapes:")
print("   1. Configurer .env avec vos clés API Binance")
print("   2. Ajuster config_dow.py selon vos préférences")
print("   3. Lancer en DRY_RUN d'abord: python dow_bot.py")
print("   4. Surveiller les logs dans logs/dow_bot.log")
print()

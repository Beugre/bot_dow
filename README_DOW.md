# Bot Dow Theory - Refonte complète

## 🎯 Stratégie

Stratégie de **Trend Following** basée sur **Dow Theory** et **Market Structure**.

### Principes
- Détection des swings (pivots hauts/bas)
- Classification HH/HL/LH/LL (Higher High, Higher Low, Lower High, Lower Low)
- Entrée sur cassure de structure
- Stop Loss structurel
- Risk % fixe par trade
- Zero risk à +1R
- Trailing stop optionnel

### Timeframes
- **H1** : Exécution et signaux
- **H4** : Filtre macro (EMA200)

### Univers
7 paires principales (pas de DOGE) :
- BTC/USDC
- ETH/USDC
- BNB/USDC
- SOL/USDC
- AVAX/USDC
- XRP/USDC
- MATIC/USDC

## 📁 Structure des fichiers

```
satochi/
├── config_dow.py              # Configuration complète
├── dow_bot.py                 # Bot principal
├── swing_detector.py          # Détection des swings + classification HH/HL/LH/LL
├── market_structure.py        # Analyse de structure + signaux
├── risk_manager_dow.py        # Money management + positions
├── data_fetcher_dow.py        # Récupération données Binance
├── telegram_notifier.py       # Notifications (à garder de l'ancien bot)
├── requirements_dow.txt       # Dépendances
└── .env.example              # Template configuration
```

## 🚀 Installation

```bash
# Installer les dépendances
pip install -r requirements_dow.txt

# Copier et configurer .env
cp .env.example .env
nano .env
```

## ⚙️ Configuration

Éditer `config_dow.py` pour ajuster :

- `RISK_PERCENT` : 1-3% (défaut: 2%)
- `MAX_OPEN_TRADES` : 5-10 (défaut: 5)
- `TRIGGER_ZERO_R` : 0.8-1.2R (défaut: 1.0R)
- `LOCK_PROFIT_R` : 0.1-0.3R (défaut: 0.2R)
- `MIN_STOP_PCT` / `MAX_STOP_PCT` : Limites du stop loss
- `DRY_RUN` : True pour mode simulation

## 🎮 Utilisation

```bash
# Lancer le bot
python dow_bot.py
```

Le bot va :
1. Scanner les 7 paires toutes les heures
2. Détecter les swings et classifier la structure
3. Chercher des cassures de HH (achat) ou LL (vente)
4. Vérifier le filtre EMA200 H4
5. Calculer la taille de position (risk%)
6. Exécuter les trades
7. Gérer les positions (zero risk, trailing, exits)

## 📊 Signaux

### Signal BUY (LONG)
- ✅ Structure haussière (HH + HL récents)
- ✅ Prix > EMA200 H4 (biais bullish)
- ✅ Cassure du dernier HH
- ✅ Stop Loss sur le dernier HL
- ✅ Stop distance entre MIN_STOP_PCT et MAX_STOP_PCT

### Signal SELL (SHORT)
- ✅ Structure baissière (LH + LL récents)
- ✅ Prix < EMA200 H4 (biais bearish)
- ✅ Cassure du dernier LL
- ✅ Stop Loss sur le dernier LH
- ✅ Stop distance entre MIN_STOP_PCT et MAX_STOP_PCT

## 🛡️ Gestion du risque

- **Risk par trade** : 2% du capital
- **Max trades simultanés** : 5
- **Max trades par paire** : 2
- **Max risk total** : 10%

### Zero Risk
- Activé à **+1R** de profit
- Lock profit à **+0.2R** minimum
- Plus de risque de perte après activation

### Trailing Stop (optionnel)
- À +2R → lock à +1R
- À +3R → lock à +2R

## 📈 Invalidation de tendance

- **Uptrend invalidé** : Prix casse le dernier HL à la baisse
- **Downtrend invalidé** : Prix casse le dernier LH à la hausse

Quand invalidé :
- ❌ Pas de nouveaux trades dans cette direction
- ✅ Attendre nouvelle structure HH/HL ou LH/LL

## 📝 Logs

Les logs sont dans `logs/dow_bot.log` :

```bash
tail -f logs/dow_bot.log
```

## 🔔 Notifications Telegram

Configurer dans `.env` :
```
TELEGRAM_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id
```

Notifications pour :
- Nouvelles positions
- Fermetures de positions
- Zero risk activé

## 🧪 Backtesting

(À implémenter - module séparé)

Le backtest devra :
- Tester sur historique 2-3 ans
- Varier les paramètres (RISK_PERCENT, TRIGGER_ZERO_R, etc.)
- Calculer CAGR, Drawdown max, Win rate, Profit factor
- Générer equity curve

## ⚠️ Important

- **Toujours commencer en DRY_RUN = True**
- Vérifier les logs avant de passer en live
- Surveiller le risk exposé
- Ne pas dépasser MAX_TOTAL_RISK_PCT

## 🆚 Différences avec l'ancien bot

| Ancien bot (RSI) | Nouveau bot (Dow Theory) |
|------------------|--------------------------|
| Indicateur RSI | Structure de marché |
| Timeframe fixe | Multi-timeframe (H1 + H4) |
| OCO Binance | Stop loss structurel |
| Pas de re-entry | Re-entry autorisé |
| Protection statique | Zero risk dynamique + trailing |
| 1 trade/paire | Jusqu'à 2 trades/paire |

## 📚 Ressources

- **Dow Theory** : https://www.investopedia.com/terms/d/dowtheory.asp
- **Market Structure** : https://www.babypips.com/learn/forex/market-structure

---

**Bot créé le 13 décembre 2025** 🚀

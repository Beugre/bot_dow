#!/usr/bin/env python3
"""
📱 NOTIFICATEUR TELEGRAM - RSI SCALPING PRO
Notifications Telegram optimisées pour le bot de scalping
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional, Any

try:
    import telegram
    from telegram import Bot
    from telegram.error import TelegramError
except ImportError:
    print("⚠️ python-telegram-bot non installé. Installez avec: pip install python-telegram-bot")
    telegram = None


@dataclass
class NotificationConfig:
    """Configuration des notifications"""
    send_start: bool = True
    send_trade_open: bool = True
    send_trade_close: bool = True
    send_daily_summary: bool = True
    send_errors: bool = True
    send_signals: bool = False  # Peut être verbeux


class TelegramNotifier:
    """Gestionnaire de notifications Telegram pour RSI Scalping"""
    
    def __init__(self, bot_token: str, chat_id: str, config: Optional[NotificationConfig] = None, trading_config=None):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.config = config or NotificationConfig()
        self.trading_config = trading_config  # Configuration de trading pour les valeurs dynamiques
        self.logger = logging.getLogger(__name__)
        
        # Initialisation du bot
        self.bot = None
        if telegram and bot_token and chat_id:
            try:
                self.bot = Bot(token=bot_token) # type: ignore
                self.logger.info("📱 Notificateur Telegram initialisé")
            except Exception as e:
                self.logger.error(f"❌ Erreur initialisation Telegram: {e}")
        else:
            self.logger.warning("⚠️ Telegram non configuré ou module manquant")

    async def send_message(self, message: str, parse_mode: Optional[str] = None) -> bool:
        """Envoie un message Telegram"""
        if not self.bot:
            self.logger.debug("Telegram non configuré - message non envoyé")
            return False
        
        try:
            # Nettoyage du message pour éviter les erreurs de parsing
            clean_message = message.replace('_', ' ').replace('*', '').replace('`', '')
            
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=clean_message,
                parse_mode=parse_mode  # Désactiver le Markdown
            ) # type: ignore
            return True
        except TelegramError as e: # type: ignore
            self.logger.error(f"❌ Erreur envoi Telegram: {e}")
            # Retry sans formatage en cas d'erreur
            try:
                simple_message = message.replace('*', '').replace('_', '').replace('`', '').replace('#', '')
                await self.bot.send_message(
                    chat_id=self.chat_id,
                    text=simple_message
                ) # type: ignore
                return True
            except:
                return False
        except Exception as e:
            self.logger.error(f"❌ Erreur inattendue Telegram: {e}")
            return False

    async def send_start_notification(self, capital: float):
        """Notification de démarrage du bot RSI Scalping"""
        if not self.config.send_start:
            return
        
        # Valeurs dynamiques basées sur la configuration de trading
        daily_target_percent = self.trading_config.DAILY_TARGET_PERCENT if self.trading_config else 1.0
        daily_stop_percent = self.trading_config.DAILY_STOP_LOSS_PERCENT if self.trading_config else 2.0
        position_size_percent = self.trading_config.POSITION_SIZE_PERCENT if self.trading_config else 22.5
        max_positions = self.trading_config.MAX_OPEN_POSITIONS if self.trading_config else 2
        rsi_threshold = self.trading_config.RSI_OVERSOLD if self.trading_config else 28
        
        message = f"""
🚀 **RSI SCALPING PRO - DÉMARRÉ**

💰 **Capital initial:** {capital:.2f} USDC
🎯 **Objectif quotidien:** +{daily_target_percent}% = +{capital * daily_target_percent / 100:.2f} USDC
🛑 **Stop loss quotidien:** -{daily_stop_percent}% = -{capital * daily_stop_percent / 100:.2f} USDC

📊 **STRATÉGIE:**
🔍 RSI < {rsi_threshold} (survente profonde)
📈 EMA(9) > EMA(21) + MACD > Signal
🎯 Bollinger inférieur + Volume élevé
🔄 Breakout +0.07% activé

💼 **POSITION:**
📊 Taille: {position_size_percent}% du capital
🔢 Max positions: {max_positions} simultanées
⏱️ Timeframe: 1 minute
🕘 Scan: toutes les 40 secondes

⏰ **Démarrage:** {datetime.now().strftime('%H:%M:%S')}

**LET'S SCALP SOME PROFITS! 💸**
"""
        
        await self.send_message(message)
        self.logger.info("📱 Notification de démarrage envoyée")

    async def send_trade_open_notification(self, trade_data: Dict[str, Any]):
        """Notification d'ouverture de trade"""
        if not self.config.send_trade_open:
            return
        
        # Extraction des données du trade
        pair = trade_data.get('pair', '')
        entry_price = trade_data.get('entry_price', 0)
        quantity = trade_data.get('quantity', 0)
        capital_engaged = trade_data.get('capital_engaged', 0)
        stop_loss = trade_data.get('stop_loss', 0)
        take_profit = trade_data.get('take_profit', 0)
        rsi_value = trade_data.get('rsi_value', 0)
        breakout_detected = trade_data.get('breakout_detected', False)
        valid_conditions = trade_data.get('valid_conditions', 0)
        
        # Valeurs dynamiques de configuration
        tp_percent = self.trading_config.TAKE_PROFIT_PERCENT if self.trading_config else 0.9
        sl_percent = self.trading_config.STOP_LOSS_PERCENT if self.trading_config else 0.4
        
        breakout_emoji = "🔄 BREAKOUT! " if breakout_detected else ""
        
        message = f"""
📈 **TRADE OUVERT - {pair}** {breakout_emoji}

💰 **Prix d'entrée:** {entry_price:.6f} USDC
📊 **Quantité:** {quantity:.6f}
💵 **Capital engagé:** {capital_engaged:.2f} USDC

🛑 **Stop Loss:** {stop_loss:.6f} USDC (-{sl_percent}%)
🎯 **Take Profit:** {take_profit:.6f} USDC (+{tp_percent}%)

🧠 **ANALYSE:**
🔍 RSI: {rsi_value:.1f} (survente profonde)
✅ Conditions validées: {valid_conditions}/5
{breakout_emoji}

⏰ **Ouverture:** {datetime.now().strftime('%H:%M:%S')}
"""
        
        await self.send_message(message)
        self.logger.info(f"📱 Notification ouverture trade {pair} envoyée")

    async def send_trade_close_notification(self, trade_data: Dict[str, Any]):
        """Notification de fermeture de trade"""
        if not self.config.send_trade_close:
            return
        
        # Extraction des données
        pair = trade_data.get('pair', '')
        exit_price = trade_data.get('exit_price', 0)
        pnl_amount = trade_data.get('pnl_amount', 0)
        pnl_percent = trade_data.get('pnl_percent', 0)
        duration = trade_data.get('duration_formatted', '')
        exit_reason = trade_data.get('exit_reason', '')
        daily_pnl = trade_data.get('daily_pnl', 0)
        total_capital = trade_data.get('total_capital', 0)
        
        # Emoji selon le résultat
        result_emoji = "🚀" if pnl_amount > 0 else "📉"
        
        # Calcul du pourcentage journalier
        daily_pnl_percent = (daily_pnl / total_capital * 100) if total_capital > 0 else 0
        
        # Formatage de la raison de sortie
        exit_reasons = {
            'TAKE_PROFIT': '🎯 Take Profit atteint',
            'STOP_LOSS': '🛑 Stop Loss déclenché',
            'TIMEOUT': '⏰ Timeout stagnation',
            'EARLY_EXIT': '🧠 Sortie anticipée',
            'MANUAL': '👤 Fermeture manuelle',
            'ERROR': '❌ Erreur système'
        }
        exit_description = exit_reasons.get(exit_reason, f"🔄 {exit_reason}")
        
        message = f"""
{result_emoji} **TRADE FERMÉ - {pair}**

💰 **Prix de sortie:** {exit_price:.6f} USDC
📊 **Résultat:** {pnl_amount:+.2f} USDC ({pnl_percent:+.2f}%)
⏱️ **Durée:** {duration}
🔄 **Raison:** {exit_description}

📈 **BILAN QUOTIDIEN:**
💎 **P&L jour:** {daily_pnl:+.2f} USDC ({daily_pnl_percent:+.2f}%)
💰 **Capital total:** {total_capital:.2f} USDC

⏰ **Fermeture:** {datetime.now().strftime('%H:%M:%S')}
"""
        
        await self.send_message(message)
        self.logger.info(f"📱 Notification fermeture trade {pair} envoyée")

    async def send_signal_notification(self, analysis_data: Dict[str, Any]):
        """Notification de signal détecté"""
        if not self.config.send_signals:
            return
        
        pair = analysis_data.get('pair', '')
        valid_conditions = analysis_data.get('valid_conditions', 0)
        total_score = analysis_data.get('total_score', 0)
        rsi_value = analysis_data.get('rsi_value', 0)
        breakout_detected = analysis_data.get('breakout_detected', False)
        recommendation = analysis_data.get('recommendation', '')
        
        breakout_text = "🔄 BREAKOUT DÉTECTÉ! " if breakout_detected else ""
        
        message = f"""
✅ **SIGNAL DÉTECTÉ - {pair}** {breakout_text}

🎯 **Recommandation:** {recommendation}
📊 **Score:** {total_score:.1f} ({valid_conditions}/5 conditions)
🔍 **RSI:** {rsi_value:.1f}

⏰ **Détection:** {datetime.now().strftime('%H:%M:%S')}
"""
        
        await self.send_message(message)
        self.logger.info(f"📱 Notification signal {pair} envoyée")

    async def send_daily_summary(self, summary_data: Dict[str, Any]):
        """Notification de résumé quotidien"""
        if not self.config.send_daily_summary:
            return
        
        # Extraction des données
        daily_pnl = summary_data.get('daily_pnl', 0)
        total_trades = summary_data.get('total_trades', 0)
        winning_trades = summary_data.get('winning_trades', 0)
        losing_trades = summary_data.get('losing_trades', 0)
        total_capital = summary_data.get('total_capital', 0)
        uptime_hours = summary_data.get('uptime_hours', 0)
        
        # Calculs
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        daily_pnl_percent = (daily_pnl / total_capital * 100) if total_capital > 0 else 0
        
        # Objectif quotidien
        daily_target = self.trading_config.DAILY_TARGET_PERCENT if self.trading_config else 1.0
        target_amount = total_capital * daily_target / 100
        
        # Émoji selon la performance
        if daily_pnl >= target_amount:
            status_emoji = "🎉"
            status_text = "OBJECTIF ATTEINT!"
        elif daily_pnl > 0:
            status_emoji = "✅"
            status_text = "JOURNÉE POSITIVE"
        else:
            status_emoji = "📉"
            status_text = "JOURNÉE NÉGATIVE"
        
        message = f"""
{status_emoji} **RÉSUMÉ QUOTIDIEN - {status_text}**

💰 **P&L QUOTIDIEN:**
📊 Résultat: {daily_pnl:+.2f} USDC ({daily_pnl_percent:+.2f}%)
🎯 Objectif: +{daily_target}% (+{target_amount:.2f} USDC)
💎 Capital final: {total_capital:.2f} USDC

📈 **STATISTIQUES TRADES:**
🔢 Total trades: {total_trades}
✅ Gagnants: {winning_trades}
❌ Perdants: {losing_trades}
🎯 Taux de réussite: {win_rate:.1f}%

⏰ **UPTIME:** {uptime_hours:.1f} heures

📅 **Date:** {datetime.now().strftime('%d/%m/%Y')}

**EXCELLENT TRAVAIL! 🚀**
"""
        
        await self.send_message(message)
        self.logger.info("📱 Notification résumé quotidien envoyée")

    async def send_error_notification(self, error_data: Dict[str, Any]):
        """Notification d'erreur"""
        if not self.config.send_errors:
            return
        
        component = error_data.get('component', 'UNKNOWN')
        message_text = error_data.get('message', '')
        pair = error_data.get('pair', '')
        action = error_data.get('action', '')
        
        pair_text = f" - {pair}" if pair else ""
        action_text = f" ({action})" if action else ""
        
        message = f"""
⚠️ **ERREUR BOT RSI SCALPING**

🔥 **Composant:** {component}{pair_text}
📝 **Message:** {message_text}{action_text}
⏰ **Heure:** {datetime.now().strftime('%H:%M:%S')}

*Vérifiez les logs pour plus de détails.*
"""
        
        await self.send_message(message)
        self.logger.info("📱 Notification erreur envoyée")

    async def send_warning_notification(self, warning_data: Dict[str, Any]):
        """Notification d'avertissement"""
        warning_text = warning_data.get('message', '')
        component = warning_data.get('component', '')
        
        component_text = f" ({component})" if component else ""
        
        message = f"""
⚠️ **AVERTISSEMENT{component_text}**

{warning_text}

⏰ **Heure:** {datetime.now().strftime('%H:%M:%S')}
"""
        
        await self.send_message(message)
        self.logger.info("📱 Notification avertissement envoyée")

    async def send_risk_alert(self, risk_data: Dict[str, Any]):
        """Notification d'alerte de risque"""
        risk_level = risk_data.get('level', 'UNKNOWN')
        details = risk_data.get('details', '')
        current_capital = risk_data.get('current_capital', 0)
        
        # Émojis selon le niveau
        level_emojis = {
            'LOW': '🟡',
            'MEDIUM': '🟠',
            'HIGH': '🔴',
            'CRITICAL': '🚨'
        }
        
        emoji = level_emojis.get(risk_level, '⚠️')
        
        message = f"""
{emoji} **ALERTE RISQUE - {risk_level}**

{details}

💰 **Capital actuel:** {current_capital:.2f} USDC

⏰ **Alerte:** {datetime.now().strftime('%H:%M:%S')}
"""
        
        await self.send_message(message)
        self.logger.info("📱 Notification alerte risque envoyée")

    async def send_position_update(self, position_data: Dict[str, Any]):
        """Notification de mise à jour de position (trailing stop)"""
        pair = position_data.get('pair', '')
        current_pnl = position_data.get('current_pnl', 0)
        current_pnl_percent = position_data.get('current_pnl_percent', 0)
        trailing_stop = position_data.get('trailing_stop', 0)
        
        pnl_emoji = "📈" if current_pnl > 0 else "📉"
        
        message = f"""
{pnl_emoji} **POSITION UPDATE - {pair}**

💰 **P&L actuel:** {current_pnl:+.2f} USDC ({current_pnl_percent:+.2f}%)
🔄 **Trailing Stop:** {trailing_stop:.6f} USDC

⏰ **Update:** {datetime.now().strftime('%H:%M:%S')}
"""
        
        await self.send_message(message)

    async def send_custom_notification(self, title: str, content: str, emoji: str = "ℹ️"):
        """Notification personnalisée"""
        message = f"""
{emoji} **{title}**

{content}

⏰ **Heure:** {datetime.now().strftime('%H:%M:%S')}
"""
        
        await self.send_message(message)

    async def test_connection(self) -> bool:
        """Test la connexion Telegram"""
        if not self.bot:
            return False
        
        try:
            await self.bot.get_me() # type: ignore
            await self.send_message("🤖 Test de connexion - RSI SCALPING PRO BOT")
            return True
        except Exception as e:
            self.logger.error(f"❌ Test connexion Telegram échoué: {e}")
            return False

    def configure_notifications(self, config: NotificationConfig):
        """Configure les types de notifications"""
        self.config = config
        self.logger.info("📱 Configuration notifications mise à jour")

    async def send_heartbeat(self):
        """Envoie un signal de vie du bot"""
        message = f"""
💓 **BOT RSI SCALPING - ACTIF**

⏰ **Heure:** {datetime.now().strftime('%H:%M:%S')}
🔄 **Statut:** Monitoring actif des signaux
📊 **Stratégie:** RSI < 28 + confirmations techniques

**Bot en parfaite santé! 💪**
"""
        
        await self.send_message(message)

    async def send_pairs_monitoring_update(self, pairs_data: Dict[str, Any]):
        """Notification des paires surveillées"""
        eligible_pairs = pairs_data.get('eligible_pairs', [])
        rejected_pairs = pairs_data.get('rejected_pairs', {})
        total_analyzed = pairs_data.get('total_analyzed', 0)
        
        message = f"""
🔍 **SCAN PAIRES COMPLETED**

📊 **Paires analysées:** {total_analyzed}
✅ **Éligibles:** {len(eligible_pairs)}
❌ **Rejetées:** {len(rejected_pairs)}

🏆 **Paires surveillées:**
{', '.join(eligible_pairs) if eligible_pairs else 'Aucune'}

⏰ **Scan:** {datetime.now().strftime('%H:%M:%S')}
"""
        
        await self.send_message(message)

    async def send_debug_trade_limits(self, debug_data: Dict[str, Any]):
        """Notification de debug pour les limites de trades"""
        daily_trades = debug_data.get('daily_trades', 0)
        max_daily_trades = debug_data.get('max_daily_trades', 20)
        trades_history_count = debug_data.get('trades_history_count', 0)
        firebase_trades_today = debug_data.get('firebase_trades_today', 0)
        current_date = debug_data.get('current_date', '')
        last_reset_date = debug_data.get('last_reset_date', '')
        trade_timestamps = debug_data.get('trade_timestamps', [])
        
        # Analyser si la limite est correcte
        status_emoji = "❌" if daily_trades >= max_daily_trades else "✅"
        
        message = f"""
🔧 **DEBUG - LIMITES TRADES** {status_emoji}

📊 **COMPTEURS ACTUELS:**
📈 Compteur daily_trades: {daily_trades}/{max_daily_trades}
📋 Historique trades: {trades_history_count}
🔥 Firebase trades aujourd'hui: {firebase_trades_today}
⏰ Timestamps actifs: {len(trade_timestamps)}

📅 **DATES:**
🗓️ Date actuelle: {current_date}
🔄 Dernier reset: {last_reset_date}

⚠️ **PROBLÈME POTENTIEL:**
{'✅ Compteurs normaux' if daily_trades < max_daily_trades else '❌ Limite atteinte - Reset nécessaire?'}

⏰ **Debug:** {datetime.now().strftime('%H:%M:%S')}
"""
        
        await self.send_message(message)

    async def send_trade_counter_reset_notification(self, reset_data: Dict[str, Any]):
        """Notification de réinitialisation du compteur de trades"""
        old_count = reset_data.get('old_count', 0)
        new_count = reset_data.get('new_count', 0)
        reason = reset_data.get('reason', 'Manuel')
        
        message = f"""
🔄 **COMPTEUR TRADES RÉINITIALISÉ**

📊 **CHANGEMENT:**
❌ Ancien compteur: {old_count}
✅ Nouveau compteur: {new_count}
🔧 Raison: {reason}

💡 **RÉSULTAT:**
🚀 Trading réactivé
✅ Limites quotidiennes reset

⏰ **Reset:** {datetime.now().strftime('%H:%M:%S')}
"""
        
        await self.send_message(message)


# Exemple d'utilisation
async def main():
    """Test du notificateur"""
    # Configuration à mettre dans les variables d'environnement
    BOT_TOKEN = "YOUR_BOT_TOKEN"
    CHAT_ID = "YOUR_CHAT_ID"
    
    notifier = TelegramNotifier(BOT_TOKEN, CHAT_ID)
    
    # Test de connexion
    if await notifier.test_connection():
        print("✅ Connexion Telegram OK")
    else:
        print("❌ Connexion Telegram échouée")


if __name__ == "__main__":
    asyncio.run(main())

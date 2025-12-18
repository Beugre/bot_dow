"""
Bot principal - Dow Theory / Market Structure Trading
"""
import time
import logging
from datetime import datetime
from typing import Dict, List
import config_dow as config
from data_fetcher_dow import DataFetcher
from market_structure import MarketStructure
from risk_manager_dow import RiskManager
from telegram_notifier import TelegramNotifier


# Configuration du logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DowBot:
    """
    Bot de trading basé sur Dow Theory et Market Structure
    """
    
    def __init__(self):
        """Initialise le bot"""
        logger.info("=" * 70)
        logger.info("🚀 DÉMARRAGE DU BOT DOW THEORY")
        logger.info("=" * 70)
        
        # Composants
        self.data_fetcher = DataFetcher()
        self.market_structure = MarketStructure()
        self.risk_manager = RiskManager(initial_capital=config.BACKTEST_INITIAL_CAPITAL)
        
        # Telegram (optionnel)
        self.telegram = None
        if config.TELEGRAM_TOKEN and config.TELEGRAM_CHAT_ID:
            try:
                self.telegram = TelegramNotifier()
                logger.info("✅ Telegram activé")
            except:
                logger.warning("⚠️ Telegram non disponible")
        
        # État
        self.running = False
        self.cycle_count = 0
        
        logger.info(f"💰 Capital initial: {config.BACKTEST_INITIAL_CAPITAL} USDC")
        logger.info(f"📊 Paires surveillées: {', '.join(config.PAIRS)}")
        logger.info(f"⚠️ Risk par trade: {config.RISK_PERCENT}%")
        logger.info(f"🎯 Zero risk: {config.TRIGGER_ZERO_R}R")
        logger.info(f"🔄 Mode: {'DRY RUN' if config.DRY_RUN else 'LIVE'}")
        logger.info("=" * 70)
    
    def scan_opportunities(self) -> List[Dict]:
        """
        Scan toutes les paires pour détecter des opportunités
        
        Returns:
            Liste d'opportunités détectées
        """
        opportunities = []
        
        for symbol in config.PAIRS:
            try:
                # Récupérer les données
                data = self.data_fetcher.fetch_multiple_timeframes(symbol)
                
                if "H1" not in data or "H4" not in data:
                    logger.warning(f"⚠️ Données manquantes pour {symbol}")
                    continue
                
                # Analyser la structure
                analysis = self.market_structure.analyze(data["H1"], data["H4"])
                
                # Vérifier signal BUY
                buy_signal, buy_sl, buy_details = self.market_structure.check_buy_signal(analysis)
                if buy_signal:
                    # Vérifier si on peut ouvrir une position LONG
                    can_open, reason = self.risk_manager.can_open_position(
                        symbol, 
                        side="LONG",
                        structure_id=analysis.get("structure_id")
                    )
                    if can_open:
                        opportunities.append({
                            "symbol": symbol,
                            "side": "LONG",
                            "entry_price": buy_details["entry_price"],
                            "stop_loss": buy_sl,
                            "details": buy_details,
                            "analysis": analysis
                        })
                        logger.info(f"✨ Signal BUY détecté: {symbol}")
                        logger.info(f"   Entry: {buy_details['entry_price']:.4f}, SL: {buy_sl:.4f}")
                        logger.info(f"   Raison: {buy_details['reason']}")
                    else:
                        logger.debug(f"❌ {symbol} LONG: {reason}")
                
                # Vérifier signal SELL
                sell_signal, sell_sl, sell_details = self.market_structure.check_sell_signal(analysis)
                if sell_signal:
                    # Vérifier si on peut ouvrir une position SHORT
                    can_open, reason = self.risk_manager.can_open_position(
                        symbol, 
                        side="SHORT",
                        structure_id=analysis.get("structure_id")
                    )
                    if can_open:
                        opportunities.append({
                            "symbol": symbol,
                            "side": "SHORT",
                            "entry_price": sell_details["entry_price"],
                            "stop_loss": sell_sl,
                            "details": sell_details,
                            "analysis": analysis
                        })
                        logger.info(f"✨ Signal SELL détecté: {symbol}")
                        logger.info(f"   Entry: {sell_details['entry_price']:.4f}, SL: {sell_sl:.4f}")
                        logger.info(f"   Raison: {sell_details['reason']}")
                    else:
                        logger.debug(f"❌ {symbol} SHORT: {reason}")
                
            except Exception as e:
                logger.error(f"❌ Erreur scan {symbol}: {e}", exc_info=True)
        
        return opportunities
    
    def execute_trade(self, opportunity: Dict):
        """
        Exécute un trade
        
        Args:
            opportunity: Dict avec infos du signal
        """
        symbol = opportunity["symbol"]
        side = opportunity["side"]
        entry_price = opportunity["entry_price"]
        stop_loss = opportunity["stop_loss"]
        
        try:
            # Calculer la taille de position
            quantity = self.risk_manager.calculate_position_size(
                entry_price=entry_price,
                stop_loss=stop_loss,
                side=side
            )
            
            if quantity <= 0:
                logger.warning(f"⚠️ Quantité invalide pour {symbol}: {quantity}")
                return
            
            logger.info(f"🎯 Exécution trade {side} sur {symbol}")
            logger.info(f"   Quantité: {quantity:.4f}")
            logger.info(f"   Entry: {entry_price:.4f}")
            logger.info(f"   SL: {stop_loss:.4f}")
            
            # Placer l'ordre d'entrée
            order_side = "buy" if side == "LONG" else "sell"
            order = self.data_fetcher.place_market_order(symbol, order_side, quantity)
            
            if not order:
                logger.error(f"❌ Échec placement ordre {symbol}")
                return
            
            # Ajouter la position au risk manager
            # 🔥 structure_id = identifiant unique de la structure (ex: "LONG_45632.12_44103.55")
            position = self.risk_manager.add_position(
                symbol=symbol,
                side=side,
                entry_price=entry_price,
                quantity=quantity,
                stop_loss=stop_loss,
                structure_type=opportunity.get("analysis", {}).get("structure_id")
            )
            
            logger.info(f"✅ Position {side} ouverte sur {symbol}")
            logger.info(f"   R initial: {position.initial_r:.4f}")
            
            # Notification Telegram
            if self.telegram:
                msg = (
                    f"🎯 NOUVELLE POSITION\n\n"
                    f"Symbole: {symbol}\n"
                    f"Side: {side}\n"
                    f"Entry: {entry_price:.4f}\n"
                    f"Quantité: {quantity:.4f}\n"
                    f"SL: {stop_loss:.4f}\n"
                    f"R: {position.initial_r:.4f}"
                )
                self.telegram.send_message(msg)
            
        except Exception as e:
            logger.error(f"❌ Erreur execute_trade {symbol}: {e}", exc_info=True)
    
    def manage_positions(self):
        """
        Gère les positions ouvertes (trailing, zero risk, exit)
        """
        for symbol, positions in list(self.risk_manager.positions.items()):
            for position in list(positions):
                try:
                    # Prix actuel
                    current_price = self.data_fetcher.get_current_price(symbol)
                    if not current_price:
                        continue
                    
                    # Mettre à jour la position
                    self.risk_manager.update_position(position, current_price)
                    
                    # Vérifier stop loss
                    if self.risk_manager.check_stop_hit(position, current_price):
                        logger.info(f"🛑 Stop Loss touché: {symbol} @ {current_price:.4f}")
                        self.close_position(position, current_price, "STOP_LOSS")
                        continue
                    
                    # Vérifier invalidation de tendance
                    data = self.data_fetcher.fetch_multiple_timeframes(symbol)
                    if "H1" in data and "H4" in data:
                        analysis = self.market_structure.analyze(data["H1"], data["H4"])
                        
                        if self.market_structure.check_trend_invalidation(analysis, position.side):
                            logger.info(f"⚠️ Tendance invalidée: {symbol}")
                            self.close_position(position, current_price, "TREND_INVALIDATION")
                            continue
                    
                    # Log du statut
                    profit_r = position.get_profit_r(current_price)
                    pnl = position.get_pnl(current_price)
                    
                    logger.debug(
                        f"📊 {symbol} {position.side}: "
                        f"Price={current_price:.4f}, "
                        f"P&L={pnl:+.2f} USDC ({profit_r:+.2f}R), "
                        f"SL={position.current_sl:.4f}, "
                        f"ZeroRisk={'✅' if position.zero_risk_activated else '❌'}"
                    )
                    
                except Exception as e:
                    logger.error(f"❌ Erreur manage position {symbol}: {e}", exc_info=True)
    
    def close_position(self, position, exit_price: float, reason: str):
        """
        Ferme une position
        
        Args:
            position: Position à fermer
            exit_price: Prix de sortie
            reason: Raison de la fermeture
        """
        try:
            symbol = position.symbol
            side = position.side
            quantity = position.quantity
            
            # Placer l'ordre de sortie
            order_side = "sell" if side == "LONG" else "buy"
            order = self.data_fetcher.place_market_order(symbol, order_side, quantity)
            
            # Calculer P&L
            pnl = position.get_pnl(exit_price)
            profit_r = position.get_profit_r(exit_price)
            
            logger.info(f"🔒 Position fermée: {symbol} {side}")
            logger.info(f"   Entry: {position.entry_price:.4f}, Exit: {exit_price:.4f}")
            logger.info(f"   P&L: {pnl:+.2f} USDC ({profit_r:+.2f}R)")
            logger.info(f"   Raison: {reason}")
            
            # Mettre à jour le risk manager
            self.risk_manager.close_position(position, exit_price, reason)
            
            # Notification Telegram
            if self.telegram:
                emoji = "✅" if pnl > 0 else "❌"
                msg = (
                    f"{emoji} POSITION FERMÉE\n\n"
                    f"Symbole: {symbol}\n"
                    f"Side: {side}\n"
                    f"Entry: {position.entry_price:.4f}\n"
                    f"Exit: {exit_price:.4f}\n"
                    f"P&L: {pnl:+.2f} USDC ({profit_r:+.2f}R)\n"
                    f"Raison: {reason}"
                )
                self.telegram.send_message(msg)
            
        except Exception as e:
            logger.error(f"❌ Erreur close_position: {e}", exc_info=True)
    
    def print_stats(self):
        """Affiche les statistiques"""
        stats = self.risk_manager.get_stats()
        
        logger.info("\n" + "=" * 70)
        logger.info("📊 STATISTIQUES DU BOT")
        logger.info("=" * 70)
        logger.info(f"Capital initial: {stats['initial_capital']:.2f} USDC")
        logger.info(f"Capital actuel: {stats['current_capital']:.2f} USDC")
        logger.info(f"P&L total: {stats['total_pnl']:+.2f} USDC ({stats['return_pct']:+.2f}%)")
        logger.info(f"Trades: {stats['total_trades']} (W:{stats['winning_trades']}, L:{stats['losing_trades']})")
        logger.info(f"Win rate: {stats['win_rate']:.1f}%")
        logger.info(f"Profit factor: {stats['profit_factor']:.2f}")
        logger.info(f"Avg win: {stats['avg_win']:.2f} USDC")
        logger.info(f"Avg loss: {stats['avg_loss']:.2f} USDC")
        logger.info(f"Positions ouvertes: {stats['open_positions']}")
        logger.info(f"Risque exposé: {stats['risk_exposed']:.2f}%")
        logger.info("=" * 70 + "\n")
    
    def run(self):
        """Boucle principale du bot"""
        self.running = True
        
        try:
            while self.running:
                self.cycle_count += 1
                logger.info(f"\n{'='*70}")
                logger.info(f"🔄 CYCLE {self.cycle_count} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                logger.info(f"{'='*70}")
                
                # Gérer les positions existantes
                self.manage_positions()
                
                # Scanner les opportunités
                opportunities = self.scan_opportunities()
                
                # Exécuter les trades
                for opp in opportunities:
                    self.execute_trade(opp)
                
                # Afficher stats toutes les 10 cycles
                if self.cycle_count % 10 == 0:
                    self.print_stats()
                
                # Attendre avant le prochain cycle
                logger.info(f"⏳ Attente {config.CHECK_INTERVAL}s avant prochain cycle...")
                time.sleep(config.CHECK_INTERVAL)
                
        except KeyboardInterrupt:
            logger.info("\n⏸️ Arrêt demandé par l'utilisateur")
        except Exception as e:
            logger.error(f"❌ Erreur fatale: {e}", exc_info=True)
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Arrêt propre du bot"""
        logger.info("\n🛑 Arrêt du bot...")
        self.running = False
        
        # Stats finales
        self.print_stats()
        
        # Fermer toutes les positions?
        # Note: En production, garder les positions ouvertes
        
        logger.info("✅ Bot arrêté")


if __name__ == "__main__":
    bot = DowBot()
    bot.run()

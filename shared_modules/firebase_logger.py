#!/usr/bin/env python3
"""
🔥 FIREBASE LOGGER - RSI Scalping Pro
Gestionnaire de logging Firebase pour le bot de trading
"""

import asyncio
import logging
import json
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any

try:
    import firebase_admin
    from firebase_admin import credentials, firestore
except ImportError:
    print("⚠️ Firebase Admin SDK non installé. Installez avec: pip install firebase-admin")
    firebase_admin = None
    firestore = None


class FirebaseLogger:
    """Gestionnaire de logs Firebase pour le trading bot"""
    
    def __init__(self, credentials_path: str):
        self.credentials_path = credentials_path
        self.db = None
        self.app = None
        self.logger = logging.getLogger(__name__)
        self.collections = {
            'trades': 'rsi_scalping_trades',
            'signals': 'rsi_scalping_signals', 
            'errors': 'rsi_scalping_errors',
            'daily_stats': 'rsi_scalping_daily_stats',
            'pairs_analysis': 'rsi_scalping_pairs_analysis',
            'logs': 'rsi_scalping_logs',           # Nouveau: Logs en miroir console
            'trailing_stops': 'rsi_scalping_trailing_stops'  # Nouveau: États trailing stop
        }
        
    async def initialize(self) -> bool:
        """Initialise la connexion Firebase"""
        try:
            if not firebase_admin:
                self.logger.warning("⚠️ Firebase Admin SDK non disponible")
                return False
            
            # Vérification du fichier de credentials
            if not os.path.exists(self.credentials_path):
                self.logger.error(f"❌ Fichier credentials Firebase non trouvé: {self.credentials_path}")
                return False
            
            # Initialisation Firebase
            if not firebase_admin._apps:
                cred = credentials.Certificate(self.credentials_path)
                self.app = firebase_admin.initialize_app(cred)
            else:
                self.app = firebase_admin.get_app()
            
            # Initialisation Firestore
            self.db = firestore.client()
            
            # Test de connexion
            await self._test_connection()
            
            self.logger.info("🔥 Firebase Logger initialisé avec succès")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erreur initialisation Firebase: {e}")
            return False
    
    async def _test_connection(self):
        """Test la connexion Firestore"""
        try:
            # Tentative d'écriture de test
            test_doc = {
                'test': True,
                'timestamp': datetime.now(timezone.utc),
                'message': 'Test connexion Firebase'
            }
            
            doc_ref = self.db.collection('test').document('connection_test')
            doc_ref.set(test_doc)
            
            # Suppression du document de test
            doc_ref.delete()
            
            self.logger.info("✅ Test connexion Firebase réussi")
            
        except Exception as e:
            self.logger.error(f"❌ Test connexion Firebase échoué: {e}")
            raise
    
    async def log_trade_open(self, pair: str, entry_price: float, quantity: float, 
                           take_profit: float, stop_loss: float, analysis_data: Dict) -> bool:
        """Log l'ouverture d'un trade"""
        try:
            if not self.db:
                return False
            
            trade_doc = {
                'pair': pair,
                'action': 'BUY',
                'entry_price': entry_price,
                'quantity': quantity,
                'take_profit': take_profit,
                'stop_loss': stop_loss,
                'entry_timestamp': datetime.now(timezone.utc),
                'status': 'OPEN',
                'analysis_data': {
                    'rsi': analysis_data.get('rsi', 0),
                    'ema9': analysis_data.get('ema9', 0),
                    'ema21': analysis_data.get('ema21', 0),
                    'macd': analysis_data.get('macd', 0),
                    'signal': analysis_data.get('signal', 0),
                    'bb_lower': analysis_data.get('bb_lower', 0),
                    'volume_ratio': analysis_data.get('volume_ratio', 0),
                    'breakout_level': analysis_data.get('breakout_level', 0),
                    'conditions_met': analysis_data.get('conditions_met', []),
                    'signal_strength': analysis_data.get('signal_strength', 0)
                },
                'position_value': quantity * entry_price,
                'expected_pnl': {
                    'tp_amount': (take_profit - entry_price) * quantity,
                    'sl_amount': (entry_price - stop_loss) * quantity
                }
            }
            
            # Génération d'un ID unique pour le trade
            trade_id = f"{pair}_{int(datetime.now().timestamp())}"
            
            # Enregistrement dans Firestore
            doc_ref = self.db.collection(self.collections['trades']).document(trade_id)
            doc_ref.set(trade_doc)
            
            self.logger.info(f"🔥 Trade ouvert loggé: {trade_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erreur log trade ouvert: {e}")
            return False
    
    async def log_trade_close(self, pair: str, exit_price: float, pnl_amount: float, 
                            pnl_percent: float, exit_reason: str) -> bool:
        """Log la fermeture d'un trade"""
        try:
            if not self.db:
                return False
            
            # Recherche du trade ouvert correspondant
            trades_ref = self.db.collection(self.collections['trades'])
            query = trades_ref.where('pair', '==', pair).where('status', '==', 'OPEN').limit(1)
            
            docs = query.stream()
            trade_doc = None
            trade_id = None
            
            for doc in docs:
                trade_doc = doc.to_dict()
                trade_id = doc.id
                break
            
            if not trade_doc:
                self.logger.warning(f"⚠️ Trade ouvert non trouvé pour {pair}")
                return False
            
            # Calcul de la durée du trade
            entry_time = trade_doc['entry_timestamp']
            exit_time = datetime.now(timezone.utc)
            duration_seconds = (exit_time - entry_time).total_seconds()
            
            # Mise à jour du document trade
            update_data = {
                'exit_price': exit_price,
                'exit_timestamp': exit_time,
                'exit_reason': exit_reason,
                'status': 'CLOSED',
                'pnl': {
                    'amount': pnl_amount,
                    'percent': pnl_percent
                },
                'duration_seconds': duration_seconds,
                'trade_result': 'WIN' if pnl_amount > 0 else 'LOSS'
            }
            
            # Mise à jour dans Firestore
            doc_ref = self.db.collection(self.collections['trades']).document(trade_id)
            doc_ref.update(update_data)
            
            self.logger.info(f"🔥 Trade fermé loggé: {trade_id} | P&L: {pnl_amount:+.2f}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erreur log trade fermé: {e}")
            return False
    
    async def log_signal_analysis(self, pair: str, signal_data: Dict, is_valid: bool) -> bool:
        """Log une analyse de signal"""
        try:
            if not self.db:
                return False
            
            signal_doc = {
                'pair': pair,
                'timestamp': datetime.now(timezone.utc),
                'is_valid_signal': is_valid,
                'signal_data': signal_data,
                'conditions_met': signal_data.get('conditions_met', []),
                'signal_strength': signal_data.get('signal_strength', 0),
                'current_price': signal_data.get('current_price', 0),
                'action_taken': 'BUY_ATTEMPT' if is_valid else 'IGNORED'
            }
            
            # Enregistrement
            doc_ref = self.db.collection(self.collections['signals']).document()
            doc_ref.set(signal_doc)
            
            if is_valid:
                self.logger.info(f"🔥 Signal valide loggé: {pair}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erreur log signal: {e}")
            return False
    
    async def log_pair_rejected(self, pair: str, reason: str, details: Dict = None) -> bool:
        """Log une paire rejetée avec la raison"""
        try:
            if not self.db:
                return False
            
            rejection_doc = {
                'pair': pair,
                'timestamp': datetime.now(timezone.utc),
                'rejection_reason': reason,
                'details': details or {},
                'action': 'PAIR_REJECTED'
            }
            
            # Enregistrement
            doc_ref = self.db.collection(self.collections['pairs_analysis']).document()
            doc_ref.set(rejection_doc)
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erreur log paire rejetée: {e}")
            return False
    
    async def log_error(self, error_type: str, error_message: str, context: str = "", 
                       stack_trace: str = "") -> bool:
        """Log une erreur"""
        try:
            if not self.db:
                return False
            
            error_doc = {
                'timestamp': datetime.now(timezone.utc),
                'error_type': error_type,
                'error_message': error_message,
                'context': context,
                'stack_trace': stack_trace,
                'severity': 'ERROR'
            }
            
            # Enregistrement
            doc_ref = self.db.collection(self.collections['errors']).document()
            doc_ref.set(error_doc)
            
            self.logger.info(f"🔥 Erreur loggée: {error_type}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erreur log erreur: {e}")
            return False
    
    async def log_daily_stats(self, date: str, stats: Dict) -> bool:
        """Log les statistiques quotidiennes"""
        try:
            if not self.db:
                return False
            
            daily_doc = {
                'date': date,
                'timestamp': datetime.now(timezone.utc),
                'stats': stats,
                'trades_count': stats.get('trades_count', 0),
                'win_rate': stats.get('win_rate', 0),
                'total_pnl': stats.get('total_pnl', 0),
                'best_trade': stats.get('best_trade', 0),
                'worst_trade': stats.get('worst_trade', 0),
                'avg_trade_duration': stats.get('avg_trade_duration', 0)
            }
            
            # Enregistrement avec la date comme ID
            doc_ref = self.db.collection(self.collections['daily_stats']).document(date)
            doc_ref.set(daily_doc)
            
            self.logger.info(f"🔥 Stats quotidiennes loggées: {date}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erreur log stats quotidiennes: {e}")
            return False
    
    async def log_console_mirror(self, level: str, message: str, module: str = "main") -> bool:
        """Log en miroir de la console vers Firebase"""
        try:
            if not self.db:
                return False
            
            log_doc = {
                'timestamp': datetime.now(timezone.utc),
                'level': level,  # INFO, WARNING, ERROR, DEBUG
                'message': message,
                'module': module,
                'bot_type': 'rsi_scalping_pro'
            }
            
            # Enregistrement
            doc_ref = self.db.collection(self.collections['logs']).document()
            doc_ref.set(log_doc)
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erreur log console mirror: {e}")
            return False
    
    async def log_pair_rejected_detailed(self, pair: str, reason: str, details: Dict = None, 
                                        spread: float = 0, volume: float = 0, volatility: float = 0) -> bool:
        """Log une paire rejetée avec détails complets"""
        try:
            if not self.db:
                return False
            
            rejection_doc = {
                'pair': pair,
                'timestamp': datetime.now(timezone.utc),
                'rejection_reason': reason,
                'details': details or {},
                'metrics': {
                    'spread_percent': spread,
                    'volume_usdc': volume,
                    'volatility_percent': volatility
                },
                'action': 'PAIR_REJECTED',
                'log_message': f"⛔ PAIRE REJETÉE: {pair} - {reason}"
            }
            
            # Enregistrement
            doc_ref = self.db.collection(self.collections['pairs_analysis']).document()
            doc_ref.set(rejection_doc)
            
            # Log console mirror
            await self.log_console_mirror('INFO', f"⛔ PAIRE REJETÉE: {pair} - {reason}", 'pair_scanner')
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erreur log paire rejetée: {e}")
            return False
    
    async def log_signal_detected(self, pair: str, signal_data: Dict, is_valid: bool, 
                                 signal_strength: int, action_taken: str = "") -> bool:
        """Log un signal détecté avec détails"""
        try:
            if not self.db:
                return False
            
            rsi = signal_data.get('rsi', 0)
            conditions = signal_data.get('conditions_met', [])
            
            if is_valid:
                message = f"📶 Signal détecté pour {pair} avec RSI={rsi:.1f}, force={signal_strength}/6"
                action = action_taken or 'BUY_ATTEMPT'
            else:
                reason = action_taken or "conditions insuffisantes"
                message = f"🔍 Signal ignoré pour {pair} : {reason}"
                action = 'IGNORED'
            
            signal_doc = {
                'pair': pair,
                'timestamp': datetime.now(timezone.utc),
                'is_valid_signal': is_valid,
                'signal_data': signal_data,
                'conditions_met': conditions,
                'signal_strength': signal_strength,
                'current_price': signal_data.get('current_price', 0),
                'action_taken': action,
                'log_message': message,
                'rsi_value': rsi,
                'ema9': signal_data.get('ema9', 0),
                'ema21': signal_data.get('ema21', 0)
            }
            
            # Enregistrement
            doc_ref = self.db.collection(self.collections['signals']).document()
            doc_ref.set(signal_doc)
            
            # Log console mirror
            await self.log_console_mirror('INFO', message, 'signal_detector')
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erreur log signal: {e}")
            return False
    
    async def log_trade_execution(self, pair: str, action: str, price: float, quantity: float, 
                                 trade_id: str = "", success: bool = True, reason: str = "") -> bool:
        """Log l'exécution d'un trade"""
        try:
            if not self.db:
                return False
            
            if success:
                if action == 'BUY':
                    message = f"✅ BUY {pair} à {price:.2f} USDC ({quantity:.6f})"
                else:
                    message = f"📉 SELL {pair} à {price:.2f} USDC ({quantity:.6f})"
                level = 'INFO'
            else:
                message = f"❌ ÉCHEC {action} {pair}: {reason}"
                level = 'ERROR'
            
            trade_doc = {
                'pair': pair,
                'action': action,
                'price': price,
                'quantity': quantity,
                'trade_id': trade_id,
                'success': success,
                'reason': reason,
                'timestamp': datetime.now(timezone.utc),
                'log_message': message,
                'position_value': price * quantity
            }
            
            # Enregistrement dans trades
            doc_ref = self.db.collection(self.collections['trades']).document()
            doc_ref.set(trade_doc)
            
            # Log console mirror
            await self.log_console_mirror(level, message, 'trade_executor')
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erreur log trade execution: {e}")
            return False
    
    async def log_scan_summary(self, pairs_analyzed: int, valid_signals: int, trades_executed: int, 
                              scan_duration: float = 0) -> bool:
        """Log le résumé d'un cycle de scan"""
        try:
            if not self.db:
                return False
            
            message = f"⏱️ Scan terminé. {pairs_analyzed} paires analysées. {valid_signals} signaux valides. {trades_executed} trade(s) exécuté(s)."
            
            scan_doc = {
                'timestamp': datetime.now(timezone.utc),
                'pairs_analyzed': pairs_analyzed,
                'valid_signals': valid_signals,
                'trades_executed': trades_executed,
                'scan_duration_seconds': scan_duration,
                'log_message': message,
                'scan_type': 'main_cycle'
            }
            
            # Enregistrement dans signals (option)
            doc_ref = self.db.collection(self.collections['signals']).document()
            doc_ref.set(scan_doc)
            
            # Log console mirror
            await self.log_console_mirror('INFO', message, 'main_scanner')
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erreur log scan summary: {e}")
            return False
    
    async def log_trailing_stop_state(self, pair: str, current_price: float, stop_price: float, 
                                     highest_price: float, trigger_price: float, is_active: bool) -> bool:
        """Log l'état du trailing stop"""
        try:
            if not self.db:
                return False
            
            trailing_doc = {
                'pair': pair,
                'timestamp': datetime.now(timezone.utc),
                'current_price': current_price,
                'stop_price': stop_price,
                'highest_price': highest_price,
                'trigger_price': trigger_price,
                'is_active': is_active,
                'distance_percent': ((current_price - stop_price) / current_price * 100) if current_price > 0 else 0,
                'profit_percent': ((current_price - trigger_price) / trigger_price * 100) if trigger_price > 0 else 0
            }
            
            # Enregistrement
            doc_ref = self.db.collection(self.collections['trailing_stops']).document()
            doc_ref.set(trailing_doc)
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erreur log trailing stop: {e}")
            return False
    
    async def get_daily_trades(self, date: str) -> List[Dict]:
        """Récupère les trades d'une journée"""
        try:
            if not self.db:
                return []
            
            # Conversion de la date
            start_date = datetime.strptime(date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            end_date = start_date.replace(hour=23, minute=59, second=59)
            
            # Requête Firestore
            trades_ref = self.db.collection(self.collections['trades'])
            query = trades_ref.where('entry_timestamp', '>=', start_date).where('entry_timestamp', '<=', end_date)
            
            trades = []
            for doc in query.stream():
                trade_data = doc.to_dict()
                trade_data['id'] = doc.id
                trades.append(trade_data)
            
            return trades
            
        except Exception as e:
            self.logger.error(f"❌ Erreur récupération trades quotidiens: {e}")
            return []
    
    async def get_trade_statistics(self, days: int = 30) -> Dict:
        """Récupère les statistiques de trading sur X jours"""
        try:
            if not self.db:
                return {}
            
            # Calcul de la date de début
            end_date = datetime.now(timezone.utc)
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
            start_date = start_date - timedelta(days=days)
            
            # Requête Firestore
            trades_ref = self.db.collection(self.collections['trades'])
            query = trades_ref.where('entry_timestamp', '>=', start_date).where('status', '==', 'CLOSED')
            
            trades = []
            for doc in query.stream():
                trades.append(doc.to_dict())
            
            if not trades:
                return {'trades_count': 0, 'win_rate': 0, 'total_pnl': 0}
            
            # Calcul des statistiques
            total_trades = len(trades)
            winning_trades = sum(1 for trade in trades if trade.get('pnl', {}).get('amount', 0) > 0)
            total_pnl = sum(trade.get('pnl', {}).get('amount', 0) for trade in trades)
            
            win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
            
            avg_duration = sum(trade.get('duration_seconds', 0) for trade in trades) / total_trades if total_trades > 0 else 0
            
            best_trade = max((trade.get('pnl', {}).get('amount', 0) for trade in trades), default=0)
            worst_trade = min((trade.get('pnl', {}).get('amount', 0) for trade in trades), default=0)
            
            return {
                'trades_count': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': total_trades - winning_trades,
                'win_rate': win_rate,
                'total_pnl': total_pnl,
                'avg_trade_duration': avg_duration,
                'best_trade': best_trade,
                'worst_trade': worst_trade,
                'period_days': days
            }
            
        except Exception as e:
            self.logger.error(f"❌ Erreur récupération statistiques: {e}")
            return {}
    
    async def cleanup_old_data(self, days_to_keep: int = 90) -> bool:
        """Nettoie les anciennes données (garde X jours)"""
        try:
            if not self.db:
                return False
            
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
            
            # Nettoyage des signaux anciens
            signals_ref = self.db.collection(self.collections['signals'])
            old_signals = signals_ref.where('timestamp', '<', cutoff_date).limit(500)
            
            deleted_count = 0
            for doc in old_signals.stream():
                doc.reference.delete()
                deleted_count += 1
            
            self.logger.info(f"🔥 Nettoyage Firebase: {deleted_count} anciens signaux supprimés")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erreur nettoyage Firebase: {e}")
            return False
    
    async def close(self):
        """Ferme la connexion Firebase"""
        try:
            if self.app and firebase_admin:
                firebase_admin.delete_app(self.app)
                self.logger.info("🔥 Connexion Firebase fermée")
        except Exception as e:
            self.logger.error(f"❌ Erreur fermeture Firebase: {e}")


# Test du firebase logger
async def main():
    """Test du firebase logger"""
    logger = FirebaseLogger("firebase-credentials.json")
    
    if await logger.initialize():
        print("✅ Firebase Logger initialisé avec succès")
        
        # Test log trade
        test_analysis = {
            'rsi': 25.5,
            'ema9': 42000,
            'ema21': 41800,
            'conditions_met': ['RSI < 28', 'EMA9 > EMA21'],
            'signal_strength': 4
        }
        
        await logger.log_trade_open(
            pair="BTCUSDC",
            entry_price=42000.0,
            quantity=0.001,
            take_profit=42378.0,
            stop_loss=41832.0,
            analysis_data=test_analysis
        )
        
        print("✅ Test trade loggé")
        
        await logger.close()
    else:
        print("❌ Échec initialisation Firebase Logger")


if __name__ == "__main__":
    asyncio.run(main())

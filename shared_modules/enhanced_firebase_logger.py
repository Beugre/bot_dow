#!/usr/bin/env python3
"""
FIREBASE LOGGER AVANCÉ POUR SATOCHI BOT
Enregistrement complet des trades, performances, logs et métriques
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import pandas as pd
from dataclasses import asdict
import os
import asyncio

try:
    import firebase_admin
    from firebase_admin import credentials, firestore, storage
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    logging.warning("Firebase SDK not available - using local storage fallback")

logger = logging.getLogger(__name__)

class EnhancedFirebaseLogger:
    """Logger Firebase avancé pour toutes les données du bot"""
    
    def __init__(self, config_path: str = 'configs/firebase_config.json'):
        self.config_path = config_path
        self.db = None
        self.bucket = None
        self.local_backup = True
        self.backup_dir = 'data/firebase_backup'
        
        # S'assurer que le dossier de backup existe
        os.makedirs(self.backup_dir, exist_ok=True)
        
        if FIREBASE_AVAILABLE:
            self._initialize_firebase()
        else:
            logger.warning("Firebase non disponible - utilisation du stockage local uniquement")

    def _initialize_firebase(self):
        """Initialise la connexion Firebase"""
        try:
            if not firebase_admin._apps:
                # Charger la configuration
                if os.path.exists(self.config_path):
                    cred = credentials.Certificate(self.config_path)
                    firebase_admin.initialize_app(cred, {
                        'storageBucket': 'satochi-bot.appspot.com'
                    })
                else:
                    logger.warning(f"Config Firebase non trouvée: {self.config_path}")
                    return

            self.db = firestore.client()
            self.bucket = storage.bucket()
            logger.info("✅ Firebase initialisé avec succès")
            
        except Exception as e:
            logger.error(f"❌ Erreur initialisation Firebase: {e}")
            self.db = None
            self.bucket = None

    async def log_trade(self, trade_result) -> bool:
        """Enregistre un trade complet"""
        try:
            trade_data = {
                'timestamp': datetime.now().isoformat(),
                'strategy': trade_result.strategy,
                'symbol': trade_result.symbol,
                'side': trade_result.side,
                'amount': float(trade_result.amount),
                'price': float(trade_result.price),
                'profit_pct': float(trade_result.profit_pct),
                'profit_usdt': float(trade_result.profit_usdt),
                'success': trade_result.success,
                'execution_time_ms': getattr(trade_result, 'execution_time_ms', 0),
                'fees_usdt': getattr(trade_result, 'fees_usdt', 0),
                'slippage_pct': getattr(trade_result, 'slippage_pct', 0),
                'market_conditions': getattr(trade_result, 'market_conditions', {}),
                'risk_metrics': getattr(trade_result, 'risk_metrics', {})
            }

            # Firebase
            if self.db:
                doc_ref = self.db.collection('trades').document()
                doc_ref.set(trade_data)
                logger.debug(f"✅ Trade enregistré Firebase: {trade_result.strategy}")

            # Backup local
            if self.local_backup:
                await self._save_local_backup('trades', trade_data)

            return True

        except Exception as e:
            logger.error(f"❌ Erreur log trade: {e}")
            return False

    async def log_cycle_performance(self, cycle_data: Dict) -> bool:
        """Enregistre les performances d'un cycle"""
        try:
            performance_data = {
                'timestamp': datetime.now().isoformat(),
                'cycle_id': cycle_data.get('cycle_id', ''),
                'total_trades': cycle_data.get('total_trades', 0),
                'successful_trades': cycle_data.get('successful_trades', 0),
                'total_profit_usdt': float(cycle_data.get('total_profit_usdt', 0)),
                'total_profit_pct': float(cycle_data.get('total_profit_pct', 0)),
                'strategy_breakdown': cycle_data.get('strategy_breakdown', {}),
                'execution_time_seconds': cycle_data.get('execution_time_seconds', 0),
                'market_conditions': cycle_data.get('market_conditions', {}),
                'risk_metrics': cycle_data.get('risk_metrics', {}),
                'portfolio_value': cycle_data.get('portfolio_value', 0),
                'drawdown_pct': cycle_data.get('drawdown_pct', 0)
            }

            # Firebase
            if self.db:
                doc_ref = self.db.collection('cycle_performance').document()
                doc_ref.set(performance_data)

            # Backup local
            if self.local_backup:
                await self._save_local_backup('cycle_performance', performance_data)

            return True

        except Exception as e:
            logger.error(f"❌ Erreur log cycle performance: {e}")
            return False

    async def log_strategy_metrics(self, strategy_name: str, metrics: Dict) -> bool:
        """Enregistre les métriques détaillées d'une stratégie"""
        try:
            strategy_data = {
                'timestamp': datetime.now().isoformat(),
                'strategy_name': strategy_name,
                'total_trades': metrics.get('total_trades', 0),
                'win_rate': float(metrics.get('win_rate', 0)),
                'avg_profit_pct': float(metrics.get('avg_profit_pct', 0)),
                'max_profit_pct': float(metrics.get('max_profit_pct', 0)),
                'max_loss_pct': float(metrics.get('max_loss_pct', 0)),
                'sharpe_ratio': float(metrics.get('sharpe_ratio', 0)),
                'sortino_ratio': float(metrics.get('sortino_ratio', 0)),
                'max_drawdown_pct': float(metrics.get('max_drawdown_pct', 0)),
                'profit_factor': float(metrics.get('profit_factor', 0)),
                'avg_holding_time_minutes': metrics.get('avg_holding_time_minutes', 0),
                'total_fees_usdt': float(metrics.get('total_fees_usdt', 0)),
                'capital_allocation': float(metrics.get('capital_allocation', 0)),
                'roi_annualized': float(metrics.get('roi_annualized', 0))
            }

            # Firebase
            if self.db:
                doc_ref = self.db.collection('strategy_metrics').document()
                doc_ref.set(strategy_data)

            # Backup local
            if self.local_backup:
                await self._save_local_backup('strategy_metrics', strategy_data)

            return True

        except Exception as e:
            logger.error(f"❌ Erreur log strategy metrics: {e}")
            return False

    async def log_system_metrics(self, metrics: Dict) -> bool:
        """Enregistre les métriques système"""
        try:
            system_data = {
                'timestamp': datetime.now().isoformat(),
                'cpu_usage_pct': float(metrics.get('cpu_usage_pct', 0)),
                'memory_usage_mb': float(metrics.get('memory_usage_mb', 0)),
                'disk_usage_pct': float(metrics.get('disk_usage_pct', 0)),
                'network_latency_ms': float(metrics.get('network_latency_ms', 0)),
                'api_calls_count': metrics.get('api_calls_count', 0),
                'api_errors_count': metrics.get('api_errors_count', 0),
                'active_strategies': metrics.get('active_strategies', []),
                'total_portfolio_value': float(metrics.get('total_portfolio_value', 0)),
                'bot_uptime_hours': float(metrics.get('bot_uptime_hours', 0))
            }

            # Firebase
            if self.db:
                doc_ref = self.db.collection('system_metrics').document()
                doc_ref.set(system_data)

            # Backup local
            if self.local_backup:
                await self._save_local_backup('system_metrics', system_data)

            return True

        except Exception as e:
            logger.error(f"❌ Erreur log system metrics: {e}")
            return False

    async def log_error(self, error_data: Dict) -> bool:
        """Enregistre les erreurs système"""
        try:
            error_log = {
                'timestamp': datetime.now().isoformat(),
                'level': error_data.get('level', 'ERROR'),
                'component': error_data.get('component', 'UNKNOWN'),
                'message': str(error_data.get('message', '')),
                'stack_trace': error_data.get('stack_trace', ''),
                'context': error_data.get('context', {}),
                'strategy': error_data.get('strategy', ''),
                'symbol': error_data.get('symbol', ''),
                'recovery_action': error_data.get('recovery_action', '')
            }

            # Firebase
            if self.db:
                doc_ref = self.db.collection('error_logs').document()
                doc_ref.set(error_log)

            # Backup local
            if self.local_backup:
                await self._save_local_backup('error_logs', error_log)

            return True

        except Exception as e:
            logger.error(f"❌ Erreur log error: {e}")
            return False

    async def get_performance_summary(self, days: int = 30) -> Dict:
        """Récupère un résumé des performances"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            if self.db:
                # Récupération depuis Firebase
                trades_ref = self.db.collection('trades')
                query = trades_ref.where('timestamp', '>=', start_date.isoformat())
                trades = [doc.to_dict() for doc in query.stream()]
            else:
                # Récupération depuis backup local
                trades = await self._load_local_backup('trades', start_date)

            if not trades:
                return {}

            # Calcul des métriques
            total_trades = len(trades)
            successful_trades = sum(1 for t in trades if t.get('success', False))
            total_profit = sum(t.get('profit_usdt', 0) for t in trades)
            
            strategy_breakdown = {}
            for trade in trades:
                strategy = trade.get('strategy', 'UNKNOWN')
                if strategy not in strategy_breakdown:
                    strategy_breakdown[strategy] = {
                        'trades': 0,
                        'profit': 0,
                        'success_rate': 0
                    }
                strategy_breakdown[strategy]['trades'] += 1
                strategy_breakdown[strategy]['profit'] += trade.get('profit_usdt', 0)

            # Calcul success rate par stratégie
            for strategy, data in strategy_breakdown.items():
                strategy_trades = [t for t in trades if t.get('strategy') == strategy]
                successful = sum(1 for t in strategy_trades if t.get('success', False))
                data['success_rate'] = successful / len(strategy_trades) if strategy_trades else 0

            return {
                'period_days': days,
                'total_trades': total_trades,
                'successful_trades': successful_trades,
                'success_rate': successful_trades / total_trades if total_trades > 0 else 0,
                'total_profit_usdt': total_profit,
                'avg_profit_per_trade': total_profit / total_trades if total_trades > 0 else 0,
                'strategy_breakdown': strategy_breakdown,
                'generated_at': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"❌ Erreur get performance summary: {e}")
            return {}

    async def _save_local_backup(self, collection: str, data: Dict):
        """Sauvegarde locale des données"""
        try:
            date_str = datetime.now().strftime('%Y-%m-%d')
            backup_file = f"{self.backup_dir}/{collection}_{date_str}.jsonl"
            
            with open(backup_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(data, ensure_ascii=False) + '\n')
                
        except Exception as e:
            logger.error(f"❌ Erreur backup local: {e}")

    async def _load_local_backup(self, collection: str, start_date: datetime) -> List[Dict]:
        """Charge les données depuis le backup local"""
        try:
            data = []
            # Chercher dans tous les fichiers depuis start_date
            current_date = start_date
            while current_date <= datetime.now():
                date_str = current_date.strftime('%Y-%m-%d')
                backup_file = f"{self.backup_dir}/{collection}_{date_str}.jsonl"
                
                if os.path.exists(backup_file):
                    with open(backup_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            try:
                                item = json.loads(line.strip())
                                item_date = datetime.fromisoformat(item['timestamp'].replace('Z', '+00:00'))
                                if item_date >= start_date:
                                    data.append(item)
                            except:
                                continue
                
                current_date += timedelta(days=1)
            
            return data
            
        except Exception as e:
            logger.error(f"❌ Erreur load local backup: {e}")
            return []

    async def export_data_to_csv(self, collection: str, days: int = 30) -> str:
        """Exporte les données en CSV"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            if self.db:
                # Export depuis Firebase
                collection_ref = self.db.collection(collection)
                query = collection_ref.where('timestamp', '>=', start_date.isoformat())
                data = [doc.to_dict() for doc in query.stream()]
            else:
                # Export depuis backup local
                data = await self._load_local_backup(collection, start_date)

            if not data:
                return ""

            # Conversion en DataFrame et export CSV
            df = pd.DataFrame(data)
            csv_filename = f"exports/{collection}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            os.makedirs('exports', exist_ok=True)
            df.to_csv(csv_filename, index=False)
            
            logger.info(f"✅ Export CSV créé: {csv_filename}")
            return csv_filename

        except Exception as e:
            logger.error(f"❌ Erreur export CSV: {e}")
            return ""

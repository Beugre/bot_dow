"""
Backtest du bot Dow Theory sur données historiques
Teste la stratégie sur 2-3 ans pour valider les performances (H1)
"""

import ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Tuple
import json
import matplotlib.pyplot as plt

import config_dow as config
from config_dow import (
    PAIRS,
    RISK_PERCENT,
    MAX_OPEN_TRADES,
    MAX_TRADES_PER_PAIR,
    TRIGGER_ZERO_R,
    LOCK_PROFIT_R,
    TRAILING_STEPS,
    MIN_STOP_PCT,
    MAX_STOP_PCT,
)
from market_structure import MarketStructure
from risk_manager_dow import RiskManager, Position

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Calcule l'ATR (Average True Range)
    """
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)

    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    return atr


class BacktestEngine:
    """Moteur de backtest pour la stratégie Dow Theory (H1)"""

    def __init__(
        self,
        initial_capital: float = 10000,
        start_date: str = "2022-01-01",
        end_date: str = None,
        pairs: List[str] = None,
        risk_percent: float = None,
        trigger_zero_r: float = None,
        lock_profit_r: float = None,
        trading_mode: str = "HYBRID",
    ):
        """
        Initialise le backtester

        Args:
            initial_capital: Capital de départ en USDC
            start_date: Date de début du backtest (YYYY-MM-DD)
            end_date: Date de fin (None = aujourd'hui)
            pairs: Liste des paires à tester (None = toutes)
            risk_percent: % de risque par trade (None = config)
            trigger_zero_r: R pour activer zero risk (None = config)
            lock_profit_r: R à verrouiller (None = config)
            trading_mode: "SWING", "SCALP" ou "HYBRID"
        """
        self.initial_capital = initial_capital
        self.start_date = start_date
        self.end_date = end_date or datetime.now().strftime("%Y-%m-%d")
        self.pairs = pairs or PAIRS
        self.risk_percent = risk_percent or RISK_PERCENT
        self.trigger_zero_r = trigger_zero_r or TRIGGER_ZERO_R
        self.lock_profit_r = lock_profit_r or LOCK_PROFIT_R
        self.trading_mode = trading_mode.upper()

        # Binance client
        self.exchange = ccxt.binance()

        # Components
        self.risk_manager = RiskManager(initial_capital)

        # Analyseur de structure (unique pour toute la durée du backtest)
        self.structure_analyzer = MarketStructure()

        # Structure anti-spam (complété par RiskManager)
        self.last_trade_structure: Dict[str, Dict] = {}

        # Limitation du nombre de trades par jour
        self.max_trades_per_day: int = getattr(config, "MAX_TRADES_PER_DAY", 3)
        self.daily_trade_counts: Dict[datetime.date, int] = {}

        # Résultats
        self.trades: List[Dict] = []
        self.equity_curve: List[Dict] = []
        self.daily_returns: List[float] = []

    # ------------------------------------------------------------------ #
    # Données historiques
    # ------------------------------------------------------------------ #
    def fetch_historical_data(self, pair: str) -> pd.DataFrame:
        """
        Récupère les données historiques H1
        """
        logger.info(f"📥 Téléchargement {pair} en H4...")

        start_ts = int(datetime.strptime(self.start_date, "%Y-%m-%d").timestamp() * 1000)
        end_ts = int(datetime.strptime(self.end_date, "%Y-%m-%d").timestamp() * 1000)

        all_h4 = []
        current_ts = start_ts

        while current_ts < end_ts:
            try:
                ohlcv = self.exchange.fetch_ohlcv(pair, "4h", since=current_ts, limit=1000)

                if not ohlcv:
                    break

                all_h4.extend(ohlcv)
                current_ts = ohlcv[-1][0] + 14400000  # +4h en ms

                logger.info(f"   H4: {len(all_h4)} bougies")
            except Exception as e:
                logger.error(f"Erreur fetch H4: {e}")
                break

        if not all_h4:
            return pd.DataFrame(
                columns=["timestamp", "open", "high", "low", "close", "volume", "datetime"]
            )

        df_h4 = pd.DataFrame(
            all_h4,
            columns=["timestamp", "open", "high", "low", "close", "volume"],
        )
        df_h4["datetime"] = pd.to_datetime(df_h4["timestamp"], unit="ms")

        logger.info(f"✅ {pair}: {len(df_h4)} H4 chargées")
        return df_h4

    # ------------------------------------------------------------------ #
    # Boucle principale
    # ------------------------------------------------------------------ #
    def run_backtest(self) -> Dict:
        """
        Execute le backtest complet (H1)
        """
        logger.info("=" * 70)
        logger.info("🚀 BACKTEST DOW THEORY (H4)")
        logger.info(f"📅 Période: {self.start_date} → {self.end_date}")
        logger.info(f"💰 Capital initial: {self.initial_capital} USDC")
        logger.info(f"📊 Paires: {', '.join(self.pairs)}")
        logger.info(f"⚙️ Risque: {self.risk_percent}% | Zero R: {self.trigger_zero_r}R → {self.lock_profit_r}R")
        logger.info("=" * 70)

        # Télécharger toutes les données H1
        historical_data: Dict[str, pd.DataFrame] = {}
        for pair in self.pairs:
            try:
                df_h1 = self.fetch_historical_data(pair)
                if not df_h1.empty:
                    historical_data[pair] = df_h1
            except Exception as e:
                logger.error(f"❌ Impossible de charger {pair}: {e}")
                continue

        if not historical_data:
            logger.error("❌ Aucune donnée chargée")
            return {}

        logger.info("\n🔄 Simulation des trades H4...")

        # Bornes communes aux paires
        min_date = max(data["datetime"].min() for data in historical_data.values())
        max_date = min(data["datetime"].max() for data in historical_data.values())

        logger.info(f"📅 Simulation: {min_date} → {max_date}")

        lookback_hours = 600 * 4  # 600 bougies H4 = 2400h = 100 jours
        current_time = min_date + timedelta(hours=lookback_hours)

        logger.info(f"⏭️ Démarrage simulation après {lookback_hours // 4} bougies H4 de lookback : {current_time}")

        h4_count = 0

        while current_time <= max_date:
            h4_count += 1

            # Mise à jour des positions ouvertes
            self._update_positions(current_time, historical_data)

            # Recherche de nouveaux signaux d'entrée
            for pair in self.pairs:
                if pair not in historical_data:
                    continue
                self._check_entry_signal(pair, current_time, historical_data[pair])

            # Enregistrer l'équity une fois par jour (toutes les 6 bougies H4)
            if h4_count % 6 == 0:
                self.equity_curve.append(
                    {
                        "datetime": current_time,
                        "equity": self.risk_manager.current_capital,
                        "trades": len(self.trades),
                    }
                )

            current_time += timedelta(hours=4)

        results = self._calculate_metrics()
        self._print_summary(results)
        return results

    # ------------------------------------------------------------------ #
    # Gestion des entrées
    # ------------------------------------------------------------------ #
    def _can_open_new_trade(
        self,
        symbol: str,
        current_time: datetime,
        side: str,
        structure_id: str = None,
    ) -> Tuple[bool, str]:
        """
        Vérifie si on peut ouvrir un nouveau trade (global + par paire + par jour + structure).
        """

        # 1) RiskManager : limites globales + par paire + structure
        ok, reason = self.risk_manager.can_open_position(symbol, side=side, structure_id=structure_id)
        if not ok:
            return False, reason

        # 2) Limite de trades par jour (tous symboles confondus)
        day = current_time.date()
        day_count = self.daily_trade_counts.get(day, 0)
        if day_count >= self.max_trades_per_day:
            return False, f"❌ Max trades/jour atteint: {day_count}/{self.max_trades_per_day}"

        return True, "✅ OK"

    def _check_entry_signal(self, pair: str, current_time: datetime, data: pd.DataFrame):
        """
        Vérifie un signal d’entrée (H1) pour une paire donnée.
        """

        # Récupère toutes les bougies jusqu'à current_time
        df_h1 = data[data["datetime"] <= current_time].copy()

        # Assez d'historique ?
        min_len = max(200, 200 + 14)  # pour EMA200 + ATR14
        if len(df_h1) < min_len:
            return

        # Calcul indicateurs (EMA, ATR) sur tout l'historique dispo
        df_h1["ema50"] = df_h1["close"].ewm(span=50, adjust=False).mean()
        df_h1["ema200"] = df_h1["close"].ewm(span=200, adjust=False).mean()
        df_h1["atr14"] = compute_atr(df_h1, period=14)

        last = df_h1.iloc[-1]
        current_price = float(last["close"])
        ema50 = float(last["ema50"])
        ema200 = float(last["ema200"])
        atr = float(last["atr14"])

        if np.isnan(ema50) or np.isnan(ema200) or np.isnan(atr):
            return

        # Filtre volatilité : ignore si ATR trop faible (marché endormi)
        atr_pct = (atr / current_price) * 100
        min_atr_pct = getattr(config, "MIN_ATR_PERCENT", 0.25)
        if atr_pct < min_atr_pct:
            return

        # Analyse de structure (Dow Theory)
        analysis = self.structure_analyzer.analyze(df_h1)
        if not analysis:
            return

        structure_id = analysis.get("structure_id")
        macro_bias = analysis.get("macro_bias")
        trend = analysis.get("trend")
        
        # Extraction des niveaux pour logs trade (stockés pour _enter_trade)
        last_hh = analysis.get("last_hh")
        last_hl = analysis.get("last_hl")
        last_lh = analysis.get("last_lh")
        last_ll = analysis.get("last_ll")

        # ----------------------------- #
        # SWING LONG (trend following)
        # ----------------------------- #
        long_ok = (
            macro_bias == "BULLISH"
            and trend == "UPTREND"
            and current_price > ema50 > ema200
        )

        # ----------------------------- #
        # SWING SHORT (trend following)
        # ----------------------------- #
        short_ok = (
            macro_bias == "BEARISH"
            and trend == "DOWNTREND"
            and current_price < ema50 < ema200
        )

        # Mode HYBRID : swing prioritaire, avec gestion active du risque (zero-risk + trailing)
        try:
            # BUY (SWING)
            if long_ok:
                buy_signal, stop_loss_buy, target = self.structure_analyzer.check_buy_signal(analysis)
                
                if buy_signal and stop_loss_buy is not None:
                    can_open, reason = self._can_open_new_trade(
                        pair,
                        current_time=current_time,
                        side="LONG",
                        structure_id=structure_id,
                    )
                    if can_open:
                        self._enter_trade(
                            pair,
                            "LONG",
                            current_price,
                            stop_loss_buy,
                            current_time,
                            structure_id,
                            analysis,
                        )
                    else:
                        logger.debug(f"[ENTRY BLOCKED LONG {pair}] {reason}")
                else:
                    logger.debug(f"[NO LONG SIGNAL {pair}] Signal={buy_signal}, SL={'%.2f' % stop_loss_buy if stop_loss_buy else 'None'}")
                return  # priorité au long si signal dispo

            # SELL (SWING)
            if short_ok:
                sell_signal, stop_loss_sell, target = self.structure_analyzer.check_sell_signal(analysis)
                
                if sell_signal and stop_loss_sell is not None:
                    can_open, reason = self._can_open_new_trade(
                        pair,
                        current_time=current_time,
                        side="SHORT",
                        structure_id=structure_id,
                    )
                    if can_open:
                        self._enter_trade(
                            pair,
                            "SHORT",
                            current_price,
                            stop_loss_sell,
                            current_time,
                            structure_id,
                            analysis,
                        )
                    else:
                        logger.debug(f"[ENTRY BLOCKED SHORT {pair}] {reason}")
                else:
                    logger.debug(f"[NO SHORT SIGNAL {pair}] Signal={sell_signal}, SL={'%.2f' % stop_loss_sell if stop_loss_sell else 'None'}")
                return

        except Exception as e:
            logger.error(f"Erreur analyse {pair} @ {current_time}: {e}")

    def _enter_trade(
        self,
        pair: str,
        side: str,
        entry_price: float,
        stop_loss: float,
        entry_time: datetime,
        structure_id: str = None,
        analysis: dict = None,
    ):
        """
        Ouvre une position
        """

        # Calcul du % de stop
        stop_pct = abs(entry_price - stop_loss) / entry_price * 100
        
        # Extraction des détails de structure pour logs
        if analysis:
            last_hh = analysis.get("last_HH")
            last_hl = analysis.get("last_HL")
            last_lh = analysis.get("last_LH")
            last_ll = analysis.get("last_LL")
            trend = analysis.get("trend")
            macro = analysis.get("macro_bias")
            
            # Log détaillé pour LONG
            if side == "LONG" and last_hh and last_hl:
                distance_hh_hl = abs(last_hh.price - last_hl.price) / last_hh.price * 100
                logger.info(
                    f"\n{'='*80}\n"
                    f"🚀 OUVERTURE POSITION LONG {pair}\n"
                    f"{'='*80}\n"
                    f"📅 Date: {entry_time.strftime('%Y-%m-%d %H:%M')}\n"
                    f"💰 Prix entrée: {entry_price:.4f}\n"
                    f"🛑 Stop Loss: {stop_loss:.4f} ({stop_pct:.2f}%)\n"
                    f"🎯 Structure ID: {structure_id}\n"
                    f"\n📊 STRUCTURE DOW:\n"
                    f"   🔼 HH (Higher High): {last_hh.price:.4f} @ idx {last_hh.index} ({last_hh.label})\n"
                    f"   🔽 HL (Higher Low):  {last_hl.price:.4f} @ idx {last_hl.index} ({last_hl.label})\n"
                    f"   📏 Distance HH-HL: {distance_hh_hl:.2f}%\n"
                    f"\n🎯 CONTEXTE:\n"
                    f"   📈 Trend: {trend}\n"
                    f"   🌍 Macro Bias: {macro}\n"
                    f"   💵 Capital: {self.risk_manager.current_capital:.2f} USDC\n"
                    f"{'='*80}"
                )
            # Log détaillé pour SHORT
            elif side == "SHORT" and last_lh and last_ll:
                distance_lh_ll = abs(last_lh.price - last_ll.price) / last_lh.price * 100
                logger.info(
                    f"\n{'='*80}\n"
                    f"🔻 OUVERTURE POSITION SHORT {pair}\n"
                    f"{'='*80}\n"
                    f"📅 Date: {entry_time.strftime('%Y-%m-%d %H:%M')}\n"
                    f"💰 Prix entrée: {entry_price:.4f}\n"
                    f"🛑 Stop Loss: {stop_loss:.4f} ({stop_pct:.2f}%)\n"
                    f"🎯 Structure ID: {structure_id}\n"
                    f"\n📊 STRUCTURE DOW:\n"
                    f"   🔽 LH (Lower High): {last_lh.price:.4f} @ idx {last_lh.index} ({last_lh.label})\n"
                    f"   🔼 LL (Lower Low):  {last_ll.price:.4f} @ idx {last_ll.index} ({last_ll.label})\n"
                    f"   📏 Distance LH-LL: {distance_lh_ll:.2f}%\n"
                    f"\n🎯 CONTEXTE:\n"
                    f"   📉 Trend: {trend}\n"
                    f"   🌍 Macro Bias: {macro}\n"
                    f"   💵 Capital: {self.risk_manager.current_capital:.2f} USDC\n"
                    f"{'='*80}"
                )
            # Log simplifié si structure incomplète
            else:
                logger.info(
                    f"\n{'='*80}\n"
                    f"{'🚀' if side == 'LONG' else '🔻'} OUVERTURE POSITION {side} {pair}\n"
                    f"{'='*80}\n"
                    f"📅 Date: {entry_time.strftime('%Y-%m-%d %H:%M')}\n"
                    f"💰 Prix entrée: {entry_price:.4f}\n"
                    f"🛑 Stop Loss: {stop_loss:.4f} ({stop_pct:.2f}%)\n"
                    f"🎯 Structure ID: {structure_id}\n"
                    f"\n⚠️ STRUCTURE DOW: Incomplète\n"
                    f"   HH: {'✅' if last_hh else '❌'} | HL: {'✅' if last_hl else '❌'}\n"
                    f"   LH: {'✅' if last_lh else '❌'} | LL: {'✅' if last_ll else '❌'}\n"
                    f"\n🎯 CONTEXTE:\n"
                    f"   Trend: {trend or 'N/A'}\n"
                    f"   Macro Bias: {macro or 'N/A'}\n"
                    f"   💵 Capital: {self.risk_manager.current_capital:.2f} USDC\n"
                    f"{'='*80}"
                )

        # Bornes de stop (sécurité supplémentaires)
        if stop_pct < MIN_STOP_PCT or stop_pct > MAX_STOP_PCT:
            logger.debug(
                f"[NO ENTRY {pair} {side}] stop_pct hors bornes: {stop_pct:.2f}% "
                f"({MIN_STOP_PCT:.2f}%–{MAX_STOP_PCT:.2f}%)"
            )
            return

        # Taille de position via RiskManager
        qty = self.risk_manager.calculate_position_size(entry_price, stop_loss, side)
        if qty <= 0:
            logger.debug(f"[NO ENTRY {pair} {side}] qty calculée <= 0")
            return

        # Enregistrer dernière structure tradée côté BacktestEngine (en plus de RiskManager)
        if structure_id:
            self.last_trade_structure[pair] = {
                "type": side,
                "structure_id": structure_id,
                "time": entry_time,
            }

        # Création de la position via RiskManager
        position = self.risk_manager.add_position(
            symbol=pair,
            side=side,
            entry_price=entry_price,
            quantity=qty,
            stop_loss=stop_loss,
            structure_type=structure_id,
            entry_time=entry_time,
        )

        # Incrément compteur de trades du jour
        day = entry_time.date()
        self.daily_trade_counts[day] = self.daily_trade_counts.get(day, 0) + 1

        logger.info(f"📈 {side} {pair} @ {entry_price:.4f} | SL {stop_loss:.4f} | Qty {qty}")

    # ------------------------------------------------------------------ #
    # Gestion des positions
    # ------------------------------------------------------------------ #
    def _update_positions(self, current_time: datetime, historical_data: Dict[str, pd.DataFrame]):
        """
        Met à jour trailing SL, zero risk, et ferme les positions si nécessaire (H1)
        """

        positions_to_close = []

        for pair, pos_list in list(self.risk_manager.positions.items()):
            df = historical_data.get(pair)
            if df is None or df.empty:
                continue

            # Bougie courante
            df_pair = df[df["datetime"] <= current_time]
            if df_pair.empty:
                continue

            current_row = df_pair.iloc[-1]
            current_price = float(current_row["close"])
            current_high = float(current_row["high"])
            current_low = float(current_row["low"])

            for position in list(pos_list):
                # Mettre à jour extrêmes
                if position.side == "LONG":
                    position.highest_price = max(position.highest_price, current_high)
                else:
                    position.lowest_price = min(position.lowest_price, current_low)

                # MAJ via RiskManager (zero-risk, trailing, etc.)
                self.risk_manager.update_position(position, current_price)

                # Vérification du stop
                if position.side == "LONG" and current_low <= position.current_sl:
                    positions_to_close.append((pair, position, position.current_sl, current_time))
                elif position.side == "SHORT" and current_high >= position.current_sl:
                    positions_to_close.append((pair, position, position.current_sl, current_time))

        # Clôture des positions dont le stop est touché
        for pair, position, exit_price, exit_time in positions_to_close:
            pnl = position.get_pnl(exit_price)
            r_mul = position.get_profit_r(exit_price)

            # Retirer d'abord des positions ouvertes
            if pair in self.risk_manager.positions:
                self.risk_manager.positions[pair] = [
                    p for p in self.risk_manager.positions[pair] if p != position
                ]
                if not self.risk_manager.positions[pair]:
                    del self.risk_manager.positions[pair]

            # Fermer via RiskManager (mise à jour capital + historique)
            self.risk_manager.close_position(position, exit_price, "stop_hit")

            trade = {
                "pair": pair,
                "side": position.side,
                "entry_price": position.entry_price,
                "exit_price": exit_price,
                "quantity": position.quantity,
                "pnl": pnl,
                "r_multiple": r_mul,
                "entry_time": position.entry_time,
                "exit_time": exit_time,
                "duration_hours": (exit_time - position.entry_time).total_seconds() / 3600,
                "zero_risk_activated": position.zero_risk_activated,
            }

            self.trades.append(trade)

            logger.info(
                f"📊 CLOSE {pair} {position.side} @ {exit_price:.4f} | "
                f"PnL {pnl:+.2f} | {r_mul:+.2f}R | Capital {self.risk_manager.current_capital:.2f}"
            )

    # ------------------------------------------------------------------ #
    # Statistiques
    # ------------------------------------------------------------------ #
    def _calculate_metrics(self) -> Dict:
        """
        Calcule les métriques globales du backtest
        """

        if not self.trades:
            return {"error": "Aucun trade exécuté"}

        df = pd.DataFrame(self.trades)

        total_trades = len(df)
        winners = df[df.pnl > 0]
        losers = df[df.pnl < 0]

        win_rate = len(winners) / total_trades * 100
        avg_win = winners.pnl.mean() if len(winners) else 0
        avg_loss = losers.pnl.mean() if len(losers) else 0

        total_pnl = df.pnl.sum()
        total_return = total_pnl / self.initial_capital * 100

        gross_profit = winners.pnl.sum()
        gross_loss = abs(losers.pnl.sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        expectancy = (win_rate / 100 * avg_win) + ((100 - win_rate) / 100 * avg_loss)

        # Max drawdown
        equity = [self.initial_capital]
        for pnl in df.pnl:
            equity.append(equity[-1] + pnl)

        peak = equity[0]
        max_dd = 0
        for e in equity:
            if e > peak:
                peak = e
            dd = (peak - e) / peak * 100
            if dd > max_dd:
                max_dd = dd

        avg_r = df.r_multiple.mean()
        best_r = df.r_multiple.max()
        worst_r = df.r_multiple.min()

        avg_duration = df.duration_hours.mean()

        zero_risk_pct = len(df[df.zero_risk_activated == True]) / total_trades * 100

        by_pair = df.groupby("pair").agg({"pnl": ["count", "sum", "mean"]}).round(2)
        
        # Convertir by_pair en dict simple (JSON-serializable)
        by_pair_dict = {}
        for pair in by_pair.index:
            by_pair_dict[pair] = {
                "count": int(by_pair.loc[pair, ("pnl", "count")]),
                "sum": float(by_pair.loc[pair, ("pnl", "sum")]),
                "mean": float(by_pair.loc[pair, ("pnl", "mean")])
            }

        return {
            "total_trades": total_trades,
            "winning_trades": len(winners),
            "losing_trades": len(losers),
            "win_rate": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "total_pnl": total_pnl,
            "total_return_pct": total_return,
            "profit_factor": profit_factor,
            "expectancy": expectancy,
            "max_drawdown_pct": max_dd,
            "avg_r_multiple": avg_r,
            "best_trade_r": best_r,
            "worst_trade_r": worst_r,
            "avg_duration_hours": avg_duration,
            "zero_risk_activated_pct": zero_risk_pct,
            "final_capital": self.risk_manager.current_capital,
            "by_pair": by_pair_dict,
            "trades": df.to_dict("records"),
        }

    def _print_summary(self, results: Dict):
        """
        Affiche le résumé des performances
        """

        if "error" in results:
            logger.error(f"❌ {results['error']}")
            return

        print("\n" + "=" * 70)
        print("📊 RÉSULTATS DU BACKTEST (H1)")
        print("=" * 70)

        print("\n💰 PERFORMANCE:")
        print(f"   Capital initial : {self.initial_capital:.2f} USDC")
        print(f"   Capital final   : {results['final_capital']:.2f} USDC")
        print(f"   PnL total       : {results['total_pnl']:+.2f} USDC ({results['total_return_pct']:+.2f}%)")
        print(f"   Max Drawdown    : {results['max_drawdown_pct']:.2f}%")

        print("\n📈 TRADES:")
        print(f"   Total trades    : {results['total_trades']}")
        print(f"   Gagnants        : {results['winning_trades']} ({results['win_rate']:.1f}%)")
        print(f"   Perdants        : {results['losing_trades']}")
        print(f"   Avg Win         : {results['avg_win']:.2f} USDC")
        print(f"   Avg Loss        : {results['avg_loss']:.2f} USDC")
        print(f"   Profit Factor   : {results['profit_factor']:.2f}")
        print(f"   Expectancy      : {results['expectancy']:.2f} USDC")

        print("\n📊 R-MULTIPLES:")
        print(f"   Moyenne         : {results['avg_r_multiple']:+.2f}R")
        print(f"   Meilleur        : {results['best_trade_r']:+.2f}R")
        print(f"   Pire            : {results['worst_trade_r']:+.2f}R")

        print("\n⏱️ DURÉE:")
        print(
            f"   Avg hold time   : {results['avg_duration_hours']:.1f}h "
            f"({results['avg_duration_hours'] / 24:.1f}j)"
        )

        print("\n🛡️ ZERO RISK:")
        print(f"   Activé sur      : {results['zero_risk_activated_pct']:.1f}% des trades")

        print("\n📋 PAR PAIRE:")
        df_trades = pd.DataFrame(results["trades"])
        for pair in df_trades["pair"].unique():
            t = df_trades[df_trades["pair"] == pair]
            pnl = t.pnl.sum()
            wr = len(t[t.pnl > 0]) / len(t) * 100
            print(f"   {pair:12} {len(t):3} trades | Win: {wr:5.1f}% | PnL: {pnl:+8.2f}")

        print("=" * 70)

    # ------------------------------------------------------------------ #
    # Graphiques
    # ------------------------------------------------------------------ #
    def plot_results(self):
        """Graphiques du backtest"""

        if not self.trades:
            logger.warning("Aucun trade à tracer")
            return

        df = pd.DataFrame(self.trades)

        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle("Résultats Backtest Dow Theory (H4)", fontsize=16, fontweight="bold")

        # Equity curve
        equity = [self.initial_capital]
        for pnl in df.pnl:
            equity.append(equity[-1] + pnl)

        ax1 = axes[0, 0]
        ax1.plot(equity, linewidth=2)
        ax1.set_title("Équity Curve")
        ax1.grid(True)

        # Distribution des R
        ax2 = axes[0, 1]
        ax2.hist(df.r_multiple, bins=30)
        ax2.set_title("Distribution des R-multiples")

        # PnL cumulé
        df["cum_pnl"] = df.pnl.cumsum()
        ax3 = axes[1, 0]
        ax3.plot(df.exit_time, df.cum_pnl)
        ax3.set_title("PnL Cumulé")
        ax3.grid(True)

        # Win rate par paire
        ax4 = axes[1, 1]
        win = []
        pairs = []
        for pair in df.pair.unique():
            t = df[df.pair == pair]
            wr = len(t[t.pnl > 0]) / len(t) * 100
            win.append(wr)
            pairs.append(pair)
        ax4.barh(pairs, win)
        ax4.set_title("Win Rate par Paire")

        plt.tight_layout()
        filename = f"backtest_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        plt.savefig(filename, dpi=300)
        logger.info(f"📊 Graphiques sauvegardés: {filename}")
        plt.show()


def main():
    """Exécution du backtest (H1)"""

    print("\n" + "=" * 70)
    print("🔬 BACKTEST BOT DOW THEORY — H1 (HYBRID MODE)")
    print("=" * 70)

    backtest = BacktestEngine(
        initial_capital=10000,
        start_date="2023-01-01",
        pairs=PAIRS,
        risk_percent=RISK_PERCENT,
        trigger_zero_r=TRIGGER_ZERO_R,
        lock_profit_r=LOCK_PROFIT_R,
        trading_mode="HYBRID",
    )

    results = backtest.run_backtest()

    if results and "error" not in results:
        filename = f"backtest_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        results_json = results.copy()
        if "trades" in results_json:
            for t in results_json["trades"]:
                if isinstance(t.get("entry_time"), datetime):
                    t["entry_time"] = t["entry_time"].isoformat()
                if isinstance(t.get("exit_time"), datetime):
                    t["exit_time"] = t["exit_time"].isoformat()

        with open(filename, "w") as f:
            json.dump(results_json, f, indent=2)

        logger.info(f"💾 Résultats sauvegardés: {filename}")

        backtest.plot_results()

    print("\n✅ Backtest terminé !\n")


if __name__ == "__main__":
    main()

"""
Gestionnaire de positions avec calcul de taille basé sur risk%
"""
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import config_dow as config


@dataclass
class Position:
    """Représente une position ouverte"""
    symbol: str
    side: str  # "LONG" ou "SHORT"
    entry_price: float
    quantity: float
    stop_loss: float
    entry_time: datetime
    initial_r: float  # Distance initiale du stop en $
    zero_risk_activated: bool = False
    highest_price: float = 0.0  # Pour trailing (LONG)
    lowest_price: float = float("inf")  # Pour trailing (SHORT)
    current_sl: float = 0.0  # SL actuel (après trailing)

    def __post_init__(self):
        """Initialisation après création"""
        self.current_sl = self.stop_loss
        if self.side == "LONG":
            self.highest_price = self.entry_price
        else:
            self.lowest_price = self.entry_price

    def get_profit_r(self, current_price: float) -> float:
        """
        Calcule le profit en R

        Args:
            current_price: Prix actuel

        Returns:
            Profit en multiples de R
        """
        if self.side == "LONG":
            return (current_price - self.entry_price) / self.initial_r
        else:
            return (self.entry_price - current_price) / self.initial_r

    def get_pnl(self, current_price: float) -> float:
        """
        Calcule le P&L en $

        Args:
            current_price: Prix actuel

        Returns:
            P&L en dollars
        """
        if self.side == "LONG":
            return (current_price - self.entry_price) * self.quantity
        else:
            return (self.entry_price - current_price) * self.quantity


class RiskManager:
    """
    Gère le money management et le calcul des tailles de position
    """

    def __init__(self, initial_capital: float):
        """
        Args:
            initial_capital: Capital initial en USDC
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.positions: Dict[str, List[Position]] = {}  # {symbol: [positions]}
        self.closed_trades: List[Dict] = []

        # 🔥 ANTI-SPAM CRITIQUE : Tracking de la dernière structure tradée par symbole
        # {symbol: {"type": "BUY"/"SELL", "structure_id": str, "timestamp": datetime}}
        self.last_structure_traded: Dict[str, Dict] = {}

    # ------------------------------------------------------------------ #
    # Taille de position
    # ------------------------------------------------------------------ #
    def calculate_position_size(
        self,
        entry_price: float,
        stop_loss: float,
        side: str,
    ) -> float:
        """
        Calcule la taille de position basée sur le risk%

        Args:
            entry_price: Prix d'entrée
            stop_loss: Prix du stop loss
            side: "LONG" ou "SHORT"

        Returns:
            Quantité à acheter/vendre
        """
        # Montant à risquer
        risk_amount = self.current_capital * (config.RISK_PERCENT / 100)

        # Distance du stop
        if side == "LONG":
            stop_distance = entry_price - stop_loss
        else:
            stop_distance = stop_loss - entry_price

        if stop_distance <= 0:
            return 0.0

        # Quantité = Risk / Stop Distance
        quantity = risk_amount / stop_distance

        return quantity

    # ------------------------------------------------------------------ #
    # Vérifications avant ouverture
    # ------------------------------------------------------------------ #
    def can_open_position(
        self,
        symbol: str,
        side: Optional[str] = None,
        structure_id: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        🔥 VÉRIFICATIONS CRITIQUES avant d'ouvrir une position

        Args:
            symbol: Symbole de la paire
            side: "LONG" ou "SHORT" (optionnel)
            structure_id: ID unique de la structure (ex: "LONG_45632.12_44103.55")

        Returns:
            (can_open, reason)
        """
        # 🔥 CHECK 1: MAX_TRADES_PER_SYMBOL (1 seul trade par paire à la fois)
        pair_positions = len(self.positions.get(symbol, []))
        if pair_positions >= config.MAX_TRADES_PER_PAIR:
            return (
                False,
                f"❌ Déjà {pair_positions} position(s) sur {symbol} "
                f"(max: {config.MAX_TRADES_PER_PAIR})",
            )

        # 🔥 CHECK 2: MAX_GLOBAL_TRADES (limite totale)
        total_positions = sum(len(positions) for positions in self.positions.values())
        if total_positions >= config.MAX_OPEN_TRADES:
            return (
                False,
                f"❌ Max trades globaux atteint: {total_positions}/{config.MAX_OPEN_TRADES}",
            )

        # 🔥 CHECK 3: MÊME STRUCTURE (éviter doublons sur HH/HL identiques)
        if structure_id and symbol in self.last_structure_traded:
            last_struct_id = self.last_structure_traded[symbol].get("structure_id")
            if structure_id == last_struct_id:
                return (
                    False,
                    f"❌ Structure identique déjà tradée sur {symbol} ({structure_id})",
                )

        # 🔥 CHECK 3b: LIMITE SHORTS (max 1 SHORT simultané)
        if side == "SHORT":
            current_shorts = self.total_shorts()
            if current_shorts >= 1:
                return (
                    False,
                    f"❌ Max 1 SHORT simultané (actuellement: {current_shorts})",
                )

        # 🔥 CHECK 4: Risque total
        total_risk = self.get_total_risk_exposed()
        if total_risk >= config.MAX_TOTAL_RISK_PCT:
            return (
                False,
                f"❌ Risque total max atteint: {total_risk:.1f}%/"
                f"{config.MAX_TOTAL_RISK_PCT}%",
            )

        return True, "✅ OK"

    def get_total_risk_exposed(self) -> float:
        """
        Calcule le risque total engagé (en % du capital)

        Returns:
            Risque total en %
        """
        total_risk = 0.0

        for _, positions in self.positions.items():
            for pos in positions:
                # Si zero risk activé, pas de risque
                if pos.zero_risk_activated:
                    continue

                # Risque = distance au SL * quantité
                if pos.side == "LONG":
                    risk = (pos.entry_price - pos.current_sl) * pos.quantity
                else:
                    risk = (pos.current_sl - pos.entry_price) * pos.quantity

                total_risk += (risk / self.current_capital) * 100

        return total_risk

    def total_shorts(self) -> int:
        """
        🔥 Compte le nombre de positions SHORT ouvertes
        """
        count = 0
        for _, positions in self.positions.items():
            for pos in positions:
                if pos.side == "SHORT":
                    count += 1
        return count

    # ------------------------------------------------------------------ #
    # Ajout / update / clôture de position
    # ------------------------------------------------------------------ #
    def add_position(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        quantity: float,
        stop_loss: float,
        structure_type: Optional[str] = None,
        entry_time: Optional[datetime] = None,
    ) -> Position:
        """
        Ajoute une position au portfolio

        Args:
            symbol: Symbole de la paire
            side: "LONG" ou "SHORT"
            entry_price: Prix d'entrée
            quantity: Quantité
            stop_loss: Prix du stop loss
            structure_type: Type de structure (HH, HL, LH, LL) ou ID complet
            entry_time: Date/heure simulée d'entrée (backtest). Si None → datetime.now()

        Returns:
            Position créée
        """
        # Calculer R initial
        if side == "LONG":
            initial_r = entry_price - stop_loss
        else:
            initial_r = stop_loss - entry_price

        position = Position(
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            quantity=quantity,
            stop_loss=stop_loss,
            entry_time=entry_time or datetime.now(),
            initial_r=initial_r,
        )

        if symbol not in self.positions:
            self.positions[symbol] = []

        self.positions[symbol].append(position)

        # 🔥 TRACKER LA STRUCTURE
        self.last_structure_traded[symbol] = {
            "type": side,
            "structure_id": structure_type,
            "timestamp": datetime.now(),
        }

        return position

    def update_position(self, position: Position, current_price: float):
        """
        Met à jour une position (trailing, zero risk, etc.)
        """
        # Mettre à jour highest/lowest
        if position.side == "LONG":
            position.highest_price = max(position.highest_price, current_price)
        else:
            position.lowest_price = min(position.lowest_price, current_price)

        # Calculer profit en R
        profit_r = position.get_profit_r(current_price)

        # Activer zero risk à +1R
        if not position.zero_risk_activated and profit_r >= config.TRIGGER_ZERO_R:
            self._activate_zero_risk(position)

        # Trailing si activé
        if getattr(config, "TRAILING_ENABLED", True) and position.zero_risk_activated:
            self._apply_trailing(position, current_price, profit_r)

    def _activate_zero_risk(self, position: Position):
        """
        Active le zero risk à entry_price exact
        """
        position.current_sl = position.entry_price
        position.zero_risk_activated = True

    def _apply_trailing(self, position: Position, current_price: float, profit_r: float):
        """
        Applique le trailing stop progressif
        """
        for trigger_r, lock_r in config.TRAILING_STEPS:
            if profit_r >= trigger_r:
                if position.side == "LONG":
                    new_sl = position.entry_price + (lock_r * position.initial_r)
                    if new_sl > position.current_sl:
                        position.current_sl = new_sl
                else:
                    new_sl = position.entry_price - (lock_r * position.initial_r)
                    if new_sl < position.current_sl:
                        position.current_sl = new_sl

    def check_stop_hit(self, position: Position, current_price: float) -> bool:
        """
        Vérifie si le stop loss est touché
        """
        if position.side == "LONG":
            return current_price <= position.current_sl
        else:
            return current_price >= position.current_sl

    def close_position(self, position: Position, exit_price: float, reason: str):
        """
        Ferme une position et met à jour le capital
        """
        pnl = position.get_pnl(exit_price)
        profit_r = position.get_profit_r(exit_price)

        self.current_capital += pnl

        trade = {
            "symbol": position.symbol,
            "side": position.side,
            "entry_price": position.entry_price,
            "exit_price": exit_price,
            "quantity": position.quantity,
            "entry_time": position.entry_time,
            "exit_time": datetime.now(),
            "pnl": pnl,
            "profit_r": profit_r,
            "reason": reason,
            "zero_risk_activated": position.zero_risk_activated,
        }

        self.closed_trades.append(trade)

        if position.symbol in self.positions:
            self.positions[position.symbol].remove(position)
            if not self.positions[position.symbol]:
                del self.positions[position.symbol]

    # ------------------------------------------------------------------ #
    # Stats portfolio
    # ------------------------------------------------------------------ #
    def get_stats(self) -> Dict:
        """
        Retourne les statistiques du portfolio
        """
        total_trades = len(self.closed_trades)
        winning_trades = [t for t in self.closed_trades if t["pnl"] > 0]
        losing_trades = [t for t in self.closed_trades if t["pnl"] <= 0]

        total_pnl = sum(t["pnl"] for t in self.closed_trades)
        win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0

        avg_win = (
            sum(t["pnl"] for t in winning_trades) / len(winning_trades)
            if winning_trades
            else 0
        )
        avg_loss = (
            sum(t["pnl"] for t in losing_trades) / len(losing_trades)
            if losing_trades
            else 0
        )

        profit_factor = (
            abs(sum(t["pnl"] for t in winning_trades) / sum(t["pnl"] for t in losing_trades))
            if losing_trades and sum(t["pnl"] for t in losing_trades) != 0
            else 0
        )

        return {
            "initial_capital": self.initial_capital,
            "current_capital": self.current_capital,
            "total_pnl": total_pnl,
            "return_pct": (total_pnl / self.initial_capital * 100)
            if self.initial_capital != 0
            else 0,
            "total_trades": total_trades,
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": profit_factor,
            "open_positions": sum(len(p) for p in self.positions.values()),
            "risk_exposed": self.get_total_risk_exposed(),
        }

"""
Analyse de la structure de marché (Market Structure) et génération de signaux — Timeframe H4
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from swing_detector import SwingDetector, Swing
import config_dow as config
import logging


class MarketStructure:
    """
    Gère l'analyse complète de la structure de marché en H4
    """
    
    def __init__(self):
        self.swing_detector = SwingDetector(lookback=config.SWING_LOOKBACK)
        self.logger = logging.getLogger(__name__)

    # ----------------------------------------------------------------------
    # 🔥 MACRO BIAS (H1)
    # ----------------------------------------------------------------------
    def get_macro_bias(self, df_h1: pd.DataFrame, current_price: float) -> str:
        """
        Détermine le biais macro basé sur les swings H1.
        
        Logique :
            - 2 ou 3 swings sur les 3 derniers → BULLISH ou BEARISH
            - Sinon → NEUTRAL
        """

if len(df_h4) < config.SWING_LOOKBACK:
            return "NEUTRAL"

        swings_h4 = self.swing_detector.detect_swings(df_h4)
        swings_h4 = self.swing_detector.classify_swings(swings_h4)

        swings_major = swings_h4[-3:] if len(swings_h4) >= 3 else swings_h4
        
        if len(swings_major) < 2:
            return "NEUTRAL"
        
        bullish = 0
        bearish = 0
        
        for s in swings_major:
            label = getattr(s, "label", None)
            if not label:
                continue
            
            if label in ["HH", "HL"]:
                bullish += 1
            elif label in ["LH", "LL"]:
                bearish += 1
        
        # Logging debug
        self.logger.debug(f"[MACRO H4] swings={len(swings_major)}, bullish={bullish}, bearish={bearish}")
        
        if bullish >= 2:
            return "BULLISH"
        elif bearish >= 2:
            return "BEARISH"
        return "NEUTRAL"

    # ----------------------------------------------------------------------
    # 🔥 Analyse complète (H1)
    # ----------------------------------------------------------------------
    def analyze(self, df_h1: pd.DataFrame) -> Dict:
        """
        Analyse complète de la structure marché en H1.
        """

        swings = self.swing_detector.detect_swings(df_h1)
        swings = self.swing_detector.classify_swings(swings)

        trend = self.swing_detector.get_trend(swings)
        current_price = df_h1["close"].iloc[-1]

        macro_bias = self.get_macro_bias(df_h1, current_price)

        last_hh = self.swing_detector.get_last_swing_by_type(swings, "HIGH", "HH")
        last_hl = self.swing_detector.get_last_swing_by_type(swings, "LOW", "HL")
        last_lh = self.swing_detector.get_last_swing_by_type(swings, "HIGH", "LH")
        last_ll = self.swing_detector.get_last_swing_by_type(swings, "LOW", "LL")
        
        structure = self.swing_detector.get_structure_summary(swings)

        # 🔥 PATCH ANTI-SPAM: Identifiant unique de structure avec ARRONDI (évite micro-variations H4)
        structure_id = None
        if trend == "UPTREND" and last_hh and last_hl:
            # Arrondir à 1 décimale pour éviter que 26850.12 vs 26850.55 créent 2 IDs différents
            structure_id = f"LONG_{round(last_hh.price, 1)}_{round(last_hl.price, 1)}"
        elif trend == "DOWNTREND" and last_lh and last_ll:
            structure_id = f"SHORT_{round(last_lh.price, 1)}_{round(last_ll.price, 1)}"
        
        return {
            "current_price": current_price,
            "trend": trend,
            "macro_bias": macro_bias,
            "swings": swings,
            "last_HH": last_hh,
            "last_HL": last_hl,
            "last_LH": last_lh,
            "last_LL": last_ll,
            "structure": structure,
            "structure_id": structure_id,
            "df_h4": df_h4   # ❗ Timeframe H4
        }

    # ----------------------------------------------------------------------
    # 🔥 BUY SIGNAL (H4)
    # ----------------------------------------------------------------------
    def check_buy_signal(self, analysis: Dict) -> Tuple[bool, Optional[float], Optional[Dict]]:

        df_h4 = analysis.get("df_h4")

        # Anti-range — range trop étroit = pas de tendance
        if df_h4 is not None and len(df_h4) >= 20:
            recent = df_h4.tail(20)
            range_pct = (recent["high"].max() - recent["low"].min()) / recent["close"].iloc[-1] * 100
            if range_pct < config.RANGE_MIN_PCT:
                return False, None, {"reason": f"Range H4 trop étroit ({range_pct:.2f}% < {config.RANGE_MIN_PCT}%)"}

        # Momentum minimal
        if len(df_h4) >= 3:
            r = df_h4.tail(3)
            momentum = (r["high"].max() - r["low"].min()) / r["close"].iloc[-1] * 100
            if momentum < 0.5:  # H4 = momentum plus large
                return False, None, {"reason": f"Momentum trop faible ({momentum:.2f}%)"}

        # Filtre macro
        if analysis["macro_bias"] == "BEARISH":
            return False, None, {"reason": "Macro BEARISH : aucun long autorisé"}

        # Trend
        if analysis["trend"] != "UPTREND":
            return False, None, {"reason": "Pas en UPTREND"}

        if analysis["macro_bias"] != "BULLISH":
            return False, None, {"reason": "Macro pas BULLISH"}

        last_hh = analysis["last_HH"]
        last_hl = analysis["last_HL"]

        if not last_hh:
            return False, None, {"reason": "Aucun HH détecté"}
        if not last_hl:
            return False, None, {"reason": "Aucun HL détecté"}

        df_h1_len = len(df_h1)
        if hasattr(last_hh, "index") and (df_h1_len - 1 - last_hh.index) > 80:
            return False, None, {"reason": "HH trop ancien (>80h)"}

        current_price = analysis["current_price"]

        # Cassure HH
        if not self.swing_detector.is_breakout(current_price, last_hh, "UP"):
            return False, None, {"reason": f"Cassure HH non valide : prix {current_price:.4f} < HH {last_hh.price:.4f}"}

        breakout_pct = (current_price - last_hh.price) / last_hh.price * 100
        if breakout_pct < 0.25:
            return False, None, {"reason": f"Fake breakout ({breakout_pct:.2f}%)"}

        candle = df_h1.iloc[-1]
        if candle["close"] < candle["open"]:
            return False, None, {"reason": "Bougie breakout rouge"}

        if candle["close"] < last_hh.price * 1.0015:
            return False, None, {"reason": "Clôture trop faible après cassure"}

        # Position dans la bougie
        rng = candle["high"] - candle["low"]
        if rng > 0:
            pos = (candle["close"] - candle["low"]) / rng * 100
            if pos < 40:
                return False, None, {"reason": f"Breakout pas propre ({pos:.1f}% dans bougie)"}

        # Distance HH-HL minimale
        dist = abs(last_hh.price - last_hl.price) / last_hl.price * 100
        if dist < 0.35:
            return False, None, {"reason": f"Structure trop serrée ({dist:.2f}% < 0.35%)"}

        stop_loss = last_hl.price
        stop_pct = abs(current_price - stop_loss) / current_price * 100

        if stop_pct < config.MIN_STOP_PCT:
            return False, None, {"reason": "Stop trop petit"}
        if stop_pct > config.MAX_STOP_PCT:
            return False, None, {"reason": "Stop trop grand"}

        return True, stop_loss, {
            "entry_price": current_price,
            "stop_loss": stop_loss,
            "last_HH": last_hh.price,
            "last_HL": last_hl.price
        }

    # ----------------------------------------------------------------------
    # 🔥 SELL SIGNAL (H4)
    # ----------------------------------------------------------------------
    def check_sell_signal(self, analysis: Dict) -> Tuple[bool, Optional[float], Optional[Dict]]:

        df_h4 = analysis.get("df_h4")

        if len(df_h4) >= 3:
            r = df_h4.tail(3)
            momentum = (r["high"].max() - r["low"].min()) / r["close"].iloc[-1] * 100
            if momentum < 0.5:  # H4 = momentum plus large
                return False, None, {"reason": f"Momentum insuffisant ({momentum:.2f}%)"}

        if analysis["macro_bias"] != "BEARISH":
            return False, None, {"reason": f"Macro {analysis['macro_bias']} — aucun short autorisé"}

        if analysis["trend"] != "DOWNTREND":
            return False, None, {"reason": "Pas en DOWNTREND"}

        last_ll = analysis["last_LL"]
        last_lh = analysis["last_LH"]

        if not last_ll:
            return False, None, {"reason": "Aucun LL détecté"}
        if not last_lh:
            return False, None, {"reason": "Aucun LH détecté"}

        df_len = len(df_h1)
        if hasattr(last_ll, "index") and (df_len - 1 - last_ll.index) > 80:
            return False, None, {"reason": "LL trop ancien"}

        current_price = analysis["current_price"]

        if not self.swing_detector.is_breakout(current_price, last_ll, "DOWN"):
            return False, None, {"reason": "Pas de cassure LL"}

        breakout_pct = (last_ll.price - current_price) / last_ll.price * 100
        if breakout_pct < 0.25:
            return False, None, {"reason": "Fake breakout"}

        candle = df_h1.iloc[-1]
        if candle["close"] > candle["open"]:
            return False, None, {"reason": "Breakout short bougie verte"}

        rng = candle["high"] - candle["low"]
        if rng > 0:
            pos = (candle["close"] - candle["low"]) / rng * 100
            if pos > 40:
                return False, None, {"reason": "Clôture pas assez basse dans la bougie"}

        dist = abs(last_lh.price - last_ll.price) / last_ll.price * 100
        if dist < 0.45:
            return False, None, {"reason": "Structure short trop serrée"}

        stop_loss = last_lh.price
        stop_pct = abs(stop_loss - current_price) / current_price * 100

        if stop_pct < config.MIN_STOP_PCT:
            return False, None, {"reason": "Stop trop petit"}
        if stop_pct > config.MAX_STOP_PCT:
            return False, None, {"reason": "Stop trop grand"}

        return True, stop_loss, {
            "entry_price": current_price,
            "stop_loss": stop_loss,
            "last_LL": last_ll.price,
            "last_LH": last_lh.price
        }

    # ----------------------------------------------------------------------
    # 🔥 Trend invalidation
    # ----------------------------------------------------------------------
    def check_trend_invalidation(self, analysis: Dict, position_side: str) -> bool:

        current_price = analysis["current_price"]

        if position_side == "LONG":
            last_hl = analysis["last_HL"]
            if last_hl and current_price < last_hl.price:
                return True

        elif position_side == "SHORT":
            last_lh = analysis["last_LH"]
            if last_lh and current_price > last_lh.price:
                return True

        return False

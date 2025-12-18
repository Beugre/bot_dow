"""
Détection des swings (pivots) et classification HH/HL/LH/LL
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Swing:
    """Représente un swing (pivot haut ou bas)"""
    index: int
    timestamp: datetime
    price: float
    type: str  # "HIGH" ou "LOW"
    label: Optional[str] = None  # "HH", "HL", "LH", "LL"


class SwingDetector:
    """
    Détecte les swings et les classifie selon Dow Theory
    """
    
    def __init__(self, lookback: int = 1):
        """
        Args:
            lookback: Nombre de bougies de chaque côté pour valider un swing
        """
        self.lookback = lookback
        self.swings: List[Swing] = []
    
    def detect_swings(self, df: pd.DataFrame) -> List[Swing]:
        """
        Détecte tous les swings sur un DataFrame OHLC
        
        Args:
            df: DataFrame avec colonnes ['high', 'low', 'timestamp']
            
        Returns:
            Liste de Swing détectés
        """
        swings = []
        n = len(df)
        
        # Besoin d'au moins lookback*2 + 1 bougies
        if n < (self.lookback * 2 + 1):
            return swings
        
        # Détecter les Swing Highs
        for i in range(self.lookback, n - self.lookback):
            is_swing_high = True
            
            # Vérifier que high[i] est le plus haut sur la fenêtre
            for j in range(i - self.lookback, i + self.lookback + 1):
                if j != i and df['high'].iloc[j] >= df['high'].iloc[i]:
                    is_swing_high = False
                    break
            
            if is_swing_high:
                swing = Swing(
                    index=i,
                    timestamp=df['timestamp'].iloc[i] if 'timestamp' in df.columns else df.index[i],
                    price=df['high'].iloc[i],
                    type="HIGH"
                )
                swings.append(swing)
        
        # Détecter les Swing Lows
        for i in range(self.lookback, n - self.lookback):
            is_swing_low = True
            
            # Vérifier que low[i] est le plus bas sur la fenêtre
            for j in range(i - self.lookback, i + self.lookback + 1):
                if j != i and df['low'].iloc[j] <= df['low'].iloc[i]:
                    is_swing_low = False
                    break
            
            if is_swing_low:
                swing = Swing(
                    index=i,
                    timestamp=df['timestamp'].iloc[i] if 'timestamp' in df.columns else df.index[i],
                    price=df['low'].iloc[i],
                    type="LOW"
                )
                swings.append(swing)
        
        # Trier par index
        swings.sort(key=lambda s: s.index)
        
        # FILTRE 1: Taille minimale de swing (élimine 90% des faux swings)
        swings = self._filter_by_size(swings, df)
        
        # FILTRE 2: Distance minimale entre swings (anti-spam)
        swings = self._filter_by_distance(swings, df)
        
        # FILTRE 3: Confirmation par bougies suivantes
        swings = self._filter_by_confirmation(swings, df)
        
        return swings
    
    def _filter_by_size(self, swings: List[Swing], df: pd.DataFrame) -> List[Swing]:
        """
        🔥 FILTRE CRITIQUE : Taille minimale du swing
        Élimine 90% des faux swings (micro-wicks, noise)
        
        Args:
            swings: Liste de swings
            df: DataFrame avec données OHLC
            
        Returns:
            Swings filtrés par taille minimale
        """
        if len(swings) < 2:
            return swings
        
        from config_dow import MIN_SWING_SIZE_PCT
        
        filtered = []
        
        for i, swing in enumerate(swings):
            # Trouver le swing précédent de type opposé
            prev_opposite = None
            for j in range(i - 1, -1, -1):
                if swings[j].type != swing.type:
                    prev_opposite = swings[j]
                    break
            
            if prev_opposite is None:
                filtered.append(swing)  # Garder le premier
                continue
            
            # Calculer la taille du swing en %
            swing_size_pct = abs(swing.price - prev_opposite.price) / prev_opposite.price * 100
            
            # Filtrer si trop petit
            if swing_size_pct >= MIN_SWING_SIZE_PCT:
                filtered.append(swing)
        
        return filtered
    
    def _filter_by_distance(self, swings: List[Swing], df: pd.DataFrame) -> List[Swing]:
        """
        Filtre les swings trop proches (distance < MIN_SWING_DISTANCE_PCT)
        
        Args:
            swings: Liste de swings
            df: DataFrame avec donn\u00e9es OHLC
            
        Returns:
            Swings filtr\u00e9s
        """
        if len(swings) < 2:
            return swings
        
        from config_dow import MIN_SWING_DISTANCE_PCT
        
        filtered = [swings[0]]  # Garder le premier
        
        for i in range(1, len(swings)):
            current = swings[i]
            previous = filtered[-1]
            
            # Distance en % entre les deux swings
            if current.type == previous.type:
                # M\u00eame type (HIGH-HIGH ou LOW-LOW)
                distance_pct = abs(current.price - previous.price) / previous.price * 100
                
                # Si trop proche, garder seulement le plus extr\u00eame
                if distance_pct < MIN_SWING_DISTANCE_PCT:
                    if current.type == "HIGH" and current.price > previous.price:
                        filtered[-1] = current  # Remplacer par le plus haut
                    elif current.type == "LOW" and current.price < previous.price:
                        filtered[-1] = current  # Remplacer par le plus bas
                    continue
            
            filtered.append(current)
        
        return filtered
    
    def _filter_by_confirmation(self, swings: List[Swing], df: pd.DataFrame) -> List[Swing]:
        """
        🔥 FILTRE CRITIQUE : Confirmation du swing par N bougies
        Un pivot n'est validé que si les N bougies suivantes confirment le retournement
        
        Args:
            swings: Liste de swings
            df: DataFrame avec données OHLC
            
        Returns:
            Swings confirmés uniquement
        """
        if len(swings) == 0:
            return swings
        
        from config_dow import SWING_CONFIRMATION_CANDLES
        
        filtered = []
        n = len(df)
        
        for swing in swings:
            idx = swing.index
            
            # Vérifier qu'on a assez de bougies après le pivot
            if idx + SWING_CONFIRMATION_CANDLES >= n:
                continue  # Pas assez de données pour confirmer
            
            confirmed = True
            
            if swing.type == "HIGH":
                # Pour un swing high, les bougies suivantes doivent être plus basses
                for i in range(1, SWING_CONFIRMATION_CANDLES + 1):
                    if df['high'].iloc[idx + i] > swing.price:
                        confirmed = False
                        break
            
            else:  # swing.type == "LOW"
                # Pour un swing low, les bougies suivantes doivent être plus hautes
                for i in range(1, SWING_CONFIRMATION_CANDLES + 1):
                    if df['low'].iloc[idx + i] < swing.price:
                        confirmed = False
                        break
            
            if confirmed:
                filtered.append(swing)
        
        return filtered
    
    def classify_swings(self, swings: List[Swing]) -> List[Swing]:
        """
        Classifie les swings en HH/HL/LH/LL
        
        Args:
            swings: Liste de swings triés par index
            
        Returns:
            Liste de swings avec labels ajoutés
        """
        if len(swings) < 2:
            return swings
        
        # Séparer highs et lows
        highs = [s for s in swings if s.type == "HIGH"]
        lows = [s for s in swings if s.type == "LOW"]
        
        # Classifier les highs (HH ou LH)
        for i in range(1, len(highs)):
            current = highs[i]
            previous = highs[i-1]
            
            if current.price > previous.price:
                current.label = "HH"  # Higher High
            else:
                current.label = "LH"  # Lower High
        
        # Classifier les lows (HL ou LL)
        for i in range(1, len(lows)):
            current = lows[i]
            previous = lows[i-1]
            
            if current.price > previous.price:
                current.label = "HL"  # Higher Low
            else:
                current.label = "LL"  # Lower Low
        
        return swings
    
    def get_trend(self, swings: List[Swing]) -> str:
        """
        Détermine la tendance actuelle basée sur les derniers swings
        
        Args:
            swings: Liste de swings classifiés
            
        Returns:
            "UPTREND", "DOWNTREND", ou "NEUTRAL"
        """
        if len(swings) < 4:
            return "NEUTRAL"
        
        # Récupérer les derniers swings significatifs
        highs = [s for s in swings if s.type == "HIGH" and s.label]
        lows = [s for s in swings if s.type == "LOW" and s.label]
        
        if not highs or not lows:
            return "NEUTRAL"
        
        last_high = highs[-1]
        last_low = lows[-1]
        
        # UPTREND : dernier HH + dernier HL
        if len(highs) >= 1 and len(lows) >= 1:
            if last_high.label == "HH" and last_low.label == "HL":
                return "UPTREND"
        
        # DOWNTREND : dernier LH + dernier LL
        if len(highs) >= 1 and len(lows) >= 1:
            if last_high.label == "LH" and last_low.label == "LL":
                return "DOWNTREND"
        
        return "NEUTRAL"
    
    def get_last_swing_by_type(self, swings: List[Swing], swing_type: str, label: Optional[str] = None) -> Optional[Swing]:
        """
        Récupère le dernier swing d'un type donné
        
        Args:
            swings: Liste de swings
            swing_type: "HIGH" ou "LOW"
            label: Optionnel - "HH", "HL", "LH", "LL"
            
        Returns:
            Le dernier swing correspondant ou None
        """
        filtered = [s for s in swings if s.type == swing_type]
        
        if label:
            filtered = [s for s in filtered if s.label == label]
        
        return filtered[-1] if filtered else None
    
    def is_breakout(self, current_price: float, swing: Swing, direction: str) -> bool:
        """
        Vérifie si le prix a cassé un swing
        
        Args:
            current_price: Prix actuel
            swing: Swing à tester
            direction: "UP" ou "DOWN"
            
        Returns:
            True si cassure confirmée
        """
        if direction == "UP":
            return current_price > swing.price
        elif direction == "DOWN":
            return current_price < swing.price
        
        return False
    
    def get_structure_summary(self, swings: List[Swing]) -> Dict:
        """
        Résumé de la structure de marché
        
        Returns:
            Dict avec infos sur la structure actuelle
        """
        trend = self.get_trend(swings)
        
        last_hh = self.get_last_swing_by_type(swings, "HIGH", "HH")
        last_hl = self.get_last_swing_by_type(swings, "LOW", "HL")
        last_lh = self.get_last_swing_by_type(swings, "HIGH", "LH")
        last_ll = self.get_last_swing_by_type(swings, "LOW", "LL")
        
        return {
            "trend": trend,
            "last_HH": last_hh.price if last_hh else None,
            "last_HL": last_hl.price if last_hl else None,
            "last_LH": last_lh.price if last_lh else None,
            "last_LL": last_ll.price if last_ll else None,
            "total_swings": len(swings),
            "highs": len([s for s in swings if s.type == "HIGH"]),
            "lows": len([s for s in swings if s.type == "LOW"])
        }

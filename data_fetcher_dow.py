"""
Récupération des données de marché depuis Binance
"""
import ccxt
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Optional
import config_dow as config


class DataFetcher:
    """
    Gère la récupération des données OHLC depuis Binance
    """
    
    def __init__(self):
        """Initialise la connexion à Binance"""
        self.exchange = ccxt.binance({
            'apiKey': config.BINANCE_API_KEY,
            'secret': config.BINANCE_API_SECRET,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot'
            }
        })
    
    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 1000
    ) -> Optional[pd.DataFrame]:
        """
        Récupère les bougies OHLCV
        
        Args:
            symbol: Symbole (ex: "BTC/USDC")
            timeframe: Timeframe (ex: "1h", "4h")
            limit: Nombre de bougies
            
        Returns:
            DataFrame avec colonnes [timestamp, open, high, low, close, volume]
        """
        try:
            ohlcv = self.exchange.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                limit=limit
            )
            
            if not ohlcv:
                return None
            
            df = pd.DataFrame(
                ohlcv,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            
            # Convertir timestamp en datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            return df
            
        except Exception as e:
            print(f"Erreur fetch_ohlcv pour {symbol} {timeframe}: {e}")
            return None
    
    def fetch_multiple_timeframes(
        self,
        symbol: str
    ) -> Dict[str, pd.DataFrame]:
        """
        Récupère H1 et H4 pour un symbole
        
        Args:
            symbol: Symbole (ex: "BTC/USDC")
            
        Returns:
            Dict avec keys "H1" et "H4"
        """
        data = {}
        
        # Fetch H1
        df_h1 = self.fetch_ohlcv(symbol, config.TIMEFRAME_EXECUTION, config.CANDLES_H1)
        if df_h1 is not None:
            data["H1"] = df_h1
        
        # Fetch H4
        df_h4 = self.fetch_ohlcv(symbol, config.TIMEFRAME_MACRO, config.CANDLES_H4)
        if df_h4 is not None:
            data["H4"] = df_h4
        
        return data
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Récupère le prix actuel
        
        Args:
            symbol: Symbole
            
        Returns:
            Prix actuel ou None
        """
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return ticker['last']
        except Exception as e:
            print(f"Erreur get_current_price pour {symbol}: {e}")
            return None
    
    def place_market_order(
        self,
        symbol: str,
        side: str,
        quantity: float
    ) -> Optional[Dict]:
        """
        Place un ordre market
        
        Args:
            symbol: Symbole
            side: "buy" ou "sell"
            quantity: Quantité
            
        Returns:
            Info de l'ordre ou None
        """
        if config.DRY_RUN:
            print(f"[DRY RUN] Ordre market {side} {quantity} {symbol}")
            return {
                "id": f"dry_run_{datetime.now().timestamp()}",
                "symbol": symbol,
                "side": side,
                "amount": quantity,
                "status": "closed"
            }
        
        try:
            order = self.exchange.create_market_order(
                symbol=symbol,
                side=side,
                amount=quantity
            )
            return order
        except Exception as e:
            print(f"Erreur place_market_order {side} {quantity} {symbol}: {e}")
            return None
    
    def place_stop_loss(
        self,
        symbol: str,
        side: str,
        quantity: float,
        stop_price: float
    ) -> Optional[Dict]:
        """
        Place un stop loss
        
        Args:
            symbol: Symbole
            side: "buy" ou "sell" (inverse de la position)
            quantity: Quantité
            stop_price: Prix du stop
            
        Returns:
            Info de l'ordre ou None
        """
        if config.DRY_RUN:
            print(f"[DRY RUN] Stop loss {side} {quantity} {symbol} @ {stop_price}")
            return {
                "id": f"dry_run_sl_{datetime.now().timestamp()}",
                "symbol": symbol,
                "side": side,
                "amount": quantity,
                "stopPrice": stop_price,
                "status": "open"
            }
        
        try:
            order = self.exchange.create_order(
                symbol=symbol,
                type='stop_loss_limit',
                side=side,
                amount=quantity,
                price=stop_price,
                params={'stopPrice': stop_price}
            )
            return order
        except Exception as e:
            print(f"Erreur place_stop_loss {symbol}: {e}")
            return None

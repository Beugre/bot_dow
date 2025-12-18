#!/usr/bin/env python3
"""
📊 SHARED BASE CONFIG - Configuration commune
Clés API et paramètres partagés entre les deux bots
"""

import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class APIConfig:
    """🔐 Configuration API commune aux deux bots"""
    
    # 🏦 BINANCE - Clés récupérées de l'ancien bot RSI
    BINANCE_API_KEY: str = os.getenv("BINANCE_API_KEY", "aieZmzWGghN6oYlc7ldlgyQUpxyZUn21D874SzT5WEfHnzgkRYDjqzcfn2TqQNwB")
    BINANCE_SECRET_KEY: str = os.getenv("BINANCE_SECRET_KEY", "mWPOjQWawnBuXEaBAGhz335Ht46bgwFJpMP41TWOC2pU6YKxcGPJlTawQ9yytZMf")
    BINANCE_TESTNET: bool = os.getenv("BINANCE_TESTNET", "false").lower() == "true"
    
    # 📱 TELEGRAM - Configuration récupérée de l'ancien bot
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "7994723833:AAGwkuU4xBaNTstSTBGKwVGgifgDNCoLs4o")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "1181024836")
    
    # 🔥 FIREBASE
    FIREBASE_CREDENTIALS: str = os.getenv("FIREBASE_CREDENTIALS", "firebase-credentials.json")
    FIREBASE_PROJECT_ID: str = os.getenv("FIREBASE_PROJECT_ID", "")
    FIREBASE_DATABASE_URL: str = os.getenv("FIREBASE_DATABASE_URL", "")
    
    # 📊 GOOGLE SHEETS
    GOOGLE_SHEETS_CREDENTIALS: str = os.getenv("GOOGLE_SHEETS_CREDENTIALS", "")
    GOOGLE_SHEETS_SPREADSHEET_ID: str = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID", "")


def get_api_config() -> APIConfig:
    """📊 Retourne la configuration API standard"""
    return APIConfig()


@dataclass
class LoggingConfig:
    """📝 Configuration logging commune"""
    
    # 📝 NIVEAUX
    CONSOLE_LEVEL: str = "INFO"
    FILE_LEVEL: str = "DEBUG"
    
    # 📄 FORMAT
    FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # 📁 RÉPERTOIRES
    LOG_DIR: str = "logs"
    LOG_MAX_SIZE: int = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT: int = 5
    
    # 🔄 ROTATION
    ROTATION_ENABLED: bool = True
    ROTATION_WHEN: str = "midnight"
    ROTATION_INTERVAL: int = 1


# 🌍 INSTANCES GLOBALES
api_config = APIConfig()
logging_config = LoggingConfig()


def validate_api_config() -> list:
    """Valide la configuration API"""
    errors = []
    
    if not api_config.BINANCE_API_KEY:
        errors.append("❌ BINANCE_API_KEY manquante")
    if not api_config.BINANCE_SECRET_KEY:
        errors.append("❌ BINANCE_SECRET_KEY manquante")
    
    return errors


def print_api_status():
    """Affiche le statut des APIs"""
    print("🔐 STATUS CONFIGURATION API")
    print("="*40)
    print(f"🏦 Binance: {'✅' if api_config.BINANCE_API_KEY else '❌'}")
    print(f"📱 Telegram: {'✅' if api_config.TELEGRAM_BOT_TOKEN else '❌'}")
    print(f"🔥 Firebase: {'✅' if api_config.FIREBASE_CREDENTIALS else '❌'}")
    print(f"🧪 Testnet: {'✅' if api_config.BINANCE_TESTNET else '❌'}")
    print("="*40)


if __name__ == "__main__":
    print_api_status()
    errors = validate_api_config()
    if errors:
        print("\n❌ ERREURS:")
        for error in errors:
            print(f"  {error}")
    else:
        print("\n✅ Configuration API valide !")

#!/usr/bin/env python3
"""
Visualiseur de logs Firebase en temps réel pour Satochi Bot
"""

import os
import time
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    FIREBASE_AVAILABLE = True
except ImportError:
    print("❌ Firebase non disponible. Installez firebase-admin")
    exit(1)

load_dotenv()

def init_firebase():
    """Initialise Firebase"""
    try:
        cred_path = os.getenv('FIREBASE_CREDENTIALS_PATH')
        if not cred_path or not os.path.exists(cred_path):
            print("❌ Fichier Firebase credentials non trouvé")
            return None
            
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        return firestore.client()
    except Exception as e:
        print(f"❌ Erreur Firebase: {e}")
        return None

def watch_logs(db):
    """Surveille les logs en temps réel"""
    if not db:
        return
    
    collection_name = f"satochi_logs_{datetime.now().strftime('%Y_%m')}"
    print(f"🔍 Surveillance des logs: {collection_name}")
    print("=" * 80)
    
    # Timestamp de départ (dernière minute)
    start_time = datetime.now() - timedelta(minutes=1)
    
    try:
        while True:
            # Récupérer les logs récents
            query = (db.collection(collection_name)
                    .where('timestamp', '>=', start_time)
                    .order_by('timestamp')
                    .limit(50))
            
            docs = query.stream()
            
            for doc in docs:
                data = doc.to_dict()
                timestamp = data.get('timestamp', datetime.now())
                level = data.get('level', 'INFO')
                message = data.get('message', '')
                
                # Formatage avec couleurs
                if level == 'ERROR':
                    color = '\033[91m'  # Rouge
                elif level == 'WARNING':
                    color = '\033[93m'  # Jaune
                elif level == 'DEBUG':
                    color = '\033[94m'  # Bleu
                else:
                    color = '\033[92m'  # Vert
                
                reset_color = '\033[0m'
                
                # Affichage formaté
                time_str = timestamp.strftime('%H:%M:%S') if hasattr(timestamp, 'strftime') else str(timestamp)
                print(f"{color}[{time_str}] {level:7} | {message}{reset_color}")
                
                # Afficher données extra si disponibles
                extra_keys = [k for k in data.keys() if k not in ['timestamp', 'level', 'message', 'bot_version', 'session_id']]
                if extra_keys:
                    for key in extra_keys:
                        value = data[key]
                        print(f"                   └─ {key}: {value}")
                
                # Mettre à jour le timestamp de départ
                if hasattr(timestamp, 'timestamp'):
                    start_time = datetime.fromtimestamp(timestamp.timestamp()) + timedelta(seconds=1)
                elif hasattr(timestamp, 'strftime'):
                    start_time = timestamp + timedelta(seconds=1)
            
            time.sleep(2)  # Vérifier toutes les 2 secondes
            
    except KeyboardInterrupt:
        print("\n🛑 Surveillance arrêtée")
    except Exception as e:
        print(f"❌ Erreur surveillance: {e}")

def show_recent_logs(db, hours=1):
    """Affiche les logs récents"""
    if not db:
        return
    
    collection_name = f"satochi_logs_{datetime.now().strftime('%Y_%m')}"
    start_time = datetime.now() - timedelta(hours=hours)
    
    print(f"📋 Logs des dernières {hours}h:")
    print("=" * 80)
    
    try:
        query = (db.collection(collection_name)
                .where('timestamp', '>=', start_time)
                .order_by('timestamp', direction=firestore.Query.DESCENDING)
                .limit(100))
        
        docs = query.stream()
        
        for doc in docs:
            data = doc.to_dict()
            timestamp = data.get('timestamp', datetime.now())
            level = data.get('level', 'INFO')
            message = data.get('message', '')
            
            time_str = timestamp.strftime('%H:%M:%S') if hasattr(timestamp, 'strftime') else str(timestamp)
            print(f"[{time_str}] {level:7} | {message}")
            
    except Exception as e:
        print(f"❌ Erreur récupération logs: {e}")

def main():
    print("🚀 Satochi Bot - Visualiseur de logs Firebase")
    print("=" * 50)
    
    db = init_firebase()
    if not db:
        return
    
    print("Choisissez une option:")
    print("1. Surveiller en temps réel")
    print("2. Afficher logs récents (1h)")
    print("3. Afficher logs récents (24h)")
    
    choice = input("\nVotre choix (1-3): ").strip()
    
    if choice == "1":
        watch_logs(db)
    elif choice == "2":
        show_recent_logs(db, 1)
    elif choice == "3":
        show_recent_logs(db, 24)
    else:
        print("❌ Choix invalide")

if __name__ == "__main__":
    main()

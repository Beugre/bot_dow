#!/usr/bin/env python3
"""
🧪 TEST BINANCE LIVE COLLECTION
Script pour tester le contenu de la collection binance_live
"""

import os
import sys
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

# Configuration Firebase
def init_firebase():
    """Initialise Firebase avec le fichier de credentials"""
    try:
        # Vérifier si Firebase est déjà initialisé
        if firebase_admin._apps:
            return firebase_admin.get_app()
            
        firebase_cred_path = os.getenv('FIREBASE_CREDENTIALS_PATH', 'firebase-credentials.json')
        
        if not os.path.exists(firebase_cred_path):
            print(f"❌ Fichier credentials Firebase non trouvé: {firebase_cred_path}")
            return None
            
        print(f"🔑 Utilisation credentials Firebase: {firebase_cred_path}")
        
        cred = credentials.Certificate(firebase_cred_path)
        return firebase_admin.initialize_app(cred)
        
    except Exception as e:
        print(f"❌ Erreur Firebase: {e}")
        return None

def test_binance_live():
    """Test le contenu de la collection binance_live"""
    try:
        # Initialiser Firebase
        app = init_firebase()
        if not app:
            print("❌ Firebase non initialisé")
            return
            
        db = firestore.client()
        
        print("🔍 Test de la collection binance_live...")
        
        # Récupérer les documents de binance_live
        binance_ref = db.collection('binance_live')
        docs = list(binance_ref.limit(10).stream())
        
        print(f"📊 Trouvé {len(docs)} documents dans binance_live")
        
        for i, doc in enumerate(docs):
            data = doc.to_dict()
            print(f"\n📄 Document {i+1} (ID: {doc.id}):")
            
            if 'balances' in data:
                balances = data.get('balances', [])
                print(f"   💰 {len(balances)} balances trouvées")
                
                non_zero_balances = []
                for balance in balances:
                    asset = balance.get('asset', '')
                    free = float(balance.get('free', 0))
                    locked = float(balance.get('locked', 0))
                    total = float(balance.get('total', 0))
                    
                    if total > 0.001:  # Balances significatives
                        non_zero_balances.append(f"{asset}: {total}")
                
                print(f"   🎯 Balances non-nulles: {non_zero_balances}")
            else:
                print("   ❌ Pas de champ 'balances' trouvé")
            
            # Afficher les autres champs
            other_fields = {k: v for k, v in data.items() if k != 'balances'}
            if other_fields:
                print(f"   📝 Autres champs: {list(other_fields.keys())}")
        
        # Tester aussi les collections de logs récentes
        print(f"\n🔍 Test des logs récents...")
        current_month = datetime.now().strftime('%Y_%m')
        logs_ref = db.collection(f'satochi_logs_{current_month}')
        recent_logs = list(logs_ref.order_by('timestamp', direction=firestore.Query.DESCENDING).limit(5).stream())
        
        print(f"📊 {len(recent_logs)} logs récents trouvés")
        for log_doc in recent_logs:
            log_data = log_doc.to_dict()
            timestamp = log_data.get('timestamp')
            level = log_data.get('level', 'UNKNOWN')
            message = log_data.get('message', 'No message')[:50]
            print(f"   📝 {timestamp} [{level}] {message}...")
        
    except Exception as e:
        print(f"❌ Erreur test binance_live: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_binance_live()

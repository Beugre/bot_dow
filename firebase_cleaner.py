#!/usr/bin/env python3
"""
🧹 FIREBASE LOG CLEANER
Supprime automatiquement les logs Firebase de plus de X jours pour éviter la facturation
"""

import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    print("❌ Firebase non disponible, impossible de nettoyer les logs")
    sys.exit(1)

class FirebaseCleaner:
    def __init__(self, retention_days=5):
        """
        Initialise le nettoyeur Firebase
        :param retention_days: Nombre de jours à conserver (défaut: 5)
        """
        self.retention_days = retention_days
        self.cutoff_date = datetime.now() - timedelta(days=retention_days)
        self.firebase_db = None
        
        # Chargement des variables d'environnement
        load_dotenv()
        
        # Initialisation Firebase
        self.setup_firebase()
    
    def setup_firebase(self):
        """Configuration de Firebase"""
        try:
            firebase_cred_path = os.getenv('FIREBASE_CREDENTIALS_PATH')
            if not firebase_cred_path or not os.path.exists(firebase_cred_path):
                print("❌ Firebase credentials non trouvées")
                return False
            
            # Initialisation Firebase si pas déjà fait
            if not firebase_admin._apps:
                cred = credentials.Certificate(firebase_cred_path)
                firebase_admin.initialize_app(cred)
            
            self.firebase_db = firestore.client()
            print("✅ Firebase connecté pour nettoyage")
            return True
            
        except Exception as e:
            print(f"❌ Erreur setup Firebase: {e}")
            return False
    
    def clean_collection(self, collection_name, date_field='timestamp', batch_size=100):
        """
        Nettoie une collection Firebase
        :param collection_name: Nom de la collection
        :param date_field: Champ contenant la date
        :param batch_size: Nombre de documents à traiter par batch
        """
        if not self.firebase_db:
            print("❌ Firebase non configuré")
            return 0
        
        try:
            collection_ref = self.firebase_db.collection(collection_name)
            
            # Requête pour trouver les documents anciens
            query = collection_ref.where(date_field, '<', self.cutoff_date).limit(batch_size)
            
            deleted_count = 0
            
            while True:
                docs = query.get()
                
                if not docs:
                    break
                
                # Suppression en batch
                batch = self.firebase_db.batch()
                batch_count = 0
                
                for doc in docs:
                    batch.delete(doc.reference)
                    batch_count += 1
                
                if batch_count > 0:
                    batch.commit()
                    deleted_count += batch_count
                    print(f"   📦 Supprimé {batch_count} documents de {collection_name}")
                
                # Si moins de documents que la limite, on a fini
                if len(docs) < batch_size:
                    break
            
            return deleted_count
            
        except Exception as e:
            print(f"❌ Erreur nettoyage {collection_name}: {e}")
            return 0
    
    def clean_all_logs(self):
        """Nettoie toutes les collections de logs"""
        print(f"🧹 Début du nettoyage Firebase (rétention: {self.retention_days} jours)")
        print(f"📅 Suppression des logs antérieurs au: {self.cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}")
        
        total_deleted = 0
        
        # Collections à nettoyer (ajustez selon votre structure)
        collections_to_clean = [
            'bot_activity',     # Logs d'activité du bot
            'trades',          # Logs des trades
            'errors',          # Logs d'erreurs
            'debug_logs',      # Logs de debug
            'notifications',   # Logs des notifications
            'market_data',     # Données de marché (si stockées)
        ]
        
        for collection in collections_to_clean:
            print(f"🔍 Nettoyage de la collection: {collection}")
            deleted = self.clean_collection(collection)
            total_deleted += deleted
            
            if deleted > 0:
                print(f"   ✅ {deleted} documents supprimés de {collection}")
            else:
                print(f"   ℹ️ Aucun document ancien dans {collection}")
        
        print(f"🎯 Nettoyage terminé: {total_deleted} documents supprimés au total")
        
        # Calcul approximatif des économies
        if total_deleted > 0:
            # Estimation: ~0.0001$ par document lu/écrit
            estimated_savings = total_deleted * 0.0001
            print(f"💰 Économie estimée: ~${estimated_savings:.4f}")
        
        return total_deleted
    
    def get_storage_stats(self):
        """Affiche les statistiques de stockage"""
        if not self.firebase_db:
            return
        
        print("📊 Statistiques de stockage Firebase:")
        
        collections_to_check = [
            'bot_activity', 'trades', 'errors', 'debug_logs', 
            'notifications', 'market_data'
        ]
        
        for collection in collections_to_check:
            try:
                # Compter les documents récents
                recent_query = self.firebase_db.collection(collection).where(
                    'timestamp', '>=', self.cutoff_date
                ).limit(1000)
                recent_docs = recent_query.get()
                recent_count = len(recent_docs)
                
                # Compter les documents anciens
                old_query = self.firebase_db.collection(collection).where(
                    'timestamp', '<', self.cutoff_date
                ).limit(1000)
                old_docs = old_query.get()
                old_count = len(old_docs)
                
                print(f"   📁 {collection}: {recent_count} récents, {old_count} anciens")
                
            except Exception as e:
                print(f"   ❌ Erreur stats {collection}: {e}")

def main():
    """Point d'entrée principal"""
    print("🧹 Firebase Log Cleaner - Satochi Bot")
    print("=" * 50)
    
    # Paramètres configurables
    retention_days = int(os.getenv('FIREBASE_RETENTION_DAYS', '5'))
    
    # Création du cleaner
    cleaner = FirebaseCleaner(retention_days=retention_days)
    
    # Affichage des stats avant nettoyage
    print("\n📊 État avant nettoyage:")
    cleaner.get_storage_stats()
    
    # Nettoyage
    print(f"\n🧹 Nettoyage en cours...")
    total_deleted = cleaner.clean_all_logs()
    
    # Affichage des stats après nettoyage
    if total_deleted > 0:
        print(f"\n📊 État après nettoyage:")
        cleaner.get_storage_stats()
    
    print(f"\n✅ Nettoyage terminé!")

if __name__ == "__main__":
    main()

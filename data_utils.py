import os
import psycopg2
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
import time

def get_feedback_data(filters=None, force_refresh=False):
    # Récupérer la chaîne de connexion
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        raise ValueError("La variable d'environnement DATABASE_URL n'est pas définie")
    
    # ✅ SOLUTION : Forcer une nouvelle connexion à chaque fois
    engine = create_engine(
        DATABASE_URL,
        poolclass=NullPool,
        isolation_level="READ COMMITTED",  # S'assurer de lire les dernières données
        connect_args={
            'application_name': 'feedback_app',  # Pour identifier la connexion
            'options': '-c statement_timeout=30000'  # Timeout de 30s
        }
    )
    
    try:
        # ✅ SOLUTION : Commencer par vérifier les données récentes
        with engine.connect() as conn:
            # Forcer la synchronisation avec la base
            conn.execute(text("SELECT 1"))
            
            # ✅ SOLUTION : Ajouter un paramètre pour forcer le rafraîchissement
            query = "SELECT rating, sentiment, timestamp, language, unique_code, comment FROM feedback ORDER BY timestamp DESC"
            
            # ✅ SOLUTION : Utiliser execute directement pour éviter tout cache
            if force_refresh:
                # Forcer un rafraîchissement explicite
                conn.execute(text("COMMIT"))
            
            df = pd.read_sql_query(text(query), conn)
        
        # Conversion du champ timestamp
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Application des filtres
        if filters:
            if 'language' in filters and filters['language']:
                df = df[df['language'].isin(filters['language'])]
            if 'sentiment' in filters and filters['sentiment']:
                df = df[df['sentiment'].isin(filters['sentiment'])]
            if 'rating_range' in filters and filters['rating_range']:
                df = df[(df['rating'] >= filters['rating_range'][0]) & (df['rating'] <= filters['rating_range'][1])]
            if 'date_range' in filters and filters['date_range']:
                df = df[(df['timestamp'] >= filters['date_range'][0]) & (df['timestamp'] <= filters['date_range'][1])]
        
        # ✅ SOLUTION : Log pour débogage
        print(f"✅ Données chargées : {len(df)} enregistrements")
        if len(df) > 0:
            print(f"📅 Dernier enregistrement : {df['timestamp'].max()}")
        
        return df
    
    except Exception as e:
        print(f"❌ Erreur lors du chargement des données : {e}")
        raise
    
    finally:
        # ✅ Fermer proprement
        engine.dispose()

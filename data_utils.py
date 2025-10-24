import os
import psycopg2
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

def get_feedback_data(filters=None):
    # Récupérer la chaîne de connexion depuis une variable d'environnement
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        raise ValueError("La variable d'environnement DATABASE_URL n'est pas définie")
    
    # ✅ CORRECTION 1: Créer engine sans pool pour éviter le cache
    engine = create_engine(
        DATABASE_URL,
        poolclass=NullPool,  # Désactive le pool de connexions
        isolation_level="AUTOCOMMIT"  # Force la lecture des dernières données
    )
    
    try:
        # ✅ CORRECTION 2: Requête SQL avec ORDER BY pour garantir l'ordre
        query = """
        SELECT rating, sentiment, timestamp, language, unique_code, comment 
        FROM feedback 
        ORDER BY timestamp DESC
        """
        
        # ✅ CORRECTION 3: Lecture avec connexion fraîche
        with engine.connect() as conn:
            df = pd.read_sql_query(query, conn)
        
        # Log pour debug (à retirer en production)
        print(f"[DEBUG] Lignes chargées: {len(df)}")
        if len(df) > 0:
            print(f"[DEBUG] Dernière entrée: {df['timestamp'].max()}")
        
        # Conversion du champ timestamp en datetime
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
        
        return df
    
    finally:
        # ✅ CORRECTION 4: Fermer proprement l'engine
        engine.dispose()

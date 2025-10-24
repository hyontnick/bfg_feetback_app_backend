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
    
    # ✅ CORRECTION : Créer engine SANS pool pour éviter le cache
    engine = create_engine(
        DATABASE_URL,
        poolclass=NullPool,      # Pas de pool = connexion fraîche à chaque fois
        pool_pre_ping=True       # Vérifie que la connexion est vivante
    )
    
    try:
        # Requête SQL
        query = "SELECT rating, sentiment, timestamp, language, unique_code, comment FROM feedback ORDER BY timestamp DESC"
        df = pd.read_sql_query(query, engine)
        
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
        # ✅ IMPORTANT : Fermer l'engine après chaque utilisation
        engine.dispose()

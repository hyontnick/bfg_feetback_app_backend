import pandas as pd
import re
from fastapi import FastAPI
from pydantic import BaseModel
from googletrans import Translator
from textblob import TextBlob
import joblib
import numpy as np
from langdetect import detect, DetectorFactory
from typing import Dict
from fastapi.middleware.cors import CORSMiddleware

# Fixer la graine pour langdetect
DetectorFactory.seed = 0

# Initialiser FastAPI
app = FastAPI(title="Sentiment Analysis API", description="API pour prédire le sentiment des commentaires avec texte et emojis.")

# Configure les origines autorisées (ici, tout est autorisé, mais tu peux restreindre)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Ou ["http://localhost:3000"] pour plus de sécurité
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modèle Pydantic pour valider l'entrée
class CommentRequest(BaseModel):
    comment: str

# Charger le dictionnaire des emojis
emoji_data = pd.read_csv('Emoji_Sentiment_Data.csv')

def create_emoji_sentiment_dict(emoji_df):
    emoji_dict = {}
    for _, row in emoji_df.iterrows():
        emoji = row['Emoji']
        total = row['Negative'] + row['Neutral'] + row['Positive']
        if total > 0:
            score = (row['Positive'] - row['Negative']) / total
            emoji_dict[emoji] = score
    return emoji_dict

emoji_sentiment = create_emoji_sentiment_dict(emoji_data)

# Charger le modèle et le vectoriseur
model = joblib.load('sentiment_model.pkl')
vectorizer = joblib.load('tfidf_vectorizer.pkl')

# Fonction pour extraire les emojis
def extract_emojis(text):
    if not text or isinstance(text, float):
        return []
    return [char for char in str(text) if char in emoji_sentiment]

# Calculer le score des emojis
def get_emoji_score(text):
    emojis = extract_emojis(text)
    if not emojis:
        return 0.0
    return sum(emoji_sentiment.get(emoji, 0.0) for emoji in emojis) / len(emojis)

# Classifier le sentiment des emojis
def get_emoji_sentiment(score):
    if score > 0.1:
        return 'positive'
    elif score < -0.1:
        return 'negative'
    return 'neutral'

# Nettoyer le texte
def clean_text(text):
    if not text or isinstance(text, float):
        return ''
    for emoji in emoji_sentiment:
        text = text.replace(emoji, '')
    text = re.sub(r'[^a-zA-Z0-9\s.,!?]', '', text)
    return text.strip()

# Traduire en anglais
def translate_to_english(text):
    if not text:
        return ''
    try:
        lang = detect(text)
        if lang == 'en':
            return text
        translated = Translator().translate(text, src=lang, dest='en').text
        if len(translated.split()) < 2 and not translated.isalpha():
            return ''
        return translated
    except Exception:
        return ''  # Caractères intraduisibles

# Classifier le sentiment du texte
def get_text_sentiment(text):
    if not text or text.strip() == '':
        return 'neutral'
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity
    if polarity > 0.1:
        return 'positive'
    elif polarity < -0.1:
        return 'negative'
    return 'neutral'

# Combiner texte et emojis selon les règles
def combine_sentiments(text_sentiment, emoji_sentiment):
    if text_sentiment == 'neutral' and emoji_sentiment == 'neutral':
        return 'neutral'
    elif text_sentiment == 'negative' and emoji_sentiment == 'positive':
        return 'neutral'
    elif text_sentiment == 'positive' and emoji_sentiment == 'negative':
        return 'neutral'
    elif text_sentiment == 'negative' and emoji_sentiment == 'neutral':
        return 'negative'
    elif text_sentiment == 'positive' and emoji_sentiment == 'neutral':
        return 'positive'
    elif text_sentiment == 'neutral' and emoji_sentiment == 'positive':
        return 'positive'
    elif text_sentiment == 'neutral' and emoji_sentiment == 'negative':
        return 'negative'
    return text_sentiment

# Pipeline de prédiction
def predict_sentiment(comment):
    emoji_score = get_emoji_score(comment)
    emoji_sentiment = get_emoji_sentiment(emoji_score)
    cleaned_comment = clean_text(comment)
    translated_comment = translate_to_english(cleaned_comment)
    text_sentiment = get_text_sentiment(translated_comment)
    combined_sentiment = combine_sentiments(text_sentiment, emoji_sentiment)
    text_tfidf = vectorizer.transform([translated_comment]).toarray()
    features = np.hstack((text_tfidf, [[emoji_score * 0.5]]))
    model_prediction = model.predict(features)[0]
    return combined_sentiment if combined_sentiment != model_prediction else model_prediction

# Endpoint pour prédire le sentiment
@app.post("/predict_feedback")
async def predict(request: CommentRequest) -> Dict[str, str]:
    sentiment = predict_sentiment(request.comment)
    return {"comment": request.comment, "sentiment": sentiment}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
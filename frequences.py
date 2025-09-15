import dash
from dash import html, dcc, callback, Output, Input, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from wordcloud import WordCloud
from PIL import Image
import numpy as np
from io import BytesIO
from data_utils import get_feedback_data

# Dictionnaire de traductions
translations = {
    'fr': {
        'frequences_title': 'Fréquences',
        'wordcloud_title': 'Nuage de Mots',
        'wordfreq_title': 'Mots les plus Fréquents',
        'groupedbar_title': 'Fréquences par Catégorie',
        'heatmap_title': 'Carte Thermique des Fréquences'
    },
    'en': {
        'frequences_title': 'Frequencies',
        'wordcloud_title': 'Word Cloud',
        'wordfreq_title': 'Most Frequent Words',
        'groupedbar_title': 'Frequencies by Category',
        'heatmap_title': 'Heatmap of Frequencies'
    }
}

def layout():
    return html.Div([
        html.H2(id='frequences-title', className="text-center mb-4", style={"color": "#2c3e50", "font-family": "Roboto, sans-serif", "font-weight": "bold"}),
        dcc.Store(id='frequence-data-store'),
        dbc.Row([
            dbc.Col(dcc.Graph(id='wordcloud'), width=6, className="frequence-graph-col"),
            dbc.Col(dcc.Graph(id='wordfreq-bar'), width=6, className="frequence-graph-col")
        ]),
        dbc.Row([
            dbc.Col(dcc.Graph(id='grouped-bar'), width=6, className="frequence-graph-col"),
            dbc.Col(dcc.Graph(id='heatmap'), width=6, className="frequence-graph-col")
        ])
    ], className="p-4")

@callback(
    [Output('frequences-title', 'children'),
     Output('wordcloud', 'figure'),
     Output('wordfreq-bar', 'figure'),
     Output('grouped-bar', 'figure'),
     Output('heatmap', 'figure'),
     Output('frequence-data-store', 'data')],
    [Input('filters-store', 'data'),
     Input('frequences-title-store', 'data'),
     Input('interval-component', 'n_intervals')]  # Store temporaire pour la langue
)
def update_frequence_charts(filters, title_from_store, real_time_update):
    language = 'fr' if not title_from_store else ('en' if title_from_store in translations['en'].values() else 'fr')
    t = translations[language]

    df = get_feedback_data(filters)
    if df.empty:
        return [t['frequences_title']] + [go.Figure()] * 4 + [{}]

    # Préparation des données textuelles
    text_data = ' '.join(df['comment'].dropna().astype(str).values)
    word_freq = pd.Series(text_data.lower().split()).value_counts()[:20]  # Top 20 mots

    # Graphique 6: Nuage de mots
    wordcloud = WordCloud(width=800, height=300, background_color='white', min_font_size=10,
                          colormap='viridis').generate(text_data)  # Palette viridis pour un gradient
    img_array = np.array(wordcloud.to_image())
    wordcloud_fig = go.Figure(go.Image(z=img_array))
    wordcloud_fig.update_layout(
        title=f"{t['wordcloud_title']} (Total Mots: {len(text_data.split())})",
        height=300,
        margin=dict(l=0, r=0, t=40, b=0),
        autosize=False
    )

    # Graphique 7: Diagramme en barres des mots les plus fréquents
    wordfreq_fig = go.Figure(
        data=[go.Bar(
            x=word_freq.index,
            y=word_freq.values,
            marker_color=px.colors.qualitative.Bold,  # Palette de couleurs vives
            text=word_freq.values,
            textposition='auto'
        )],
        layout=go.Layout(
            title=f"{t['wordfreq_title']} (Moyenne: {word_freq.mean():.2f})",
            xaxis={'title': 'Mots' if language == 'fr' else 'Words', 'tickangle': -45},
            yaxis={'title': 'Fréquence' if language == 'fr' else 'Frequency'},
            template='plotly_white',
            height=300
        )
    )

    # Graphique 8: Diagramme en barres groupées (par sentiment)
    grouped_data = df.groupby(['sentiment', 'rating']).size().unstack(fill_value=0)
    sentiment_colors = {'positive': '#27AE60', 'neutral': '#F39C12', 'negative': '#E74C3C'}  # Couleurs caractéristiques
    grouped_fig = go.Figure(
        data=[go.Bar(
            name=col, x=grouped_data.index, y=grouped_data[col],
            marker_color=sentiment_colors[col] if col in sentiment_colors else '#3498DB'
        ) for col in grouped_data.columns],
        layout=go.Layout(
            title=t['groupedbar_title'],
            xaxis={'title': 'Sentiment' if language == 'fr' else 'Sentiment'},
            yaxis={'title': 'Nombre' if language == 'fr' else 'Count'},
            barmode='group',
            template='plotly_white',
            height=300,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
    )
    grouped_fig.add_annotation(
        text=f"Total: {grouped_data.values.sum()}",
        xref="paper", yref="paper",
        x=0.95, y=0.95, showarrow=False
    )

    # Graphique 9: Carte thermique
    heatmap_data = df.groupby(['sentiment', 'rating']).size().unstack(fill_value=0)
    heatmap_fig = go.Figure(
        data=go.Heatmap(
            z=heatmap_data.values,
            x=heatmap_data.columns,
            y=heatmap_data.index,
            colorscale='Viridis',  # Palette contrastée
            colorbar=dict(title='Fréquence' if language == 'fr' else 'Frequency')
        ),
        layout=go.Layout(
            title=t['heatmap_title'],
            xaxis={'title': 'Rating'},
            yaxis={'title': 'Sentiment' if language == 'fr' else 'Sentiment'},
            template='plotly_white',
            height=300
        )
    )
    heatmap_fig.add_annotation(
        text=f"Max: {heatmap_data.values.max()}",
        xref="paper", yref="paper",
        x=0.95, y=0.95, showarrow=False
    )

    return [t['frequences_title'], wordcloud_fig, wordfreq_fig, grouped_fig, heatmap_fig, df.to_dict('records')]
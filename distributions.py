import dash
from dash import html, dcc, callback, Output, Input, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from sklearn.decomposition import PCA
from data_utils import get_feedback_data

# Dictionnaire de traductions
translations = {
    'fr': {
        'distributions_title': 'Distributions',
        'boxplot_title': 'Distribution des Notes par Sentiment',
        'violin_title': 'Densité des Notes par Sentiment',
        'scatter_title': 'Répartition des Commentaires par Composantes',
        'bubble_title': 'Taille des Notes par Sentiment'
    },
    'en': {
        'distributions_title': 'Distributions',
        'boxplot_title': 'Distribution of Ratings by Sentiment',
        'violin_title': 'Density of Ratings by Sentiment',
        'scatter_title': 'Distribution of Comments by Components',
        'bubble_title': 'Size of Ratings by Sentiment'
    }
}

def layout():
    return html.Div([
        html.H2(id='distributions-title', className="text-center mb-4", style={"color": "#2c3e50", "font-family": "Roboto, sans-serif", "font-weight": "bold"}),
        dcc.Store(id='distribution-data-store'),
        dbc.Row([
            dbc.Col(dcc.Graph(id='boxplot'), width=6, className="distribution-graph-col"),
            dbc.Col(dcc.Graph(id='violin'), width=6, className="distribution-graph-col")
        ]),
        dbc.Row([
            dbc.Col(dcc.Graph(id='scatter'), width=6, className="distribution-graph-col"),
            dbc.Col(dcc.Graph(id='bubble'), width=6, className="distribution-graph-col")
        ])
    ], className="p-4")

@callback(
    [Output('distributions-title', 'children'),
     Output('boxplot', 'figure'),
     Output('violin', 'figure'),
     Output('scatter', 'figure'),
     Output('bubble', 'figure'),
     Output('distribution-data-store', 'data')],
    [Input('filters-store', 'data'),
     Input('distributions-title-store', 'data'),
     Input('interval-component', 'n_intervals')]  # Store temporaire pour la langue
)
def update_distribution_charts(filters, title_from_store, real_time_update):
    language = 'fr' if not title_from_store else ('en' if title_from_store in translations['en'].values() else 'fr')
    t = translations[language]

    df = get_feedback_data(filters)
    if df.empty:
        return [t['distributions_title']] + [go.Figure()] * 4 + [{}]

    # Préparation des données
    df['rating'] = pd.to_numeric(df['rating'], errors='coerce')
    df = df.dropna(subset=['rating'])

    # Graphique 10: Distribution des Notes par Sentiment (Boxplot)
    sentiment_colors = {'positive': '#27AE60', 'neutral': '#F39C12', 'negative': '#E74C3C'}
    boxplot_fig = px.box(
        df,
        y='rating',
        color='sentiment',
        title=f"{t['boxplot_title']} (Moyenne: {df['rating'].mean():.2f})",
        labels={'rating': 'Note' if language == 'fr' else 'Rating', 'sentiment': 'Sentiment'},
        color_discrete_map=sentiment_colors,
        template='plotly_white',
        height=300
    )
    boxplot_fig.add_trace(go.Scatter(
        x=df['sentiment'].unique(),
        y=[df[df['sentiment'] == s]['rating'].mean() for s in df['sentiment'].unique()],
        mode='markers',
        name='Moyenne',
        marker=dict(color='#3498DB', size=10)
    ))

    # Graphique 11: Densité des Notes par Sentiment (Violin)
    violin_fig = px.violin(
        df,
        y='rating',
        color='sentiment',
        title=f"{t['violin_title']} (Médiane: {df['rating'].median():.2f})",
        labels={'rating': 'Note' if language == 'fr' else 'Rating', 'sentiment': 'Sentiment'},
        color_discrete_map=sentiment_colors,
        template='plotly_white',
        height=300
    )
    violin_fig.add_trace(go.Scatter(
        x=df['sentiment'].unique(),
        y=[df[df['sentiment'] == s]['rating'].median() for s in df['sentiment'].unique()],
        mode='markers',
        name='Médiane',
        marker=dict(color='#E74C3C', size=10)
    ))

    # Graphique 12: Répartition des Commentaires par Composantes (Scatter)
    text_features = df['comment'].dropna().apply(lambda x: len(str(x)))  # Longueur des commentaires
    X = np.vstack([df['rating'].values, text_features.values]).T
    pca = PCA(n_components=2)
    X_pca = pca.fit_transform(X)
    scatter_df = pd.DataFrame(X_pca, columns=['PC1', 'PC2'])
    scatter_df['sentiment'] = df['sentiment']
    scatter_fig = px.scatter(
        scatter_df,
        x='PC1',
        y='PC2',
        color='sentiment',
        title=f"{t['scatter_title']} (Variance Expliquée: {sum(pca.explained_variance_ratio_)*100:.1f}%)",
        labels={'PC1': 'Composante Principale 1', 'PC2': 'Composante Principale 2', 'sentiment': 'Sentiment'},
        color_discrete_map=sentiment_colors,
        template='plotly_white',
        height=300
    )
    scatter_fig.update_traces(marker=dict(size=10))

    # Graphique 13: Taille des Notes par Sentiment (Bubble)
    bubble_fig = px.scatter(
        df,
        x='rating',
        y='sentiment',
        size='rating',  # Taille proportionnelle à la note
        color='sentiment',
        title=t['bubble_title'],
        labels={'rating': 'Note' if language == 'fr' else 'Rating', 'sentiment': 'Sentiment'},
        color_discrete_map=sentiment_colors,
        template='plotly_white',
        height=300
    )
    bubble_fig.update_traces(marker=dict(sizemin=10, sizemode='area'))
    bubble_fig.add_annotation(
        text=f"Total: {len(df)}",
        xref="paper", yref="paper",
        x=0.95, y=0.95, showarrow=False
    )

    return [t['distributions_title'], boxplot_fig, violin_fig, scatter_fig, bubble_fig, df.to_dict('records')]
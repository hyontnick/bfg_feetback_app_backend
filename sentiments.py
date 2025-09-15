import dash
from dash import html, dcc, callback, Output, Input, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from data_utils import get_feedback_data

# Dictionnaire de traductions (à synchroniser avec app.py)
translations = {
    'fr': {
        'sentiments_title': 'Sentiments',
        'bar_chart_title': 'Distribution des Notes',
        'pie_chart_title': 'Répartition par Sentiment',
        'stacked_bar_chart_title': 'Notes par Sentiment',
        'line_chart_title': 'Évolution du Nombre de Commentaires',
        'area_chart_title': 'Évolution Cumulative des Commentaires'
    },
    'en': {
        'sentiments_title': 'Sentiments',
        'bar_chart_title': 'Rating Distribution',
        'pie_chart_title': 'Sentiment Distribution',
        'stacked_bar_chart_title': 'Ratings by Sentiment',
        'line_chart_title': 'Evolution of Comment Count',
        'area_chart_title': 'Cumulative Evolution of Comments'
    }
}

def layout():
    return html.Div([
        html.H2(id='sentiments-title', className="text-center mb-4", style={"color": "#2c3e50", "font-family": "Roboto, sans-serif", "font-weight": "bold"}),
        dcc.Store(id='sentiment-data-store'),
        dbc.Row([
            dbc.Col(dcc.Graph(id='bar-chart'), width=4, className="sentiment-graph-col"),
            dbc.Col(dcc.Graph(id='pie-chart'), width=4, className="sentiment-graph-col"),
            dbc.Col(dcc.Graph(id='stacked-bar-chart'), width=4, className="sentiment-graph-col")
        ]),
        dbc.Row([
            dbc.Col(dcc.Graph(id='line-chart'), width=6, className="sentiment-graph-col"),
            dbc.Col(dcc.Graph(id='area-chart'), width=6, className="sentiment-graph-col")
        ])
    ], className="p-4")

@callback(
    [Output('sentiments-title', 'children'),
     Output('bar-chart', 'figure'),
     Output('pie-chart', 'figure'),
     Output('stacked-bar-chart', 'figure'),
     Output('line-chart', 'figure'),
     Output('area-chart', 'figure'),
     Output('sentiment-data-store', 'data')],
    [Input('filters-store', 'data'),
     Input('language-store', 'data'),
     Input('interval-component', 'n_intervals')]  # Déclencheur d'intervalle
)
def update_sentiment_charts(filters, language, real_time_update):
    t = translations.get(language, translations['fr'])  # Par défaut à 'fr' si language est None

    df = get_feedback_data(filters)
    if df.empty:
        return [t['sentiments_title']] + [go.Figure()] * 5 + [{}]

    df['timestamp'] = pd.to_datetime(df['timestamp']).dt.date

    # Graphique 1: Diagramme en barres
    bar_data = df['rating'].value_counts().sort_index()
    bar_fig = go.Figure(
        data=[go.Bar(
            x=bar_data.index,
            y=bar_data.values,
            marker_color=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEEAD'],  # Couleurs vives et distinctes
            text=bar_data.values,
            textposition='auto'
        )],
        layout=go.Layout(
            title=f"{t['bar_chart_title']} (Moyenne: {df['rating'].mean():.2f})",
            xaxis={'title': 'Notes' if language == 'fr' else 'Ratings', 'tickmode': 'linear'},
            yaxis={'title': 'Nombre de Commentaires' if language == 'fr' else 'Number of Comments'},
            template='plotly_white',
            height=300,
            showlegend=False
        )
    )
    bar_fig.add_annotation(
        text=f"Max: {bar_data.max()}",
        xref="paper", yref="paper",
        x=1, y=1.1, showarrow=False
    )

    # Graphique 2: Diagramme circulaire
    sentiment_colors = {'positive': '#27AE60', 'neutral': '#F39C12', 'negative': '#E74C3C'}  # Couleurs caractéristiques
    pie_fig = px.pie(
        df,
        names='sentiment',
        title=t['pie_chart_title'],
        hole=0.3,
        color='sentiment',
        color_discrete_map=sentiment_colors,
        height=300
    )
    pie_fig.update_traces(textinfo='percent+label', pull=[0.1 if s == df['sentiment'].mode()[0] else 0 for s in df['sentiment']])

    # Graphique 3: Diagramme en barres empilées
    stacked_fig = go.Figure(
        data=[
            go.Bar(name='Positif' if language == 'fr' else 'Positive', x=df['rating'].value_counts().index, y=df[df['sentiment'] == 'positive']['rating'].value_counts().fillna(0), marker_color='#27AE60'),
            go.Bar(name='Neutre' if language == 'fr' else 'Neutral', x=df['rating'].value_counts().index, y=df[df['sentiment'] == 'neutral']['rating'].value_counts().fillna(0), marker_color='#F39C12'),
            go.Bar(name='Négatif' if language == 'fr' else 'Negative', x=df['rating'].value_counts().index, y=df[df['sentiment'] == 'negative']['rating'].value_counts().fillna(0), marker_color='#E74C3C')
        ],
        layout=go.Layout(
            title=t['stacked_bar_chart_title'],
            xaxis={'title': 'Notes' if language == 'fr' else 'Ratings'},
            yaxis={'title': 'Nombre de Commentaires' if language == 'fr' else 'Number of Comments'},
            barmode='stack',
            template='plotly_white',
            height=300,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
    )

    # Graphique 4: Graphique en ligne
    line_data = df.groupby(df['timestamp']).size().reset_index(name='counts')
    line_fig = px.line(
        line_data,
        x='timestamp',
        y='counts',
        title=t['line_chart_title'],
        labels={'timestamp': 'Date', 'counts': 'Nombre de Commentaires' if language == 'fr' else 'Number of Comments'},
        template='plotly_white',
        height=300,
        color_discrete_sequence=['#3498DB']
    )
    line_fig.add_trace(go.Scatter(x=line_data['timestamp'], y=line_data['counts'].rolling(window=3).mean(), mode='lines', name='Tendance', line=dict(color='#E74C3C', dash='dash')))
    line_fig.add_annotation(
        text=f"Moyenne: {line_data['counts'].mean():.2f}",
        xref="paper", yref="paper",
        x=0.95, y=0.95, showarrow=False, font=dict(color="#E74C3C")
    )

    # Graphique 5: Graphique en aires
    area_data = df.groupby(df['timestamp']).size().cumsum().reset_index(name='cumulative_counts')
    area_fig = go.Figure(
        data=[go.Scatter(
            x=area_data['timestamp'],
            y=area_data['cumulative_counts'],
            fill='tozeroy',
            mode='none',
            fillcolor='rgba(96, 125, 139, 0.5)'  # Gradient gris-bleu
        )],
        layout=go.Layout(
            title=t['area_chart_title'],
            xaxis={'title': 'Date'},
            yaxis={'title': 'Nombre de Commentaires Cumulés' if language == 'fr' else 'Cumulative Number of Comments'},
            template='plotly_white',
            height=300,
            showlegend=False
        )
    )
    area_fig.add_annotation(
        text=f"Total: {area_data['cumulative_counts'].iloc[-1]}",
        xref="paper", yref="paper",
        x=0.95, y=0.95, showarrow=False
    )

    return [t['sentiments_title']] + [bar_fig, pie_fig, stacked_fig, line_fig, area_fig] + [df.to_dict('records')]
import os
import dash
from dash import html, dcc, callback, Output, Input, State, ALL
import dash_bootstrap_components as dbc
import pandas as pd
from sqlalchemy import create_engine
import re
from datetime import datetime, timedelta
from collections import Counter
import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from data_utils import get_feedback_data

# Configuration de la connexion à Supabase
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("La variable d'environnement DATABASE_URL n'est pas définie")
engine = create_engine(DATABASE_URL)

# Initialisation de l'application Dash avec un thème Bootstrap et Font Awesome
app = dash.Dash(__name__, update_title=None, external_stylesheets=[dbc.themes.BOOTSTRAP, 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css'], suppress_callback_exceptions=True)

app.title = "Feedback"

server = app.server  # Expose Flask server pour endpoints custom

# Dictionnaire pour le multilinguisme
translations = {
    'fr': {
        'dashboard_title': 'Tableau de Bord Feedback',
        'total_comments': 'Nombre total de commentaires',
        'avg_rating': 'Moyenne des notes',
        'top_ratings': 'Nombre de ratings max',
        'min_rating': 'Note minimale',
        'positive_comments': 'Commentaires positifs',
        'neutral_comments': 'Commentaires neutres',
        'negative_comments': 'Commentaires négatifs',
        'peak_hour': 'Heure de pic des commentaires',
        'avg_hourly_freq': 'Fréquence horaire moyenne',
        'avg_time_between': 'Durée moyenne entre commentaires',
        'emoji_count': 'Nombre de commentaires avec émojis',
        'unique_users': 'Nombre d\'utilisateurs uniques',
        'dominant_lang': 'Langue dominante',
        'top_emojis': 'Top 3 emojis',
        'tab_sentiment': 'KPI',
        'tab_evolution': 'Sentiments',
        'tab_frequence': 'Fréquences',
        'tab_comparaison': 'Distributions',
        'tab_regroupement': 'Regroupement et Table',
        'filter_language': 'Langue',
        'filter_sentiment': 'Sentiment',
        'filter_rating': 'Note',
        'filter_date': 'Date',
        'filter_unique_code': 'Code unique',
        'filter_text_search': 'Recherche texte',
        'download_pdf': 'Télécharger PDF',
        'filters': 'Filtres',
        'sentiments_title': 'Sentiments',
        'frequences_title': 'Fréquences',
        'distributions_title': 'Distributions',
        'regroupement_title': 'Regroupement et Table'
    },
    'en': {
        'dashboard_title': 'Feedback Dashboard',
        'total_comments': 'Total Number of Comments',
        'avg_rating': 'Average Rating',
        'top_ratings': 'Number of Max Ratings',
        'min_rating': 'Minimum Rating',
        'positive_comments': 'Positive Comments',
        'neutral_comments': 'Neutral Comments',
        'negative_comments': 'Negative Comments',
        'peak_hour': 'Peak Hour of Comments',
        'avg_hourly_freq': 'Average Hourly Frequency',
        'avg_time_between': 'Average Time Between Comments',
        'emoji_count': 'Number of Comments with Emojis',
        'unique_users': 'Number of Unique Users',
        'dominant_lang': 'Dominant Language',
        'top_emojis': 'Top 3 Emojis',
        'tab_sentiment': 'KPI',
        'tab_evolution': 'Sentiments',
        'tab_frequence': 'Frequencies',
        'tab_comparaison': 'Distributions',
        'tab_regroupement': 'Grouping and Table',
        'filter_language': 'Language',
        'filter_sentiment': 'Sentiment',
        'filter_rating': 'Rating',
        'filter_date': 'Date',
        'filter_unique_code': 'Unique Code',
        'filter_text_search': 'Text Search',
        'download_pdf': 'Download PDF',
        'filters': 'Filters',
        'sentiments_title': 'Sentiments',
        'frequences_title': 'Frequencies',
        'distributions_title': 'Distributions',
        'regroupement_title': 'Grouping and Table',
    }
}

# Endpoint /health pour monitoring
@server.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok"})
    
# Calcul des KPI avec évolution sur 1 semaine
def calculate_kpis(df):
    total_comments = len(df)
    avg_rating = df['rating'].mean() if total_comments > 0 else 0
    sentiment_counts = df['sentiment'].value_counts().to_dict()
    positive = sentiment_counts.get('positive', 0)
    neutral = sentiment_counts.get('neutral', 0)
    negative = sentiment_counts.get('negative', 0)
    top_ratings = len(df[df['rating'] == df['rating'].max()]) if total_comments > 0 else 0
    hourly_freq = df['timestamp'].dt.hour.value_counts().idxmax() if total_comments > 0 and not df['timestamp'].empty else 'N/A'
    lang_counts = df['language'].value_counts().to_dict()
    dominant_lang = max(lang_counts.items(), key=lambda x: x[1])[0] if lang_counts else 'N/A'
    dominant_lang_count = lang_counts.get(dominant_lang, 0)
    emoji_count = df['comment'].str.contains(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F700-\U0001F77F\U0001F780-\U0001F7FF\U0001F800-\U0001F8FF\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF\U00002702-\U000027B0\U000024C2-\U0001F251]').sum()
    unique_users = df['unique_code'].nunique()
    min_rating = df['rating'].min() if total_comments > 0 else 0
    time_diffs = df['timestamp'].sort_values().diff().dt.total_seconds() / 3600
    avg_time_between = time_diffs.mean() if len(time_diffs) > 1 else 0
    avg_hourly_freq = total_comments / (24 * 7 if total_comments > 0 else 1)

    # Calcul de l'évolution sur les dernières 7 jours
    now = datetime.now()
    one_week_ago = now - timedelta(days=7)
    df_recent = df[df['timestamp'] >= one_week_ago]
    df_previous = df[df['timestamp'] < one_week_ago]

    def calculate_change(current, previous):
        if previous == 0:
            return 99.99 if current > 0 else -99.99 if current == 0 else 0
        change = ((current - previous) / abs(previous)) * 100
        return max(min(change, 99.99), -99.99)

    total_comments_prev = len(df_previous)
    avg_rating_prev = df_previous['rating'].mean() if total_comments_prev > 0 else 0
    positive_prev = df_previous['sentiment'].value_counts().get('positive', 0)
    neutral_prev = df_previous['sentiment'].value_counts().get('neutral', 0)
    negative_prev = df_previous['sentiment'].value_counts().get('negative', 0)
    top_ratings_prev = len(df_previous[df_previous['rating'] == df_previous['rating'].max()]) if total_comments_prev > 0 else 0
    min_rating_prev = df_previous['rating'].min() if total_comments_prev > 0 else 0
    time_diffs_prev = df_previous['timestamp'].sort_values().diff().dt.total_seconds() / 3600
    avg_time_between_prev = time_diffs_prev.mean() if len(time_diffs_prev) > 1 else 0
    avg_hourly_freq_prev = total_comments_prev / (24 * 7 if total_comments_prev > 0 else 1)
    unique_users_prev = df_previous['unique_code'].nunique()
    emoji_count_prev = df_previous['comment'].str.contains(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F700-\U0001F77F\U0001F780-\U0001F7FF\U0001F800-\U0001F8FF\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF\U00002702-\U000027B0\U000024C2-\U0001F251]').sum()

    # Évolution en pourcentage
    total_comments_change = calculate_change(total_comments, total_comments_prev)
    avg_rating_change = calculate_change(avg_rating, avg_rating_prev)
    positive_change = calculate_change(positive, positive_prev)
    neutral_change = calculate_change(neutral, neutral_prev)
    negative_change = calculate_change(negative, negative_prev)
    top_ratings_change = calculate_change(top_ratings, top_ratings_prev)
    min_rating_change = calculate_change(min_rating, min_rating_prev)
    avg_time_between_change = calculate_change(avg_time_between, avg_time_between_prev)
    avg_hourly_freq_change = calculate_change(avg_hourly_freq, avg_hourly_freq_prev)
    unique_users_change = calculate_change(unique_users, unique_users_prev)
    emoji_count_change = calculate_change(emoji_count, emoji_count_prev)

    # Icône et couleur selon l'évolution
    def get_trend_icon(change):
        if change > 0:
            return (html.I(className="fas fa-arrow-up", style={"color": "green"}), f"+{change:.2f}%")
        elif change < 0:
            return (html.I(className="fas fa-arrow-down", style={"color": "red"}), f"{change:.2f}%")
        else:
            return (html.I(className="fas fa-minus", style={"color": "orange"}), "0%")

    emoji_pattern = re.compile(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F700-\U0001F77F\U0001F780-\U0001F7FF\U0001F800-\U0001F8FF\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF\U00002702-\U000027B0\U000024C2-\U0001F251]')
    all_emojis = []
    for comment in df['comment']:
        emojis = emoji_pattern.findall(comment)
        all_emojis.extend(emojis)
    top_emojis = Counter(all_emojis).most_common(3) if all_emojis else []

    return {
        'total_comments': total_comments,
        'avg_rating': round(avg_rating, 2),
        'positive': positive,
        'neutral': neutral,
        'negative': negative,
        'top_ratings': top_ratings,
        'peak_hour': hourly_freq,
        'dominant_lang': dominant_lang,
        'dominant_lang_count': dominant_lang_count,
        'emoji_count': emoji_count,
        'unique_users': unique_users,
        'min_rating': min_rating,
        'avg_time_between': round(avg_time_between, 2),
        'avg_hourly_freq': round(avg_hourly_freq, 2),
        'top_emojis': top_emojis,
        'total_comments_trend': get_trend_icon(total_comments_change),
        'avg_rating_trend': get_trend_icon(avg_rating_change),
        'positive_trend': get_trend_icon(positive_change),
        'neutral_trend': get_trend_icon(neutral_change),
        'negative_trend': get_trend_icon(negative_change),
        'top_ratings_trend': get_trend_icon(top_ratings_change),
        'min_rating_trend': get_trend_icon(min_rating_change),
        'avg_time_between_trend': get_trend_icon(avg_time_between_change),
        'avg_hourly_freq_trend': get_trend_icon(avg_hourly_freq_change),
        'unique_users_trend': get_trend_icon(unique_users_change),
        'emoji_count_trend': get_trend_icon(emoji_count_change)
    }

# Modal pour les filtres sur petits écrans
filter_modal = dbc.Modal(
    [
        dbc.ModalHeader(dbc.ModalTitle(translations['fr']['filters'])),
        dbc.ModalBody([
            # Filtre Langue
            dbc.Row([
                html.I(className="fas fa-globe"),
                dcc.Dropdown(
                    id='filter-language-modal',
                    options=[{'label': lang, 'value': lang} for lang in pd.read_sql_query("SELECT DISTINCT language FROM feedback", engine)['language'].dropna().unique()],
                    multi=True,
                    placeholder=translations['fr']['filter_language']
                )
            ], className="mb-3"),
            # Filtre Sentiment
            dbc.Row([
                html.I(className="fas fa-heart"),
                dbc.Checklist(
                    id='filter-sentiment-modal',
                    options=[
                        {'label': [html.I(className="fas fa-smile"), " Positive"], 'value': 'positive'},
                        {'label': [html.I(className="fas fa-meh"), " Neutral"], 'value': 'neutral'},
                        {'label': [html.I(className="fas fa-frown"), " Negative"], 'value': 'negative'}
                    ],
                    value=[],
                    inline=True
                )
            ], className="mb-3"),
            # Filtre Note
            dbc.Row([
                html.I(className="fas fa-star"),
                dcc.RangeSlider(
                    id='filter-rating-modal',
                    min=0,
                    max=5,
                    step=0.5,
                    value=[0, 5],
                    marks={i: str(i) for i in range(0, 6)},
                    tooltip={"placement": "bottom", "always_visible": True}
                )
            ], className="mb-3"),
            # Filtre Date
            dbc.Row([
                html.I(className="fas fa-calendar"),
                dcc.DatePickerRange(
                    id='filter-date-modal',
                    start_date=pd.read_sql_query("SELECT MIN(timestamp)::text AS min_timestamp FROM feedback", engine)['min_timestamp'][0],
                    end_date=pd.to_datetime('today'),
                    display_format='YYYY-MM-DD'
                )
            ], className="mb-3"),
            # Bouton de téléchargement PDF dans le modal
            dbc.Button(
                [html.I(className="fas fa-download"), " ", translations['fr']['download_pdf']],
                id='download-pdf-modal',
                color="success",
                className="mt-3"
            ),
        ]),
        dbc.ModalFooter(
            dbc.Button("Close", id="close-filter-modal", className="ml-auto")
        ),
    ],
    id="filter-modal",
    is_open=False,
)

# Layout de l'application
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    dbc.Navbar(
        [
            # Logo à gauche
            dbc.NavbarBrand(
                html.Img(src=app.get_asset_url('logo.png'), height="40px"),
                className="ms-2"
            ),
            # Titre centré
            dbc.NavbarBrand(
                id="navbar-title",
                className="mx-auto"
            ),
            # Bouton hamburger pour filtres sur petits écrans
            dbc.NavbarToggler(id="navbar-toggler", n_clicks=0, className="d-md-none"),
            # Contenu à droite (langue et retour)
            dbc.Nav(
                [
                    # Sélection de langue
                    dbc.DropdownMenu(
                        label=[html.I(className="fas fa-globe"), " Language"],
                        nav=True,
                        in_navbar=True,
                        align_end=True,
                        children=[
                            dbc.DropdownMenuItem("Français", id="lang-fr"),
                            dbc.DropdownMenuItem("English", id="lang-en"),
                        ],
                    ),
                    # Bouton de retour à l'accueil
                    dbc.Button(
                        [html.I(className="fas fa-arrow-left"), " Home"],
                        id="home-button",
                        color="primary",
                        className="ms-2",
                        n_clicks=0
                    ),
                ],
                className="ms-auto",
                navbar=True,
            ),
        ],
        color="#2c3e50",
        dark=True,
        className="mb-4"
    ),
    dbc.Tabs([
        dbc.Tab(label=translations['fr']['tab_sentiment'], tab_id="tab-sentiment", label_style={"color": "#34495e"}, active_label_style={"color": "#ffffff", "background-color": "#2c3e50"}, className="tab-with-icon", id="tab-sentiment-icon"),
        dbc.Tab(label=translations['fr']['tab_evolution'], tab_id="tab-evolution", label_style={"color": "#34495e"}, active_label_style={"color": "#ffffff", "background-color": "#2c3e50"}, className="tab-with-icon", id="tab-evolution-icon"),
        dbc.Tab(label=translations['fr']['tab_frequence'], tab_id="tab-frequence", label_style={"color": "#34495e"}, active_label_style={"color": "#ffffff", "background-color": "#2c3e50"}, className="tab-with-icon", id="tab-frequence-icon"),
        dbc.Tab(label=translations['fr']['tab_comparaison'], tab_id="tab-comparaison", label_style={"color": "#34495e"}, active_label_style={"color": "#ffffff", "background-color": "#2c3e50"}, className="tab-with-icon", id="tab-comparaison-icon"),
        dbc.Tab(label=translations['fr']['tab_regroupement'], tab_id="tab-regroupement", label_style={"color": "#34495e"}, active_label_style={"color": "#ffffff", "background-color": "#2c3e50"}, className="tab-with-icon", id="tab-regroupement-icon"),
    ], id="tabs", active_tab="tab-sentiment", className="nav-tabs-custom"),
    dbc.Row([
        # Barre latérale des filtres (visible uniquement sur grands écrans, largeur ajustée)
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5([html.I(className="fas fa-filter"), " Filtres"], className="mb-0")),
                dbc.CardBody([
                    # Filtre Langue
                    dbc.Row([
                        html.I(className="fas fa-globe"),
                        dcc.Dropdown(
                            id='filter-language',
                            options=[{'label': lang, 'value': lang} for lang in pd.read_sql_query("SELECT DISTINCT language FROM feedback", engine)['language'].dropna().unique()],
                            multi=True,
                            placeholder=translations['fr']['filter_language']
                        )
                    ], className="mb-3"),
                    # Filtre Sentiment
                    dbc.Row([
                        html.I(className="fas fa-heart"),
                        dbc.Checklist(
                            id='filter-sentiment',
                            options=[
                                {'label': [html.I(className="fas fa-smile"), " Positive"], 'value': 'positive'},
                                {'label': [html.I(className="fas fa-meh"), " Neutral"], 'value': 'neutral'},
                                {'label': [html.I(className="fas fa-frown"), " Negative"], 'value': 'negative'}
                            ],
                            value=[],
                            inline=True
                        )
                    ], className="mb-3"),
                    # Filtre Note
                    dbc.Row([
                        html.I(className="fas fa-star"),
                        dcc.RangeSlider(
                            id='filter-rating',
                            min=0,
                            max=5,
                            step=0.5,
                            value=[0, 5],
                            marks={i: str(i) for i in range(0, 6)},
                            tooltip={"placement": "bottom", "always_visible": True}
                        )
                    ], className="mb-3"),
                    # Filtre Date
                    dbc.Row([
                        html.I(className="fas fa-calendar"),
                        dcc.DatePickerRange(
                            id='filter-date',
                            start_date=pd.read_sql_query("SELECT MIN(timestamp)::text AS min_timestamp FROM feedback", engine)['min_timestamp'][0],
                            end_date=pd.to_datetime('today'),
                            display_format='YYYY-MM-DD'
                        )
                    ], className="mb-3"),
                    # Bouton de téléchargement PDF
                    dbc.Button(
                        [html.I(className="fas fa-download"), " ", translations['fr']['download_pdf']],
                        id='download-pdf',
                        color="success",
                        className="mt-3"
                    ),
                ])
            ], style={"height": "100%", "position": "sticky", "top": "10px"})
        ], width={"size": 2, "order": "first"}, className="d-none d-md-block", style={"padding": "10px", "background-color": "#f8f9fa"}),
        # Contenu principal (étendu sur grands écrans)
        dbc.Col([
            html.Div(id="tab-content", className="p-4")
        ], width={"size": 10, "order": "last"}, className="col-md-10 col-lg-10"),
    ]),
    filter_modal,  # Ajout du modal pour petits écrans
    dcc.Store(id='language-store', data='fr'),  # Stocke la langue sélectionnée
    dcc.Store(id='filters-store', data={}),  # Stocke les filtres appliqués
    dcc.Download(id="download"),  # Composant de téléchargement explicite
    dcc.Interval(id='interval-component', interval=5000, n_intervals=0)  # Mise à jour toutes les 5 secondes
])

# Callback pour ajouter les icônes dynamiquement sans doublons
app.clientside_callback(
    """
    function() {
        const icons = {
            'tab-sentiment-icon': 'fas fa-heart',
            'tab-evolution-icon': 'fas fa-clock',
            'tab-frequence-icon': 'fas fa-chart-bar',
            'tab-comparaison-icon': 'fas fa-balance-scale',
            'tab-regroupement-icon': 'fas fa-table'
        };
        for (let id in icons) {
            const tab = document.getElementById(id);
            if (tab) {
                const existingIcons = tab.getElementsByTagName('i');
                while (existingIcons.length > 0) {
                    existingIcons[0].remove();
                }
                const icon = document.createElement('i');
                icon.className = icons[id];
                tab.insertBefore(icon, tab.firstChild);
                tab.style.display = 'flex';
                tab.style.alignItems = 'center';
                tab.style.gap = '8px';
            }
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output('tabs', 'style'),
    Input('tabs', 'children')
)

# Callback pour changer la langue
@callback(
    Output('language-store', 'data'),
    Input('lang-fr', 'n_clicks'),
    Input('lang-en', 'n_clicks'),
    State('language-store', 'data'),
    prevent_initial_call=True
)
def update_language(fr_clicks, en_clicks, current_language):
    ctx = dash.callback_context
    if not ctx.triggered:
        return current_language
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if button_id == 'lang-fr':
        return 'fr'
    elif button_id == 'lang-en':
        return 'en'
    return current_language

# Callback pour mettre à jour le titre et les onglets avec la langue
@callback(
    [Output("navbar-title", "children"),
     Output("tabs", "children"),
     Output("filter-modal", "children")],
    Input('language-store', 'data')
)
def update_language_content(language):
    t = translations[language]
    navbar_title = html.H4(t['dashboard_title'], style={"color": "#ffffff", "margin": "0"})
    tabs = [
        dbc.Tab(label=t['tab_sentiment'], tab_id="tab-sentiment", label_style={"color": "#34495e"}, active_label_style={"color": "#ffffff", "background-color": "#2c3e50"}, className="tab-with-icon", id="tab-sentiment-icon"),
        dbc.Tab(label=t['tab_evolution'], tab_id="tab-evolution", label_style={"color": "#34495e"}, active_label_style={"color": "#ffffff", "background-color": "#2c3e50"}, className="tab-with-icon", id="tab-evolution-icon"),
        dbc.Tab(label=t['tab_frequence'], tab_id="tab-frequence", label_style={"color": "#34495e"}, active_label_style={"color": "#ffffff", "background-color": "#2c3e50"}, className="tab-with-icon", id="tab-frequence-icon"),
        dbc.Tab(label=t['tab_comparaison'], tab_id="tab-comparaison", label_style={"color": "#34495e"}, active_label_style={"color": "#ffffff", "background-color": "#2c3e50"}, className="tab-with-icon", id="tab-comparaison-icon"),
        dbc.Tab(label=t['tab_regroupement'], tab_id="tab-regroupement", label_style={"color": "#34495e"}, active_label_style={"color": "#ffffff", "background-color": "#2c3e50"}, className="tab-with-icon", id="tab-regroupement-icon"),
    ]
    modal_content = [
        dbc.ModalHeader(dbc.ModalTitle(t['filters'])),
        dbc.ModalBody([
            # Filtre Langue
            dbc.Row([
                html.I(className="fas fa-globe"),
                dcc.Dropdown(
                    id='filter-language-modal',
                    options=[{'label': lang, 'value': lang} for lang in pd.read_sql_query("SELECT DISTINCT language FROM feedback", engine)['language'].dropna().unique()],
                    multi=True,
                    placeholder=t['filter_language']
                )
            ], className="mb-3"),
            # Filtre Sentiment
            dbc.Row([
                html.I(className="fas fa-heart"),
                dbc.Checklist(
                    id='filter-sentiment-modal',
                    options=[
                        {'label': [html.I(className="fas fa-smile"), " Positive"], 'value': 'positive'},
                        {'label': [html.I(className="fas fa-meh"), " Neutral"], 'value': 'neutral'},
                        {'label': [html.I(className="fas fa-frown"), " Negative"], 'value': 'negative'}
                    ],
                    value=[],
                    inline=True
                )
            ], className="mb-3"),
            # Filtre Note
            dbc.Row([
                html.I(className="fas fa-star"),
                dcc.RangeSlider(
                    id='filter-rating-modal',
                    min=0,
                    max=5,
                    step=0.5,
                    value=[0, 5],
                    marks={i: str(i) for i in range(0, 6)},
                    tooltip={"placement": "bottom", "always_visible": True}
                )
            ], className="mb-3"),
            # Filtre Date
            dbc.Row([
                html.I(className="fas fa-calendar"),
                dcc.DatePickerRange(
                    id='filter-date-modal',
                    start_date=pd.read_sql_query("SELECT MIN(timestamp)::text FROM feedback", engine)['MIN(timestamp)'][0],
                    end_date=pd.to_datetime('today'),
                    display_format='YYYY-MM-DD'
                )
            ], className="mb-3"),
            # Bouton de téléchargement PDF dans le modal
            dbc.Button(
                [html.I(className="fas fa-download"), " ", t['download_pdf']],
                id='download-pdf-modal',
                color="success",
                className="mt-3"
            ),
        ]),
        dbc.ModalFooter(
            dbc.Button("Close", id="close-filter-modal", className="ml-auto")
        ),
    ]
    return navbar_title, tabs, modal_content

@callback(
    Output('filters-store', 'data'),
    Input('filter-language', 'value'),
    Input('filter-sentiment', 'value'),
    Input('filter-rating', 'value'),
    Input('filter-date', 'start_date'),
    Input('filter-date', 'end_date'),
    Input('filter-language-modal', 'value'),
    Input('filter-sentiment-modal', 'value'),
    Input('filter-rating-modal', 'value'),
    Input('filter-date-modal', 'start_date'),
    Input('filter-date-modal', 'end_date')
)
def update_filters(lang, sent, rating, start_date, end_date, lang_modal, sent_modal, rating_modal, start_date_modal, end_date_modal):
    try:
        filters = {}
        ctx = dash.callback_context
        triggered_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None

        # Utiliser la dernière valeur modifiée, que ce soit du modal ou de la barre latérale
        language = lang_modal if triggered_id == 'filter-language-modal' else lang
        sentiment = sent_modal if triggered_id == 'filter-sentiment-modal' else sent
        rating_range = rating_modal if triggered_id == 'filter-rating-modal' else rating
        date_range = [pd.to_datetime(start_date_modal), pd.to_datetime(end_date_modal)] if triggered_id in ['filter-date-modal', 'filter-date-modal-end_date'] else \
                     [pd.to_datetime(start_date), pd.to_datetime(end_date)] if start_date and end_date else None

        # Validation et ajout des filtres
        if language and any(l for l in language if l):
            filters['language'] = [l for l in language if l]
        if sentiment and any(s for s in sentiment if s):
            filters['sentiment'] = [s for s in sentiment if s]
        if rating_range and len(rating_range) == 2 and rating_range[0] is not None and rating_range[1] is not None:
            filters['rating_range'] = rating_range
        if date_range and len(date_range) == 2 and date_range[0] is not None and date_range[1] is not None:
            filters['date_range'] = date_range

        return filters
    except Exception as e:
        return {}

# Importation des layouts des onglets
from sentiments import layout as evolution_layout, update_sentiment_charts
from frequences import layout as frequence_layout, update_frequence_charts
from distributions import layout as distribution_layout, update_distribution_charts
from regroupement import layout as regroupement_layout, update_regroupement_table

# Callback pour mettre à jour le contenu des onglets avec les filtres
@callback(
    Output("tab-content", "children"),
    Input("tabs", "active_tab"),
    Input('filters-store', 'data'),
    Input('language-store', 'data')
)
def render_tab_content(active_tab, filters, language):
    df = get_feedback_data(filters)
    kpis = calculate_kpis(df)
    t = translations[language]
    if active_tab == "tab-sentiment":
        return html.Div([
            html.H2(t['dashboard_title'], className="text-center mb-4", style={"color": "#2c3e50", "font-family": "Roboto, sans-serif", "font-weight": "bold"}),
            dbc.Row([
                dbc.Col(html.Div([
                    html.H5(t['total_comments'], className="text-center", style={"color": "#34495e"}),
                    html.P(f"{kpis['total_comments']}", className="text-center display-4", style={"color": "#2c3e50", "font-weight": "bold"}),
                    html.Div(kpis['total_comments_trend'][0], className="text-center"),
                    html.Small(kpis['total_comments_trend'][1], className="text-center")
                ], className="card p-3 m-2", style={"background": "linear-gradient(135deg, #ffffff, #ecf0f1)", "border-radius": "10px", "box-shadow": "0 4px 8px rgba(0,0,0,0.1)", "transition": "transform 0.2s"}), className="col-12 col-md-3"),
                dbc.Col(html.Div([
                    html.H5(t['avg_rating'], className="text-center", style={"color": "#34495e"}),
                    html.P(f"{kpis['avg_rating']}/5", className="text-center display-4", style={"color": "#2c3e50", "font-weight": "bold"}),
                    html.Div(kpis['avg_rating_trend'][0], className="text-center"),
                    html.Small(kpis['avg_rating_trend'][1], className="text-center")
                ], className="card p-3 m-2", style={"background": "linear-gradient(135deg, #ffffff, #ecf0f1)", "border-radius": "10px", "box-shadow": "0 4px 8px rgba(0,0,0,0.1)", "transition": "transform 0.2s"}), className="col-12 col-md-3"),
                dbc.Col(html.Div([
                    html.H5(t['top_ratings'], className="text-center", style={"color": "#34495e"}),
                    html.P(f"{kpis['top_ratings']}", className="text-center display-4", style={"color": "#2c3e50", "font-weight": "bold"}),
                    html.Div(kpis['top_ratings_trend'][0], className="text-center"),
                    html.Small(kpis['top_ratings_trend'][1], className="text-center")
                ], className="card p-3 m-2", style={"background": "linear-gradient(135deg, #ffffff, #ecf0f1)", "border-radius": "10px", "box-shadow": "0 4px 8px rgba(0,0,0,0.1)", "transition": "transform 0.2s"}), className="col-12 col-md-3"),
                dbc.Col(html.Div([
                    html.H5(t['min_rating'], className="text-center", style={"color": "#34495e"}),
                    html.P(f"{kpis['min_rating']}/5", className="text-center display-4", style={"color": "#2c3e50", "font-weight": "bold"}),
                    html.Div(kpis['min_rating_trend'][0], className="text-center"),
                    html.Small(kpis['min_rating_trend'][1], className="text-center")
                ], className="card p-3 m-2", style={"background": "linear-gradient(135deg, #ffffff, #ecf0f1)", "border-radius": "10px", "box-shadow": "0 4px 8px rgba(0,0,0,0.1)", "transition": "transform 0.2s"}), className="col-12 col-md-3"),
            ]),
            dbc.Row([
                dbc.Col(html.Div([
                    html.H5(t['positive_comments'], className="text-center", style={"color": "#27ae60"}),
                    html.P(f"{kpis['positive']}", className="text-center display-4", style={"color": "#27ae60", "font-weight": "bold"}),
                    html.Div(kpis['positive_trend'][0], className="text-center"),
                    html.Small(kpis['positive_trend'][1], className="text-center")
                ], className="card p-3 m-2", style={"background": "linear-gradient(135deg, #ffffff, #e8f5e9)", "border-radius": "10px", "box-shadow": "0 4px 8px rgba(0,0,0,0.1)", "transition": "transform 0.2s"}), className="col-12 col-md-4"),
                dbc.Col(html.Div([
                    html.H5(t['neutral_comments'], className="text-center", style={"color": "#f39c12"}),
                    html.P(f"{kpis['neutral']}", className="text-center display-4", style={"color": "#f39c12", "font-weight": "bold"}),
                    html.Div(kpis['neutral_trend'][0], className="text-center"),
                    html.Small(kpis['neutral_trend'][1], className="text-center")
                ], className="card p-3 m-2", style={"background": "linear-gradient(135deg, #ffffff, #fef9e7)", "border-radius": "10px", "box-shadow": "0 4px 8px rgba(0,0,0,0.1)", "transition": "transform 0.2s"}), className="col-12 col-md-4"),
                dbc.Col(html.Div([
                    html.H5(t['negative_comments'], className="text-center", style={"color": "#e74c3c"}),
                    html.P(f"{kpis['negative']}", className="text-center display-4", style={"color": "#e74c3c", "font-weight": "bold"}),
                    html.Div(kpis['negative_trend'][0], className="text-center"),
                    html.Small(kpis['negative_trend'][1], className="text-center")
                ], className="card p-3 m-2", style={"background": "linear-gradient(135deg, #ffffff, #fdecea)", "border-radius": "10px", "box-shadow": "0 4px 8px rgba(0,0,0,0.1)", "transition": "transform 0.2s"}), className="col-12 col-md-4"),
            ]),
            dbc.Row([
                dbc.Col(html.Div([
                    html.H5(t['peak_hour'], className="text-center", style={"color": "#2980b9"}),
                    html.P(f"{kpis['peak_hour']}:00" if kpis['peak_hour'] != 'N/A' else 'N/A', className="text-center display-4", style={"color": "#2980b9", "font-weight": "bold"})
                ], className="card p-3 m-2", style={"background": "linear-gradient(135deg, #ffffff, #e6f0fa)", "border-radius": "10px", "box-shadow": "0 4px 8px rgba(0,0,0,0.1)", "transition": "transform 0.2s"}), className="col-12 col-md-4"),
                dbc.Col(html.Div([
                    html.H5(t['avg_hourly_freq'], className="text-center", style={"color": "#2980b9"}),
                    html.P(f"{kpis['avg_hourly_freq']}/h", className="text-center display-4", style={"color": "#2980b9", "font-weight": "bold"}),
                    html.Div(kpis['avg_hourly_freq_trend'][0], className="text-center"),
                    html.Small(kpis['avg_hourly_freq_trend'][1], className="text-center")
                ], className="card p-3 m-2", style={"background": "linear-gradient(135deg, #ffffff, #e6f0fa)", "border-radius": "10px", "box-shadow": "0 4px 8px rgba(0,0,0,0.1)", "transition": "transform 0.2s"}), className="col-12 col-md-4"),
                dbc.Col(html.Div([
                    html.H5(t['avg_time_between'], className="text-center", style={"color": "#2980b9"}),
                    html.P(f"{kpis['avg_time_between']}h", className="text-center display-4", style={"color": "#2980b9", "font-weight": "bold"}),
                    html.Div(kpis['avg_time_between_trend'][0], className="text-center"),
                    html.Small(kpis['avg_time_between_trend'][1], className="text-center")
                ], className="card p-3 m-2", style={"background": "linear-gradient(135deg, #ffffff, #e6f0fa)", "border-radius": "10px", "box-shadow": "0 4px 8px rgba(0,0,0,0.1)", "transition": "transform 0.2s"}), className="col-12 col-md-4"),
            ]),
            dbc.Row([
                dbc.Col(html.Div([
                    html.H5(t['emoji_count'], className="text-center", style={"color": "#34495e"}),
                    html.P(f"{kpis['emoji_count']}", className="text-center display-4", style={"color": "#2c3e50", "font-weight": "bold"}),
                    html.Div(kpis['emoji_count_trend'][0], className="text-center"),
                    html.Small(kpis['emoji_count_trend'][1], className="text-center")
                ], className="card p-3 m-2", style={"background": "linear-gradient(135deg, #ffffff, #ecf0f1)", "border-radius": "10px", "box-shadow": "0 4px 8px rgba(0,0,0,0.1)", "transition": "transform 0.2s"}), className="col-12 col-md-3"),
                dbc.Col(html.Div([
                    html.H5(t['unique_users'], className="text-center", style={"color": "#34495e"}),
                    html.P(f"{kpis['unique_users']}", className="text-center display-4", style={"color": "#2c3e50", "font-weight": "bold"}),
                    html.Div(kpis['unique_users_trend'][0], className="text-center"),
                    html.Small(kpis['unique_users_trend'][1], className="text-center")
                ], className="card p-3 m-2", style={"background": "linear-gradient(135deg, #ffffff, #ecf0f1)", "border-radius": "10px", "box-shadow": "0 4px 8px rgba(0,0,0,0.1)", "transition": "transform 0.2s"}), className="col-12 col-md-3"),
                dbc.Col(html.Div([
                    html.H5(t['dominant_lang'], className="text-center", style={"color": "#34495e"}),
                    html.P(f"{kpis['dominant_lang']} ({kpis['dominant_lang_count']})", className="text-center display-4", style={"color": "#2c3e50", "font-weight": "bold"})
                ], className="card p-3 m-2", style={"background": "linear-gradient(135deg, #ffffff, #ecf0f1)", "border-radius": "10px", "box-shadow": "0 4px 8px rgba(0,0,0,0.1)", "transition": "transform 0.2s"}), className="col-12 col-md-3"),
                dbc.Col(html.Div([
                    html.H5(t['top_emojis'], className="text-center", style={"color": "#34495e"}),
                    html.P(f"{', '.join([f'{emoji} ({count})' for emoji, count in kpis['top_emojis']])}", className="text-center display-4", style={"color": "#2c3e50", "font-weight": "bold"})
                ], className="card p-3 m-2", style={"background": "linear-gradient(135deg, #ffffff, #ecf0f1)", "border-radius": "10px", "box-shadow": "0 4px 8px rgba(0,0,0,0.1)", "transition": "transform 0.2s"}), className="col-12 col-md-3"),
            ])
        ])
    elif active_tab == "tab-evolution":
        # Injecter le layout de sentiments.py et gérer le titre dynamiquement
        layout_content = evolution_layout()
        return html.Div([
            dcc.Store(id='sentiments-title-store', data=t['sentiments_title']),
            layout_content
        ])
    elif active_tab == "tab-frequence":
        layout_content = frequence_layout()
        return html.Div([
            dcc.Store(id='frequences-title-store', data=t['frequences_title']),
            layout_content
        ])
    elif active_tab == "tab-comparaison":
        layout_content = distribution_layout()
        return html.Div([
            dcc.Store(id='distributions-title-store', data=t['distributions_title']),
            layout_content
        ])
    elif active_tab == "tab-regroupement":
        layout_content = regroupement_layout()
        return html.Div([
            dcc.Store(id='regroupement-title-store', data=t['regroupement_title']),
            layout_content
        ])
    return html.P("Développement à venir..." if language == 'fr' else "Development coming soon...")

# Callback pour rediriger vers la page d'accueil dans une nouvelle fenêtre
app.clientside_callback(
    """
    function(n_clicks) {
        if (n_clicks > 0) {
            window.location.href = 'https://admin-blflge.onrender.com';
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output('home-button', 'n_clicks'),
    Input('home-button', 'n_clicks'),
    prevent_initial_call=True
)

# Callback pour gérer l'ouverture/fermeture du modal des filtres
@callback(
    Output("filter-modal", "is_open"),
    [Input("navbar-toggler", "n_clicks"), Input("close-filter-modal", "n_clicks")],
    [State("filter-modal", "is_open")]
)
def toggle_modal(n1, n2, is_open):
    if n1 or n2:
        return not is_open
    return is_open

# Callback pour générer et télécharger le PDF
@callback(
    Output("download", "data"),
    Input("download-pdf", "n_clicks"),
    Input("download-pdf-modal", "n_clicks"),
    State('filters-store', 'data'),
    State('language-store', 'data'),
    prevent_initial_call=True
)
def generate_pdf(n_clicks, n_clicks_modal, filters, language):
    if not (n_clicks or n_clicks_modal):
        return dash.no_update
    
    df = get_feedback_data(filters)
    kpis = calculate_kpis(df)
    t = translations[language]

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    title_style = styles['Title']
    table_data = [
        [Paragraph("<b>Metric</b>", styles['Normal']), Paragraph("<b>Value</b>", styles['Normal'])],
        [t['total_comments'], str(kpis['total_comments'])],
        [t['avg_rating'], f"{kpis['avg_rating']}/5"],
        [t['top_ratings'], str(kpis['top_ratings'])],
        [t['min_rating'], f"{kpis['min_rating']}/5"],
        [t['positive_comments'], str(kpis['positive'])],
        [t['neutral_comments'], str(kpis['neutral'])],
        [t['negative_comments'], str(kpis['negative'])],
        [t['peak_hour'], f"{kpis['peak_hour']}:00" if kpis['peak_hour'] != 'N/A' else 'N/A'],
        [t['avg_hourly_freq'], f"{kpis['avg_hourly_freq']}/h"],
        [t['avg_time_between'], f"{kpis['avg_time_between']}h"],
        [t['emoji_count'], str(kpis['emoji_count'])],
        [t['unique_users'], str(kpis['unique_users'])],
        [t['dominant_lang'], f"{kpis['dominant_lang']} ({kpis['dominant_lang_count']})"],
        [t['top_emojis'], ', '.join([f'{emoji} ({count})' for emoji, count in kpis['top_emojis']])]
    ]

    table = Table(table_data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))

    elements = [
        Paragraph(f"<b>{t['dashboard_title']} Report</b>", title_style),
        Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']),
        table
    ]
    doc.build(elements)

    buffer.seek(0)
    return dcc.send_bytes(buffer.read(), filename="feedback_report.pdf")

server = app.server

if __name__ == '__main__':
    app.run(debug=True)

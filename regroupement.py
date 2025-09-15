import dash
from dash import html, dcc, callback, Output, Input, State, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
from data_utils import get_feedback_data
import io
import base64

# Dictionnaire de traductions
translations = {
    'fr': {
        'regroupement_title': 'Regroupement et Table',
        'table_title': 'Tableau des Commentaires',
        'download_button': [html.I(className="fas fa-download", style={'margin-right': '5px'}), 'Télécharger'],
        'no_data': 'Aucune donnée disponible'
    },
    'en': {
        'regroupement_title': 'Grouping and Table',
        'table_title': 'Comments Table',
        'download_button': [html.I(className="fas fa-download", style={'margin-right': '5px'}), 'Download'],
        'no_data': 'No data available'
    }
}

def layout():
    return html.Div([
        html.H2(id='regroupement-title', className="text-center mb-4", style={"color": "#2c3e50", "font-family": "Roboto, sans-serif", "font-weight": "bold"}),
        dcc.Store(id='regroupement-data-store'),
        html.H3(id='table-title', className="text-center mb-3", style={"color": "#34495e"}),
        dash_table.DataTable(
            id='comments-table',
            columns=[
                {'name': '', 'id': 'select', 'type': 'numeric'},  # Colonne pour la sélection, gérée par row_selectable
                # {'name': 'Code Unique', 'id': 'unique_code', 'type': 'text'},
                {'name': 'Commentaire', 'id': 'comment', 'type': 'text'},
                {'name': 'Note', 'id': 'rating', 'type': 'numeric'},
                {'name': 'Sentiment', 'id': 'sentiment', 'type': 'text'},
                {'name': 'Timestamp', 'id': 'timestamp', 'type': 'datetime'},
                {'name': 'Langue', 'id': 'language', 'type': 'text'}
            ],
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left', 'padding': '5px'},
            style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold'},
            style_data_conditional=[
                {'if': {'row_index': 'odd'}, 'backgroundColor': '#f2f2f2'}
            ],
            page_size=10,
            row_selectable='multi'  # Ajoute des cases à cocher pour sélection multiple
        ),
        html.Div([
            dbc.Button(
                id='download-button',
                children=translations['fr']['download_button'],
                color="primary",
                className="mt-3"
            ),
            dcc.Download(id='download-data')
        ])
    ], className="p-4")

@callback(
    [Output('regroupement-title', 'children'),
     Output('table-title', 'children'),
     Output('comments-table', 'data'),
     Output('regroupement-data-store', 'data')],
    [Input('filters-store', 'data'),
     Input('regroupement-title-store', 'data'),
     Input('interval-component', 'n_intervals')]  # Store temporaire pour la langue
)
def update_regroupement_table(filters, title_from_store, real_time_update):
    language = 'fr' if not title_from_store else ('en' if title_from_store in translations['en'].values() else 'fr')
    t = translations[language]

    df = get_feedback_data(filters)
    if df.empty:
        return [t['regroupement_title'], t['no_data'], [], {}]

    # Utiliser les données brutes de la base sans modification
    data = df.to_dict('records')

    return [t['regroupement_title'], t['table_title'], data, df.to_dict('records')]

@callback(
    Output('download-data', 'data'),
    Input('download-button', 'n_clicks'),
    State('comments-table', 'selected_rows'),
    State('regroupement-data-store', 'data'),
    prevent_initial_call=True
)
def download_data(n_clicks, selected_rows, stored_data):
    if n_clicks and stored_data:
        df = pd.DataFrame(stored_data)
        if selected_rows and len(selected_rows) > 0:
            df_selected = df.iloc[selected_rows]
        else:
            df_selected = df
        csv_string = df_selected.to_csv(index=False, encoding='utf-8')
        csv_string_io = io.StringIO(csv_string)
        return dcc.send_string(csv_string_io.getvalue(), filename='feedback_data.csv')
    return None
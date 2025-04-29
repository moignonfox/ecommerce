"""import dash
from dash import dcc, html, Input, Output, State
import plotly.express as px
import pandas as pd
import pymongo
from datetime import datetime
import sys
from dateutil.relativedelta import relativedelta

# Connexion à MongoDB avec gestion des erreurs
try:
    client = pymongo.MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=5000)
    client.server_info()
    db = client["ecommerce"]
except pymongo.errors.ServerSelectionTimeoutError as err:
    print(
        f"Erreur : Impossible de se connecter à MongoDB. Assurez-vous que 'mongod' est en cours d'exécution. Détails : {err}")
    sys.exit(1)

# Charger les données pour les dropdowns avec validation et nettoyage
clients = list(db.clients.find())
client_options = [
    {'label': str(c['nom']).strip(), 'value': int(c['_id'])}
    for c in clients if 'nom' in c and '_id' in c and c['nom'] and c['_id'] is not None
]

produits = list(db.produits.find())
produit_options = [
    {'label': str(p['nom']).strip().replace('\n', '').replace('\r', ''), 'value': str(p['_id']).strip()}
    for p in produits if 'nom' in p and '_id' in p and p['nom'] and p['_id'] is not None
]

# Debugging
print("Client options:", client_options)
print("Produit options:", produit_options)

# Initialisation de l'application Dash
app = dash.Dash(__name__)

# Styles CSS pour un design clair, précis et moderne
app.css.append_css({
    "external_url": "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css"
})

# Mise en page avec style
app.layout = html.Div([
    # En-tête
    html.Div([
        html.H1("Dashboard E-commerce", style={
            'textAlign': 'center',
            'color': '#ffffff',
            'backgroundColor': '#2c3e50',
            'padding': '20px',
            'margin': '0',
            'borderRadius': '10px 10px 0 0',
            'fontFamily': 'Arial, sans-serif'
        })
    ]),

    # Filtres
    html.Div([
        html.Label("Client :", style={'fontWeight': 'bold', 'marginRight': '10px'}),
        dcc.Dropdown(
            id='client-filter',
            options=client_options,
            value=None,
            placeholder="Tous les clients",
            style={
                'width': '200px',
                'borderRadius': '5px',
                'border': '1px solid #ccc',
                'padding': '5px'
            }
        ),
        html.Label("Période :", style={'fontWeight': 'bold', 'marginRight': '10px', 'marginLeft': '20px'}),
        dcc.DatePickerRange(
            id='date-filter',
            start_date=datetime(2010, 1, 1),
            end_date=datetime(2011, 12, 31),
            display_format='YYYY-MM-DD',
            style={
                'borderRadius': '5px',
                'border': '1px solid #ccc',
                'padding': '5px'
            }
        ),
        html.Label("Produit :", style={'fontWeight': 'bold', 'marginRight': '10px', 'marginLeft': '20px'}),
        dcc.Dropdown(
            id='produit-filter',
            options=produit_options,
            value=None,
            placeholder="Tous les produits",
            style={
                'width': '200px',
                'borderRadius': '5px',
                'border': '1px solid #ccc',
                'padding': '5px'
            }
        ),
        html.Button("Exporter en CSV", id="export-button", n_clicks=0, style={
            'backgroundColor': '#3498db',
            'color': 'white',
            'border': 'none',
            'padding': '10px 20px',
            'borderRadius': '5px',
            'cursor': 'pointer',
            'marginLeft': '20px',
            'fontWeight': 'bold'
        }),
        dcc.Download(id="download-dataframe-csv"),
    ], style={
        'display': 'flex',
        'alignItems': 'center',
        'gap': '20px',
        'padding': '20px',
        'backgroundColor': '#ecf0f1',
        'borderRadius': '0 0 10px 10px',
        'boxShadow': '0 2px 5px rgba(0,0,0,0.1)'
    }),

    # Métriques
    html.Div(id='metrics', style={
        'display': 'flex',
        'justifyContent': 'space-around',
        'margin': '20px 0',
        'padding': '20px',
        'backgroundColor': '#ffffff',
        'borderRadius': '10px',
        'boxShadow': '0 2px 5px rgba(0,0,0,0.1)'
    }),

    # Graphiques
    html.Div([
        dcc.Graph(id='ventes-par-categorie', style={'marginBottom': '20px'}),
        dcc.Graph(id='ventes-par-periode', style={'marginBottom': '20px'}),
        dcc.Graph(id='stock-par-produit', style={'marginBottom': '20px'}),
        dcc.Graph(id='stock-evolution')  # Nouveau graphique pour l'évolution du stock
    ], style={
        'padding': '20px',
        'backgroundColor': '#f9f9f9',
        'borderRadius': '10px',
        'boxShadow': '0 2px 5px rgba(0,0,0,0.1)'
    })
], style={
    'maxWidth': '1200px',
    'margin': '0 auto',
    'backgroundColor': '#f4f4f4',
    'minHeight': '100vh',
    'fontFamily': 'Arial, sans-serif'
})


# Callback pour mettre à jour le dashboard
@app.callback(
    [Output('metrics', 'children'),
     Output('ventes-par-categorie', 'figure'),
     Output('ventes-par-periode', 'figure'),
     Output('stock-par-produit', 'figure'),
     Output('stock-evolution', 'figure')],
    [Input('client-filter', 'value'),
     Input('date-filter', 'start_date'),
     Input('date-filter', 'end_date'),
     Input('produit-filter', 'value')]
)
def update_dashboard(client_id, start_date, end_date, produit_id):
    query = {}
    if client_id is not None:
        query['client_id'] = client_id
    if start_date and end_date:
        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date)
        query['date'] = {
            '$gte': start_dt,
            '$lte': end_dt
        }
    else:
        start_dt = datetime(2010, 1, 1)
        end_dt = datetime(2011, 12, 31)

    # Étape 1 : Récupérer les commandes correspondant aux filtres de client et de date
    commandes = list(db.commandes.find(query))

    # Étape 2 : Filtrer les commandes par produit (si un produit est sélectionné)
    if produit_id:
        filtered_commandes = []
        for commande in commandes:
            for produit in commande['produits']:
                if produit['produit_id'] == produit_id:
                    prod = db.produits.find_one({'_id': produit_id})
                    if prod:
                        montant_produit = prod['prix'] * produit['quantite']
                        commande_copy = commande.copy()
                        commande_copy['montant_total'] = montant_produit
                        commande_copy['produits'] = [produit]
                        filtered_commandes.append(commande_copy)
                    break
        commandes = filtered_commandes
    else:
        filtered_commandes = commandes

    # Étape 3 : Calculer les métriques basées sur les commandes filtrées
    total_revenus = sum(c['montant_total'] for c in filtered_commandes)
    nombre_commandes = len(filtered_commandes)
    panier_moyen = total_revenus / nombre_commandes if nombre_commandes else 0

    # Étape 4 : Calculer le stock restant pour chaque produit
    produits = list(db.produits.find({} if not produit_id else {'_id': produit_id}))
    quantites_vendues = {}
    for commande in commandes:
        for produit in commande['produits']:
            prod_id = produit['produit_id']
            quantite = produit['quantite']
            quantites_vendues[prod_id] = quantites_vendues.get(prod_id, 0) + quantite

    # Calculer le stock restant et préparer les données pour le graphique
    stock_data = []
    for p in produits:
        prod_id = p['_id']
        stock_initial = p['stock']
        quantite_vendue = quantites_vendues.get(prod_id, 0)
        stock_restant = max(0, stock_initial - quantite_vendue)
        stock_data.append({
            'Produit': p['nom'],
            'Stock Restant': stock_restant,
            'Stock Faible': stock_restant < 10  # Indiquer si le stock est faible (< 10 unités)
        })

    # Calculer le stock restant total pour la métrique
    stock_restant_total = sum(item['Stock Restant'] for item in stock_data)

    # Mettre à jour les métriques avec le stock restant total
    metrics = html.Div([
        html.Div([
            html.H3(f"Revenus totaux", style={'color': '#2c3e50'}),
            html.P(f"{total_revenus:.2f} €", style={'fontSize': '24px', 'color': '#3498db'})
        ], style={'textAlign': 'center'}),
        html.Div([
            html.H3(f"Panier moyen", style={'color': '#2c3e50'}),
            html.P(f"{panier_moyen:.2f} €", style={'fontSize': '24px', 'color': '#3498db'})
        ], style={'textAlign': 'center'}),
        html.Div([
            html.H3(f"Nombre de commandes", style={'color': '#2c3e50'}),
            html.P(f"{nombre_commandes}", style={'fontSize': '24px', 'color': '#3498db'})
        ], style={'textAlign': 'center'}),
        html.Div([
            html.H3(f"Stock restant total", style={'color': '#2c3e50'}),
            html.P(f"{stock_restant_total}", style={'fontSize': '24px', 'color': '#3498db'})
        ], style={'textAlign': 'center'})
    ])

    # Ventes par catégorie
    categorie_data = {}
    for commande in filtered_commandes:
        for produit in commande['produits']:
            prod = db.produits.find_one({'_id': produit['produit_id']})
            if not prod:
                continue
            cat = prod['categorie']
            montant = prod['prix'] * produit['quantite']
            categorie_data[cat] = categorie_data.get(cat, 0) + montant
    df_categorie = pd.DataFrame(list(categorie_data.items()), columns=['Categorie', 'Ventes'])
    fig_categorie = px.pie(df_categorie, names='Categorie', values='Ventes', title='Ventes par catégorie',
                           color_discrete_sequence=px.colors.qualitative.Pastel) if not df_categorie.empty else px.pie(
        title='Ventes par catégorie')

    # Ventes par période
    delta = end_dt - start_dt
    date_format = '%Y-%m-%d' if delta.days <= 31 else '%Y-%m'
    df_periode = pd.DataFrame([
        {'Date': c['date'].strftime(date_format), 'Montant': c['montant_total']}
        for c in filtered_commandes
    ])
    if not df_periode.empty:
        df_periode = df_periode.groupby('Date').sum().reset_index()
        df_periode = df_periode.sort_values('Date')
        fig_periode = px.line(df_periode, x='Date', y='Montant', title='Ventes par période',
                              line_shape='linear', render_mode='svg',
                              color_discrete_sequence=['#3498db'])
        fig_periode.update_xaxes(range=[start_dt.strftime(date_format), end_dt.strftime(date_format)])
    else:
        fig_periode = px.line(title='Ventes par période')

    # Stock restant par produit (avec alerte de stock faible)
    df_stock = pd.DataFrame(stock_data)
    if not df_stock.empty:
        fig_stock = px.bar(df_stock, x='Produit', y='Stock Restant', title='Stock restant par produit',
                           color='Stock Faible',  # Colorer en fonction du stock faible
                           color_discrete_map={True: '#e74c3c',
                                               False: '#3498db'})  # Rouge pour stock faible, bleu sinon
        fig_stock.update_layout(
            xaxis_tickangle=-45,
            xaxis_title="Produit",
            yaxis_title="Stock Restant",
            height=600,
            margin=dict(b=150),
            xaxis_tickfont=dict(size=10),
            showlegend=False  # Cacher la légende car elle est évidente avec les couleurs
        )
    else:
        fig_stock = px.bar(title='Stock restant par produit')

    # Évolution du stock restant au fil du temps
    stock_evolution_data = []
    for p in produits:
        prod_id = p['_id']
        stock_initial = p['stock']
        stock_actuel = stock_initial
        # Parcourir les commandes triées par date pour calculer l'évolution
        commandes_sorted = sorted(commandes, key=lambda x: x['date'])
        for commande in commandes_sorted:
            date = commande['date'].strftime(date_format)
            for produit in commande['produits']:
                if produit['produit_id'] == prod_id:
                    quantite = produit['quantite']
                    stock_actuel = max(0, stock_actuel - quantite)
                    stock_evolution_data.append({
                        'Produit': p['nom'],
                        'Date': date,
                        'Stock Restant': stock_actuel
                    })

    df_stock_evolution = pd.DataFrame(stock_evolution_data)
    if not df_stock_evolution.empty:
        df_stock_evolution = df_stock_evolution.sort_values('Date')
        fig_stock_evolution = px.line(df_stock_evolution, x='Date', y='Stock Restant', color='Produit',
                                      title='Évolution du stock restant au fil du temps',
                                      line_shape='linear', render_mode='svg')
        fig_stock_evolution.update_xaxes(range=[start_dt.strftime(date_format), end_dt.strftime(date_format)])
    else:
        fig_stock_evolution = px.line(title='Évolution du stock restant au fil du temps')

    return metrics, fig_categorie, fig_periode, fig_stock, fig_stock_evolution


# Callback pour l'export CSV
@app.callback(
    Output("download-dataframe-csv", "data"),
    Input("export-button", "n_clicks"),
    State('client-filter', 'value'),
    State('date-filter', 'start_date'),
    State('date-filter', 'end_date'),
    State('produit-filter', 'value'),
    prevent_initial_call=True,
)
def export_to_csv(n_clicks, client_id, start_date, end_date, produit_id):
    query = {}
    if client_id is not None:
        query['client_id'] = client_id
    if start_date and end_date:
        query['date'] = {
            '$gte': datetime.fromisoformat(start_date),
            '$lte': datetime.fromisoformat(end_date)
        }

    commandes = list(db.commandes.find(query))
    if produit_id:
        filtered_commandes = []
        for commande in commandes:
            for produit in commande['produits']:
                if produit['produit_id'] == produit_id:
                    prod = db.produits.find_one({'_id': produit_id})
                    if prod:
                        montant_produit = prod['prix'] * produit['quantite']
                        commande_copy = commande.copy()
                        commande_copy['montant_total'] = montant_produit
                        commande_copy['produits'] = [produit]
                        filtered_commandes.append(commande_copy)
                    break
        commandes = filtered_commandes

    export_data = []
    for commande in commandes:
        for produit in commande['produits']:
            prod = db.produits.find_one({'_id': produit['produit_id']})
            if not prod:
                continue
            export_data.append({
                "CommandeID": commande['_id'],
                "ClientID": commande['client_id'],
                "Produit": prod['nom'],
                "Categorie": prod['categorie'],
                "Quantite": produit['quantite'],
                "PrixUnitaire": prod['prix'],
                "Montant": prod['prix'] * produit['quantite'],
                "Date": commande['date'].strftime('%Y-%m-%d')
            })

    df_export = pd.DataFrame(export_data)
    return dcc.send_data_frame(df_export.to_csv, "ventes_export.csv")


# Lancer l'application
if __name__ == '__main__':
    app.run(debug=True) """


#première modife
"""import dash
from dash import dcc, html, Input, Output, State, dash_table
import plotly.express as px
import pandas as pd
import pymongo
from datetime import datetime
import sys
from dateutil.relativedelta import relativedelta
from aggregations import ventes_par_periode, ventes_par_produit, ventes_par_categorie, calculer_metrics, stocks_restants

# Connexion à MongoDB avec gestion des erreurs
try:
    client = pymongo.MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=5000)
    client.server_info()
    db = client["ecommerce"]
except pymongo.errors.ServerSelectionTimeoutError as err:
    print(f"Erreur : Impossible de se connecter à MongoDB. Assurez-vous que 'mongod' est en cours d'exécution. Détails : {err}")
    sys.exit(1)

# Charger les données pour les dropdowns
clients = list(db.clients.find())
client_options = [
    {'label': str(c['nom']).strip(), 'value': int(c['_id'])}
    for c in clients if 'nom' in c and '_id' in c and c['nom'] and c['_id'] is not None
]

produits = list(db.produits.find())
produit_options = [
    {'label': str(p['nom']).strip().replace('\n', '').replace('\r', ''), 'value': str(p['_id']).strip()}
    for p in produits if 'nom' in p and '_id' in p and p['nom'] and p['_id'] is not None
]

# Initialisation de l'application Dash
app = dash.Dash(__name__)

# Styles Tailwind CSS et FontAwesome
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css">
    </head>
    <body class="bg-gray-100 font-sans">
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# Mise en page avec Tailwind
app.layout = html.Div([
    # En-tête
    html.Div([
        html.H1("Dashboard E-commerce", className="text-3xl font-bold text-center text-white bg-blue-900 p-6 rounded-t-lg")
    ]),

    # Filtres
    html.Div([
        html.Label("Client :", className="font-semibold mr-2"),
        dcc.Dropdown(
            id='client-filter',
            options=client_options,
            value=None,
            placeholder="Tous les clients",
            className="w-48 rounded-lg border-gray-300 p-2"
        ),
        html.Label("Période :", className="font-semibold mr-2 ml-4"),
        dcc.DatePickerRange(
            id='date-filter',
            start_date=datetime(2010, 1, 1),
            end_date=datetime(2011, 12, 31),
            display_format='YYYY-MM-DD',
            className="rounded-lg border-gray-300 p-2"
        ),
        html.Label("Produit :", className="font-semibold mr-2 ml-4"),
        dcc.Dropdown(
            id='produit-filter',
            options=produit_options,
            value=None,
            placeholder="Tous les produits",
            className="w-48 rounded-lg border-gray-300 p-2"
        ),
        html.Button("Réinitialiser", id="reset-button", n_clicks=0, className="ml-4 bg-gray-500 text-white px-4 py-2 rounded-lg hover:bg-gray-600"),
        html.Button(
            [html.I(className="fas fa-download mr-2"), "Exporter en CSV"],
            id="export-button",
            n_clicks=0,
            className="ml-4 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
        ),
        dcc.Download(id="download-dataframe-csv"),
        dcc.Loading(
            id="loading",
            type="circle",
            children=html.Div(id="loading-output")
        )
    ], className="flex items-center gap-4 p-6 bg-white rounded-b-lg shadow-md"),

    # Métriques
    html.Div(id='metrics', className="grid grid-cols-1 md:grid-cols-3 gap-6 p-6 bg-white rounded-lg shadow-md mt-4"),

    # Graphiques
    html.Div([
        html.Div([
            dcc.Graph(id='ventes-par-categorie', className="w-full"),
            dcc.Graph(id='ventes-par-periode', className="w-full mt-4"),
        ], className="w-full md:w-1/2 p-4"),
        html.Div([
            dcc.Graph(id='ventes-par-produit', className="w-full"),
            dcc.Graph(id='stock-par-produit', className="w-full mt-4"),
        ], className="w-full md:w-1/2 p-4"),
    ], className="flex flex-col md:flex-row gap-4 mt-4 bg-white rounded-lg shadow-md p-6"),
], className="max-w-7xl mx-auto p-4")

# Callback pour réinitialiser les filtres
@app.callback(
    [Output('client-filter', 'value'),
     Output('date-filter', 'start_date'),
     Output('date-filter', 'end_date'),
     Output('produit-filter', 'value')],
    Input('reset-button', 'n_clicks')
)
def reset_filters(n_clicks):
    return None, datetime(2010, 1, 1), datetime(2011, 12, 31), None

# Callback pour mettre à jour le dashboard
@app.callback(
    [Output('metrics', 'children'),
     Output('ventes-par-categorie', 'figure'),
     Output('ventes-par-periode', 'figure'),
     Output('ventes-par-produit', 'figure'),
     Output('stock-par-produit', 'figure'),
     Output('loading-output', 'children')],
    [Input('client-filter', 'value'),
     Input('date-filter', 'start_date'),
     Input('date-filter', 'end_date'),
     Input('produit-filter', 'value')]
)
def update_dashboard(client_id, start_date, end_date, produit_id):
    # Conversion des dates
    start_dt = datetime.fromisoformat(start_date)
    end_dt = datetime.fromisoformat(end_date)

    # Métriques
    metrics_data = calculer_metrics(start_dt, end_dt)
    metrics = [
        html.Div([
            html.H3("Revenus Totaux", className="text-lg font-semibold text-gray-700"),
            html.P(f"{metrics_data['total_revenus']:.2f} €", className="text-2xl text-blue-600")
        ], className="text-center p-4 bg-gray-50 rounded-lg shadow"),
        html.Div([
            html.H3("Panier Moyen", className="text-lg font-semibold text-gray-700"),
            html.P(f"{metrics_data['panier_moyen']:.2f} €", className="text-2xl text-blue-600")
        ], className="text-center p-4 bg-gray-50 rounded-lg shadow"),
        html.Div([
            html.H3("Nombre de Commandes", className="text-lg font-semibold text-gray-700"),
            html.P(f"{metrics_data['nombre_commandes']}", className="text-2xl text-blue-600")
        ], className="text-center p-4 bg-gray-50 rounded-lg shadow"),
    ]

    # Ventes par catégorie (depuis aggregations.py)
    cat_data = ventes_par_categorie()
    df_categorie = pd.DataFrame(cat_data)
    fig_categorie = px.pie(
        df_categorie,
        names='_id',
        values='total_ventes',
        title='Ventes par Catégorie',
        color_discrete_sequence=px.colors.qualitative.Pastel,
        hover_data={'total_ventes': ':.2f'}
    ) if not df_categorie.empty else px.pie(title='Ventes par Catégorie')
    fig_categorie.update_layout(margin=dict(t=50, b=50, l=50, r=50))

    # Ventes par période (depuis aggregations.py)
    periode_data = ventes_par_periode(start_dt, end_dt)
    df_periode = pd.DataFrame(periode_data)
    fig_periode = px.line(
        df_periode,
        x='_id',
        y='total_ventes',
        title='Ventes par Période',
        labels={'_id': 'Date', 'total_ventes': 'Montant'},
        color_discrete_sequence=['#3498db'],
        line_shape='linear'
    ) if not df_periode.empty else px.line(title='Ventes par Période')
    fig_periode.update_layout(margin=dict(t=50, b=50, l=50, r=50))

    # Ventes par produit (depuis aggregations.py)
    produit_data = ventes_par_produit()
    df_produit = pd.DataFrame(produit_data)
    fig_produit = px.bar(
        df_produit,
        x='_id',
        y='total_ventes',
        title='Ventes par Produit',
        labels={'_id': 'Produit', 'total_ventes': 'Montant'},
        color_discrete_sequence=['#3498db'],
        text='total_ventes'
    ) if not df_produit.empty else px.bar(title='Ventes par Produit')
    fig_produit.update_traces(texttemplate='%{text:.2f}', textposition='outside')
    fig_produit.update_layout(xaxis_tickangle=-45, margin=dict(t=50, b=150, l=50, r=50))

    # Stock par produit (depuis aggregations.py)
    stock_data = stocks_restants()
    df_stock = pd.DataFrame(stock_data)
    fig_stock = px.bar(
        df_stock,
        x='nom',
        y='stock',
        title='Stock Restant par Produit',
        labels={'nom': 'Produit', 'stock': 'Stock Restant'},
        color_discrete_sequence=['#3498db'],
        text='stock'
    ) if not df_stock.empty else px.bar(title='Stock Restant par Produit')
    fig_stock.update_traces(texttemplate='%{text}', textposition='outside')
    fig_stock.update_layout(xaxis_tickangle=-45, margin=dict(t=50, b=150, l=50, r=50))

    return metrics, fig_categorie, fig_periode, fig_produit, fig_stock, None

# Callback pour l'export CSV
@app.callback(
    Output("download-dataframe-csv", "data"),
    Input("export-button", "n_clicks"),
    State('client-filter', 'value'),
    State('date-filter', 'start_date'),
    State('date-filter', 'end_date'),
    State('produit-filter', 'value'),
    prevent_initial_call=True,
)
def export_to_csv(n_clicks, client_id, start_date, end_date, produit_id):
    query = {}
    if client_id is not None:
        query['client_id'] = client_id
    if start_date and end_date:
        query['date'] = {
            '$gte': datetime.fromisoformat(start_date),
            '$lte': datetime.fromisoformat(end_date)
        }

    commandes = list(db.commandes.find(query))
    if produit_id:
        filtered_commandes = []
        for commande in commandes:
            for produit in commande['produits']:
                if produit['produit_id'] == produit_id:
                    prod = db.produits.find_one({'_id': produit_id})
                    if prod:
                        montant_produit = prod['prix'] * produit['quantite']
                        commande_copy = commande.copy()
                        commande_copy['montant_total'] = montant_produit
                        commande_copy['produits'] = [produit]
                        filtered_commandes.append(commande_copy)
                    break
        commandes = filtered_commandes

    export_data = []
    for commande in commandes:
        for produit in commande['produits']:
            prod = db.produits.find_one({'_id': produit['produit_id']})
            if not prod:
                continue
            export_data.append({
                "CommandeID": commande['_id'],
                "ClientID": commande['client_id'],
                "Produit": prod['nom'],
                "Categorie": prod['categorie'],
                "Quantite": produit['quantite'],
                "PrixUnitaire": prod['prix'],
                "Montant": prod['prix'] * produit['quantite'],
                "Date": commande['date'].strftime('%Y-%m-%d')
            })

    df_export = pd.DataFrame(export_data)
    return dcc.send_data_frame(df_export.to_csv, "ventes_export.csv")

# Lancer l'application
if __name__ == '__main__':
    app.run(debug=True)"""


## deuxiem modife a voir dans fichier test


### troisieme modife
import dash
from dash import dcc, html, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objs as go
import pandas as pd
import pymongo
from datetime import datetime
import sys
from dateutil.relativedelta import relativedelta
from aggregations import ventes_par_periode, ventes_par_produit, ventes_par_categorie, calculer_metrics, stocks_restants
import redis
import json
import pdfkit
import io

# Connexion à MongoDB avec gestion des erreurs
try:
    client = pymongo.MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=5000)
    client.server_info()
    db = client["ecommerce"]
except pymongo.errors.ServerSelectionTimeoutError as err:
    print(f"Erreur : Impossible de se connecter à MongoDB. Assurez-vous que 'mongod' est en cours d'exécution. Détails : {err}")
    sys.exit(1)

# Connexion à Redis pour le cache
try:
    cache = redis.Redis(host='localhost', port=6379, db=0)
except redis.ConnectionError as err:
    print(f"Erreur : Impossible de se connecter à Redis. Assurez-vous que Redis est en cours d'exécution. Détails : {err}")
    sys.exit(1)

# Charger les données pour les dropdowns
clients = list(db.clients.find())
client_options = [
    {'label': str(c['nom']).strip(), 'value': int(c['_id'])}
    for c in clients if 'nom' in c and '_id' in c and c['nom'] and c['_id'] is not None
]

produits = list(db.produits.find())
produit_options = [
    {'label': str(p['nom']).strip().replace('\n', '').replace('\r', ''), 'value': str(p['_id']).strip()}
    for p in produits if 'nom' in p and '_id' in p and p['nom'] and p['_id'] is not None
]

categories = list(db.produits.distinct("categorie"))
categorie_options = [{'label': cat, 'value': cat} for cat in categories]

# Initialisation de l'application Dash avec Bootstrap
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Mise en page avec Bootstrap
app.layout = html.Div([
    dcc.Store(id='sales-data-store'),  # Stocke les commandes filtrées
    dcc.Store(id='date-range-store'),  # Stocke les dates
    html.Div([
        # Navbar
        dbc.NavbarSimple(
            children=[
                dbc.NavItem(dbc.NavLink("Ventes", active=True, href="#")),
                dbc.NavItem(dbc.NavLink("Stocks", href="#")),
                dbc.NavItem(dbc.NavLink("Clients", href="#")),
            ],
            brand="📊 Dashboard E-commerce",
            brand_href="#",
            color="warning",  # Orange élégant
            dark=True,
            className="mb-4"
        ),

        # Filtres
        html.Div([
            dbc.Row([
                dbc.Col([
                    html.Label("Client", className="form-label text-white"),
                    dcc.Dropdown(
                        id='client-filter',
                        options=client_options,
                        value=None,
                        placeholder="Tous les clients",
                        className="form-select"
                    )
                ], width=3),
                dbc.Col([
                    html.Label("Période", className="form-label text-white"),
                    dcc.DatePickerRange(
                        id='date-filter',
                        start_date=datetime(2010, 1, 1),
                        end_date=datetime(2011, 12, 31),
                        display_format='YYYY-MM-DD',
                        className="form-control"
                    )
                ], width=4),
                dbc.Col([
                    html.Label("Produit", className="form-label text-white"),
                    dcc.Dropdown(
                        id='produit-filter',
                        options=produit_options,
                        value=None,
                        placeholder="Tous les produits",
                        className="form-select"
                    )
                ], width=3),
                dbc.Col([
                    html.Label("Catégorie", className="form-label text-white"),
                    dcc.Dropdown(
                        id='categorie-filter',
                        options=categorie_options,
                        value=None,
                        placeholder="Toutes les catégories",
                        className="form-select"
                    )
                ], width=2),
            ], className="mb-4"),
            # Boutons d'action
            html.Div([
                html.Button("Charger les données", id='load-data-btn', n_clicks=0, className="btn me-2", style={'backgroundColor': '#2ecc71', 'borderColor': '#2ecc71', 'color': 'white'}),  # Vert émeraude
                html.Button("Vider le cache", id='clear-cache-btn', n_clicks=0, className="btn me-2", style={'backgroundColor': '#f1c40f', 'borderColor': '#f1c40f', 'color': 'white'}),  # Doré
                html.Button("Exporter en PDF", id='export-pdf-btn', n_clicks=0, className="btn", style={'borderColor': '#95a5a6', 'color': '#95a5a6'}),  # Gris clair avec contour
                dcc.Download(id="download-pdf"),
                html.Div(id='cache-clear-status', className="text-success ms-2")
            ], className="d-flex justify-content-center mb-4")
        ], style={'backgroundColor': '#2c3e50', 'padding': '20px', 'borderRadius': '0 0 10px 10px'}),  # Gris foncé

        # Toast pour notifications
        dbc.Toast(
            id="notification-toast",
            header="Notification",
            is_open=False,
            dismissable=True,
            duration=4000,
            style={"position": "fixed", "top": 66, "right": 10, "width": 350},
        ),

        # Métriques
        dcc.Loading(
            id="loading-metrics",
            type="default",
            children=html.Div([
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H5("Revenus Totaux", className="card-title"),
                                html.H3(id='total-revenue-display', children="Chargement...")
                            ])
                        ], style={'backgroundColor': '#8e44ad', 'color': 'white'}, className="shadow-sm mb-4")  # Violet
                    ], width=3),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H5("Panier Moyen", className="card-title"),
                                html.H3(id='avg-order-display', children="Chargement...")
                            ])
                        ], style={'backgroundColor': '#1abc9c', 'color': 'white'}, className="shadow-sm mb-4")  # Turquoise
                    ], width=3),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H5("Nombre de Commandes", className="card-title"),
                                html.H3(id='num-orders-display', children="Chargement...")
                            ])
                        ], style={'backgroundColor': '#e91e63', 'color': 'white'}, className="shadow-sm mb-4")  # Rose
                    ], width=3),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H5("Top 5 Produits (Quantité)", className="card-title"),
                                html.Ul(id='top-products-display', children="Chargement...", style={'fontSize': '1rem'})
                            ])
                        ], style={'backgroundColor': '#f5f5dc', 'color': '#2c3e50'}, className="shadow-sm mb-4")  # Beige clair avec texte gris foncé
                    ], width=3),
                ], className="my-4")
            ])
        ),

        # Tabs pour organiser les graphiques
        dbc.Tabs([
            dbc.Tab([
                html.Div([
                    html.H2("Ventes par Période", className="text-center my-4"),
                    dcc.Loading(
                        id="loading-sales-period",
                        type="default",
                        children=dcc.Graph(id='graph-sales-by-period')
                    ),
                    html.Button("Basculer Bar/Line", id='toggle-chart-type-btn', n_clicks=0, className="btn mt-2", style={'borderColor': '#3498db', 'color': '#3498db'})  # Bleu clair
                ], className="p-4")
            ], label="Ventes par Période"),
            dbc.Tab([
                html.Div([
                    html.H2("Répartition des Ventes par Catégorie", className="text-center my-4"),
                    dcc.Loading(
                        id="loading-category-dist",
                        type="default",
                        children=dcc.Graph(id='graph-category-distribution')
                    ),
                    html.Button("Basculer Stacked", id='toggle-stacked-btn', n_clicks=0, className="btn mt-2", style={'borderColor': '#9b59b6', 'color': '#9b59b6'}),  # Violet
                    html.Button("Détails", id='category-details-btn', n_clicks=0, className="btn mt-2 ms-2", style={'borderColor': '#e91e63', 'color': '#e91e63'})  # Rose
                ], className="p-4")
            ], label="Ventes par Catégorie"),
            dbc.Tab([
                html.Div([
                    html.H2("Ventes par Produit", className="text-center my-4"),
                    html.Div([
                        html.Button("Top 10", id='btn-top-10', n_clicks=0, className="btn me-2", style={'borderColor': '#1abc9c', 'color': '#1abc9c'}),  # Turquoise
                        html.Button("Tout afficher", id='btn-all', n_clicks=0, className="btn me-2", style={'borderColor': '#e67e22', 'color': '#e67e22'}),  # Orange
                    ], className="d-flex justify-content-start mb-4"),
                    dcc.Loading(
                        id="loading-products",
                        type="default",
                        children=dcc.Graph(id='graph-products')
                    )
                ], className="p-4")
            ], label="Ventes par Produit"),
            dbc.Tab([
                html.Div([
                    html.H2("Stock Restant par Produit", className="text-center my-4"),
                    dcc.Loading(
                        id="loading-stock",
                        type="default",
                        children=dcc.Graph(id='graph-stock')
                    )
                ], className="p-4")
            ], label="Stocks"),
        ], style={'backgroundColor': '#ecf0f1', 'color': '#7f8c8d'}, className="mb-4 rounded shadow-sm"),  # Gris clair avec texte gris foncé

        # Modal pour les détails de catégorie
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Détails des Ventes par Catégorie")),
            dbc.ModalBody(id="category-details-content"),
            dbc.ModalFooter(
                dbc.Button("Fermer", id="close-modal-btn", className="ms-auto", n_clicks=0)
            ),
        ], id="category-details-modal", is_open=False),
    ], className="container", style={'backgroundColor': '#fdf5e6', 'padding': '20px', 'borderRadius': '10px'})  # Crème
])

# Callback pour charger les données (commandes filtrées) et les stocker
@app.callback(
    [Output('sales-data-store', 'data'),
     Output('date-range-store', 'data')],
    [Input('load-data-btn', 'n_clicks'),
     Input('client-filter', 'value'),
     Input('date-filter', 'start_date'),
     Input('date-filter', 'end_date'),
     Input('produit-filter', 'value'),
     Input('categorie-filter', 'value')]
)
def load_filtered_data(load_clicks, client_id, start_date, end_date, produit_id, categorie_id):
    print("Callback load_filtered_data déclenché")
    print(f"Filtres: client_id={client_id}, start_date={start_date}, end_date={end_date}, produit_id={produit_id}, categorie_id={categorie_id}")

    # Conversion des dates
    try:
        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date)
    except Exception as e:
        print(f"Erreur lors de la conversion des dates: {e}")
        return [], {'start_date': start_date, 'end_date': end_date}

    # Filtres
    query = {}
    if client_id is not None:
        query['client_id'] = client_id
    if start_date and end_date:
        query['date'] = {
            '$gte': start_dt,
            '$lte': end_dt
        }

    # Récupération des commandes
    try:
        commandes = list(db.commandes.find(query))
        print(f"Nombre de commandes trouvées: {len(commandes)}")
    except Exception as e:
        print(f"Erreur lors de la récupération des commandes: {e}")
        return [], {'start_date': start_date, 'end_date': end_date}

    # Filtrage par produit
    if produit_id:
        filtered_commandes = []
        for commande in commandes:
            try:
                for produit in commande.get('produits', []):
                    if produit.get('produit_id') == produit_id:
                        prod = db.produits.find_one({'_id': produit_id})
                        if prod:
                            montant_produit = prod.get('prix', 0) * produit.get('quantite', 0)
                            commande_copy = commande.copy()
                            commande_copy['montant_total'] = montant_produit
                            commande_copy['produits'] = [produit]
                            filtered_commandes.append(commande_copy)
                        break
            except Exception as e:
                print(f"Erreur lors du filtrage par produit: {e}")
                continue
        commandes = filtered_commandes
        print(f"Nombre de commandes après filtrage par produit: {len(commandes)}")

    return commandes, {'start_date': start_date, 'end_date': end_date}

# Callback pour les métriques
@app.callback(
    [Output('total-revenue-display', 'children'),
     Output('avg-order-display', 'children'),
     Output('num-orders-display', 'children')],
    [Input('sales-data-store', 'data'),
     Input('date-range-store', 'data')]
)
def update_metrics(commandes, date_range):
    print("Callback update_metrics déclenché")
    try:
        start_dt = datetime.fromisoformat(date_range['start_date'])
        end_dt = datetime.fromisoformat(date_range['end_date'])
    except Exception as e:
        print(f"Erreur lors de la conversion des dates dans update_metrics: {e}")
        return "Erreur date", "Erreur date", "Erreur date"

    try:
        metrics_data = calculer_metrics(start_dt, end_dt)
        total_revenue = f"{metrics_data.get('total_revenus', 0):.2f} €"
        avg_order = f"{metrics_data.get('panier_moyen', 0):.2f} €"
        num_orders = str(metrics_data.get('nombre_commandes', 0))
        print(f"Métriques calculées: total_revenue={total_revenue}, avg_order={avg_order}, num_orders={num_orders}")
    except Exception as e:
        print(f"Erreur lors du calcul des métriques: {e}")
        return "Erreur métriques", "Erreur métriques", "Erreur métriques"

    return total_revenue, avg_order, num_orders

# Callback pour les top 5 produits
@app.callback(
    Output('top-products-display', 'children'),
    Input('sales-data-store', 'data')
)
def update_top_products(commandes):
    print("Callback update_top_products déclenché")
    try:
        produit_data = ventes_par_produit()
        df_produit = pd.DataFrame(produit_data)
        if not df_produit.empty and 'quantite_vendue' in df_produit.columns:
            top_5_produits = df_produit.nlargest(5, 'quantite_vendue')
            top_products_html = [html.Li(f"{row['_id']}: {row['quantite_vendue']} unités") for _, row in top_5_produits.iterrows()]
        else:
            top_products_html = [html.Li("Aucun produit")]
        print("Top 5 produits calculé")
    except Exception as e:
        print(f"Erreur lors du calcul des top 5 produits: {e}")
        top_products_html = [html.Li("Erreur top produits")]

    return top_products_html

# Callback pour le graphique des ventes par période
@app.callback(
    Output('graph-sales-by-period', 'figure'),
    [Input('sales-data-store', 'data'),
     Input('date-range-store', 'data'),
     Input('toggle-chart-type-btn', 'n_clicks')],
    [State('toggle-chart-type-btn', 'n_clicks')]
)
def update_sales_by_period(commandes, date_range, toggle_clicks, chart_toggle_state):
    print("Callback update_sales_by_period déclenché")
    try:
        start_dt = datetime.fromisoformat(date_range['start_date'])
        end_dt = datetime.fromisoformat(date_range['end_date'])
    except Exception as e:
        print(f"Erreur lors de la conversion des dates dans update_sales_by_period: {e}")
        fig = go.Figure()
        fig.update_layout(title='Erreur Ventes par Période')
        return fig

    try:
        periode_data = ventes_par_periode(start_dt, end_dt)
        df_periode = pd.DataFrame(periode_data)
        chart_type = 'bar' if chart_toggle_state % 2 == 0 else 'line'
        if not df_periode.empty and 'total_ventes' in df_periode.columns:
            fig = px.line(df_periode, x='_id', y='total_ventes', title='Ventes par Période') if chart_type == 'line' else px.bar(df_periode, x='_id', y='total_ventes', title='Ventes par Période')
            fig.update_layout(xaxis_title="Date", yaxis_title="Montant", margin=dict(t=50, b=50, l=50, r=50))
        else:
            fig = go.Figure()
            fig.update_layout(title='Ventes par Période (Aucune donnée)')
        print("Graphique ventes par période créé")
    except Exception as e:
        print(f"Erreur lors de la création du graphique ventes par période: {e}")
        fig = go.Figure()
        fig.update_layout(title='Erreur Ventes par Période')

    return fig

# Callback pour le graphique des ventes par catégorie
@app.callback(
    Output('graph-category-distribution', 'figure'),
    [Input('sales-data-store', 'data'),
     Input('categorie-filter', 'value'),
     Input('toggle-stacked-btn', 'n_clicks')],
    [State('toggle-stacked-btn', 'n_clicks')]
)
def update_category_distribution(commandes, categorie_id, toggle_clicks, stacked_toggle_state):
    print("Callback update_category_distribution déclenché")
    try:
        cat_data = ventes_par_categorie()
        df_categorie = pd.DataFrame(cat_data)
        if categorie_id:
            df_categorie = df_categorie[df_categorie['_id'] == categorie_id]
        is_stacked = stacked_toggle_state % 2 != 0
        if not df_categorie.empty and 'total_ventes' in df_categorie.columns:
            if is_stacked:
                fig = px.bar(df_categorie, x='_id', y='total_ventes', title='Répartition par Catégorie (Stacked)', labels={'_id': 'Catégorie', 'total_ventes': 'Montant'})
            else:
                fig = px.pie(df_categorie, names='_id', values='total_ventes', title='Répartition par Catégorie')
            fig.update_layout(margin=dict(t=50, b=50, l=50, r=50))
        else:
            fig = go.Figure()
            fig.update_layout(title='Répartition par Catégorie (Aucune donnée)')
        print("Graphique ventes par catégorie créé")
    except Exception as e:
        print(f"Erreur lors de la création du graphique ventes par catégorie: {e}")
        fig = go.Figure()
        fig.update_layout(title='Erreur Ventes par Catégorie')

    return fig

# Callback pour le graphique des ventes par produit
@app.callback(
    Output('graph-products', 'figure'),
    [Input('sales-data-store', 'data'),
     Input('btn-top-10', 'n_clicks'),
     Input('btn-all', 'n_clicks')]
)
def update_sales_by_product(commandes, top_10_clicks, all_clicks):
    print("Callback update_sales_by_product déclenché")
    try:
        produit_data = ventes_par_produit()
        df_produit = pd.DataFrame(produit_data)
        if top_10_clicks > 0 and all_clicks == 0:
            df_produit = df_produit.nlargest(10, 'total_ventes')
        if not df_produit.empty and 'total_ventes' in df_produit.columns:
            fig = px.bar(df_produit, x='_id', y='total_ventes', title='Ventes par Produit', labels={'_id': 'Produit', 'total_ventes': 'Montant'})
            fig.update_layout(xaxis_tickangle=-45, margin=dict(t=50, b=150, l=50, r=50))
        else:
            fig = go.Figure()
            fig.update_layout(title='Ventes par Produit (Aucune donnée)')
        print("Graphique ventes par produit créé")
    except Exception as e:
        print(f"Erreur lors de la création du graphique ventes par produit: {e}")
        fig = go.Figure()
        fig.update_layout(title='Erreur Ventes par Produit')

    return fig

# Callback pour le graphique des stocks
@app.callback(
    Output('graph-stock', 'figure'),
    [Input('sales-data-store', 'data'),
     Input('produit-filter', 'value')]
)
def update_stock(commandes, produit_id):
    print("Callback update_stock déclenché")
    try:
        stock_data = stocks_restants()
        df_stock = pd.DataFrame(stock_data)
        if produit_id:
            df_stock = df_stock[df_stock['nom'] == produit_id]
        if not df_stock.empty and 'stock' in df_stock.columns:
            fig = px.bar(df_stock, x='nom', y='stock', title='Stock Restant par Produit', labels={'nom': 'Produit', 'stock': 'Stock Restant'})
            fig.update_layout(xaxis_tickangle=-45, margin=dict(t=50, b=150, l=50, r=50))
        else:
            fig = go.Figure()
            fig.update_layout(title='Stock Restant par Produit (Aucune donnée)')
        print("Graphique stock par produit créé")
    except Exception as e:
        print(f"Erreur lors de la création du graphique stock par produit: {e}")
        fig = go.Figure()
        fig.update_layout(title='Erreur Stock par Produit')

    return fig

# Callback combiné pour gérer les notifications et le statut du cache
@app.callback(
    [Output('notification-toast', 'is_open'),
     Output('notification-toast', 'children'),
     Output('cache-clear-status', 'children')],
    [Input('sales-data-store', 'data'),
     Input('clear-cache-btn', 'n_clicks')]
)
def update_notifications_and_cache(commandes, clear_cache_clicks):
    print("Callback update_notifications_and_cache déclenché")
    ctx = dash.callback_context
    if not ctx.triggered:
        return False, "Initialisation", ""

    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if trigger_id == 'clear-cache-btn':
        try:
            cache.flushdb()
            return True, "Le cache a été vidé avec succès.", "Cache vidé avec succès !"
        except Exception as e:
            print(f"Erreur lors de la vidange du cache: {e}")
            return True, "Erreur lors de la vidange du cache.", "Erreur cache"

    elif trigger_id == 'sales-data-store':
        if commandes is None or len(commandes) == 0:
            return True, "Aucune donnée chargée.", ""
        return True, "Données chargées avec succès.", ""

    return False, "Aucune action", ""

# Callback pour ouvrir/fermer le modal
@app.callback(
    [Output('category-details-modal', 'is_open'),
     Output('category-details-content', 'children')],
    [Input('category-details-btn', 'n_clicks'),
     Input('close-modal-btn', 'n_clicks')],
    [State('category-details-modal', 'is_open'),
     State('categorie-filter', 'value')]
)
def toggle_modal(category_btn_clicks, close_btn_clicks, is_open, categorie_id):
    ctx = dash.callback_context
    if not ctx.triggered:
        return is_open, ""

    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if trigger_id == 'category-details-btn' and not is_open:
        try:
            cat_data = ventes_par_categorie()
            df_categorie = pd.DataFrame(cat_data)
            if categorie_id:
                df_categorie = df_categorie[df_categorie['_id'] == categorie_id]
            content = [
                html.P(f"Total des ventes pour la catégorie {categorie_id}: {df_categorie['total_ventes'].sum():.2f} €") if not df_categorie.empty else html.P("Aucune donnée disponible.")
            ]
        except Exception as e:
            print(f"Erreur lors du calcul des détails de catégorie: {e}")
            content = [html.P("Erreur lors du chargement des détails.")]
        return True, content
    return False, ""

# Callback pour l'export PDF avec pdfkit
@app.callback(
    Output("download-pdf", "data"),
    Input("export-pdf-btn", "n_clicks"),
    [State('total-revenue-display', 'children'),
     State('avg-order-display', 'children'),
     State('num-orders-display', 'children')],
    prevent_initial_call=True,
)
def export_to_pdf(n_clicks, total_revenue, avg_order, num_orders):
    # Générer un HTML pour le PDF
    html_content = f"""
    <html>
    <head><title>Dashboard E-commerce</title></head>
    <body>
        <h1>Dashboard E-commerce</h1>
        <h2>Résumé des Métriques</h2>
        <p>Revenus Totaux: {total_revenue}</p>
        <p>Panier Moyen: {avg_order}</p>
        <p>Nombre de Commandes: {num_orders}</p>
        <h2>Graphiques</h2>
        <p>[Les graphiques nécessitent une conversion en image pour le PDF]</p>
    </body>
    </html>
    """
    # Générer le PDF avec pdfkit
    pdf_buffer = io.BytesIO()
    pdfkit.from_string(html_content, pdf_buffer)
    pdf_buffer.seek(0)
    return dcc.send_bytes(pdf_buffer.getvalue(), "dashboard_export.pdf")

# Lancer l'application
if __name__ == '__main__':
    app.run(debug=True)
import dash
from dash import dcc, html, Input, Output
import plotly.express as px
import pandas as pd
import pymongo
from datetime import datetime
import sys

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

# Mise en page
app.layout = html.Div([
    html.H1("Dashboard E-commerce", style={'textAlign': 'center'}),

    # Filtres
    html.Div([
        html.Label("Client :"),
        dcc.Dropdown(
            id='client-filter',
            options=client_options,
            value=None,
            placeholder="Tous les clients",
            style={'width': '200px'}
        ),
        html.Label("Période :"),
        dcc.DatePickerRange(
            id='date-filter',
            start_date=datetime(2010, 1, 1),
            end_date=datetime(2011, 12, 31),
            display_format='YYYY-MM-DD'
        ),
        html.Label("Produit :"),
        dcc.Dropdown(
            id='produit-filter',
            options=produit_options,
            value=None,
            placeholder="Tous les produits",
            style={'width': '200px'}
        ),
        html.Button("Exporter en CSV", id="export-button", n_clicks=0),
        dcc.Download(id="download-dataframe-csv"),
    ], style={'display': 'flex', 'gap': '20px', 'margin': '20px'}),

    # Métriques
    html.Div(id='metrics', style={'margin': '20px'}),

    # Graphiques
    dcc.Graph(id='ventes-par-categorie'),
    dcc.Graph(id='ventes-par-periode'),
    dcc.Graph(id='stock-par-produit')
])


# Callback pour mettre à jour le dashboard
@app.callback(
    [Output('metrics', 'children'),
     Output('ventes-par-categorie', 'figure'),
     Output('ventes-par-periode', 'figure'),
     Output('stock-par-produit', 'figure')],
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
        query['date'] = {
            '$gte': datetime.fromisoformat(start_date),
            '$lte': datetime.fromisoformat(end_date)
        }

    commandes = list(db.commandes.find(query))
    total_revenus = sum(c['montant_total'] for c in commandes)
    panier_moyen = total_revenus / len(commandes) if commandes else 0
    metrics = html.Div([
        html.H3(f"Revenus totaux : {total_revenus:.2f} €"),
        html.H3(f"Panier moyen : {panier_moyen:.2f} €"),
        html.H3(f"Nombre de commandes : {len(commandes)}")
    ])

    categorie_data = {}
    for commande in commandes:
        for produit in commande['produits']:
            if produit_id and produit['produit_id'] != produit_id:
                continue
            prod = db.produits.find_one({'_id': produit['produit_id']})
            if not prod:
                continue
            cat = prod['categorie']
            montant = prod['prix'] * produit['quantite']
            categorie_data[cat] = categorie_data.get(cat, 0) + montant
    df_categorie = pd.DataFrame(list(categorie_data.items()), columns=['Categorie', 'Ventes'])
    fig_categorie = px.pie(df_categorie, names='Categorie', values='Ventes',
                           title='Ventes par catégorie') if not df_categorie.empty else px.pie(
        title='Ventes par catégorie')

    df_periode = pd.DataFrame([
        {'Date': c['date'].strftime('%Y-%m'), 'Montant': c['montant_total']}
        for c in commandes
    ])
    df_periode = df_periode.groupby('Date').sum().reset_index()
    fig_periode = px.line(df_periode, x='Date', y='Montant',
                          title='Ventes par période') if not df_periode.empty else px.line(title='Ventes par période')

    produits = list(db.produits.find({} if not produit_id else {'_id': produit_id}))
    df_stock = pd.DataFrame([
        {'Produit': p['nom'], 'Stock': p['stock']}
        for p in produits
    ])
    fig_stock = px.bar(df_stock, x='Produit', y='Stock', title='Stock par produit') if not df_stock.empty else px.bar(
        title='Stock par produit')

    return metrics, fig_categorie, fig_periode, fig_stock


# Callback pour l'export CSV
@app.callback(
    Output("download-dataframe-csv", "data"),
    Input("export-button", "n_clicks"),
    Input('client-filter', 'value'),
    Input('date-filter', 'start_date'),
    Input('date-filter', 'end_date'),
    Input('produit-filter', 'value'),
    prevent_initial_call=True,
)
def export_to_csv(n_clicks, client_id, start_date, end_date, produit_id):
    if n_clicks == 0:
        return None

    query = {}
    if client_id is not None:
        query['client_id'] = client_id
    if start_date and end_date:
        query['date'] = {
            '$gte': datetime.fromisoformat(start_date),
            '$lte': datetime.fromisoformat(end_date)
        }

    commandes = list(db.commandes.find(query))
    export_data = []
    for commande in commandes:
        for produit in commande['produits']:
            if produit_id and produit['produit_id'] != produit_id:
                continue
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
    app.run_server(debug=True)
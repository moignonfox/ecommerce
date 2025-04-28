# Fichier : dashboard.py
import dash
from dash import dcc, html, Input, Output
import plotly.express as px
import pandas as pd
import pymongo
from datetime import datetime

# Connexion à MongoDB
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["ecommerce"]

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
            options=[{'label': c['nom'], 'value': c['_id']} for c in db.clients.find()],
            value=None,
            placeholder="Tous les clients",
            style={'width': '200px'}
        ),
        html.Label("Période :"),
        dcc.DatePickerRange(
            id='date-filter',
            start_date=datetime(2010, 1, 1),  # Ajusté pour 2010
            end_date=datetime(2011, 12, 31),
            display_format='YYYY-MM-DD'
        ),
        html.Label("Produit :"),
        dcc.Dropdown(
            id='produit-filter',
            options=[{'label': p['nom'], 'value': p['_id']} for p in db.produits.find()],
            value=None,
            placeholder="Tous les produits",
            style={'width': '200px'}
        ),
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
    # Construire le filtre
    query = {}
    if client_id:
        query['client_id'] = client_id
    if start_date and end_date:
        query['date'] = {
            '$gte': datetime.fromisoformat(start_date),
            '$lte': datetime.fromisoformat(end_date)
        }

    # Récupérer les commandes
    commandes = list(db.commandes.find(query))

    # Calcul des métriques
    total_revenus = sum(c['montant_total'] for c in commandes)
    panier_moyen = total_revenus / len(commandes) if commandes else 0
    metrics = html.Div([
        html.H3(f"Revenus totaux : {total_revenus:.2f} €"),
        html.H3(f"Panier moyen : {panier_moyen:.2f} €"),
        html.H3(f"Nombre de commandes : {len(commandes)}")
    ])

    # Ventes par catégorie
    categorie_data = {}
    for commande in commandes:
        for produit in commande['produits']:
            if produit_id and produit['produit_id'] != produit_id:
                continue
            prod = db.produits.find_one({'_id': produit['produit_id']})
            cat = prod['categorie']
            montant = prod['prix'] * produit['quantite']
            categorie_data[cat] = categorie_data.get(cat, 0) + montant
    df_categorie = pd.DataFrame(list(categorie_data.items()), columns=['Categorie', 'Ventes'])
    fig_categorie = px.pie(df_categorie, names='Categorie', values='Ventes', title='Ventes par catégorie')

    # Ventes par période
    df_periode = pd.DataFrame([
        {'Date': c['date'].strftime('%Y-%m'), 'Montant': c['montant_total']}
        for c in commandes
    ])
    df_periode = df_periode.groupby('Date').sum().reset_index()
    fig_periode = px.line(df_periode, x='Date', y='Montant', title='Ventes par période')

    # Stock par produit
    produits = list(db.produits.find({} if not produit_id else {'_id': produit_id}))
    df_stock = pd.DataFrame([
        {'Produit': p['nom'], 'Stock': p['stock']}
        for p in produits
    ])
    fig_stock = px.bar(df_stock, x='Produit', y='Stock', title='Stock par produit')

    return metrics, fig_categorie, fig_periode, fig_stock


# Lancer l'application
if __name__ == '__main__':
    app.run(debug=True)
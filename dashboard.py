import dash
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
    app.run(debug=True)
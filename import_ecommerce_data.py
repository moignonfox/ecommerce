# Fichier : import_ecommerce_data.py
import pandas as pd
import pymongo
from datetime import datetime
import random

# Connexion à MongoDB
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["ecommerce"]
client.drop_database("ecommerce")  # Réinitialiser la base

# Charger le dataset CSV
df = pd.read_csv("ecommerce_data.csv", encoding= "ISO-8859-1")#, nrows=10000

# Étape 1 : Créer la collection Produits
# Extraire les produits uniques (StockCode, Description, UnitPrice)
produits_df = df[['StockCode', 'Description', 'UnitPrice']].drop_duplicates(subset=['StockCode'])

# Ajouter un champ catégorie (déduit à partir de la description)
def deduce_category(description):
    if not isinstance(description, str):
        return "Divers"  # Ou ce que tu veux par défaut
    description = description.lower()
    if any(word in description for word in ['light', 'lantern', 'holder', 'lamp']):
        return "Maison"
    elif any(word in description for word in ['doll', 'playhouse', 'block', 'babushka', 'bird']):
        return "Jouets"
    elif any(word in description for word in ['warmer', 'cosy', 'teaspoons']):
        return "Cuisine"
    else:
        return "Divers"

produits = []
for idx, row in produits_df.iterrows():
    produit = {
        "_id": str(row['StockCode']),  # Utiliser StockCode comme identifiant
        "nom": row['Description'],
        "categorie": deduce_category(row['Description']),
        "prix": float(row['UnitPrice']),
        "stock": random.randint(50, 500)  # Simuler un stock
    }
    produits.append(produit)
db.produits.insert_many(produits)

# Étape 2 : Créer la collection Clients
# Extraire les clients uniques (CustomerID)
clients_df = df[['CustomerID']].drop_duplicates()
clients = []
for idx, row in clients_df.iterrows():
    if pd.isna(row['CustomerID']):
        continue  # Ignorer les clients sans ID
    client = {
        "_id": int(row['CustomerID']),
        "nom": f"Client_{int(row['CustomerID'])}",
        "email": f"client_{int(row['CustomerID'])}@example.com"
    }
    clients.append(client)
db.clients.insert_many(clients)

# Étape 3 : Créer la collection Commandes
# Regrouper par InvoiceNo
commandes_group = df.groupby('InvoiceNo')
commandes = []
for invoice_no, group in commandes_group:
    # Ignorer si pas de CustomerID
    if pd.isna(group['CustomerID'].iloc[0]):
        continue
    # Liste des produits dans cette commande
    produits_commandes = [
        {"produit_id": row['StockCode'], "quantite": int(row['Quantity'])}
        for idx, row in group.iterrows()
    ]
    # Calculer le montant total
    montant_total = sum(
        float(row['UnitPrice']) * int(row['Quantity'])
        for idx, row in group.iterrows()
    )
    # Convertir la date
    try:
        date = datetime.strptime(group['InvoiceDate'].iloc[0], '%m/%d/%Y %H:%M')
    except ValueError:
        print(f"Erreur de format de date sur {group['InvoiceDate'].iloc[0]}")
        date = None  # ou passer à la suite

    commande = {
        "_id": invoice_no,
        "client_id": int(group['CustomerID'].iloc[0]),
        "produits": produits_commandes,
        "date": date,
        "montant_total": round(montant_total, 2)
    }
    commandes.append(commande)
db.commandes.insert_many(commandes)

print("Dataset importé avec succès dans MongoDB.")
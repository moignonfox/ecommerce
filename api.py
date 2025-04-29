from fastapi import FastAPI
from pymongo import MongoClient
from datetime import datetime
from typing import Optional
from pydantic import BaseModel

app = FastAPI()

# Connexion à MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["ecommerce"]


class VentesQuery(BaseModel):
    client_id: Optional[int] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    produit_id: Optional[str] = None  # StockCode est une chaîne


@app.get("/ventes")
def get_ventes(query: VentesQuery):
    filters = {}
    if query.client_id:
        filters['client_id'] = query.client_id
    if query.start_date and query.end_date:
        filters['date'] = {
            '$gte': datetime.fromisoformat(query.start_date),
            '$lte': datetime.fromisoformat(query.end_date)
        }

    commandes = list(db.commandes.find(filters))
    total_revenus = sum(c['montant_total'] for c in commandes)
    panier_moyen = total_revenus / len(commandes) if commandes else 0

    categorie_data = {}
    for commande in commandes:
        for produit in commande['produits']:
            if query.produit_id and produit['produit_id'] != query.produit_id:
                continue
            prod = db.produits.find_one({'_id': produit['produit_id']})
            cat = prod['categorie']
            montant = prod['prix'] * produit['quantite']
            categorie_data[cat] = categorie_data.get(cat, 0) + montant

    return {
        "total_revenus": total_revenus,
        "panier_moyen": panier_moyen,
        "nombre_commandes": len(commandes),
        "ventes_par_categorie": categorie_data
    }


@app.get("/stocks")
def get_stocks():
    produits = list(db.produits.find())
    return [
        {"nom": p['nom'], "stock": p['stock'], "categorie": p['categorie']}
        for p in produits
    ]
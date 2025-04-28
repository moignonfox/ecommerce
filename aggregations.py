# Fichier : aggregations.py
import pymongo
from datetime import datetime

# Connexion à MongoDB
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["ecommerce"]

def ventes_par_periode(start_date, end_date):
    pipeline = [
        {"$match": {"date": {"$gte": start_date, "$lte": end_date}}},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m", "date": "$date"}},
            "total_ventes": {"$sum": "$montant_total"},
            "nombre_commandes": {"$sum": 1}
        }},
        {"$sort": {"_id": 1}}
    ]
    return list(db.commandes.aggregate(pipeline))

def ventes_par_produit():
    pipeline = [
        {"$unwind": "$produits"},
        {"$lookup": {
            "from": "produits",
            "localField": "produits.produit_id",
            "foreignField": "_id",
            "as": "produit_info"
        }},
        {"$unwind": "$produit_info"},
        {"$group": {
            "_id": "$produit_info.nom",
            "total_ventes": {"$sum": {"$multiply": ["$produits.quantite", "$produit_info.prix"]}},
            "quantite_vendue": {"$sum": "$produits.quantite"}
        }}
    ]
    return list(db.commandes.aggregate(pipeline))

def ventes_par_categorie():
    pipeline = [
        {"$unwind": "$produits"},
        {"$lookup": {
            "from": "produits",
            "localField": "produits.produit_id",
            "foreignField": "_id",
            "as": "produit_info"
        }},
        {"$unwind": "$produit_info"},
        {"$group": {
            "_id": "$produit_info.categorie",
            "total_ventes": {"$sum": {"$multiply": ["$produits.quantite", "$produit_info.prix"]}}
        }}
    ]
    return list(db.commandes.aggregate(pipeline))

def calculer_metrics(start_date, end_date):
    commandes = db.commandes.find({"date": {"$gte": start_date, "$lte": end_date}})
    commandes_list = list(commandes)
    total_revenus = sum(c["montant_total"] for c in commandes_list)
    nombre_commandes = len(commandes_list)
    panier_moyen = total_revenus / nombre_commandes if nombre_commandes > 0 else 0
    return {
        "total_revenus": total_revenus,
        "panier_moyen": panier_moyen,
        "nombre_commandes": nombre_commandes
    }

def stocks_restants():
    return list(db.produits.find({}, {"nom": 1, "stock": 1, "categorie": 1, "_id": 0}))

# Tester avec les nouvelles dates
if __name__ == "__main__":
    start = datetime(2010, 1, 1)
    end = datetime(2011, 12, 31)
    print("Ventes par période :", ventes_par_periode(start, end))
    print("Ventes par produit :", ventes_par_produit())
    print("Ventes par catégorie :", ventes_par_categorie())
    print("Métriques :", calculer_metrics(start, end))
    print("Stocks :", stocks_restants())
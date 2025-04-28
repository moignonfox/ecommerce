import pymongo
from datetime import datetime
import random

# Connexion à MongoDB
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["ecommerce"]
client.drop_database("ecommerce")  # Réinitialiser la base pour repartir de zéro

# Collection Produits
produits = [
    {"_id": 1, "nom": "Smartphone X", "categorie": "Électronique", "prix": 599.99, "stock": 50},
    {"_id": 2, "nom": "T-shirt Bleu", "categorie": "Vêtements", "prix": 19.99, "stock": 200},
    {"_id": 3, "nom": "Laptop Pro", "categorie": "Électronique", "prix": 1299.99, "stock": 30},
    {"_id": 4, "nom": "Jeans Slim", "categorie": "Vêtements", "prix": 49.99, "stock": 150}
]
db.produits.insert_many(produits)

# Collection Clients
clients = [
    {"_id": 1, "nom": "Alice Dupont", "email": "alice@example.com"},
    {"_id": 2, "nom": "Bob Martin", "email": "bob@example.com"},
    {"_id": 3, "nom": "Claire Lefèvre", "email": "claire@example.com"}
]
db.clients.insert_many(clients)

# Collection Commandes
commandes = []
for i in range(20):
    client_id = random.choice([1, 2, 3])
    produits_commandes = random.sample(
        [{"produit_id": p["_id"], "quantite": random.randint(1, 5)} for p in produits],
        k=random.randint(1, 3)
    )
    montant_total = sum(
        db.produits.find_one({"_id": p["produit_id"]})["prix"] * p["quantite"]
        for p in produits_commandes
    )
    commande = {
        "_id": i + 1,
        "client_id": client_id,
        "produits": produits_commandes,
        "date": datetime(2025, random.randint(1, 4), random.randint(1, 28)),
        "montant_total": round(montant_total, 2)
    }
    commandes.append(commande)
db.commandes.insert_many(commandes)

print("Base MongoDB initialisée avec succès.")
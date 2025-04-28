import pymongo

try:
    client = pymongo.MongoClient("mongodb://localhost:27017/")
    print("Connexion réussie ! Bases disponibles :", client.list_database_names())
except Exception as e:
    print("Erreur de connexion :", e)
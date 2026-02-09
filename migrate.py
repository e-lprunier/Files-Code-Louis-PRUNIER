import json
import os

# Chemin vers les données
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
OLD_BOOKS = os.path.join(DATA_DIR, "books.json")
USERS_FILE = os.path.join(DATA_DIR, "users.json")

def migrate_books(username):
    # Créer le dossier utilisateur
    user_dir = os.path.join(DATA_DIR, username)
    os.makedirs(user_dir, exist_ok=True)
    
    # Charger les anciens livres
    try:
        with open(OLD_BOOKS, "r", encoding="utf-8") as f:
            old_books = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        old_books = []
    
    # Sauvegarder dans le nouveau fichier utilisateur
    user_books = os.path.join(user_dir, "books.json")
    with open(user_books, "w", encoding="utf-8") as f:
        json.dump(old_books, f, ensure_ascii=False, indent=2)
    
    print(f"Migré {len(old_books)} livres vers {user_books}")

if __name__ == "__main__":
    username = input("Entre ton nom d'utilisateur : ")
    migrate_books(username)
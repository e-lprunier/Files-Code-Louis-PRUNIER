"Relance : python app.py → ouvre http://127.0.0.1:5000"
"si problème de flask -> py -3 -m venv venv .\venv\Scripts\activate pip install Flask"
"dans le terminal Vs code"

from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from werkzeug.utils import secure_filename
from models import UserProfile
import os, shutil
from datetime import datetime
import json, uuid, re
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'change_this_secret'  # change en production

# données
BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

USERS_FILE = os.path.join(DATA_DIR, "users.json")

# flask-login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# utilitaires utilisateurs
def load_users():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=2)
        return {}
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

users_db = load_users()

# helper username validation (only letters, digits, - and _)
def valid_username(u):
    return bool(re.match(r'^[A-Za-z0-9_-]{3,32}$', u))

# utilitaires livres par utilisateur
def user_books_file(username):
    return os.path.join(DATA_DIR, username, "books.json")

def ensure_user_dir(username):
    path = os.path.join(DATA_DIR, username)
    os.makedirs(path, exist_ok=True)

def load_books(username):
    ensure_user_dir(username)
    fpath = user_books_file(username)
    if not os.path.exists(fpath):
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)
        return []
    with open(fpath, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_books(username, books):
    ensure_user_dir(username)
    with open(user_books_file(username), "w", encoding="utf-8") as f:
        json.dump(books, f, ensure_ascii=False, indent=2)

# user model
class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    if user_id in users_db:
        return User(user_id)
    return None

# routes auth
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if not username or not password:
            flash("Nom d'utilisateur et mot de passe requis.")
        elif not valid_username(username):
            flash("Nom d'utilisateur invalide — 3–32 caractères alphanumériques, '_' ou '-'.")
        elif username in users_db:
            flash("Nom d'utilisateur déjà pris.")
        else:
            users_db[username] = generate_password_hash(password)
            save_users(users_db)
            # create empty books file for user
            save_books(username, [])
            flash("Inscription réussie, connectez-vous.")
            return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if username in users_db and check_password_hash(users_db[username], password):
            user = User(username)
            login_user(user)
            return redirect(url_for("index"))
        flash("Nom d'utilisateur ou mot de passe incorrect.")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

# main app routes (require login)
@app.route("/")
@login_required
def index():
    books = load_books(current_user.id)
    a_acheter = [b for b in books if b.get("status") == "a_acheter"]
    achetes   = [b for b in books if b.get("status") == "achete"]
    lus       = [b for b in books if b.get("status") == "lu"]
    # <-- nouveau : charger le profil courant pour afficher l'avatar dans le template
    profile = load_profile(current_user.id)
    return render_template("index.html", a_acheter=a_acheter, achetes=achetes, lus=lus, profile=profile)

@app.route("/add", methods=["POST"])
@login_required
def add():
    title = request.form.get("title", "").strip()
    author = request.form.get("author", "").strip()
    status = request.form.get("status", "a_acheter")
    try:
        rating = float(request.form.get("rating", 0))
    except (ValueError, TypeError):
        rating = 0.0
    rating = max(0.0, min(5.0, round(rating * 2) / 2.0))
    if title:
        books = load_books(current_user.id)
        books.append({
            "id": uuid.uuid4().hex,
            "title": title,
            "author": author,
            "status": status,
            "rating": rating,
            "created_at": datetime.now().isoformat(timespec="seconds")
        })
        save_books(current_user.id, books)
    return redirect(url_for("index"))

@app.route("/mark_bought/<book_id>", methods=["POST"])
@login_required
def mark_bought(book_id):
    books = load_books(current_user.id)
    for b in books:
        if b.get("id") == book_id:
            b["status"] = "achete"
            break
    save_books(current_user.id, books)
    return redirect(url_for("index"))

@app.route("/mark_read/<book_id>", methods=["POST"])
@login_required
def mark_read(book_id):
    books = load_books(current_user.id)
    for b in books:
        if b.get("id") == book_id:
            b["status"] = "lu"
            break
    save_books(current_user.id, books)
    return redirect(url_for("index"))

@app.route("/rate/<book_id>", methods=["POST"])
@login_required
def rate(book_id):
    try:
        rating = float(request.form.get("rating", 0))
    except (ValueError, TypeError):
        rating = 0.0
    rating = max(0.0, min(5.0, round(rating * 2) / 2.0))
    books = load_books(current_user.id)
    for b in books:
        if b.get("id") == book_id:
            b["rating"] = rating
            break
    save_books(current_user.id, books)
    return redirect(url_for("index"))

@app.route("/delete/<book_id>", methods=["POST"])
@login_required
def delete(book_id):
    books = load_books(current_user.id)
    books = [b for b in books if b.get("id") != book_id]
    save_books(current_user.id, books)
    return redirect(url_for("index"))

# profile routes
UPLOAD_FOLDER = os.path.join(DATA_DIR, "avatars")
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def load_profile(username):
    profile_file = os.path.join(DATA_DIR, username, "profile.json")
    if os.path.exists(profile_file):
        with open(profile_file, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                return UserProfile.from_dict(data)
            except json.JSONDecodeError:
                pass
    return UserProfile(username=username)

def save_profile(profile):
    ensure_user_dir(profile.username)
    profile_file = os.path.join(DATA_DIR, profile.username, "profile.json")
    with open(profile_file, "w", encoding="utf-8") as f:
        json.dump(profile.to_dict(), f, ensure_ascii=False, indent=2)

@app.route('/profile')
@login_required
def profile():
    profile = load_profile(current_user.id)
    # compter les livres par section pour l'utilisateur courant
    books = load_books(current_user.id)
    a_acheter_count = sum(1 for b in books if b.get("status") == "a_acheter")
    achetes_count   = sum(1 for b in books if b.get("status") == "achete")
    lus_count       = sum(1 for b in books if b.get("status") == "lu")
    return render_template('profile.html',
                           profile=profile,
                           a_acheter_count=a_acheter_count,
                           achetes_count=achetes_count,
                           lus_count=lus_count)

@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    profile = load_profile(current_user.id)
    if request.method == 'POST':
        old_username = current_user.id
        new_username = request.form.get('username', '').strip() or old_username

        # validate username change
        if new_username != old_username:
            if not valid_username(new_username):
                flash("Nom d'utilisateur invalide — 3–32 caractères alphanumériques, '_' ou '-'.")
                return redirect(url_for('edit_profile'))
            if new_username in users_db:
                flash("Ce nom d'utilisateur est déjà pris.")
                return redirect(url_for('edit_profile'))

        # update profile fields
        profile.firstname = request.form.get('firstname', '').strip()
        profile.lastname = request.form.get('lastname', '').strip()
        profile.birthday = request.form.get('birthday', '')

        # handle uploaded avatar
        if 'avatar' in request.files:
            file = request.files['avatar']
            if file and allowed_file(file.filename):
                filename = secure_filename(f"{new_username}_{file.filename}")
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                profile.avatar = filename

        # if username changed, migrate user folder + users_db + avatar filename
        if new_username != old_username:
            # update users_db (keep same password hash)
            users_db[new_username] = users_db.pop(old_username)
            save_users(users_db)

            old_dir = os.path.join(DATA_DIR, old_username)
            new_dir = os.path.join(DATA_DIR, new_username)
            # move user folder (if exists) to new folder
            try:
                if os.path.exists(old_dir):
                    if os.path.exists(new_dir):
                        # fallback: move files individually
                        for name in os.listdir(old_dir):
                            shutil.move(os.path.join(old_dir, name), new_dir)
                        shutil.rmtree(old_dir)
                    else:
                        shutil.move(old_dir, new_dir)
                else:
                    os.makedirs(new_dir, exist_ok=True)
            except Exception as e:
                flash("Erreur lors du déplacement des données utilisateur: " + str(e))
                return redirect(url_for('edit_profile'))

            # rename avatar file if it has old prefix
            if profile.avatar and profile.avatar.startswith(f"{old_username}_"):
                old_avatar = os.path.join(UPLOAD_FOLDER, profile.avatar)
                remainder = profile.avatar[len(old_username) + 1:]
                new_avatar_name = f"{new_username}_{remainder}"
                new_avatar_path = os.path.join(UPLOAD_FOLDER, new_avatar_name)
                try:
                    if os.path.exists(old_avatar):
                        shutil.move(old_avatar, new_avatar_path)
                        profile.avatar = new_avatar_name
                except Exception:
                    # ignore avatar rename errors
                    pass

            # update profile username
            profile.username = new_username

            # re-login user with new id
            try:
                logout_user()
                login_user(User(new_username))
            except Exception:
                pass

        # save profile under current username (after possible change)
        save_profile(profile)
        flash('Profil mis à jour avec succès!')
        return redirect(url_for('profile'))

    # GET
    return render_template('edit_profile.html', profile=profile)

@app.route('/delete_account', methods=['POST'])
@login_required
def delete_account():
    username = current_user.id
    confirm = request.form.get('confirm_username', '').strip()
    if confirm != username:
        flash("Nom d'utilisateur incorrect pour confirmation.")
        return redirect(url_for('edit_profile'))

    try:
        # remove from users_db and save
        users_db.pop(username, None)
        save_users(users_db)

        # delete user folder
        user_dir = os.path.join(DATA_DIR, username)
        if os.path.exists(user_dir):
            shutil.rmtree(user_dir)

        # delete avatars that start with username_
        if os.path.exists(app.config['UPLOAD_FOLDER']):
            for fn in os.listdir(app.config['UPLOAD_FOLDER']):
                if fn.startswith(f"{username}_"):
                    try:
                        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], fn))
                    except Exception:
                        pass

        logout_user()
    except Exception as e:
        flash("Erreur lors de la suppression du compte : " + str(e))
        return redirect(url_for('edit_profile'))

    flash("Compte supprimé.")
    return redirect(url_for('register'))

@app.route('/avatars/<filename>')
def avatar(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == "__main__":
    app.run(debug=True)


"""
auth.py – Authentification avec Flask session + bcrypt
"""
import bcrypt
import json
from datetime import datetime
from flask import session as flask_session
from models import User
from utils.db import get_db
from config import SESSION_TIMEOUT_MINUTES


# ─────────────────────────────────────────────────────────────────────────────
#  Login / Logout
# ─────────────────────────────────────────────────────────────────────────────
def login_user(username: str, password: str):
    """
    Vérifie les credentials.
    Retourne (True, user_dict) ou (False, error_message).
    """
    db = get_db()
    try:
        user = db.query(User).filter(
            (User.username == username) | (User.email == username),
            User.is_active == True
        ).first()

        if not user:
            return False, "Identifiant ou mot de passe incorrect."

        if not bcrypt.checkpw(password.encode(), user.password.encode()):
            return False, "Identifiant ou mot de passe incorrect."

        # Mise à jour last_login
        user.last_login = datetime.utcnow()
        db.commit()

        user_data = {
            "id":        user.id,
            "username":  user.username,
            "email":     user.email,
            "role":      user.role,
            "full_name": user.full_name or user.username,
            "login_at":  datetime.utcnow().isoformat(),
        }
        return True, user_data

    except Exception as e:
        db.rollback()
        return False, f"Erreur serveur : {e}"
    finally:
        db.close()


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


# ─────────────────────────────────────────────────────────────────────────────
#  Register
# ─────────────────────────────────────────────────────────────────────────────
def register_user(username: str, email: str, full_name: str, password: str, role: str = "teacher"):
    """
    Crée un nouveau compte utilisateur.
    Retourne (True, user_dict) ou (False, error_message).
    """
    db = get_db()
    try:
        # Vérifier si le username ou email existe déjà
        existing = db.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()
        if existing:
            if existing.username == username:
                return False, "Ce nom d'utilisateur est déjà pris."
            return False, "Cet email est déjà utilisé."

        hashed = hash_password(password)
        new_user = User(
            username=username,
            email=email,
            full_name=full_name,
            password=hashed,
            role=role,
            is_active=True,
            created_at=datetime.utcnow(),
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        user_data = {
            "id":        new_user.id,
            "username":  new_user.username,
            "email":     new_user.email,
            "role":      new_user.role,
            "full_name": new_user.full_name or new_user.username,
            "login_at":  datetime.utcnow().isoformat(),
        }
        return True, user_data

    except Exception as e:
        db.rollback()
        return False, f"Erreur serveur : {e}"
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
#  Session helpers (via dcc.Store côté Dash)
# ─────────────────────────────────────────────────────────────────────────────
def is_authenticated(session_data: dict) -> bool:
    if not session_data or "id" not in session_data:
        return False
    return True


def is_admin(session_data: dict) -> bool:
    return is_authenticated(session_data) and session_data.get("role") == "admin"
import functools
import sqlite3

import bcrypt
from flask import jsonify
from flask_login import UserMixin, current_user

VALID_ROLES = ("admin", "manager", "uploader", "consulta")


class User(UserMixin):
    def __init__(self, id, email, name, password_hash, role="admin"):
        self.id = id
        self.email = email
        self.name = name
        self.password_hash = password_hash
        self.role = role

    def has_role(self, *roles):
        """Return True if user's role is in the given list."""
        return self.role in roles

    @property
    def can_edit(self):
        """Return True if user can edit consulta data (admin or manager)."""
        return self.role in ("admin", "manager")


def role_required(*roles):
    """Decorator that checks if the current user has one of the required roles.

    Must be used AFTER @login_required so that current_user is available.
    Returns 403 JSON for API routes, 403 HTML for page routes.
    """
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({"error": "Nao autenticado."}), 401
            if current_user.role not in roles:
                from flask import request
                if request.path.startswith("/api/"):
                    return jsonify({"error": "Acesso nao autorizado para seu perfil."}), 403
                return (
                    "<h1>403 - Acesso Negado</h1>"
                    "<p>Voce nao tem permissao para acessar esta pagina.</p>"
                    '<p><a href="/">Voltar</a></p>'
                ), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator


def init_users_table(db_path):
    """Create users table if it doesn't exist."""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'admin'
            )
        """)
        conn.commit()

        # Migration: add role column if missing (existing databases)
        cols = [row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()]
        if "role" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'admin'")
            conn.commit()
    finally:
        conn.close()


def seed_default_user(db_path):
    """Create default user if no users exist."""
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute("SELECT COUNT(*) FROM users").fetchone()
        if row[0] == 0:
            password_hash = bcrypt.hashpw(
                "hemominas2024".encode("utf-8"),
                bcrypt.gensalt(),
            ).decode("utf-8")
            conn.execute(
                "INSERT OR IGNORE INTO users (email, name, password_hash, role) VALUES (?, ?, ?, ?)",
                ("anavcunha@gmail.com", "Ana Cunha", password_hash, "admin"),
            )
            conn.commit()
    finally:
        conn.close()


def authenticate(db_path, email, password):
    """Authenticate user by email and password. Returns User or None."""
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT id, email, name, password_hash, role FROM users WHERE email = ?",
            (email,),
        ).fetchone()
        if row is None:
            return None
        if bcrypt.checkpw(password.encode("utf-8"), row[3].encode("utf-8")):
            return User(id=row[0], email=row[1], name=row[2],
                        password_hash=row[3], role=row[4])
        return None
    finally:
        conn.close()


def get_user_by_id(db_path, user_id):
    """Load user by ID. Returns User or None."""
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT id, email, name, password_hash, role FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if row is None:
            return None
        return User(id=row[0], email=row[1], name=row[2],
                    password_hash=row[3], role=row[4])
    finally:
        conn.close()


# ==========================================
# User Management CRUD (admin only)
# ==========================================


def listar_usuarios(db_path):
    """Return list of all users (without password_hash)."""
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT id, email, name, role FROM users ORDER BY id"
        ).fetchall()
        return [
            {"id": r[0], "email": r[1], "name": r[2], "role": r[3]}
            for r in rows
        ]
    finally:
        conn.close()


def criar_usuario(db_path, email, name, password, role):
    """Create a new user. Returns the new user id or raises ValueError."""
    if role not in VALID_ROLES:
        raise ValueError(f"Role invalido: {role}")
    if not email or not name or not password:
        raise ValueError("Email, nome e senha sao obrigatorios.")

    password_hash = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute(
            "INSERT INTO users (email, name, password_hash, role) VALUES (?, ?, ?, ?)",
            (email.strip(), name.strip(), password_hash, role),
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        raise ValueError(f"Email '{email}' ja esta cadastrado.")
    finally:
        conn.close()


def atualizar_usuario(db_path, user_id, name=None, role=None, password=None):
    """Update user fields. Only updates non-None fields."""
    if role is not None and role not in VALID_ROLES:
        raise ValueError(f"Role invalido: {role}")

    conn = sqlite3.connect(db_path)
    try:
        # Verify user exists
        existing = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
        if not existing:
            raise ValueError("Usuario nao encontrado.")

        if name is not None:
            conn.execute("UPDATE users SET name = ? WHERE id = ?", (name.strip(), user_id))
        if role is not None:
            conn.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
        if password is not None:
            password_hash = bcrypt.hashpw(
                password.encode("utf-8"),
                bcrypt.gensalt(),
            ).decode("utf-8")
            conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id))
        conn.commit()
    finally:
        conn.close()


def excluir_usuario(db_path, user_id):
    """Delete a user by ID. Returns True if deleted, raises ValueError if not found."""
    conn = sqlite3.connect(db_path)
    try:
        existing = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
        if not existing:
            raise ValueError("Usuario nao encontrado.")
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        return True
    finally:
        conn.close()

import os
import sqlite3
import tempfile

import bcrypt
import pytest

from src.auth import (
    User,
    authenticate,
    get_user_by_id,
    init_users_table,
    seed_default_user,
)


@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


def test_init_users_table_creates_table(db_path):
    init_users_table(db_path)
    conn = sqlite3.connect(db_path)
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
    ).fetchall()
    conn.close()
    assert len(tables) == 1


def test_init_users_table_idempotent(db_path):
    init_users_table(db_path)
    init_users_table(db_path)  # Should not raise


def test_seed_default_user_creates_user(db_path):
    init_users_table(db_path)
    seed_default_user(db_path)
    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT email, name FROM users").fetchone()
    conn.close()
    assert row[0] == "anavcunha@gmail.com"
    assert row[1] == "Ana Cunha"


def test_seed_default_user_password_is_hashed(db_path):
    init_users_table(db_path)
    seed_default_user(db_path)
    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT password_hash FROM users").fetchone()
    conn.close()
    # Password hash should not be plaintext
    assert row[0] != "hemominas2024"
    # Should be a valid bcrypt hash
    assert row[0].startswith("$2")


def test_seed_default_user_does_not_duplicate(db_path):
    init_users_table(db_path)
    seed_default_user(db_path)
    seed_default_user(db_path)
    conn = sqlite3.connect(db_path)
    count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()
    assert count == 1


def test_authenticate_correct_credentials(db_path):
    init_users_table(db_path)
    seed_default_user(db_path)
    user = authenticate(db_path, "anavcunha@gmail.com", "hemominas2024")
    assert user is not None
    assert user.email == "anavcunha@gmail.com"
    assert user.name == "Ana Cunha"


def test_authenticate_wrong_password(db_path):
    init_users_table(db_path)
    seed_default_user(db_path)
    user = authenticate(db_path, "anavcunha@gmail.com", "wrongpassword")
    assert user is None


def test_authenticate_unknown_email(db_path):
    init_users_table(db_path)
    seed_default_user(db_path)
    user = authenticate(db_path, "unknown@example.com", "hemominas2024")
    assert user is None


def test_get_user_by_id_returns_user(db_path):
    init_users_table(db_path)
    seed_default_user(db_path)
    user = get_user_by_id(db_path, 1)
    assert user is not None
    assert user.email == "anavcunha@gmail.com"
    assert user.id == 1


def test_get_user_by_id_unknown_returns_none(db_path):
    init_users_table(db_path)
    user = get_user_by_id(db_path, 999)
    assert user is None


def test_user_implements_usermixin():
    user = User(id=1, email="a@b.com", name="Test", password_hash="x")
    assert user.is_authenticated
    assert user.is_active
    assert not user.is_anonymous
    assert user.get_id() == "1"
    assert user.role == "admin"  # default role

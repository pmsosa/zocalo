"""Secrets and sign-in.

API keys are encrypted at rest with a key kept in the data folder (secret.key, readable only by its owner).
Passwords are hashed with scrypt. Sessions are random tokens in an HttpOnly cookie.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from . import db
from .config import AUTH_DEFAULT, DATA_DIR

SESSION_COOKIE = "zocalo_session"
SESSION_DAYS = 30
_KEY_FILE = DATA_DIR / "secret.key"


def _fernet() -> Fernet:
    if not _KEY_FILE.exists():
        key = Fernet.generate_key()
        fd = os.open(_KEY_FILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(key)
    return Fernet(Path(_KEY_FILE).read_bytes().strip())


def encrypt(plain: str) -> str:
    return _fernet().encrypt(plain.encode()).decode()


def decrypt(token: str | None) -> str:
    if not token:
        return ""
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken:
        return ""


def key_hint(key: str) -> str:
    key = key.strip()
    return f"…{key[-4:]}" if len(key) >= 8 else "set"


# ---------- passwords ----------
def hash_password(pw: str) -> str:
    salt = secrets.token_bytes(16)
    h = hashlib.scrypt(pw.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return "scrypt$" + base64.b64encode(salt).decode() + "$" + base64.b64encode(h).decode()


def check_password(pw: str, stored: str) -> bool:
    try:
        _, salt_b64, h_b64 = stored.split("$")
        salt, want = base64.b64decode(salt_b64), base64.b64decode(h_b64)
    except ValueError:
        return False
    got = hashlib.scrypt(pw.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return hmac.compare_digest(got, want)


# ---------- auth mode ----------
def auth_mode() -> str:
    """'none' or 'accounts'. The deploy flag sets the first value; Settings can switch none → accounts."""
    mode = db.get_setting("auth_mode")
    if mode is None:
        mode = "none" if AUTH_DEFAULT == "none" else "accounts"
        db.set_setting("auth_mode", mode)
    return mode


def has_users() -> bool:
    return db.q1("SELECT 1 AS x FROM users LIMIT 1") is not None


def create_user(username: str, password: str, is_admin: bool) -> int:
    return db.ex("INSERT INTO users(username,pw_hash,is_admin,created_at) VALUES(?,?,?,?)",
                 username.strip(), hash_password(password), int(is_admin), db.now())


def new_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    db.ex("INSERT INTO sessions(token,user_id,expires) VALUES(?,?,?)", token, user_id, db.now() + SESSION_DAYS * 86400)
    return token


def user_for_token(token: str | None) -> dict | None:
    if not token:
        return None
    row = db.q1("SELECT u.id,u.username,u.is_admin FROM sessions s JOIN users u ON u.id=s.user_id "
                "WHERE s.token=? AND s.expires>?", token, db.now())
    return row


def end_session(token: str | None) -> None:
    if token:
        db.ex("DELETE FROM sessions WHERE token=?", token)

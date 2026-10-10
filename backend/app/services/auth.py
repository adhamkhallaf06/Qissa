import hashlib
import hmac
import secrets
import sqlite3
import time
import uuid
from datetime import datetime, timedelta, timezone

from app.core import db
from app.core.config import SESSION_DAYS

# scrypt work factors (about 16 MB of memory per hash)
SCRYPT_N, SCRYPT_R, SCRYPT_P = 2 ** 14, 8, 1

# Failed logins allowed per email before a cool-down
MAX_FAILURES = 5
FAILURE_WINDOW_SECONDS = 15 * 60
_failures = {}


class AuthError(Exception):
    """A sign-up or login problem that is safe to show to the user."""


class TooManyAttempts(AuthError):
    pass


def hash_password(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P)
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${salt.hex()}${digest.hex()}"


def verify_password(password, stored):
    try:
        _, n, r, p, salt, expected = stored.split("$")
        digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=int(n), r=int(r), p=int(p))
    except ValueError:
        return False
    return hmac.compare_digest(digest.hex(), expected)


# Verified against when the email is unknown, so both cases take the same time
_DUMMY_HASH = hash_password(secrets.token_hex(8))


def _public(row):
    return {"id": row["id"], "email": row["email"], "name": row["name"]}


def _now():
    return datetime.now(timezone.utc)


def create_user(email, password, name):
    user = {"id": uuid.uuid4().hex, "email": email.strip().lower(), "name": name.strip()}
    try:
        with db.connect() as conn:
            conn.execute(
                "INSERT INTO users (id, email, name, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
                (user["id"], user["email"], user["name"], hash_password(password), _now().isoformat()),
            )
    except sqlite3.IntegrityError:
        raise AuthError("An account with this email already exists.")
    return user


def authenticate(email, password):
    email = email.strip().lower()

    recent = [t for t in _failures.get(email, []) if time.time() - t < FAILURE_WINDOW_SECONDS]
    if len(recent) >= MAX_FAILURES:
        raise TooManyAttempts("Too many failed attempts. Try again in a few minutes.")

    with db.connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

    if not verify_password(password, row["password_hash"] if row else _DUMMY_HASH) or not row:
        _failures[email] = recent + [time.time()]
        raise AuthError("Wrong email or password.")

    _failures.pop(email, None)
    return _public(row)


def _token_hash(token):
    # Only the hash is stored, so a leaked database cannot be used to log in
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(user_id):
    token = secrets.token_urlsafe(32)
    expires = _now() + timedelta(days=SESSION_DAYS)
    with db.connect() as conn:
        conn.execute("DELETE FROM sessions WHERE expires_at < ?", (_now().isoformat(),))
        conn.execute(
            "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
            (_token_hash(token), user_id, expires.isoformat()),
        )
    return token


def user_for_token(token):
    if not token:
        return None
    with db.connect() as conn:
        row = conn.execute(
            "SELECT users.* FROM sessions JOIN users ON users.id = sessions.user_id "
            "WHERE sessions.token_hash = ? AND sessions.expires_at > ?",
            (_token_hash(token), _now().isoformat()),
        ).fetchone()
    return _public(row) if row else None


def delete_session(token):
    if token:
        with db.connect() as conn:
            conn.execute("DELETE FROM sessions WHERE token_hash = ?", (_token_hash(token),))

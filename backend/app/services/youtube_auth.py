import json
import os

from app.core.config import API_BASE_URL, CLIENT_SECRETS_FILE, SECRETS_DIR, TOKEN_PICKLE
from app.services.uploader import SCOPES, load_credentials, save_credentials

REDIRECT_URI = f"{API_BASE_URL}/api/youtube/oauth/callback"

# OAuth flows waiting for Google to redirect back, keyed by state
_pending = {}


def status():
    connected = False
    if os.path.exists(TOKEN_PICKLE):
        try:
            connected = load_credentials() is not None
        except Exception:
            connected = False
    return {
        "has_client_secret": os.path.exists(CLIENT_SECRETS_FILE),
        "connected": connected,
        "redirect_uri": REDIRECT_URI,
    }


def save_client_secret(raw: bytes):
    """Validate and store the OAuth client file downloaded from Google Cloud."""
    try:
        data = json.loads(raw)
    except ValueError:
        raise ValueError("That file is not valid JSON.")
    client = data.get("installed") or data.get("web") if isinstance(data, dict) else None
    if not client or not client.get("client_id") or not client.get("client_secret"):
        raise ValueError("That does not look like a Google OAuth client file (client_secret.json).")

    SECRETS_DIR.mkdir(exist_ok=True)
    CLIENT_SECRETS_FILE.write_bytes(raw)
    os.chmod(CLIENT_SECRETS_FILE, 0o600)
    disconnect()  # a token from a different client would no longer refresh


def authorization_url():
    import google_auth_oauthlib.flow

    if not os.path.exists(CLIENT_SECRETS_FILE):
        raise ValueError("Upload your client_secret.json first.")
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        str(CLIENT_SECRETS_FILE), SCOPES, redirect_uri=REDIRECT_URI
    )
    url, state = flow.authorization_url(access_type="offline", prompt="consent")
    _pending.clear()
    _pending[state] = flow
    return url


def finish(state, code):
    flow = _pending.pop(state, None)
    if flow is None:
        raise ValueError("This sign-in link has expired. Start again from the app.")
    flow.fetch_token(code=code)
    save_credentials(flow.credentials)
    os.chmod(TOKEN_PICKLE, 0o600)


def disconnect():
    if os.path.exists(TOKEN_PICKLE):
        os.remove(TOKEN_PICKLE)

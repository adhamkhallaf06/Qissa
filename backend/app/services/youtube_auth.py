import json
import os

from app.core.config import API_BASE_URL, CLIENT_SECRETS_FILE, USER_SECRETS_DIR
from app.services.uploader import SCOPES, load_credentials, save_credentials

REDIRECT_URI = f"{API_BASE_URL}/api/youtube/oauth/callback"

# OAuth flows waiting for Google to redirect back: state -> (user_id, flow)
_pending = {}


def user_dir(user_id):
    return USER_SECRETS_DIR / user_id


def token_file(user_id):
    return user_dir(user_id) / "token.pickle"


def client_file(user_id):
    """The user's own OAuth client file, else the app-wide one in secrets/."""
    own = user_dir(user_id) / "client_secret.json"
    return own if own.exists() else CLIENT_SECRETS_FILE


def status(user_id):
    connected = False
    if os.path.exists(token_file(user_id)):
        try:
            connected = load_credentials(token_file(user_id)) is not None
        except Exception:
            connected = False
    return {
        "has_client_secret": os.path.exists(client_file(user_id)),
        "connected": connected,
        "redirect_uri": REDIRECT_URI,
    }


def save_client_secret(user_id, raw: bytes):
    """Validate and store the OAuth client file downloaded from Google Cloud."""
    try:
        data = json.loads(raw)
    except ValueError:
        raise ValueError("That file is not valid JSON.")
    client = data.get("installed") or data.get("web") if isinstance(data, dict) else None
    if not client or not client.get("client_id") or not client.get("client_secret"):
        raise ValueError("That does not look like a Google OAuth client file (client_secret.json).")

    user_dir(user_id).mkdir(parents=True, exist_ok=True)
    target = user_dir(user_id) / "client_secret.json"
    target.write_bytes(raw)
    os.chmod(target, 0o600)
    disconnect(user_id)  # a token from a different client would no longer refresh


def authorization_url(user_id):
    import google_auth_oauthlib.flow

    if not os.path.exists(client_file(user_id)):
        raise ValueError("Upload your client_secret.json first.")
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        str(client_file(user_id)), SCOPES, redirect_uri=REDIRECT_URI
    )
    url, state = flow.authorization_url(access_type="offline", prompt="consent")

    # One pending sign-in per user
    for old_state in [s for s, (owner, _) in _pending.items() if owner == user_id]:
        del _pending[old_state]
    _pending[state] = (user_id, flow)
    return url


def finish(state, code):
    """Complete the sign-in. The user is identified by the state we issued, not by a cookie."""
    user_id, flow = _pending.pop(state, (None, None))
    if flow is None:
        raise ValueError("This sign-in link has expired. Start again from the app.")
    flow.fetch_token(code=code)
    user_dir(user_id).mkdir(parents=True, exist_ok=True)
    save_credentials(flow.credentials, token_file(user_id))
    os.chmod(token_file(user_id), 0o600)


def disconnect(user_id):
    if os.path.exists(token_file(user_id)):
        os.remove(token_file(user_id))

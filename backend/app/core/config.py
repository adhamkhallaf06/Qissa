import os
from pathlib import Path

# backend/
BACKEND_DIR = Path(__file__).resolve().parents[2]

# --- Folders ---
DATA_DIR = BACKEND_DIR / "data"
INPUT_DIR = DATA_DIR / "input"
OUTPUT_DIR = DATA_DIR / "output_splits"
SECRETS_DIR = BACKEND_DIR / "secrets"

# --- YouTube credentials ---
CLIENT_SECRETS_FILE = SECRETS_DIR / "client_secret.json"
TOKEN_PICKLE = SECRETS_DIR / "token.pickle"

# --- API ---
JOBS_DIR = DATA_DIR / "jobs"  # one folder per job started from the web UI
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
FRONTEND_ORIGINS = os.environ.get("FRONTEND_ORIGINS", "http://localhost:5173").split(",")

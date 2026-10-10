import html

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import HTMLResponse

from app.api.auth import current_user
from app.services import youtube_auth

router = APIRouter(prefix="/api/youtube", tags=["youtube"])

MAX_SECRET_BYTES = 64 * 1024


def _page(title, message):
    return HTMLResponse(
        "<!doctype html><meta charset='utf-8'><title>YouTube connection</title>"
        "<body style='font-family:system-ui;display:grid;place-items:center;height:100vh;margin:0'>"
        f"<div style='text-align:center'><h2>{html.escape(title)}</h2><p>{html.escape(message)}</p></div>"
    )


@router.get("/status")
def get_status(user=Depends(current_user)):
    return youtube_auth.status(user["id"])


@router.post("/client-secret")
async def upload_client_secret(file: UploadFile, user=Depends(current_user)):
    raw = await file.read(MAX_SECRET_BYTES + 1)
    if len(raw) > MAX_SECRET_BYTES:
        raise HTTPException(400, "That file is too large to be a client_secret.json.")
    try:
        youtube_auth.save_client_secret(user["id"], raw)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return youtube_auth.status(user["id"])


@router.get("/connect")
def connect(user=Depends(current_user)):
    try:
        return {"auth_url": youtube_auth.authorization_url(user["id"])}
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@router.get("/oauth/callback", include_in_schema=False)
def oauth_callback(state: str = "", code: str = "", error: str = ""):
    if error or not code:
        return _page("YouTube was not connected", error or "Google did not return a sign-in code.")
    try:
        youtube_auth.finish(state, code)
    except Exception as exc:
        return _page("YouTube was not connected", str(exc))
    return _page("YouTube connected", "You can close this tab and go back to the app.")


@router.delete("/connection")
def disconnect(user=Depends(current_user)):
    youtube_auth.disconnect(user["id"])
    return youtube_auth.status(user["id"])

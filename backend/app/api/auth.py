from typing import Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from app.core.config import COOKIE_SECURE, SESSION_COOKIE, SESSION_DAYS
from app.services import auth

router = APIRouter(prefix="/api/auth", tags=["auth"])

EMAIL = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class SignupRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    email: str = Field(pattern=EMAIL, max_length=254)
    password: str = Field(min_length=8, max_length=200)


class LoginRequest(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=200)


def current_user(session: Optional[str] = Cookie(None, alias=SESSION_COOKIE)):
    """Dependency: the logged-in user, or 401."""
    user = auth.user_for_token(session)
    if user is None:
        raise HTTPException(401, "Please log in.")
    return user


def _start_session(response, user):
    response.set_cookie(
        SESSION_COOKIE,
        auth.create_session(user["id"]),
        max_age=SESSION_DAYS * 24 * 3600,
        httponly=True,  # not readable from JavaScript
        samesite="lax",
        secure=COOKIE_SECURE,
    )
    return user


@router.post("/signup", status_code=201)
def signup(body: SignupRequest, response: Response):
    try:
        user = auth.create_user(body.email, body.password, body.name)
    except auth.AuthError as exc:
        raise HTTPException(409, str(exc))
    return _start_session(response, user)


@router.post("/login")
def login(body: LoginRequest, response: Response):
    try:
        user = auth.authenticate(body.email, body.password)
    except auth.TooManyAttempts as exc:
        raise HTTPException(429, str(exc))
    except auth.AuthError as exc:
        raise HTTPException(401, str(exc))
    return _start_session(response, user)


@router.post("/logout", status_code=204)
def logout(response: Response, session: Optional[str] = Cookie(None, alias=SESSION_COOKIE)):
    auth.delete_session(session)
    response.delete_cookie(SESSION_COOKIE)


@router.get("/me")
def me(user=Depends(current_user)):
    return user

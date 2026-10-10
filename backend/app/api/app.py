from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth as auth_api
from app.api import jobs as jobs_api
from app.api import youtube as youtube_api
from app.core import db
from app.core.config import FRONTEND_ORIGINS
from app.services import jobs


@asynccontextmanager
async def lifespan(app):
    db.init()
    jobs.fail_interrupted()
    yield


app = FastAPI(title="Qissa", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=True,  # the session cookie
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_api.router)
app.include_router(jobs_api.router)
app.include_router(youtube_api.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}

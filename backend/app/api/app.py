from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import jobs as jobs_api
from app.api import youtube as youtube_api
from app.core.config import FRONTEND_ORIGINS
from app.services import jobs


@asynccontextmanager
async def lifespan(app):
    jobs.fail_interrupted()
    yield


app = FastAPI(title="YouTube Shorts Automation", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs_api.router)
app.include_router(youtube_api.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}

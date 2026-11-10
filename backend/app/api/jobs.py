import os
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, ValidationError

from app.api.auth import current_user
from app.schemas import PipelineOptions
from app.services import downloader, grader, jobs, youtube_auth
from app.services.splitter import allowed_extensions

router = APIRouter(prefix="/api", tags=["jobs"])


@router.get("/options/defaults")
def default_options():
    options = PipelineOptions()
    options.grading.enabled = grader.available()  # on by default once a key is set up
    return options


@router.get("/grading/status")
def grading_status(user=Depends(current_user)):
    return {"available": grader.available(), "model": grader.MODEL}


def _parse_options(options: str) -> PipelineOptions:
    try:
        return PipelineOptions.model_validate_json(options)
    except ValidationError as exc:
        first = exc.errors()[0]
        field = ".".join(str(part) for part in first["loc"])
        raise HTTPException(422, f"{field}: {first['msg']}")


def _check_options(options: PipelineOptions, user):
    if options.upload.enabled and not youtube_auth.status(user["id"])["connected"]:
        raise HTTPException(400, "Connect your YouTube account first, or turn off uploading.")
    if options.grading.enabled and not grader.available():
        raise HTTPException(400, "Grading needs an Anthropic API key on the server, or turn off grading.")


@router.post("/jobs", status_code=201)
def create_job(file: UploadFile, options: str = Form("{}"), user=Depends(current_user)):
    parsed = _parse_options(options)

    filename = Path(file.filename or "").name
    if not filename.lower().endswith(allowed_extensions):
        raise HTTPException(400, "Unsupported video type. Use one of: " + ", ".join(allowed_extensions))

    _check_options(parsed, user)

    job_id = jobs.new_id()
    with open(jobs.input_dir(job_id) / filename, "wb") as target:
        shutil.copyfileobj(file.file, target)
    return jobs.start(job_id, filename, parsed, user["id"])


class LinkJob(BaseModel):
    url: str
    options: PipelineOptions = PipelineOptions()


@router.post("/jobs/from-link", status_code=201)
def create_job_from_link(body: LinkJob, user=Depends(current_user)):
    """Start a job from a YouTube link: download it, cut it into Shorts, and upload them."""
    _check_options(body.options, user)
    try:
        video = downloader.inspect(body.url)
    except downloader.LinkError as exc:
        raise HTTPException(400, str(exc))

    job_id = jobs.new_id()
    return jobs.start(job_id, video["title"], body.options, user["id"], source_url=body.url.strip())


@router.get("/jobs")
def list_jobs(user=Depends(current_user)):
    return jobs.list_all(user["id"])


@router.get("/jobs/{job_id}")
def get_job(job_id: str, user=Depends(current_user)):
    job = jobs.get(job_id, user["id"])
    if job is None:
        raise HTTPException(404, "Job not found.")
    return job


@router.delete("/jobs/{job_id}", status_code=204)
def delete_job(job_id: str, user=Depends(current_user)):
    try:
        if not jobs.delete(job_id, user["id"]):
            raise HTTPException(404, "Job not found.")
    except RuntimeError as exc:
        raise HTTPException(409, str(exc))


@router.post("/jobs/{job_id}/retry-upload")
def retry_upload(job_id: str, user=Depends(current_user)):
    """Upload a job's remaining clips again (e.g. after YouTube's upload limit resets)."""
    if not youtube_auth.status(user["id"])["connected"]:
        raise HTTPException(400, "Connect your YouTube account first.")
    try:
        job = jobs.retry_upload(job_id, user["id"])
    except RuntimeError as exc:
        raise HTTPException(409, str(exc))
    if job is None:
        raise HTTPException(404, "Job not found.")
    return job


@router.get("/jobs/{job_id}/clips/{name}")
def get_clip(job_id: str, name: str, user=Depends(current_user)):
    job = jobs.get(job_id, user["id"])
    # Only serve files the job actually produced (also blocks path tricks)
    if job is None or name not in job["clips"]:
        raise HTTPException(404, "Clip not found.")
    return FileResponse(os.path.join(jobs.output_dir(job_id), name), media_type="video/mp4")

import os
import shutil
from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import ValidationError

from app.schemas import PipelineOptions
from app.services import jobs, youtube_auth
from app.services.splitter import allowed_extensions

router = APIRouter(prefix="/api", tags=["jobs"])


@router.get("/options/defaults")
def default_options():
    return PipelineOptions()


@router.post("/jobs", status_code=201)
def create_job(file: UploadFile, options: str = Form("{}")):
    try:
        parsed = PipelineOptions.model_validate_json(options)
    except ValidationError as exc:
        first = exc.errors()[0]
        field = ".".join(str(part) for part in first["loc"])
        raise HTTPException(422, f"{field}: {first['msg']}")

    filename = Path(file.filename or "").name
    if not filename.lower().endswith(allowed_extensions):
        raise HTTPException(400, "Unsupported video type. Use one of: " + ", ".join(allowed_extensions))

    if parsed.upload.enabled and not youtube_auth.status()["connected"]:
        raise HTTPException(400, "Connect your YouTube account first, or turn off uploading.")

    job_id = jobs.new_id()
    with open(jobs.input_dir(job_id) / filename, "wb") as target:
        shutil.copyfileobj(file.file, target)
    return jobs.start(job_id, filename, parsed)


@router.get("/jobs")
def list_jobs():
    return jobs.list_all()


@router.get("/jobs/{job_id}")
def get_job(job_id: str):
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(404, "Job not found.")
    return job


@router.delete("/jobs/{job_id}", status_code=204)
def delete_job(job_id: str):
    try:
        if not jobs.delete(job_id):
            raise HTTPException(404, "Job not found.")
    except RuntimeError as exc:
        raise HTTPException(409, str(exc))


@router.get("/jobs/{job_id}/clips/{name}")
def get_clip(job_id: str, name: str):
    job = jobs.get(job_id)
    # Only serve files the job actually produced (also blocks path tricks)
    if job is None or name not in job["clips"]:
        raise HTTPException(404, "Clip not found.")
    return FileResponse(os.path.join(jobs.output_dir(job_id), name), media_type="video/mp4")

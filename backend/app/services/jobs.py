import contextlib
import json
import shutil
import threading
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from app.core.config import JOBS_DIR
from app.main import run_pipeline
from app.schemas import PipelineOptions
from app.services import downloader, uploader, youtube_auth

# Pipeline step -> job status shown in the UI
STEP_STATUS = {
    "downloader": "downloading",
    "splitter": "splitting",
    "processor": "processing",
    "cleaner": "cleaning",
    "grader": "grading",
    "uploader": "uploading",
}
ACTIVE = {"queued", *STEP_STATUS.values()}
LOG_LINES = 200

# Whisper and ffmpeg are heavy, so jobs run one at a time
_executor = ThreadPoolExecutor(max_workers=1)
_lock = threading.Lock()


def job_dir(job_id):
    return JOBS_DIR / job_id


def input_dir(job_id):
    return job_dir(job_id) / "input"


def output_dir(job_id):
    return job_dir(job_id) / "output"


def _state_path(job_id):
    return job_dir(job_id) / "job.json"


def _save(job):
    with _lock:
        path = _state_path(job["id"])
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)


def _clips(job_id):
    folder = output_dir(job_id)
    if not folder.exists():
        return []
    return sorted(p.name for p in folder.iterdir() if p.name.endswith("_final.mp4"))


def get(job_id, user_id=None):
    """The job, or None if it does not exist or belongs to someone else."""
    path = _state_path(job_id)
    # job_id comes from the URL: only accept ids we generated
    if not job_id.isalnum() or not path.exists():
        return None
    with _lock:
        job = json.loads(path.read_text(encoding="utf-8"))
    if user_id is not None and job.get("user_id") != user_id:
        return None
    job["clips"] = _clips(job_id)
    return job


def list_all(user_id=None):
    if not JOBS_DIR.exists():
        return []
    jobs = [get(p.name, user_id) for p in JOBS_DIR.iterdir() if p.is_dir()]
    return sorted((j for j in jobs if j), key=lambda j: j["created_at"], reverse=True)


def new_id():
    job_id = uuid.uuid4().hex[:12]
    input_dir(job_id).mkdir(parents=True)
    output_dir(job_id).mkdir()
    return job_id


def start(job_id, filename, options: PipelineOptions, user_id, source_url=None):
    """Queue a job. With source_url, the video is downloaded first and filename is just its title."""
    job = {
        "id": job_id,
        "user_id": user_id,
        "filename": filename,
        "source_url": source_url,
        "status": "queued",
        "error": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "options": options.model_dump(mode="json"),
        "uploads": [],
        "grades": [],
        "log": [],
    }
    _save(job)
    _executor.submit(_run, job, options)
    return get(job_id)


def delete(job_id, user_id):
    job = get(job_id, user_id)
    if job is None:
        return False
    if job["status"] in ACTIVE:
        raise RuntimeError("This job is still running.")
    shutil.rmtree(job_dir(job_id))
    return True


def pending_uploads(job):
    """Clips that should be on YouTube but aren't yet, in upload order (best first when graded)."""
    options = job["options"]
    done = {video["file"] for video in job["uploads"]}
    clips = set(job["clips"])
    grades = job.get("grades") or []
    if options.get("grading", {}).get("enabled") and grades:
        wanted = [g["file"] for g in grades if g["score"] is not None][:options["grading"]["top_n"]]
    else:
        wanted = sorted(clips)
    return [f for f in wanted if f in clips and f not in done]


def retry_upload(job_id, user_id):
    """Upload a finished or failed job's remaining clips again, without re-processing. None if not found."""
    job = get(job_id, user_id)
    if job is None:
        return None
    if job["status"] in ACTIVE:
        raise RuntimeError("This job is still running.")
    if not job["options"]["upload"]["enabled"]:
        raise RuntimeError("Uploading was turned off for this video.")
    files = pending_uploads(job)
    if not files:
        raise RuntimeError("There are no clips left to upload.")

    job.pop("clips", None)
    job["status"] = "queued"
    job["error"] = None
    _save(job)
    _executor.submit(_run_upload, job, files)
    return get(job_id)


def fail_interrupted():
    """Jobs left mid-run by a server restart can never finish; mark them failed."""
    for job in list_all():
        if job["status"] in ACTIVE:
            job.pop("clips", None)
            job["status"] = "failed"
            job["error"] = "The server restarted while this job was running."
            _save(job)


class _JobLog:
    """Collects the pipeline's print() output into the job state."""

    def __init__(self, job):
        self.job = job
        self.buffer = ""

    def write(self, text):
        self.buffer += text
        *lines, self.buffer = self.buffer.split("\n")
        lines = [line for line in lines if line.strip()]
        if lines:
            self.job["log"] = (self.job["log"] + lines)[-LOG_LINES:]
            _save(self.job)
        return len(text)

    def flush(self):
        pass


def _uploader_kwargs(job):
    def on_upload(video):
        job["uploads"].append(video)
        _save(job)

    return {
        "client_secrets_file": youtube_auth.client_file(job["user_id"]),
        "token_path": youtube_auth.token_file(job["user_id"]),
        "on_upload": on_upload,
    }


def _finish(job, work):
    """Run work() with its output in the job log, then record done or failed."""
    try:
        with contextlib.redirect_stdout(_JobLog(job)):
            work()
        job["status"] = "done"
    except Exception as exc:
        if not isinstance(exc, uploader.UploadError):
            traceback.print_exc()
        job["status"] = "failed"
        job["error"] = str(exc) or exc.__class__.__name__
    _save(job)


def _run_upload(job, files):
    def work():
        print(f"\n🔁 Retrying upload of {len(files)} clip(s)")
        job["status"] = STEP_STATUS["uploader"]
        _save(job)
        options = PipelineOptions.model_validate(job["options"])
        taken = [video["publish_at"] for video in job["uploads"] if video["publish_at"]]
        uploader.run(output_dir(job["id"]), options=options.upload, interactive=False,
                     files=files, taken_times=taken, **_uploader_kwargs(job))

    _finish(job, work)


def _run(job, options):
    def on_step(name):
        job["status"] = STEP_STATUS[name]
        _save(job)

    def on_grades(grades):
        job["grades"] = grades
        _save(job)

    def work():
        if job.get("source_url"):
            on_step("downloader")
            downloader.download(job["source_url"], input_dir(job["id"]))
        # Uploads are recorded one by one through on_upload, so they survive a failure part-way
        run_pipeline(
            options,
            input_dir=input_dir(job["id"]),
            output_dir=output_dir(job["id"]),
            on_step=on_step,
            interactive=False,
            on_grades=on_grades,
            uploader_kwargs=_uploader_kwargs(job),
        )

    _finish(job, work)

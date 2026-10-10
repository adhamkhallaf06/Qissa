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

# Pipeline step -> job status shown in the UI
STEP_STATUS = {
    "splitter": "splitting",
    "processor": "processing",
    "cleaner": "cleaning",
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


def get(job_id):
    path = _state_path(job_id)
    # job_id comes from the URL: only accept ids we generated
    if not job_id.isalnum() or not path.exists():
        return None
    with _lock:
        job = json.loads(path.read_text(encoding="utf-8"))
    job["clips"] = _clips(job_id)
    return job


def list_all():
    if not JOBS_DIR.exists():
        return []
    jobs = [get(p.name) for p in JOBS_DIR.iterdir() if p.is_dir()]
    return sorted((j for j in jobs if j), key=lambda j: j["created_at"], reverse=True)


def new_id():
    job_id = uuid.uuid4().hex[:12]
    input_dir(job_id).mkdir(parents=True)
    output_dir(job_id).mkdir()
    return job_id


def start(job_id, filename, options: PipelineOptions):
    job = {
        "id": job_id,
        "filename": filename,
        "status": "queued",
        "error": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "options": options.model_dump(mode="json"),
        "uploads": [],
        "log": [],
    }
    _save(job)
    _executor.submit(_run, job, options)
    return get(job_id)


def delete(job_id):
    job = get(job_id)
    if job is None:
        return False
    if job["status"] in ACTIVE:
        raise RuntimeError("This job is still running.")
    shutil.rmtree(job_dir(job_id))
    return True


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


def _run(job, options):
    def on_step(name):
        job["status"] = STEP_STATUS[name]
        _save(job)

    try:
        with contextlib.redirect_stdout(_JobLog(job)):
            job["uploads"] = run_pipeline(
                options,
                input_dir=input_dir(job["id"]),
                output_dir=output_dir(job["id"]),
                on_step=on_step,
                interactive=False,
            )
        job["status"] = "done"
    except Exception as exc:
        traceback.print_exc()
        job["status"] = "failed"
        job["error"] = str(exc) or exc.__class__.__name__
    _save(job)

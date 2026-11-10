"""Download a YouTube video from a link so the pipeline can cut it into Shorts."""
from pathlib import Path
from urllib.parse import urlparse

import yt_dlp

YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be"}
MAX_DURATION_SECONDS = 3 * 60 * 60  # refuse anything longer than 3 hours
MAX_HEIGHT = 1080  # Shorts are 1080x1920, so more than 1080p only costs disk and time


class LinkError(ValueError):
    """The link is not something we can download."""


def is_youtube_url(url):
    try:
        parsed = urlparse(url.strip())
    except ValueError:
        return False
    return parsed.scheme in ("http", "https") and (parsed.hostname or "").lower() in YOUTUBE_HOSTS


class _Logger:
    """Keep yt-dlp quiet apart from warnings and errors; progress is printed by the hook."""

    def debug(self, msg):
        pass

    def info(self, msg):
        pass

    def warning(self, msg):
        print(f"⚠️ {msg}")

    def error(self, msg):
        print(f"❌ {msg}")


def _base_options():
    return {
        "noplaylist": True,  # a watch?v=...&list=... link means just that one video
        "quiet": True,
        "no_warnings": True,
        "logger": _Logger(),
    }


def inspect(url):
    """Check a link before starting a job. Returns {"title", "duration"} or raises LinkError."""
    if not is_youtube_url(url):
        raise LinkError("Paste a YouTube video link (youtube.com or youtu.be).")
    try:
        with yt_dlp.YoutubeDL(_base_options()) as ydl:
            info = ydl.extract_info(url, download=False)
    except yt_dlp.utils.DownloadError as exc:
        message = str(exc).removeprefix("ERROR: ")
        raise LinkError(f"Could not open that video: {message}") from exc

    if info.get("_type") == "playlist":
        raise LinkError("That is a playlist. Paste the link of a single video.")
    if info.get("is_live") or info.get("live_status") in ("is_live", "is_upcoming"):
        raise LinkError("Live streams can't be cut yet. Try again after the stream has ended.")
    duration = info.get("duration") or 0
    if duration > MAX_DURATION_SECONDS:
        raise LinkError(f"That video is longer than {MAX_DURATION_SECONDS // 3600} hours.")
    return {"title": info.get("title") or "YouTube video", "duration": duration}


def download(url, target_dir):
    """Download the video into target_dir as an .mp4 and return its path."""
    target_dir = Path(target_dir)
    last_step = {"value": -1}

    def on_progress(status):
        if status["status"] != "downloading":
            return
        total = status.get("total_bytes") or status.get("total_bytes_estimate")
        if not total:
            return
        percent = int(status["downloaded_bytes"] * 100 / total)
        if percent // 10 > last_step["value"]:  # one log line per 10%
            last_step["value"] = percent // 10
            print(f"Downloading… {percent}%")

    options = {
        **_base_options(),
        "format": f"bv*[height<={MAX_HEIGHT}]+ba/b[height<={MAX_HEIGHT}]/b",
        "merge_output_format": "mp4",
        "outtmpl": str(target_dir / "%(title).80B [%(id)s].%(ext)s"),
        "windowsfilenames": True,
        "progress_hooks": [on_progress],
    }
    print(f"Downloading {url}")
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)
        path = Path(ydl.prepare_filename(info)).with_suffix(".mp4")
    if not path.exists():
        # Fall back to whatever video landed in the folder
        videos = [p for p in target_dir.iterdir() if p.suffix.lower() in (".mp4", ".mkv", ".webm")]
        if not videos:
            raise RuntimeError("The download finished but no video file was found.")
        path = videos[0]
    print(f"✅ Downloaded: {path.name}")
    return path


if __name__ == "__main__":
    import sys

    from app.core.config import INPUT_DIR

    download(sys.argv[1], INPUT_DIR)

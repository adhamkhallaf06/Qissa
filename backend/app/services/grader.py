"""Grade every finished clip with Claude so only the best ones get uploaded.

Claude sees each clip's transcript plus a few frames and scores it 1-10 as a YouTube Short.
Needs an Anthropic API key: the ANTHROPIC_API_KEY environment variable, or the key pasted
into backend/secrets/anthropic_api_key.
"""
import base64
import os
import subprocess
from pathlib import Path

import anthropic
from pydantic import BaseModel

from app.core.config import ANTHROPIC_KEY_FILE, OUTPUT_DIR
from app.schemas import CaptionOptions

# Haiku is plenty for scoring a one-minute clip and costs a fraction of a cent per clip.
# Set GRADER_MODEL (e.g. claude-sonnet-5-5) for more careful judgment at a higher price.
MODEL = os.environ.get("GRADER_MODEL", "claude-haiku-5-5")
# Models that can retry a declined request on a fallback model server-side (Haiku can't)
FALLBACK_MODELS = {"claude-opus-5-5", "claude-sonnet-5-5", "claude-fable-5-2"}
FRAMES_PER_CLIP = 4
FRAME_WIDTH = 360  # small frames are plenty to judge the picture and keep the cost down
TRANSCRIPTS = "transcripts"  # subfolder of the output folder; processor.py writes here

SYSTEM_PROMPT = """You grade clips cut from a longer video, to decide which ones are worth posting as YouTube Shorts.

Each clip is up to about a minute long. You get its transcript (often Arabic) and a few frames taken evenly across it.

Score it from 1 to 10 for how well it would do as a standalone Short:
- Hook: do the first seconds give a viewer a reason to keep watching?
- Standalone: does it make sense without the rest of the video, or does it start or end in the middle of a thought?
- Payoff: is there a story, a surprising fact, a strong emotion, humour or a clear takeaway?
- Picture: is there something worth looking at, or is it a static or blank screen?
- Filler: intros, outros, sponsor reads, "subscribe" requests and long silences make a weak Short.

Use the whole scale: 8-10 only for clips you would confidently post, 1-3 for clips that should not be posted.
Write the hook and reason in English, one short sentence each."""


class ClipGrade(BaseModel):
    score: int
    hook: str
    reason: str


def api_key():
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key and ANTHROPIC_KEY_FILE.exists():
        key = ANTHROPIC_KEY_FILE.read_text(encoding="utf-8").strip()
    return key or None


def available():
    return api_key() is not None


def _duration(path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True,
    )
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0


def extract_frames(path, count=FRAMES_PER_CLIP):
    """JPEG bytes of `count` frames spread evenly across the clip."""
    duration = _duration(path)
    frames = []
    for i in range(count):
        at = duration * (i + 0.5) / count
        result = subprocess.run(
            ["ffmpeg", "-v", "error", "-ss", f"{at:.2f}", "-i", str(path), "-frames:v", "1",
             "-vf", f"scale={FRAME_WIDTH}:-2", "-f", "image2pipe", "-vcodec", "mjpeg", "-"],
            capture_output=True,
        )
        if result.returncode == 0 and result.stdout:
            frames.append(result.stdout)
    return frames


def _transcript(output_folder, clip, captions, whisper_model):
    """The transcript saved by the processor, or a fresh one when captions were off."""
    saved = Path(output_folder) / TRANSCRIPTS / f"{Path(clip).stem}.txt"
    if saved.exists():
        return saved.read_text(encoding="utf-8").strip(), whisper_model
    if whisper_model is None:
        import whisper
        whisper_model = whisper.load_model(captions.model)
    result = whisper_model.transcribe(str(Path(output_folder) / clip), language=captions.language)
    return result["text"].strip(), whisper_model


def grade_clip(client, path, transcript):
    """A ClipGrade for one clip, or None if Claude declined to grade it."""
    content = [
        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                     "data": base64.standard_b64encode(frame).decode("ascii")}}
        for frame in extract_frames(path)
    ]
    content.append({
        "type": "text",
        "text": f"Transcript:\n{transcript or '(no speech detected)'}\n\nGrade this clip.",
    })
    request = dict(
        model=MODEL,
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        output_config={"effort": "medium"},
        output_format=ClipGrade,
        messages=[{"role": "user", "content": content}],
    )
    if MODEL in FALLBACK_MODELS:
        # If a safety check declines the request, retry it on a fallback model instead of failing
        response = client.beta.messages.parse(
            **request, betas=["server-side-fallback-2026-07-01"], fallbacks="default")
    else:
        response = client.messages.parse(**request)
    if response.stop_reason == "refusal" or response.parsed_output is None:
        return None
    grade = response.parsed_output
    grade.score = max(1, min(10, grade.score))
    return grade


def rank(grades):
    """Best first; ungraded clips last; ties keep the clip order."""
    return sorted(grades, key=lambda g: -(g["score"] or 0))


def run(output_dir=OUTPUT_DIR, captions=None):
    """Grade every *_final.mp4 in output_dir. Returns the grades, best first."""
    output_folder = str(output_dir)
    captions = captions or CaptionOptions()
    key = api_key()
    if not key:
        raise RuntimeError("Grading needs an Anthropic API key. Set ANTHROPIC_API_KEY or add "
                           "backend/secrets/anthropic_api_key, then restart the backend.")

    clips = sorted(f for f in os.listdir(output_folder) if f.endswith("_final.mp4"))
    if not clips:
        print("No clips to grade.")
        return []

    client = anthropic.Anthropic(api_key=key)
    whisper_model = None
    grades = []
    for clip in clips:
        print(f"\n⭐ Grading {clip}")
        transcript, whisper_model = _transcript(output_folder, clip, captions, whisper_model)
        try:
            grade = grade_clip(client, os.path.join(output_folder, clip), transcript)
        except (anthropic.AuthenticationError, anthropic.PermissionDeniedError) as exc:
            raise RuntimeError(f"Anthropic rejected the API key: {exc.message}") from exc
        except anthropic.APIError as exc:
            # One failed clip should not sink the whole job; it just ranks last
            print(f"⚠️ Could not grade {clip}: {exc}")
            grade = None

        if grade is None:
            print("⚠️ Not graded")
            grades.append({"file": clip, "score": None, "hook": "", "reason": "Could not be graded."})
        else:
            print(f"{grade.score}/10 — {grade.reason}")
            grades.append({"file": clip, **grade.model_dump()})

    ranked = rank(grades)
    print("\n✅ Ranking: " + ", ".join(f"{g['file']} ({g['score'] or '-'})" for g in ranked))
    return ranked


if __name__ == "__main__":
    run()

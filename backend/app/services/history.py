"""Values each user has used before (titles, hashtags, caption styles, publish times).

The studio form starts empty and offers these as one-click suggestions.
"""
import json
from datetime import datetime, timezone

from app.core import db
from app.schemas import PipelineOptions

# How many of each kind to keep per user, most recent first
LIMITS = {"title": 15, "hashtag": 40, "captions": 8, "schedule": 8}
KINDS = tuple(LIMITS)


def _key(value):
    """Stored text for a value; dicts are sorted so the same style is stored once."""
    return value if isinstance(value, str) else json.dumps(value, sort_keys=True, ensure_ascii=False)


def _values(options: PipelineOptions):
    upload = options.upload
    if upload.title.strip():
        yield "title", upload.title.strip()
    for tag in upload.hashtags:
        yield "hashtag", tag
    if options.captions.enabled:
        yield "captions", options.captions.model_dump(mode="json", exclude={"enabled"})
    if upload.enabled and upload.schedule.enabled and upload.schedule.time_slots:
        yield "schedule", {"time_slots": sorted(upload.schedule.time_slots), "timezone": upload.schedule.timezone}


def record(user_id, options: PipelineOptions):
    """Remember the values a new job was started with."""
    now = datetime.now(timezone.utc).isoformat()
    with db.connect() as conn:
        for kind, value in _values(options):
            conn.execute(
                "INSERT INTO history (user_id, kind, value, used_at) VALUES (?, ?, ?, ?) "
                "ON CONFLICT (user_id, kind, value) DO UPDATE SET used_at = excluded.used_at",
                (user_id, kind, _key(value), now),
            )
        for kind, limit in LIMITS.items():
            conn.execute(
                "DELETE FROM history WHERE user_id = ? AND kind = ? AND value NOT IN ("
                "SELECT value FROM history WHERE user_id = ? AND kind = ? ORDER BY used_at DESC LIMIT ?)",
                (user_id, kind, user_id, kind, limit),
            )


def get(user_id):
    """{"title": [...], "hashtag": [...], "captions": [...], "schedule": [...]}, most recent first."""
    result = {kind: [] for kind in KINDS}
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT kind, value, used_at FROM history WHERE user_id = ? ORDER BY used_at DESC, rowid",
            (user_id,),
        ).fetchall()
    for row in rows:
        if row["kind"] not in result:
            continue
        value = row["value"] if row["kind"] in ("title", "hashtag") else json.loads(row["value"])
        result[row["kind"]].append({"value": value, "used_at": row["used_at"]})
    return result


def forget(user_id, kind, value):
    with db.connect() as conn:
        conn.execute(
            "DELETE FROM history WHERE user_id = ? AND kind = ? AND value = ?",
            (user_id, kind, _key(value)),
        )

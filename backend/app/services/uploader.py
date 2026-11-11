import os
import pickle
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from app.core.config import CLIENT_SECRETS_FILE, OUTPUT_DIR, TOKEN_PICKLE
from app.schemas import UploadOptions

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TITLE_LIMIT = 100  # YouTube's maximum title length

# YouTube error reasons -> what the user can do about them
UPLOAD_ERRORS = {
    "uploadLimitExceeded": "YouTube says this channel has reached its upload limit. Verify the channel at "
                           "youtube.com/verify or wait about 24 hours, then press Retry upload.",
    "quotaExceeded": "The YouTube API quota for your Google Cloud project is used up for today. It resets at "
                     "midnight Pacific time; press Retry upload after that.",
    "forbidden": "YouTube refused the upload for this account. Check the channel can upload videos, then "
                 "press Retry upload.",
}


class UploadError(RuntimeError):
    """A YouTube upload failed; the message says what to do about it."""


def _explain(exc, done, total):
    reasons = {d.get("reason") for d in getattr(exc, "error_details", None) or [] if isinstance(d, dict)}
    message = next((UPLOAD_ERRORS[r] for r in reasons if r in UPLOAD_ERRORS), None)
    message = message or f"YouTube returned an error: {getattr(exc, 'reason', None) or exc}"
    if done:
        message = f"Uploaded {done} of {total} clips. " + message
    return message


def safe_title(text):
    cleaned = "".join(c if c.isprintable() else "" for c in text)
    cleaned = cleaned.replace("<", "").replace(">", "").strip()
    return cleaned if cleaned else "Untitled Clip"


def build_metadata(options: UploadOptions, index=0, total=1):
    """Title, description and tags for clip number `index` out of `total`."""
    title = options.title.strip()
    if options.number_clips and total > 1:
        title = f"{title} - Part {index + 1}".strip(" -") if title else f"Part {index + 1}"

    if options.hashtags_in_title:
        # Add as many hashtags as fit in the title
        for tag in options.hashtags:
            candidate = f"{title} {tag}".strip()
            if len(candidate) > TITLE_LIMIT:
                break
            title = candidate

    tag_line = " ".join(dict.fromkeys(options.hashtags + ["#Shorts"]))
    description = "\n\n".join(part for part in (options.description.strip(), tag_line) if part)
    tags = list(dict.fromkeys([tag.lstrip("#") for tag in options.hashtags] + ["Shorts"]))

    return {
        "title": safe_title(title)[:TITLE_LIMIT],
        "description": description,
        "tags": tags,
        "categoryId": options.category_id,
    }


def publish_times(schedule, count, now=None, taken=()):
    """Publish datetime (in the schedule's timezone) for each of `count` clips.

    `taken` holds times already used by earlier uploads (e.g. before a retry); those slots are skipped.
    """
    taken = {datetime.fromisoformat(t) if isinstance(t, str) else t for t in taken}
    tz = ZoneInfo(schedule.timezone)
    now = now or datetime.now(tz)
    start_date = schedule.start_date or now.date() + timedelta(days=1)

    # Fill each day's slots in clock order, so clip 1 (the best one, when grading) goes out first.
    # Slots less than 15 minutes away are skipped (YouTube needs the time in the future), so a
    # past start date or a retry later in the day moves on to the next free slot.
    slots = sorted(schedule.time_slots)
    if not slots:
        raise ValueError("Add at least one publish time to the schedule.")
    earliest = now + timedelta(minutes=15)
    times = []
    i = 0
    while len(times) < count:
        hour, minute = map(int, slots[i % len(slots)].split(":"))
        day = start_date + timedelta(days=i // len(slots))
        publish_datetime = datetime.combine(day, time(hour, minute), tzinfo=tz)
        if publish_datetime >= earliest and publish_datetime not in taken:
            times.append(publish_datetime)
        i += 1
    return times


def load_credentials(token_path=TOKEN_PICKLE):
    """Saved YouTube credentials, refreshed if needed. None if not connected yet."""
    import google.auth.transport.requests

    if not os.path.exists(token_path):
        return None
    with open(token_path, "rb") as token:
        credentials = pickle.load(token)

    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(google.auth.transport.requests.Request())
        save_credentials(credentials, token_path)
    return credentials if credentials and credentials.valid else None


def save_credentials(credentials, token_path=TOKEN_PICKLE):
    with open(token_path, "wb") as token:
        pickle.dump(credentials, token)


def get_youtube_client(interactive=True, client_secrets_file=CLIENT_SECRETS_FILE, token_path=TOKEN_PICKLE):
    import google_auth_oauthlib.flow
    import googleapiclient.discovery

    # --- Authenticate ---
    credentials = load_credentials(token_path)
    if not credentials:
        if not interactive:
            raise RuntimeError("YouTube is not connected.")
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            str(client_secrets_file), SCOPES
        )
        credentials = flow.run_local_server(port=8080)
        save_credentials(credentials, token_path)

    return googleapiclient.discovery.build("youtube", "v3", credentials=credentials)


def run(output_dir=OUTPUT_DIR, options=None, interactive=True,
        client_secrets_file=CLIENT_SECRETS_FILE, token_path=TOKEN_PICKLE, files=None, on_upload=None,
        taken_times=()):
    """Upload every *_final.mp4 in output_dir, or just `files` in that order. Returns the uploaded videos.

    on_upload(video) is called after each upload, so progress survives a failure part-way through.
    taken_times: publish times (ISO strings) already used by this video's earlier uploads.
    """
    from googleapiclient.errors import HttpError

    output_folder = str(output_dir)
    options = options or UploadOptions()

    youtube = get_youtube_client(interactive, client_secrets_file, token_path)

    # --- Process ---
    if files is None:
        video_files = sorted([f for f in os.listdir(output_folder) if f.endswith("_final.mp4")])
    else:
        video_files = [f for f in files if os.path.isfile(os.path.join(output_folder, f))]
    if not video_files:
        print("No *_final.mp4 files found.")
        return []

    schedule = options.schedule
    times = publish_times(schedule, len(video_files), taken=taken_times) if schedule.enabled else []
    uploaded = []

    for index, vid in enumerate(video_files):
        video_path = os.path.join(output_folder, vid)
        snippet = build_metadata(options, index, len(video_files))

        if schedule.enabled:
            publish_datetime = times[index]
            publish_iso = publish_datetime.astimezone(timezone.utc).isoformat()
            # Scheduled videos must be private until publishAt
            status = {"privacyStatus": "private", "publishAt": publish_iso}

            # Print for clarity
            print(f"\nLocal scheduled time: {publish_datetime.isoformat()}")
            print(f"UTC scheduled time:   {publish_iso}")
        else:
            publish_iso = None
            status = {"privacyStatus": options.privacy}

        # Upload
        request = youtube.videos().insert(
            part="snippet,status",
            body={"snippet": snippet, "status": status},
            media_body=video_path
        )
        try:
            response = request.execute()
        except HttpError as exc:
            raise UploadError(_explain(exc, len(uploaded), len(video_files))) from exc
        print(f"✅ Uploaded Video ID: {response['id']}")
        video = {"file": vid, "video_id": response["id"], "title": snippet["title"], "publish_at": publish_iso}
        uploaded.append(video)
        if on_upload:
            on_upload(video)

    print("\n✅ All videos uploaded" + (" and scheduled." if schedule.enabled else "."))

    if options.delete_after_upload:
        print("\n🧹 Cleaning up output folder...")
        for f in os.listdir(output_folder):
            file_path = os.path.join(output_folder, f)
            if os.path.isfile(file_path) and f != ".gitkeep":
                os.remove(file_path)

        print("✅ All output files deleted.")

    return uploaded


if __name__ == "__main__":
    run()

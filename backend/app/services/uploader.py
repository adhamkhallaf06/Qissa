import os
import pickle
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from app.core.config import CLIENT_SECRETS_FILE, OUTPUT_DIR, TOKEN_PICKLE
from app.schemas import UploadOptions

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TITLE_LIMIT = 100  # YouTube's maximum title length


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


def publish_times(schedule, count, now=None):
    """Publish datetime (in the schedule's timezone) for each of `count` clips."""
    tz = ZoneInfo(schedule.timezone)
    now = now or datetime.now(tz)
    start_date = schedule.start_date or now.date() + timedelta(days=1)

    times = []
    for i in range(count):
        day_offset = i // len(schedule.time_slots)
        hour, minute = map(int, schedule.time_slots[i % len(schedule.time_slots)].split(":"))
        publish_datetime = datetime.combine(start_date + timedelta(days=day_offset), time(hour, minute), tzinfo=tz)

        # Ensure it's at least 15 minutes from now
        if publish_datetime < now + timedelta(minutes=15):
            publish_datetime = (now + timedelta(minutes=15)).replace(microsecond=0)
        times.append(publish_datetime)
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
        client_secrets_file=CLIENT_SECRETS_FILE, token_path=TOKEN_PICKLE):
    """Upload every *_final.mp4 in output_dir. Returns the uploaded videos."""
    output_folder = str(output_dir)
    options = options or UploadOptions()

    youtube = get_youtube_client(interactive, client_secrets_file, token_path)

    # --- Process ---
    video_files = sorted([f for f in os.listdir(output_folder) if f.endswith("_final.mp4")])
    if not video_files:
        print("No *_final.mp4 files found.")
        return []

    schedule = options.schedule
    times = publish_times(schedule, len(video_files)) if schedule.enabled else []
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
        response = request.execute()
        print(f"✅ Uploaded Video ID: {response['id']}")
        uploaded.append({"file": vid, "video_id": response["id"], "title": snippet["title"], "publish_at": publish_iso})

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

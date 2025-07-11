import os
import pickle
from datetime import datetime, timedelta, timezone
import google_auth_oauthlib.flow
import googleapiclient.discovery
import google.auth.transport.requests

# --- Folders ---
output_folder = "output_splits"

# --- YouTube Settings ---
CLIENT_SECRETS_FILE = "/Users/adhamkhallaf/code/python/YouTube Shorts Automation Platform/Youtube_Automation/client_secret_yoo.json"
#CLIENT_SECRETS_FILE = "/Users/adhamkhallaf/code/python/YouTube Shorts Automation Platform/Youtube_Automation/client_secret.json"
#CLIENT_SECRETS_FILE = "/Users/adhamkhallaf/code/python/YouTube Shorts Automation Platform/Youtube_Automation/client_secret_yoo.json"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CATEGORY_ID = "22"
TOKEN_PICKLE = "token.pickle"

# --- Scheduling ---
schedule_start_date = datetime.now(timezone.utc).date() + timedelta(days=1)
daily_time_slots = [9, 11, 13, 15, 17]

# --- Helpers ---
def safe_title(text):
    cleaned = "".join(c if c.isprintable() else "" for c in text).strip()
    return cleaned if cleaned else "Untitled Clip"

# --- Authenticate ---
credentials = None
if os.path.exists(TOKEN_PICKLE):
    with open(TOKEN_PICKLE, "rb") as token:
        credentials = pickle.load(token)

if not credentials or not credentials.valid:
    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(google.auth.transport.requests.Request())
    else:
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRETS_FILE, SCOPES
        )
        credentials = flow.run_local_server(port=8080)
    with open(TOKEN_PICKLE, "wb") as token:
        pickle.dump(credentials, token)

youtube = googleapiclient.discovery.build("youtube", "v3", credentials=credentials)

# --- Process ---
video_files = sorted([f for f in os.listdir(output_folder) if f.endswith("_final.mp4")])
if not video_files:
    print("No *_final.mp4 files found.")
    exit()

video_counter = 0

for vid in video_files:
    video_path = os.path.join(output_folder, vid)
    base_name = os.path.splitext(vid)[0]

    # --- Compute schedule ---
    day_offset = video_counter // len(daily_time_slots)
    slot_index = video_counter % len(daily_time_slots)
    publish_date = schedule_start_date + timedelta(days=day_offset)
    publish_hour = daily_time_slots[slot_index]

    publish_datetime = datetime(
        publish_date.year,
        publish_date.month,
        publish_date.day,
        publish_hour,
        0,
        tzinfo=timezone.utc
    )
    publish_iso = publish_datetime.isoformat()

    print(f"\nScheduling upload for {publish_iso}...")

    # --- Upload ---
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": f"{safe_title(base_name)}",
                "description": "#Shorts\nShorts #YouTubeShorts #Trending #Viral #FYP",
                "tags": ["Shorts"],
                "categoryId": CATEGORY_ID
            },
            "status": {
                "privacyStatus": "private",
                "publishAt": publish_iso
            }
        },
        media_body=video_path
    )
    response = request.execute()
    print(f"✅ Uploaded Video ID: {response['id']}")

    video_counter += 1

print("\n✅ All videos uploaded and scheduled.")

print("\n🧹 Cleaning up output folder...")

for f in os.listdir(output_folder):
    file_path = os.path.join(output_folder, f)
    if os.path.isfile(file_path):
        os.remove(file_path)

print("✅ All output files deleted.")
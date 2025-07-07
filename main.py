import os
import whisper
import pickle
from datetime import datetime, timedelta, timezone
import google_auth_oauthlib.flow
import googleapiclient.discovery
import google.auth.transport.requests
import subprocess

# --- Folders ---
input_folder = "input"
output_folder = "output"

# --- YouTube Upload Settings ---
CLIENT_SECRETS_FILE = "/Users/adhamkhallaf/code/python/YouTube Shorts Automation Platform/client_secret.json"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CATEGORY_ID = "22"  # People & Blogs
TOKEN_PICKLE = "token.pickle"

# --- Subtitle Settings ---
colors = ["&H00FFFF&", "&H007FFF&", "&HFFFFFF&"]
font_name = "Arial Unicode MS"
font_size = 12

# --- Scheduling Settings ---
schedule_start_date = datetime.now(timezone.utc).date() + timedelta(days=1)
daily_time_slots = [9, 11, 13, 15, 17]  # UTC hours


# --- Utility Functions ---
def safe_title(text):
    cleaned = "".join(c if c.isprintable() else "" for c in text).strip()
    return cleaned if cleaned else "Untitled Clip"


def get_resolution(filepath):
    result = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=s=x:p=0",
            filepath
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    w, h = result.stdout.strip().split("x")
    return int(w), int(h)


# --- Check Folders ---
if not os.path.exists(input_folder):
    print(f"Input folder '{input_folder}' not found.")
    exit()
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# Clean output folder
for f in os.listdir(output_folder):
    file_path = os.path.join(output_folder, f)
    if os.path.isfile(file_path):
        os.remove(file_path)

# Find input videos
video_files = [f for f in os.listdir(input_folder) if f.endswith(".mp4")]
if not video_files:
    print("No .mp4 files found in the input folder.")
    exit()

# Load Whisper model
model = whisper.load_model("base")

# --- Authenticate YouTube ---
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

video_counter = 0

# --- Process each video ---
for vid in video_files:
    input_path = os.path.join(input_folder, vid)
    base_name = os.path.splitext(vid)[0]
    split_pattern = os.path.join(output_folder, f"{base_name}_%03d.mp4")

    print(f"\nSplitting: {vid}")
    split_command = (
        f'ffmpeg -i "{input_path}" '
        f'-c:v libx264 -preset veryfast -c:a aac -b:a 128k '
        f'-g 50 -force_key_frames "expr:gte(t,n_forced*60)" '
        f'-f segment -segment_time 60 "{split_pattern}"'
    )
    os.system(split_command)

    split_clips = sorted([f for f in os.listdir(output_folder) if f.startswith(base_name) and f.endswith(".mp4")])

    for clip in split_clips:
        clip_input = os.path.join(output_folder, clip)
        clip_vertical = os.path.join(output_folder, f"{os.path.splitext(clip)[0]}_vertical.mp4")
        clip_subtitled = os.path.join(output_folder, f"{os.path.splitext(clip)[0]}_subtitled.mp4")
        ass_path = os.path.join(output_folder, f"{os.path.splitext(clip)[0]}.ass")

        # Determine scaling
        width, height = get_resolution(clip_input)
        if width >= height:
            vf_filter = "scale=-1:1920,crop=1080:1920"
        else:
            vf_filter = "scale=1080:-1,pad=1080:1920:(ow-iw)/2:(oh-ih)/2"

        print(f"\nConverting to vertical: {clip}")
        convert_command = f'ffmpeg -i "{clip_input}" -vf "{vf_filter}" "{clip_vertical}"'
        os.system(convert_command)

        print("Transcribing subtitles...")
        result = model.transcribe(clip_vertical, language="ar")

        # Write subtitles
        with open(ass_path, "w", encoding="utf-8") as f:
            f.write("[Script Info]\nScriptType: v4.00+\n\n")
            f.write("[V4+ Styles]\n")
            f.write(
                "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n")
            f.write(
                f"Style: Default,{font_name},{font_size},&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,80,1\n\n")
            f.write("[Events]\n")
            f.write("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")

            if result["segments"]:
                for idx, segment in enumerate(result["segments"]):
                    start = segment["start"]
                    end = segment["end"]
                    text = segment["text"].replace("\n", " ")

                    start_h = int(start // 3600)
                    start_m = int((start % 3600) // 60)
                    start_s = int(start % 60)
                    start_cs = int((start - int(start)) * 100)
                    end_h = int(end // 3600)
                    end_m = int((end % 3600) // 60)
                    end_s = int(end % 60)
                    end_cs = int((end - int(end)) * 100)

                    start_ts = f"{start_h}:{start_m:02}:{start_s:02}.{start_cs:02}"
                    end_ts = f"{end_h}:{end_m:02}:{end_s:02}.{end_cs:02}"

                    color = colors[idx % len(colors)]
                    color_tag = f"{{\\c{color}}}"

                    f.write(f"Dialogue: 0,{start_ts},{end_ts},Default,,0,0,0,,{color_tag}{text}\n")
            else:
                # No segments: dummy subtitle
                f.write("Dialogue: 0,0:00:00.00,0:00:02.00,Default,,0,0,0,,No speech detected\n")

        print("Burning subtitles...")
        subtitle_command = f'ffmpeg -i "{clip_vertical}" -vf "subtitles={ass_path}" "{clip_subtitled}"'
        os.system(subtitle_command)

        # Compute schedule
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

        print(f"Scheduling upload for {publish_iso}...")

        print("Uploading to YouTube...")
        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": f"{safe_title(base_name)} - Clip {clip}",
                    "description": "Automated upload #Shorts",
                    "tags": ["Shorts"],
                    "categoryId": CATEGORY_ID
                },
                "status": {
                    "privacyStatus": "private",
                    #"publishAt": publish_iso
                }
            },
            media_body=clip_subtitled
        )
        print("Uploaded Video")

        video_counter += 1

        os.remove(clip_input)
        os.remove(clip_vertical)
        os.remove(ass_path)

        print("Done processing and cleaned up.")

print("\nAll videos processed and uploaded.")

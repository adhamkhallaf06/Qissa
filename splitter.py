import os
import subprocess

# --- Folders ---
input_folder = "input"
output_folder = "output_splits"

allowed_extensions = (".mp4", ".mov", ".mkv", ".avi", ".flv", ".webm", ".mpg", ".mpeg", ".3gp")

if not os.path.exists(input_folder):
    print(f"Input folder '{input_folder}' not found.")
    exit()
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# Clean output folder
for f in os.listdir(output_folder):
    path = os.path.join(output_folder, f)
    if os.path.isfile(path):
        os.remove(path)

# Filter only video files with allowed extensions
video_files = [
    f for f in os.listdir(input_folder)
    if os.path.isfile(os.path.join(input_folder, f)) and f.lower().endswith(allowed_extensions)
]

if not video_files:
    print("No video files found.")
    exit()

for vid in video_files:
    input_path = os.path.join(input_folder, vid)
    base_name = os.path.splitext(vid)[0]
    split_pattern = os.path.join(output_folder, f"{base_name}_%03d.mp4")

    print(f"\nSplitting: {vid}")
    split_command = (
        f'ffmpeg -y -i "{input_path}" '
        f'-c:v libx264 -preset veryfast -crf 23 '
        f'-force_key_frames "expr:gte(t,n_forced*1)" '  
        f'-c:a aac -b:a 128k '
        f'-f segment -segment_time 60 -reset_timestamps 1 '
        f'"{split_pattern}"'
    )
    print(f"Running:\n{split_command}\n")
    subprocess.run(split_command, shell=True, check=True)

print("\n✅ All videos split successfully.")
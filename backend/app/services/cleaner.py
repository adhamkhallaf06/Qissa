import os
import subprocess

from app.core.config import OUTPUT_DIR


def run(output_dir=OUTPUT_DIR, max_silence_seconds=5.0):
    folder = str(output_dir)

    if not os.path.exists(folder):
        print(f"Folder '{folder}' not found.")
        return

    clips = sorted([
        f for f in os.listdir(folder)
        if os.path.isfile(os.path.join(folder, f)) and f != ".gitkeep"
    ])

    if not clips:
        print("No .mp4 files found.")
        return

    print("🔍 Checking audio silence in clips...\n")

    for clip in clips:
        clip_path = os.path.join(folder, clip)

        # Run ffmpeg to detect silence
        cmd = [
            "ffmpeg",
            "-i", clip_path,
            "-af", "silencedetect=noise=-30dB:d=0.5",
            "-f", "null",
            "-"
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        output = result.stderr

        # Parse silence events
        silence_lines = [line for line in output.splitlines() if "silence_start" in line or "silence_end" in line]
        total_silence = 0.0
        current_silence_start = None

        for line in silence_lines:
            if "silence_start" in line:
                parts = line.strip().split("silence_start: ")
                if len(parts) == 2:
                    current_silence_start = float(parts[1])
            elif "silence_end" in line:
                parts = line.strip().split("silence_end: ")
                if len(parts) == 2 and current_silence_start is not None:
                    silence_end = float(parts[1].split(" | ")[0])
                    total_silence += (silence_end - current_silence_start)
                    current_silence_start = None

        print(f"{clip}: total silence = {total_silence:.1f} seconds")

        if total_silence > max_silence_seconds:
            print(f"❌ Deleting {clip}: silence exceeds {max_silence_seconds:g} seconds.")
            os.remove(clip_path)
        else:
            print(f"✅ Keeping {clip}: acceptable audio.")

    print("\n✅ Done checking all clips.")


if __name__ == "__main__":
    run()

import os
import subprocess

from app.core.config import OUTPUT_DIR
from app.schemas import CaptionOptions
from app.services.captions import build_ass

# --- Extensions to process ---
allowed_extensions = (".mp4", ".mov", ".avi", ".mkv", ".webm")


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


def run(output_dir=OUTPUT_DIR, captions=None, vertical=True):
    output_folder = str(output_dir)
    captions = captions or CaptionOptions()

    # --- Check Output Folder ---
    if not os.path.exists(output_folder):
        print(f"Output folder '{output_folder}' not found.")
        return

    # --- Get Clips to Process ---
    clips = sorted([
        f for f in os.listdir(output_folder)
        if f.lower().endswith(allowed_extensions) and not f.endswith("_final.mp4")
    ])

    if not clips:
        print("No clips to process.")
        return

    # --- Load Whisper ---
    model = None
    if captions.enabled:
        import whisper
        model = whisper.load_model(captions.model)

    for clip in clips:
        basename = os.path.splitext(clip)[0]
        clip_input = os.path.join(output_folder, clip)
        clip_vertical = os.path.join(output_folder, f"{basename}_vertical.mp4")
        clip_final = os.path.join(output_folder, f"{basename}_final.mp4")
        ass_name = f"{basename}.ass"
        ass_path = os.path.join(output_folder, ass_name)

        result = None
        if model is not None:
            print(f"\n🎤 Transcribing subtitles: {clip}")
            result = model.transcribe(
                clip_input,
                language=captions.language,
                word_timestamps=bool(captions.max_words),
            )

        # --- Determine resolution ---
        width, height = get_resolution(clip_input)
        is_vertical = height >= width

        # --- Decide which input to burn subtitles on ---
        if is_vertical or not vertical:
            if is_vertical:
                print("📐 Video is already vertical. Skipping conversion.")
            clip_for_subtitles = clip_input
        else:
            print("🎬 Converting to vertical format...")
            vf_filter = "scale=1080:-1,pad=1080:1920:(ow-iw)/2:(oh-ih)/2"
            convert_command = (
                f'ffmpeg -y -i "{clip_input}" '
                f'-vf "{vf_filter}" '
                f'-c:v libx264 -preset veryfast -crf 23 -c:a aac -b:a 128k "{clip_vertical}"'
            )
            subprocess.run(convert_command, shell=True, check=True)
            clip_for_subtitles = clip_vertical

        if result is None:
            # --- No captions: the (converted) clip is the final clip ---
            os.replace(clip_for_subtitles, clip_final)
        else:
            # --- Write .ASS subtitle file ---
            print("📝 Generating subtitle file...")
            with open(ass_path, "w", encoding="utf-8") as f:
                f.write(build_ass(result["segments"], captions))

            # --- Burn subtitles ---
            # The subtitles filter gets a path relative to the output folder (cwd below)
            # so the absolute project path never has to be escaped inside the filter.
            print("🔥 Burning subtitles into video...")
            burn_command = (
                f'ffmpeg -y -i "{clip_for_subtitles}" '
                f'-vf "subtitles={ass_name}" '
                f'-c:v libx264 -preset veryfast -crf 23 -c:a aac -b:a 128k "{clip_final}"'
            )
            subprocess.run(burn_command, shell=True, check=True, cwd=output_folder)
            os.remove(ass_path)

        # --- Cleanup ---
        for leftover in (clip_input, clip_vertical):
            if os.path.exists(leftover):
                os.remove(leftover)

        print(f"✅ Done: {clip_final}")

    print("\n✅ All clips processed successfully.")


if __name__ == "__main__":
    run()

import os
import whisper
import subprocess

output_folder = "output_splits"

colors = ["&H00FFFF&", "&H007FFF&", "&HFFFFFF&"]
font_name = "Arial Unicode MS"
font_size = 12

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

if not os.path.exists(output_folder):
    print(f"Output folder '{output_folder}' not found.")
    exit()

model = whisper.load_model("base")

clips = [f for f in os.listdir(output_folder) if f.endswith(".mp4") and "_final" not in f]
if not clips:
    print("No clips to process.")
    exit()

for clip in sorted(clips):
    clip_input = os.path.join(output_folder, clip)
    clip_vertical = os.path.join(output_folder, f"{os.path.splitext(clip)[0]}_vertical.mp4")
    clip_final = os.path.join(output_folder, f"{os.path.splitext(clip)[0]}_final.mp4")
    ass_path = os.path.join(output_folder, f"{os.path.splitext(clip)[0]}.ass")

    print(f"\nTranscribing subtitles: {clip}")
    result = model.transcribe(clip_input, language="ar")

    width, height = get_resolution(clip_input)
    if width >= height:
        vf_filter = "scale=-1:1920,crop=1080:1920"
    else:
        vf_filter = "scale=1080:-1,pad=1080:1920:(ow-iw)/2:(oh-ih)/2"

    print("Converting to vertical format...")
    convert_command = (
        f'ffmpeg -y -i "{clip_input}" '
        f'-vf "{vf_filter}" '
        f'-c:v libx264 -preset veryfast -crf 23 -c:a aac -b:a 128k "{clip_vertical}"'
    )
    subprocess.run(convert_command, shell=True, check=True)

    print("Generating subtitle file...")
    with open(ass_path, "w", encoding="utf-8") as f:
        f.write("[Script Info]\nScriptType: v4.00+\n\n")
        f.write("[V4+ Styles]\n")
        f.write(
            "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        )
        f.write(
            f"Style: Default,{font_name},{font_size},&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,80,1\n\n"
        )
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
            f.write("Dialogue: 0,0:00:00.00,0:00:02.00,Default,,0,0,0,,No speech detected\n")

    print("Burning subtitles into video...")
    burn_command = (
        f'ffmpeg -y -i "{clip_vertical}" '
        f'-vf "subtitles={ass_path}" '
        f'-c:v libx264 -preset veryfast -crf 23 -c:a aac -b:a 128k "{clip_final}"'
    )
    subprocess.run(burn_command, shell=True, check=True)

    os.remove(clip_input)
    os.remove(clip_vertical)
    os.remove(ass_path)

    print(f"✅ Done: {clip_final}")

print("\n✅ All clips processed successfully.")
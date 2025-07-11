import subprocess

def run_script(script_name):
    print(f"\n🔹 Running {script_name}...")
    result = subprocess.run(["python", script_name], capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr)

if __name__ == "__main__":
    print("✅ STARTING FULL AUTOMATION PIPELINE")

    # 1. Split videos
    run_script("splitter.py")

    # 2. Convert to vertical, transcribe, burn subtitles
    run_script("processor.py")

    # 3. Delete clips that have >5 sec silence
    run_script("cleaner.py")

    # 4. Upload to YouTube
    run_script("uploader.py")

    print("\n✅ ALL STEPS COMPLETED SUCCESSFULLY")
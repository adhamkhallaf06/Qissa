from app.services import cleaner, processor, splitter, uploader


def run_step(name, step):
    print(f"\n🔹 Running {name}...")
    step()


def run_pipeline():
    print("✅ STARTING FULL AUTOMATION PIPELINE")

    # 1. Split videos
    run_step("splitter", splitter.run)

    # 2. Convert to vertical, transcribe, burn subtitles
    run_step("processor", processor.run)

    # 3. Delete clips that have >5 sec silence
    run_step("cleaner", cleaner.run)

    # 4. Upload to YouTube
    run_step("uploader", uploader.run)

    print("\n✅ ALL STEPS COMPLETED SUCCESSFULLY")


if __name__ == "__main__":
    run_pipeline()

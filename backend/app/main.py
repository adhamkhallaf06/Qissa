import argparse

from app.core.config import INPUT_DIR, OUTPUT_DIR
from app.schemas import PipelineOptions
from app.services import cleaner, grader, processor, splitter, uploader


def run_pipeline(options=None, input_dir=INPUT_DIR, output_dir=OUTPUT_DIR, on_step=None, interactive=True,
                 uploader_kwargs=None, on_grades=None):
    """Run every enabled step. Returns the list of uploaded videos."""
    options = options or PipelineOptions()

    def run_step(name, step, **kwargs):
        print(f"\n🔹 Running {name}...")
        if on_step:
            on_step(name)
        return step(**kwargs)

    print("✅ STARTING FULL AUTOMATION PIPELINE")

    # 1. Split videos
    run_step("splitter", splitter.run,
             input_dir=input_dir, output_dir=output_dir, clip_seconds=options.clip_seconds)

    # 2. Convert to vertical, transcribe, burn subtitles
    run_step("processor", processor.run,
             output_dir=output_dir, captions=options.captions, vertical=options.vertical)

    # 3. Delete clips that have too much silence
    if options.remove_silent:
        run_step("cleaner", cleaner.run,
                 output_dir=output_dir, max_silence_seconds=options.max_silence_seconds)

    # 4. Score each clip with Claude; only the best ones get uploaded, best first
    files = None
    if options.grading.enabled:
        grades = run_step("grader", grader.run, output_dir=output_dir, captions=options.captions)
        if on_grades:
            on_grades(grades)
        files = [g["file"] for g in grades if g["score"] is not None][:options.grading.top_n]
        print(f"\n🏆 Uploading the top {len(files)} of {len(grades)} clips")

    # 5. Upload to YouTube
    uploads = []
    if options.upload.enabled:
        uploads = run_step("uploader", uploader.run,
                           output_dir=output_dir, options=options.upload, interactive=interactive,
                           files=files, **(uploader_kwargs or {}))

    print("\n✅ ALL STEPS COMPLETED SUCCESSFULLY")
    return uploads or []


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the full Shorts pipeline")
    parser.add_argument("--options", help="path to a JSON file of pipeline options (see options.example.json)")
    args = parser.parse_args()

    options = None
    if args.options:
        with open(args.options, encoding="utf-8") as f:
            options = PipelineOptions.model_validate_json(f.read())
    run_pipeline(options)

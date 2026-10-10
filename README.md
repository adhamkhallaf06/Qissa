# YouTube Shorts Automation

Splits long videos into 60-second clips, converts them to vertical, burns in Arabic subtitles (Whisper), drops clips with too much silence, and schedules the rest as YouTube Shorts.

## Layout

```
backend/
  app/
    main.py            # runs the full pipeline
    core/config.py     # paths (data, secrets)
    schemas.py         # pipeline / caption options
    services/          # one module per pipeline step
      splitter.py
      processor.py
      captions.py      # builds the .ass subtitle file
      cleaner.py
      uploader.py
  data/
    input/             # drop source videos here (git-ignored)
    output_splits/     # generated clips (git-ignored)
  secrets/             # client_secret.json, token.pickle (git-ignored)
  pyproject.toml
frontend/              # web UI (not built yet)
```

## Backend setup

Requires Python 3.9+ and `ffmpeg` on your PATH.

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

Put your Google OAuth client file at `backend/secrets/client_secret.json`.

## Running

From `backend/`:

```bash
python -m app.main                 # full pipeline
python -m app.services.splitter    # a single step
python -m app.main --options options.json   # custom processing / caption settings
```

## Options

Copy `backend/options.example.json` and change what you need. Everything is optional; the defaults reproduce the original look.

- `clip_seconds`, `vertical`, `remove_silent`, `max_silence_seconds` control the processing steps.
- `captions.enabled` turns subtitles off entirely (Whisper is not loaded).
- `captions.language` (`null` = auto-detect), `captions.model`, and `captions.max_words` (words shown at once) control transcription.
- `captions.font_name`, `font_size`, `bold`, `italic`, `uppercase`, `colors` (cycled per caption), `outline_color`, `outline_width`, `shadow`, `background`, `background_color`, `position` (`top` / `middle` / `bottom`) and `margin_v` control the look.
- `upload.title`, `description`, `hashtags`, `hashtags_in_title`, `number_clips`, `category_id` set what YouTube shows. Titles are trimmed to 100 characters.
- `upload.schedule` picks when clips go public: `timezone`, `start_date` (`null` = tomorrow) and `time_slots` (`HH:MM`, one clip per slot, then the next day). Set `schedule.enabled` to `false` to publish right away with `upload.privacy`.
- `upload.enabled: false` stops after processing; `delete_after_upload: false` keeps the clips.

# YouTube Shorts Automation

Splits long videos into 60-second clips, converts them to vertical, burns in Arabic subtitles (Whisper), drops clips with too much silence, and schedules the rest as YouTube Shorts.

## Layout

```
backend/
  app/
    main.py            # runs the full pipeline
    core/config.py     # paths (data, secrets)
    services/          # one module per pipeline step
      splitter.py
      processor.py
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
```

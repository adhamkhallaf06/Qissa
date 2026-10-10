# Qissa

**Long story, cut short.** *Qissa* (قصة) is Arabic for "story", from the same root as *qass*, "to cut".

Splits long videos into 60-second clips, converts them to vertical, burns in Arabic subtitles (Whisper), drops clips with too much silence, and schedules the rest as YouTube Shorts.

## Layout

```
backend/
  app/
    main.py            # runs the full pipeline (CLI)
    api/               # FastAPI app: accounts, jobs, YouTube connection
    core/config.py     # paths (data, secrets)
    core/db.py         # SQLite (users, sessions)
    schemas.py         # pipeline / caption options
    services/          # one module per pipeline step
      splitter.py
      processor.py
      captions.py      # builds the .ass subtitle file
      cleaner.py
      uploader.py
      auth.py          # password hashing, users, sessions
      jobs.py          # background jobs started from the API
      youtube_auth.py  # OAuth client file + sign-in
  data/
    input/             # drop source videos here (git-ignored)
    output_splits/     # generated clips (git-ignored)
  secrets/             # client_secret.json, token.pickle (git-ignored)
  pyproject.toml
frontend/              # React + Vite web UI
  src/
    api.ts             # typed client for the backend API
    App.tsx
    components/
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

## API

From `backend/`:

```bash
uvicorn app.api.app:app --reload --port 8000
```

Interactive docs are at http://localhost:8000/docs.

| Endpoint | What it does |
| --- | --- |
| `POST /api/jobs` | Upload a video (`file`) plus `options` (JSON string) and start processing |
| `GET /api/jobs`, `GET /api/jobs/{id}` | Job status, log, produced clips and uploaded video IDs |
| `GET /api/jobs/{id}/clips/{name}` | Stream a finished clip |
| `DELETE /api/jobs/{id}` | Remove a finished job and its files |
| `GET /api/options/defaults` | Default options |
| `GET /api/youtube/status` | Whether a client file is stored and an account is connected |
| `POST /api/youtube/client-secret` | Store the OAuth client file from Google Cloud |
| `GET /api/youtube/connect` | Returns the Google sign-in URL |
| `DELETE /api/youtube/connection` | Forget the connected account |

Jobs run one at a time and live in `backend/data/jobs/<id>/`.

### Accounts

Everything except `/api/options/defaults` and `/api/health` needs a logged-in user.

| Endpoint | What it does |
| --- | --- |
| `POST /api/auth/signup` | Create an account (`name`, `email`, `password` of 8+ characters) and log in |
| `POST /api/auth/login` | Log in; five wrong passwords for an email lock it for 15 minutes |
| `POST /api/auth/logout` | End the session |
| `GET /api/auth/me` | The current user |

Users live in SQLite at `backend/data/app.db`. Passwords are hashed with scrypt; the session is an HttpOnly cookie valid for 30 days, and only its hash is stored. Set `COOKIE_SECURE=1` when serving over HTTPS.

Each user only sees their own jobs and clips, and connects their own YouTube channel (token in `backend/secrets/users/<id>/`). `backend/secrets/client_secret.json` is the app-wide OAuth client that every user signs in through unless they upload their own.

Google redirects back to `http://localhost:8000/api/youtube/oauth/callback`. Desktop-type OAuth clients accept this as is; for a Web-type client, add it under "Authorized redirect URIs" in Google Cloud Console. Set `API_BASE_URL` if the API runs somewhere else.

## Web UI

With the API running, in a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Pick a video, set the title and hashtags, style the captions, choose when clips go public, connect YouTube (upload `client_secret.json`, then sign in), and press **Create Shorts**. Progress, finished clips and uploaded video links appear under "Your videos".

The dev server proxies `/api` to `http://localhost:8000`.

## Options

Copy `backend/options.example.json` and change what you need. Everything is optional; the defaults reproduce the original look.

- `clip_seconds`, `vertical`, `remove_silent`, `max_silence_seconds` control the processing steps.
- `captions.enabled` turns subtitles off entirely (Whisper is not loaded).
- `captions.language` (`null` = auto-detect), `captions.model`, and `captions.max_words` (words shown at once) control transcription.
- `captions.font_name`, `font_size`, `bold`, `italic`, `uppercase`, `colors` (cycled per caption), `outline_color`, `outline_width`, `shadow`, `background`, `background_color`, `position` (`top` / `middle` / `bottom`) and `margin_v` control the look.
- `upload.title`, `description`, `hashtags`, `hashtags_in_title`, `number_clips`, `category_id` set what YouTube shows. Titles are trimmed to 100 characters.
- `upload.schedule` picks when clips go public: `timezone`, `start_date` (`null` = tomorrow) and `time_slots` (`HH:MM`, one clip per slot, then the next day). Set `schedule.enabled` to `false` to publish right away with `upload.privacy`.
- `upload.enabled: false` stops after processing; `delete_after_upload: false` keeps the clips.

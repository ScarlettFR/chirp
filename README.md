# chirp

Tiny Twitter-style site. FastAPI + SQLite + Jinja + a bit of htmx.
No SPA, no build step, no JS framework. Runs as a single process.

## run

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000.

Env:
- `SECRET_KEY` — session cookie key, change in prod
- `DB_URL` — SQLAlchemy URL, default `sqlite:///./chirp.db`
- `PORT` — default `8000`

## what's inside

- register / login, session cookie
- 280-char posts
- timeline (latest 50)
- like toggle via htmx (no full reload)
- public profile `/@name` with post count + followers/following
- follow / unfollow

## stack

- FastAPI for routes
- SQLAlchemy 2.0 + SQLite
- Jinja2 templates + Tailwind (CDN) + htmx 2
- bcrypt via passlib

## notes

- SQLite is fine for a prototype. Postgres later — just swap `DB_URL`.
- There's no rate-limit, no email confirmation, no image uploads.
  That's on purpose — the idea was to keep it small.
- Tailwind is loaded from CDN to skip the build step. For production
  compile it down to a single CSS file.

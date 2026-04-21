from __future__ import annotations

import os
import re
from pathlib import Path

from fastapi import FastAPI, Request, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, desc, func
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from .db import Base, engine, get_db
from .models import User, Post, Like, Follow
from .auth import hash_pw, check_pw


BASE = Path(__file__).parent
app = FastAPI(title="chirp", docs_url=None, redoc_url=None)

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "dev-secret-change-me"),
    same_site="lax",
)
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")

tpl = Jinja2Templates(directory=str(BASE / "templates"))

Base.metadata.create_all(engine)


USERNAME_RE = re.compile(r"^[a-z0-9_]{3,32}$")


def current_user(request: Request, db: Session) -> User | None:
    uid = request.session.get("uid")
    if not uid:
        return None
    return db.get(User, uid)


def require_user(request: Request, db: Session) -> User:
    u = current_user(request, db)
    if not u:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED)
    return u


def liked_set(db: Session, me: User | None, posts: list[Post]) -> set[int]:
    if not me or not posts:
        return set()
    ids = [p.id for p in posts]
    rows = db.execute(
        select(Like.post_id).where(Like.user_id == me.id, Like.post_id.in_(ids))
    ).all()
    return {r[0] for r in rows}


@app.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    posts = db.scalars(select(Post).order_by(desc(Post.created_at)).limit(50)).all()
    return tpl.TemplateResponse("index.html", {
        "request":  request,
        "me":       me,
        "posts":    posts,
        "like_set": liked_set(db, me, posts),
    })


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return tpl.TemplateResponse("login.html", {"request": request, "err": None})


@app.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    username = username.strip().lower()
    u = db.scalar(select(User).where(User.username == username))
    if not u or not check_pw(password, u.password_hash):
        return tpl.TemplateResponse(
            "login.html",
            {"request": request, "err": "неверный логин или пароль"},
            status_code=400,
        )
    request.session["uid"] = u.id
    return RedirectResponse("/", status_code=303)


@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return tpl.TemplateResponse("register.html", {"request": request, "err": None})


@app.post("/register")
def register(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    username = username.strip().lower()
    if not USERNAME_RE.match(username):
        return tpl.TemplateResponse(
            "register.html",
            {"request": request, "err": "имя: 3–32 символа, буквы/цифры/_"},
            status_code=400,
        )
    if len(password) < 6:
        return tpl.TemplateResponse(
            "register.html",
            {"request": request, "err": "пароль минимум 6 символов"},
            status_code=400,
        )
    if db.scalar(select(User).where(User.username == username)):
        return tpl.TemplateResponse(
            "register.html",
            {"request": request, "err": "имя занято"},
            status_code=400,
        )

    u = User(username=username, password_hash=hash_pw(password))
    db.add(u)
    db.commit()
    db.refresh(u)
    request.session["uid"] = u.id
    return RedirectResponse("/", status_code=303)


@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)


@app.post("/post")
def new_post(
    request: Request,
    body: str = Form(...),
    db: Session = Depends(get_db),
):
    me = require_user(request, db)
    body = body.strip()
    if not body or len(body) > 280:
        raise HTTPException(400, "пост пустой или длиннее 280")

    p = Post(author_id=me.id, body=body)
    db.add(p)
    db.commit()
    db.refresh(p)

    if request.headers.get("HX-Request"):
        return tpl.TemplateResponse(
            "_post.html",
            {"request": request, "post": p, "me": me, "liked": False},
        )
    return RedirectResponse("/", status_code=303)


@app.post("/post/{pid}/like", response_class=HTMLResponse)
def like(pid: int, request: Request, db: Session = Depends(get_db)):
    me = require_user(request, db)
    p = db.get(Post, pid)
    if not p:
        raise HTTPException(404)

    existing = db.scalar(select(Like).where(Like.user_id == me.id, Like.post_id == pid))
    if existing:
        db.delete(existing)
        liked = False
    else:
        db.add(Like(user_id=me.id, post_id=pid))
        liked = True
    db.commit()

    cnt = db.scalar(select(func.count()).select_from(Like).where(Like.post_id == pid)) or 0

    if request.headers.get("HX-Request"):
        return HTMLResponse(_like_btn(pid, cnt, liked))
    return RedirectResponse("/", status_code=303)


def _like_btn(pid: int, cnt: int, liked: bool) -> str:
    color = "text-pink-500" if liked else "text-slate-400"
    heart = "♥" if liked else "♡"
    return (
        f'<button hx-post="/post/{pid}/like" hx-target="this" hx-swap="outerHTML" '
        f'class="flex items-center gap-1 {color} hover:text-pink-400 text-sm">'
        f'<span>{heart}</span><span>{cnt}</span></button>'
    )


@app.get("/@{username}", response_class=HTMLResponse)
def profile(username: str, request: Request, db: Session = Depends(get_db)):
    me = current_user(request, db)
    u = db.scalar(select(User).where(User.username == username.lower()))
    if not u:
        raise HTTPException(404, "нет такого")

    posts = db.scalars(
        select(Post).where(Post.author_id == u.id).order_by(desc(Post.created_at))
    ).all()
    followers = db.scalar(select(func.count()).select_from(Follow).where(Follow.followee_id == u.id)) or 0
    following = db.scalar(select(func.count()).select_from(Follow).where(Follow.follower_id == u.id)) or 0

    i_follow = False
    if me and me.id != u.id:
        i_follow = bool(db.scalar(
            select(Follow).where(Follow.follower_id == me.id, Follow.followee_id == u.id)
        ))

    return tpl.TemplateResponse("profile.html", {
        "request":   request,
        "me":        me,
        "u":         u,
        "posts":     posts,
        "followers": followers,
        "following": following,
        "i_follow":  i_follow,
        "like_set":  liked_set(db, me, posts),
    })


@app.post("/@{username}/follow")
def follow(username: str, request: Request, db: Session = Depends(get_db)):
    me = require_user(request, db)
    target = db.scalar(select(User).where(User.username == username.lower()))
    if not target or target.id == me.id:
        raise HTTPException(400)

    existing = db.scalar(
        select(Follow).where(Follow.follower_id == me.id, Follow.followee_id == target.id)
    )
    if existing:
        db.delete(existing)
    else:
        db.add(Follow(follower_id=me.id, followee_id=target.id))
    db.commit()
    return RedirectResponse(f"/@{target.username}", status_code=303)


@app.get("/healthz")
def healthz():
    return {"ok": True}

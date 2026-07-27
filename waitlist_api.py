"""
Xenkloud Pulse — Waitlist API

A tiny, fully self-owned waitlist backend. Stores signups in a local
SQLite file (waitlist.db) — no third-party form service, no external
dependency on your data.

Setup:
    pip install fastapi uvicorn --break-system-packages

Run locally:
    uvicorn waitlist_api:app --reload --port 8001

Endpoints:
    POST /api/waitlist        { "email": "you@company.com" }  -> add signup
    GET  /api/waitlist        (requires ?key=YOUR_ADMIN_KEY)  -> list all signups
    GET  /api/waitlist/count  -> public signup count (nice for social proof)
"""

import os
import re
import sqlite3
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ---------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------
DB_PATH = "waitlist.db"
ADMIN_KEY = os.environ.get("WAITLIST_ADMIN_KEY", "change-this-key")

# Email notification settings — uses your existing IONOS mailbox,
# no third-party email service required.
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.ionos.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "hello@xenkloud.com")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
NOTIFY_TO = os.environ.get("NOTIFY_TO", "hello@xenkloud.com")


def send_contact_notification(name: str, email: str, message: str):
    """Sends an email to NOTIFY_TO using the existing IONOS mailbox.
    Fails silently (logs only) so a mail hiccup never breaks the API response
    for the person submitting the form."""
    if not SMTP_PASSWORD:
        print("SMTP_PASSWORD not set — skipping email notification.")
        return

    body = f"New contact form submission on Xenkloud Pulse\n\nName: {name}\nEmail: {email}\n\nMessage:\n{message}"
    msg = MIMEText(body)
    msg["Subject"] = f"Xenkloud Pulse contact: {name}"
    msg["From"] = SMTP_USER
    msg["To"] = NOTIFY_TO
    msg["Reply-To"] = email

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, [NOTIFY_TO], msg.as_string())
    except Exception as e:
        print(f"Failed to send contact notification email: {e}")


def send_feedback_notification(rating, email, message):
    """Sends an email whenever feedback is submitted — same self-owned
    mailbox, no third-party service."""
    if not SMTP_PASSWORD:
        print("SMTP_PASSWORD not set — skipping feedback email notification.")
        return

    rating_line = f"Rating: {rating}/5\n" if rating else ""
    email_line = f"From: {email}\n" if email else "From: (anonymous)\n"
    body = f"New feedback on Xenkloud Pulse\n\n{rating_line}{email_line}\nMessage:\n{message}"

    msg = MIMEText(body)
    msg["Subject"] = f"Xenkloud Pulse feedback{f' ({rating}/5)' if rating else ''}"
    msg["From"] = SMTP_USER
    msg["To"] = NOTIFY_TO
    if email:
        msg["Reply-To"] = email

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, [NOTIFY_TO], msg.as_string())
    except Exception as e:
        print(f"Failed to send feedback notification email: {e}")

# Allow your live site (and localhost, for testing) to call this API
ALLOWED_ORIGINS = [
    "https://pulse.xenkloud.com",
    "https://xenkloud.github.io",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
]

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

app = FastAPI(title="Xenkloud Pulse Waitlist API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------
# Database setup
# ---------------------------------------------------------------------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS waitlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS contact_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rating INTEGER,
            email TEXT,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


init_db()


# ---------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------
class WaitlistSignup(BaseModel):
    email: str


class ContactMessage(BaseModel):
    name: str
    email: str
    message: str


class Feedback(BaseModel):
    rating: str | None = None
    email: str | None = None
    message: str


# ---------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------
@app.post("/api/waitlist")
def join_waitlist(signup: WaitlistSignup):
    email = signup.email.strip().lower()

    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="That doesn't look like a valid email address.")

    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO waitlist (email, created_at) VALUES (?, ?)",
            (email, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        # Already signed up — treat as success so the UI doesn't show an error
        conn.close()
        return {"status": "already_registered"}
    conn.close()

    return {"status": "ok"}


@app.get("/api/waitlist")
def list_waitlist(key: str = Query(...)):
    if key != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key.")

    conn = get_db()
    rows = conn.execute("SELECT email, created_at FROM waitlist ORDER BY created_at DESC").fetchall()
    conn.close()

    return {"count": len(rows), "signups": [dict(r) for r in rows]}


@app.get("/api/waitlist/count")
def waitlist_count():
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) as c FROM waitlist").fetchone()["c"]
    conn.close()
    return {"count": count}


@app.post("/api/contact")
def submit_contact(msg: ContactMessage):
    name = msg.name.strip()
    email = msg.email.strip().lower()
    message = msg.message.strip()

    if not name or not message:
        raise HTTPException(status_code=400, detail="Name and message are required.")
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="That doesn't look like a valid email address.")
    if len(message) > 3000:
        raise HTTPException(status_code=400, detail="Message is too long (max 3000 characters).")

    conn = get_db()
    conn.execute(
        "INSERT INTO contact_messages (name, email, message, created_at) VALUES (?, ?, ?, ?)",
        (name, email, message, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()

    send_contact_notification(name, email, message)

    return {"status": "ok"}


@app.get("/api/contact")
def list_contact_messages(key: str = Query(...)):
    if key != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key.")

    conn = get_db()
    rows = conn.execute(
        "SELECT name, email, message, created_at FROM contact_messages ORDER BY created_at DESC"
    ).fetchall()
    conn.close()

    return {"count": len(rows), "messages": [dict(r) for r in rows]}


@app.post("/api/feedback")
def submit_feedback(fb: Feedback):
    message = fb.message.strip()
    email = (fb.email or "").strip().lower()

    if not message:
        raise HTTPException(status_code=400, detail="Feedback message is required.")
    if email and not EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="That doesn't look like a valid email address.")

    rating = None
    if fb.rating:
        try:
            rating = int(fb.rating)
        except ValueError:
            rating = None

    conn = get_db()
    conn.execute(
        "INSERT INTO feedback (rating, email, message, created_at) VALUES (?, ?, ?, ?)",
        (rating, email or None, message, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()

    send_feedback_notification(rating, email, message)

    return {"status": "ok"}


@app.get("/api/feedback")
def list_feedback(key: str = Query(...)):
    if key != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key.")

    conn = get_db()
    rows = conn.execute(
        "SELECT rating, email, message, created_at FROM feedback ORDER BY created_at DESC"
    ).fetchall()
    conn.close()

    return {"count": len(rows), "feedback": [dict(r) for r in rows]}

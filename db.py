"""SQLite data layer: users, bookings, feedback. Self-contained (stdlib sqlite3)."""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime

from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "app.db")


def _conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with _conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                product_id TEXT NOT NULL,
                title TEXT, brand TEXT, price TEXT,
                booking_date TEXT, duration TEXT,
                size TEXT, phone TEXT, note TEXT, status TEXT DEFAULT 'Pending',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                user_name TEXT,
                product_id TEXT NOT NULL,
                rating INTEGER, experience TEXT, message TEXT, recommend TEXT,
                created_at TEXT NOT NULL
            );
            """
        )
        # migrate older DBs: add any missing booking columns
        cols = {r[1] for r in c.execute("PRAGMA table_info(bookings)").fetchall()}
        for col, decl in [("size", "TEXT"), ("phone", "TEXT"), ("note", "TEXT"),
                          ("status", "TEXT DEFAULT 'Pending'")]:
            if col not in cols:
                c.execute(f"ALTER TABLE bookings ADD COLUMN {col} {decl}")


# ---- users ----
def create_user(full_name, email, password) -> tuple[bool, str]:
    try:
        with _conn() as c:
            c.execute(
                "INSERT INTO users (full_name,email,password_hash,created_at) VALUES (?,?,?,?)",
                (full_name, email.lower(), generate_password_hash(password),
                 datetime.utcnow().isoformat()),
            )
        return True, "ok"
    except sqlite3.IntegrityError:
        return False, "An account with this email already exists."


def get_user_by_email(email):
    with _conn() as c:
        r = c.execute("SELECT * FROM users WHERE email=?", (email.lower(),)).fetchone()
        return dict(r) if r else None


def verify_login(email, password):
    u = get_user_by_email(email)
    if not u or not check_password_hash(u["password_hash"], password):
        return None
    return u


def update_password(email, new_password) -> bool:
    with _conn() as c:
        cur = c.execute("UPDATE users SET password_hash=? WHERE email=?",
                        (generate_password_hash(new_password), email.lower()))
        return cur.rowcount > 0


def get_user_by_id(uid):
    with _conn() as c:
        r = c.execute("SELECT id,full_name,email,created_at FROM users WHERE id=?", (uid,)).fetchone()
        return dict(r) if r else None


def update_profile(uid, full_name, email) -> tuple[bool, str]:
    try:
        with _conn() as c:
            c.execute("UPDATE users SET full_name=?, email=? WHERE id=?",
                      (full_name, email.lower(), uid))
        return True, "ok"
    except sqlite3.IntegrityError:
        return False, "That email is already used by another account."


# ---- bookings ----
def add_booking(user_id, product, booking_date, size, phone, note):
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO bookings (user_id,product_id,title,brand,price,booking_date,size,phone,note,status,created_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (user_id, product["product_id"], product.get("title"), product.get("brand"),
             product.get("price"), booking_date, size, phone, note, "Pending",
             datetime.utcnow().isoformat()),
        )
        return cur.lastrowid


def cancel_booking(user_id, booking_id) -> bool:
    with _conn() as c:
        cur = c.execute("DELETE FROM bookings WHERE id=? AND user_id=?", (booking_id, user_id))
        return cur.rowcount > 0


def confirm_booking(user_id, booking_id) -> bool:
    with _conn() as c:
        cur = c.execute(
            "UPDATE bookings SET status='Confirmed' WHERE id=? AND user_id=? AND status='Pending'",
            (booking_id, user_id),
        )
        return cur.rowcount > 0


def count_bookings(user_id):
    with _conn() as c:
        return c.execute("SELECT COUNT(*) n FROM bookings WHERE user_id=?", (user_id,)).fetchone()["n"]


def list_bookings(user_id):
    with _conn() as c:
        rows = c.execute("SELECT * FROM bookings WHERE user_id=? ORDER BY id DESC", (user_id,)).fetchall()
        return [dict(r) for r in rows]


# ---- feedback ----
def add_feedback(user_id, user_name, product_id, rating, experience, message, recommend):
    with _conn() as c:
        c.execute(
            "INSERT INTO feedback (user_id,user_name,product_id,rating,experience,message,recommend,created_at)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (user_id, user_name, product_id, rating, experience, message, recommend,
             datetime.utcnow().isoformat()),
        )


def list_feedback(product_id):
    with _conn() as c:
        rows = c.execute("SELECT * FROM feedback WHERE product_id=? ORDER BY id DESC", (product_id,)).fetchall()
        return [dict(r) for r in rows]

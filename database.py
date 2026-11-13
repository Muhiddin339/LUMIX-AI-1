import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).with_name("lumix.db")

def connect():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with connect() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, name TEXT NOT NULL,
            points INTEGER NOT NULL DEFAULT 0,
            played INTEGER NOT NULL DEFAULT 0
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS daily (
            user_id INTEGER NOT NULL, day TEXT NOT NULL,
            PRIMARY KEY(user_id, day)
        )""")

def add_user(user_id, name):
    with connect() as con:
        con.execute("INSERT INTO users(user_id,name) VALUES(?,?) "
                    "ON CONFLICT(user_id) DO UPDATE SET name=excluded.name",
                    (user_id, name))

def get_profile(user_id):
    with connect() as con:
        row = con.execute("SELECT points, played FROM users WHERE user_id=?", (user_id,)).fetchone()
        return dict(row) if row else {"points": 0, "played": 0}

def add_points(user_id, points, played=0):
    with connect() as con:
        con.execute("UPDATE users SET points=points+?, played=played+? WHERE user_id=?",
                    (points, played, user_id))

def top_users(limit=10):
    with connect() as con:
        rows = con.execute("SELECT name, points FROM users ORDER BY points DESC LIMIT ?", (limit,)).fetchall()
        return [(r["name"], r["points"]) for r in rows]

def get_daily(user_id, day):
    with connect() as con:
        return con.execute("SELECT 1 FROM daily WHERE user_id=? AND day=?", (user_id, day)).fetchone()

def save_daily(user_id, day):
    with connect() as con:
        con.execute("INSERT OR IGNORE INTO daily(user_id,day) VALUES(?,?)", (user_id, day))

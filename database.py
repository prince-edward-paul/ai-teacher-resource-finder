import sqlite3
import pandas as pd
from datetime import datetime

DB_FILE = "ai_teacher.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password_hash TEXT,
        email TEXT,
        role TEXT
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS resources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        teacher_username TEXT,
        resource_name TEXT,
        type TEXT,
        path TEXT,
        timestamp TEXT,
        is_public INTEGER DEFAULT 0,
        likes INTEGER DEFAULT 0,
        category TEXT DEFAULT 'General',
        tags TEXT DEFAULT ''
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS downloads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        resource_name TEXT,
        user TEXT,
        timestamp TEXT
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        teacher_username TEXT,
        message TEXT,
        timestamp TEXT,
        read INTEGER DEFAULT 0
    )
    """)
    conn.commit()
    conn.close()

# -------------------------
# Resource functions
# -------------------------
def get_saved_resources(username):
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM resources WHERE teacher_username=?", conn, params=(username,))
    conn.close()
    return df

def get_public_resources(search_query="", category="All"):
    conn = sqlite3.connect(DB_FILE)
    base_query = "SELECT * FROM resources WHERE is_public=1"
    params = []

    if category != "All":
        base_query += " AND category=?"
        params.append(category)

    if search_query:
        base_query += " AND (resource_name LIKE ? OR tags LIKE ?)"
        params.extend([f"%{search_query}%", f"%{search_query}%"])

    df = pd.read_sql_query(base_query, conn, params=params)
    conn.close()
    return df

def save_resource_for_teacher(username, resource_name, r_type, path, is_public=False, category="General", tags=""):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        INSERT INTO resources (teacher_username, resource_name, type, path, timestamp, is_public, likes, category, tags)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (username, resource_name, r_type, path, datetime.now(), int(is_public), 0, category, tags))
    conn.commit()
    conn.close()

def log_download(resource_name, user="anonymous"):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO downloads (resource_name, user, timestamp) VALUES (?,?,?)",
              (resource_name, user, datetime.now()))
    c.execute("SELECT teacher_username FROM resources WHERE resource_name=?", (resource_name,))
    row = c.fetchone()
    if row:
        teacher = row[0]
        msg = f"Your resource '{resource_name}' was downloaded by {user}."
        c.execute("INSERT INTO notifications (teacher_username, message, timestamp) VALUES (?,?,?)",
                  (teacher, msg, datetime.now()))
    conn.commit()
    conn.close()

def like_resource(resource_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE resources SET likes = likes + 1 WHERE id=?", (resource_id,))
    conn.commit()
    conn.close()

def get_downloads():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM downloads", conn)
    conn.close()
    return df

def get_notifications(username):
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM notifications WHERE teacher_username=? AND read=0", conn, params=(username,))
    conn.close()
    return df

def mark_notifications_read(username):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE notifications SET read=1 WHERE teacher_username=?", (username,))
    conn.commit()
    conn.close()
import hashlib
import sqlite3
from database import DB_FILE

# -------------------------
# Password hashing
# -------------------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# -------------------------
# Register teacher
# -------------------------
def register_teacher(username, password, email):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password_hash, email, role) VALUES (?,?,?,?)",
                  (username, hash_password(password), email, "teacher"))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return False, "Username already exists"
    conn.close()
    return True, "Registered successfully"

# -------------------------
# Login teacher
# -------------------------
def login_teacher(username, password):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT username, password_hash, email, role FROM users WHERE username=?", (username,))
    row = c.fetchone()
    conn.close()
    if not row:
        return False, "Username not found"
    if hash_password(password) != row[1]:
        return False, "Incorrect password"
    return True, {"username": row[0], "password_hash": row[1], "email": row[2], "role": row[3]}
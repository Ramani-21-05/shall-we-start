"""
init_auth_db.py
───────────────
Initializes the `users` table for Role-Based Access Control (RBAC) in SQLite
(`backend/data/pharmacy_hackathon.db`) and Supabase.

Roles:
  1. ADMIN      -> Full access to all dashboards, simulation, inventory, forecast, explainability, anomaly
  2. STAFF      -> Inventory & Replenishment ONLY
  3. MARKETING  -> Sales Dashboard, Demand Forecast, Past Performance, Strategy Intelligence
"""

import os
import sys
import sqlite3
import hashlib

sys.path.insert(0, os.path.dirname(__file__))

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "pharmacy_hackathon.db")


def hash_password(password: str) -> str:
    """Simple SHA256 password hashing for demo authentication."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


DEFAULT_USERS = [
    {
        "email": "727823tuad122@skct.edu.in",
        "username": "ranjeet",
        "password": "ranjeet@3102",
        "full_name": "ranjeet c",
        "role": "ADMIN",
    },
    {
        "email": "admin@pharmacast.com",
        "username": "admin",
        "password": "admin123",
        "full_name": "System Administrator",
        "role": "ADMIN",
    },
    {
        "email": "staff@pharmacast.com",
        "username": "staff",
        "password": "staff123",
        "full_name": "Pharmacy Staff Member",
        "role": "STAFF",
    },
    {
        "email": "marketing@pharmacast.com",
        "username": "marketing",
        "password": "marketing123",
        "full_name": "Marketing & Sales Strategist",
        "role": "MARKETING",
    },
]


def init_auth_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    print("Setting up `users` schema in SQLite...")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        username TEXT UNIQUE NOT NULL,
        hashed_password TEXT NOT NULL,
        full_name TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('ADMIN', 'STAFF', 'MARKETING')),
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)

    for u in DEFAULT_USERS:
        hashed = hash_password(u["password"])
        cur.execute(
            """
            INSERT OR REPLACE INTO users (email, username, hashed_password, full_name, role, is_active)
            VALUES (?, ?, ?, ?, ?, 1)
            """,
            (u["email"], u["username"], hashed, u["full_name"], u["role"])
        )
        print(f"  [OK] Seeded user: {u['username']} (Role: {u['role']})")

    conn.commit()
    conn.close()
    print("[OK] Auth database initialization complete.")


if __name__ == "__main__":
    init_auth_db()

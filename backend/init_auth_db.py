"""
init_auth_db.py
───────────────
Initializes the `users` table for Role-Based Access Control (RBAC) in Supabase PostgreSQL.

Roles:
  1. ADMIN      -> Full access to all dashboards, simulation, inventory, forecast, explainability
  2. STAFF      -> Inventory & Replenishment ONLY
  3. MARKETING  -> Sales Dashboard, Demand Forecast, Past Performance, Strategy Intelligence
"""

import os
import sys
import hashlib
from core.database import get_supabase

sys.path.insert(0, os.path.dirname(__file__))


def hash_password(password: str) -> str:
    """SHA256 password hashing for authentication."""
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
    print("Setting up `users` in Supabase PostgreSQL...")
    try:
        sb = get_supabase()
        for u in DEFAULT_USERS:
            hashed = hash_password(u["password"])
            payload = {
                "email": u["email"],
                "username": u["username"],
                "hashed_password": hashed,
                "full_name": u["full_name"],
                "role": u["role"],
                "is_active": True,
            }
            sb.table("users").upsert(payload, on_conflict="username").execute()
            print(f"  [OK] Seeded Supabase user: {u['username']} (Role: {u['role']})")
        print("[OK] Supabase Auth users setup complete.")
    except Exception as e:
        print(f"[WARNING] Could not seed Supabase users: {e}")


if __name__ == "__main__":
    init_auth_db()

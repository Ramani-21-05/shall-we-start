"""
routers/auth.py
───────────────
Production Auth Router: Login, Admin Provisioning, Change Password, Email Credentials Dispatcher.
100% Supabase PostgreSQL Engine (Zero SQLite).
"""

import os
import secrets
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr, Field

from core.security import hash_password, verify_password, create_access_token
from core.auth_middleware import get_current_user, require_roles
from core.database import get_supabase
from core.email_service import send_credentials_email
from routers.activity_logs import _write_log

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    username_or_email: str
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class AdminCreateUserRequest(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=30)
    full_name: str = Field(..., min_length=2)
    role: str = Field(..., description="Role must be ADMIN, STAFF, or MARKETING")


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)


class SendCredentialsRequest(BaseModel):
    identifier: str = Field(..., description="Email address or username of user")


def generate_initial_password() -> str:
    """Generates a secure random initial password (e.g., Rx#9k2P!m7)."""
    rand_str = secrets.token_urlsafe(6).replace("-", "").replace("_", "")[:6]
    return f"Rx#{rand_str}!9"


@router.post("/login", response_model=AuthResponse)
def login(req: LoginRequest):
    identifier = req.username_or_email.strip().lower()

    sb = get_supabase()
    res = sb.table("users").select("id, email, username, hashed_password, full_name, role, is_active").or_(f"username.eq.{identifier},email.eq.{identifier}").limit(1).execute()

    if not res.data or len(res.data) == 0:
        _write_log(
            event_type="LOGIN",
            message=f"Failed login attempt for identifier '{identifier}'.",
            username=identifier,
            status="ERROR",
        )
        raise HTTPException(status_code=401, detail="Invalid username/email or password.")

    user = res.data[0]

    if not user.get("is_active"):
        _write_log(
            event_type="LOGIN",
            message=f"Login blocked — account deactivated for '{identifier}'.",
            username=identifier,
            status="WARNING",
        )
        raise HTTPException(status_code=403, detail="Account deactivated. Please contact an administrator.")

    if not verify_password(req.password, user["hashed_password"]):
        _write_log(
            event_type="LOGIN",
            message=f"Wrong password attempt for user '{identifier}'.",
            username=identifier,
            status="ERROR",
        )
        raise HTTPException(status_code=401, detail="Invalid username/email or password.")

    token = create_access_token(user_id=user["id"], username=user["username"], role=user["role"])

    # --- Audit Log: successful login ---
    _write_log(
        event_type="LOGIN",
        message=f"User '{user['username']}' logged in successfully.",
        username=user["username"],
        user_role=user["role"],
        status="SUCCESS",
    )

    user_dict = {
        "id": user["id"],
        "email": user["email"],
        "username": user["username"],
        "full_name": user["full_name"],
        "role": user["role"],
        "is_active": 1 if user.get("is_active") else 0,
    }

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user_dict,
    }


@router.get("/me")
def get_my_profile(current_user: dict = Depends(get_current_user)):
    """Returns currently authenticated user profile."""
    return {"user": current_user}


@router.post("/change-password")
def change_password(req: ChangePasswordRequest, current_user: dict = Depends(get_current_user)):
    username = current_user["username"]
    sb = get_supabase()

    res = sb.table("users").select("hashed_password").eq("username", username).limit(1).execute()
    if not res.data or len(res.data) == 0:
        raise HTTPException(status_code=404, detail="User account not found.")

    current_hash = res.data[0]["hashed_password"]
    if not verify_password(req.current_password, current_hash):
        raise HTTPException(status_code=400, detail="Incorrect current password.")

    new_hashed_pw = hash_password(req.new_password)
    sb.table("users").update({"hashed_password": new_hashed_pw}).eq("username", username).execute()

    _write_log(
        event_type="PASSWORD_CHANGED",
        message=f"User '{username}' changed their password.",
        username=username,
        user_role=current_user.get("role", "UNKNOWN"),
        status="SUCCESS",
    )

    return {"message": "Password successfully updated on Supabase PostgreSQL."}


@router.post("/send-credentials-email")
def send_credentials_to_user_email(req: SendCredentialsRequest):
    """
    User/Admin enters email ID or username.
    System generates a fresh temp password on Supabase and dispatches email with Email ID, Username, and Password.
    """
    ident = req.identifier.strip().lower()
    sb = get_supabase()

    res = sb.table("users").select("id, email, username, full_name, role, is_active").or_(f"username.eq.{ident},email.eq.{ident}").limit(1).execute()

    if not res.data or len(res.data) == 0:
        raise HTTPException(status_code=404, detail=f"No registered user account found for '{ident}'.")

    user = res.data[0]

    # Generate fresh temporary password
    fresh_pw = generate_initial_password()
    hashed_pw = hash_password(fresh_pw)

    # Update password in Supabase
    sb.table("users").update({"hashed_password": hashed_pw}).eq("username", user["username"]).execute()

    # Dispatch Email (Email ID, Username, Password)
    email_res = send_credentials_email(
        to_email=user["email"],
        username=user["username"],
        password=fresh_pw,
        full_name=user["full_name"],
        role=user["role"],
    )

    _write_log(
        event_type="EMAIL_SENT",
        message=f"Credentials email dispatched to '{user['email']}' for user '{user['username']}'.",
        username=user["username"],
        user_role=user["role"],
        status="SUCCESS",
        detail=f"Email: {user['email']} | Role: {user['role']}",
    )

    return {
        "message": f"Credentials email dispatched to '{user['email']}'.",
        "email_id": user["email"],
        "username": user["username"],
        "temporary_password": fresh_pw,
        "email_dispatch": email_res,
    }


# ─── ADMIN USER PROVISIONING ENDPOINTS (ADMIN ONLY) ─────────────────────────

@router.post("/admin/create-user")
def admin_create_user(req: AdminCreateUserRequest, current_user: dict = Depends(require_roles(["ADMIN"]))):
    role_upper = req.role.upper()
    if role_upper not in ["ADMIN", "STAFF", "MARKETING"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role: '{req.role}'. Must be ADMIN, STAFF, or MARKETING."
        )

    req_email = req.email.lower().strip()
    req_username = req.username.lower().strip()
    sb = get_supabase()

    # Check existing email in Supabase
    res_email = sb.table("users").select("id, email, username").eq("email", req_email).execute()
    if res_email.data and len(res_email.data) > 0:
        existing_username = res_email.data[0].get("username")
        raise HTTPException(status_code=400, detail=f"Email ID '{req_email}' is already registered to user '{existing_username}'.")

    # Check existing username in Supabase
    res_user = sb.table("users").select("id, email, username").eq("username", req_username).execute()
    if res_user.data and len(res_user.data) > 0:
        raise HTTPException(status_code=400, detail=f"Username '{req_username}' is already taken.")

    initial_password = generate_initial_password()
    hashed_pw = hash_password(initial_password)

    # Insert user directly into Supabase PostgreSQL
    sb_res = sb.table("users").insert({
        "email": req_email,
        "username": req_username,
        "hashed_password": hashed_pw,
        "full_name": req.full_name,
        "role": role_upper,
        "is_active": True,
    }).execute()

    if not sb_res.data or len(sb_res.data) == 0:
        raise HTTPException(status_code=500, detail="Failed to insert user into Supabase database.")

    created_user = sb_res.data[0]

    # Dispatch Email for non-ADMIN accounts (Email ID, Username, Password)
    email_res = None
    if role_upper != "ADMIN":
        email_res = send_credentials_email(
            to_email=req_email,
            username=req_username,
            password=initial_password,
            full_name=req.full_name,
            role=role_upper,
        )
        _write_log(
            event_type="EMAIL_SENT",
            message=f"Welcome credentials email sent to new user '{req_username}' at '{req_email}'.",
            username=current_user.get("username", "admin"),
            user_role=current_user.get("role", "ADMIN"),
            status="SUCCESS",
            detail=f"New user: {req_username} | Role: {role_upper} | Email: {req_email}",
        )

    _write_log(
        event_type="ADMIN_ACTION",
        message=f"Admin '{current_user.get('username')}' created new user '{req_username}' as {role_upper}.",
        username=current_user.get("username", "admin"),
        user_role=current_user.get("role", "ADMIN"),
        status="SUCCESS",
        detail=f"New user: {req_username} | Email: {req_email} | Role: {role_upper}",
    )

    user_dict = {
        "id": created_user.get("id"),
        "email": req_email,
        "username": req_username,
        "full_name": req.full_name,
        "role": role_upper,
        "is_active": 1,
    }

    return {
        "message": f"User '{req_username}' provisioned successfully on Supabase as {role_upper} and credentials emailed.",
        "user": user_dict,
        "initial_password": initial_password,
        "email_dispatch": email_res,
    }


@router.get("/admin/users")
def admin_list_users(current_user: dict = Depends(require_roles(["ADMIN"]))):
    sb = get_supabase()
    res = sb.table("users").select("id, email, username, full_name, role, is_active, created_at").order("created_at", desc=False).execute()
    users = res.data or []
    return {"users": users, "total_users": len(users)}


class ToggleStatusRequest(BaseModel):
    user_id: str | int
    is_active: bool


@router.post("/admin/toggle-user-status")
def admin_toggle_user_status(req: ToggleStatusRequest, current_user: dict = Depends(require_roles(["ADMIN"]))):
    sb = get_supabase()
    sb.table("users").update({"is_active": req.is_active}).eq("id", req.user_id).execute()

    action_label = 'Activated' if req.is_active else 'Deactivated'
    _write_log(
        event_type="ADMIN_ACTION",
        message=f"Admin '{current_user.get('username')}' {action_label} user ID #{req.user_id}.",
        username=current_user.get("username", "admin"),
        user_role=current_user.get("role", "ADMIN"),
        status="SUCCESS",
        detail=f"User ID: {req.user_id} | New status: {'Active' if req.is_active else 'Deactivated'}",
    )

    return {
        "message": f"User status updated to {'Active' if req.is_active else 'Deactivated'} on Supabase.",
        "is_active": req.is_active,
    }


@router.delete("/admin/delete-user/{user_id}")
def admin_delete_user(user_id: str, current_user: dict = Depends(require_roles(["ADMIN"]))):
    sb = get_supabase()

    # Check target user
    res = sb.table("users").select("id, username, email").eq("id", user_id).execute()
    if not res.data or len(res.data) == 0:
        raise HTTPException(status_code=404, detail=f"User ID #{user_id} not found.")

    target_user = res.data[0]

    # Block self-deletion
    if str(target_user.get("id")) == str(current_user.get("id")) or target_user.get("username") == current_user.get("username"):
        raise HTTPException(status_code=400, detail="You cannot delete your own active Admin account.")

    # Delete user from Supabase
    sb.table("users").delete().eq("id", user_id).execute()

    _write_log(
        event_type="ADMIN_ACTION",
        message=f"Admin '{current_user.get('username')}' permanently deleted user '{target_user.get('username')}' (#{user_id}).",
        username=current_user.get("username", "admin"),
        user_role=current_user.get("role", "ADMIN"),
        status="SUCCESS",
        detail=f"Deleted user: {target_user.get('username')} | Email: {target_user.get('email')} | ID: {user_id}",
    )

    return {
        "message": f"User '{target_user.get('username')}' (#{user_id}) permanently deleted from system.",
        "deleted_user_id": user_id,
    }

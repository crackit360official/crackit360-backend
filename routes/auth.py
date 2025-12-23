# auth.py (NO USER_TYPE VERSION)
from fastapi import APIRouter, HTTPException, BackgroundTasks, Body
from schemas.models import UserRegister, UserLogin, AuthUser, TokenResponse
from db import user_collection
from security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    create_reset_token,
    verify_reset_token
)
from utils.util import schedule_email, make_verify_link, make_reset_link
from bson import ObjectId
from datetime import datetime
from pymongo.errors import DuplicateKeyError
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import traceback

router = APIRouter(prefix="/api/auth", tags=["Auth"])
GOOGLE_CLIENT_ID = "299220062167-98gmd26a9916dijupmrpl06ouilhjfp3.apps.googleusercontent.com"


# -------------------------------------------------------
# SANITIZER (NO user_type)
# -------------------------------------------------------
def sanitize_user_doc(doc: dict) -> dict:
    SAFE_DEFAULTS = {
        "name": "",
        "email": "",
        "password": "",
        "avatar": "",
        "auth_provider": "email",
        "email_verified": False,
    }

    clean = {}
    for key, default in SAFE_DEFAULTS.items():
        value = doc.get(key)
        clean[key] = default if value is None else (str(value) if isinstance(default, str) else bool(value))

    clean["created_at"] = doc.get("created_at", datetime.utcnow())
    return clean


# -------------------------------------------------------
# STANDARD RESPONSE (no user_type)
# -------------------------------------------------------
def build_auth_response(user_doc, token: str):
    uid = str(user_doc["_id"])

    payload = {
        "id": uid,
        "name": user_doc.get("name", ""),
        "email": user_doc.get("email", ""),
        "auth_provider": user_doc.get("auth_provider", "email"),
        "avatar": user_doc.get("avatar", "") or user_doc.get("name", "")[:1].upper(),
    }

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": payload,
        # compatibility for your frontend:
        "id": payload["id"],
        "name": payload["name"],
        "email": payload["email"],
        "avatar": payload["avatar"],
        "auth_provider": payload["auth_provider"],
        "message": "Login successful",
    }


# -------------------------------------------------------
# REGISTER
# -------------------------------------------------------
@router.post("/register")
async def register_user(user: UserRegister, background_tasks: BackgroundTasks):
    existing = await user_collection.find_one({"email": user.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_pw = hash_password(user.password)

    new_user = sanitize_user_doc({
        "name": user.name,
        "email": user.email,
        "password": hashed_pw,
        "auth_provider": "email",
        "email_verified": False,
    })

    try:
        result = await user_collection.insert_one(new_user)
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail="Email already exists")

    user_id = str(result.inserted_id)
    token = create_access_token(user_id)
    verify_link = make_verify_link(token)

    html = f"""
    <h2>Welcome {user.name} 👋</h2>
    <p>Please verify your CrackIt360 account:</p>
    <a href="{verify_link}">Verify Email</a>
    """
    schedule_email(background_tasks, user.email, "Verify Your CrackIt360 Account", html)

    return {"status": "success", "message": "Registration successful. Verify email."}


# -------------------------------------------------------
# LOGIN
# -------------------------------------------------------
@router.post("/login")
async def login_user(user: UserLogin):
    db_user = await user_collection.find_one({"email": user.email})
    if not db_user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if db_user.get("auth_provider") == "google":
        raise HTTPException(status_code=403, detail="Use Google Sign-In")

    if not verify_password(user.password, db_user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not db_user.get("email_verified"):
        raise HTTPException(status_code=403, detail="Verify email before login")

    token = create_access_token(str(db_user["_id"]))
    return build_auth_response(db_user, token)


# -------------------------------------------------------
# GOOGLE LOGIN
# -------------------------------------------------------
@router.post("/google-login")
async def google_login(background_tasks: BackgroundTasks, id_token_str: str = Body(..., embed=True)):
    info = id_token.verify_oauth2_token(id_token_str, google_requests.Request(), GOOGLE_CLIENT_ID)

    email = info.get("email")
    name = info.get("name") or ""
    picture = info.get("picture") or ""

    db_user = await user_collection.find_one({"email": email})

    if db_user and db_user.get("auth_provider") == "email":
        await user_collection.update_one(
            {"_id": db_user["_id"]},
            {"$set": {"auth_provider": "google", "avatar": picture, "email_verified": True}}
        )

    elif not db_user:
        new_user = sanitize_user_doc({
            "name": name or email.split("@")[0],
            "email": email,
            "password": "",
            "auth_provider": "google",
            "avatar": picture,
            "email_verified": True,
        })
        await user_collection.insert_one(new_user)

    user_db = await user_collection.find_one({"email": email})
    token = create_access_token(str(user_db["_id"]))

    return build_auth_response(user_db, token)


# -------------------------------------------------------
# FORGOT / RESET PASSWORD (unchanged)
# -------------------------------------------------------
@router.post("/forgot-password")
async def forgot_password(background_tasks: BackgroundTasks, email: str = Body(..., embed=True)):
    user = await user_collection.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="Email not found")

    if user.get("auth_provider") == "google":
        raise HTTPException(status_code=400, detail="Google users must login via Google")

    token = create_reset_token(email)
    reset_link = make_reset_link(token)
    html = f"<a href='{reset_link}'>Reset Password</a>"

    schedule_email(background_tasks, email, "Password Reset", html)
    return {"message": "Reset link sent"}


@router.post("/reset-password")
async def reset_password(token: str = Body(...), new_password: str = Body(...)):
    email = verify_reset_token(token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid token")

    hashed = hash_password(new_password)
    await user_collection.update_one({"email": email}, {"$set": {"password": hashed}})

    return {"message": "Password reset successful"}

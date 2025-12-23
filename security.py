import os
import re
import jwt
import bcrypt
import hashlib
import secrets
import mimetypes
import pathlib
from datetime import datetime, timedelta
from typing import Dict, Any, Mapping, Optional, Iterable
from fastapi import HTTPException, status
from dotenv import load_dotenv
from bson import ObjectId
from collections import defaultdict
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from db import user_collection
from jose import jwt, JWTError
# ============================================================
# 🔧 Load Environment Variables
# ============================================================
load_dotenv()
SECRET_KEY = str(os.getenv("SECRET_KEY", "default_secret_key"))
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS"))
EMAIL_SALT = os.getenv("EMAIL_SALT")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# ============================================================
# 🔐 Password Hashing
# ============================================================
def hash_password(password: str) -> str:
    """Securely hash the password using bcrypt with safe truncation."""
    if not isinstance(password, str):
        raise TypeError("Password must be a string")

    password = password.strip()
    password_bytes = password.encode("utf-8")

    # bcrypt supports only 72 bytes — truncate safely
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]

    try:
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode("utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Password hashing failed: {str(e)}")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify the plain password against the stored bcrypt hash."""
    try:
        plain_bytes = plain_password.strip().encode("utf-8")
        if len(plain_bytes) > 72:
            plain_bytes = plain_bytes[:72]
        return bcrypt.checkpw(plain_bytes, hashed_password.encode("utf-8"))
    except Exception as e:
        print("❌ Password verification error:", e)
        return False


# ============================================================
# 🔑 JWT Access Tokens
# ============================================================
def create_access_token(subject: str, extra: Optional[Dict[str, Any]] = None,
                        expires_minutes: Optional[int] = None) -> str:
    """Create a signed JWT access token."""
    data = {"sub": subject}
    if extra:
        data.update(extra)
    expire = datetime.utcnow() + timedelta(minutes=(expires_minutes or ACCESS_TOKEN_EXPIRE_MINUTES))
    data["exp"] = expire
    return jwt.encode(data, SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and validate JWT; raise HTTP errors on invalid or expired tokens."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
        if "sub" not in payload:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def get_token_subject(token: str) -> str:
    """Extract subject (usually user ID) from JWT."""
    payload = decode_access_token(token)
    return payload.get("sub")


# ============================================================
# 🔁 Refresh Token Handling
# ============================================================
def create_refresh_token() -> str:
    """Create a secure random refresh token."""
    return secrets.token_urlsafe(64)


def hash_token(token: str) -> str:
    """Hash a token before saving (protects in DB)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# ============================================================
# 🧱 MongoDB Injection Protection
# ============================================================
def safe_object_id(id_str: str) -> ObjectId:
    """Convert safely to ObjectId or raise 400 if invalid."""
    if not ObjectId.is_valid(id_str):
        raise HTTPException(status_code=400, detail="Invalid ID format")
    return ObjectId(id_str)


def escape_regex(text: str) -> str:
    """Escape regex special characters."""
    return re.escape(str(text))


def build_safe_filter(client_filter: Mapping[str, Any], allowed_fields: Iterable[str]) -> Dict[str, Any]:
    """Whitelist-based filter builder to avoid operator injection."""
    if not client_filter:
        return {}
    safe = {}
    for key, value in client_filter.items():
        if key not in allowed_fields or key.startswith("$"):
            continue
        if isinstance(value, dict):
            raise HTTPException(status_code=400, detail=f"Invalid filter value for '{key}'")
        safe[key] = value
    return safe


def build_update_payload(body: Mapping[str, Any], allowed_fields: Iterable[str]) -> Dict[str, Any]:
    """Whitelist-based update payload builder."""
    if not body:
        raise HTTPException(status_code=400, detail="Empty update payload")
    safe_update = {}
    for key, value in body.items():
        if key not in allowed_fields or key.startswith("$"):
            continue
        if isinstance(value, dict):
            raise HTTPException(status_code=400, detail=f"Invalid update value for '{key}'")
        safe_update[key] = value
    if not safe_update:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    return {"$set": safe_update}


# ============================================================
# 🧩 File Upload & Malware Protection
# ============================================================
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".pdf", ".txt"}
ALLOWED_MIME_PREFIXES = ("image/", "text/", "application/pdf")
UPLOAD_TMP_DIR = os.getenv("UPLOAD_TMP_DIR", "./uploads/tmp")
os.makedirs(UPLOAD_TMP_DIR, exist_ok=True)


def sanitize_filename(filename: str) -> str:
    """Sanitize dangerous characters in filenames."""
    name = pathlib.Path(filename).name
    return re.sub(r"[^A-Za-z0-9._-]", "_", name)


def validate_upload(file_stream, filename: str, content_type: Optional[str] = None):
    """Validate uploaded file for size, extension, and safety."""
    safe_name = sanitize_filename(filename)
    ext = pathlib.Path(safe_name).suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="File type not allowed")

    file_path = os.path.join(UPLOAD_TMP_DIR, f"{secrets.token_hex(8)}_{safe_name}")
    size = 0

    with open(file_path, "wb") as f:
        while chunk := file_stream.read(4096):
            size += len(chunk)
            if size > MAX_UPLOAD_SIZE:
                f.close()
                os.remove(file_path)
                raise HTTPException(status_code=400, detail="File too large")
            f.write(chunk)

    guessed_mime, _ = mimetypes.guess_type(file_path)
    if guessed_mime and not guessed_mime.startswith(ALLOWED_MIME_PREFIXES):
        os.remove(file_path)
        raise HTTPException(status_code=400, detail="Suspicious file type")

    file_hash = hashlib.sha256(open(file_path, "rb").read()).hexdigest()
    return {"path": file_path, "hash": file_hash, "size": size}


# ============================================================
# 🧠 Phishing Detection
# ============================================================
URL_RE = re.compile(r"https?://[A-Za-z0-9\-\._~:/?#\[\]@!$&'()*+,;=%]+")

def detect_phishing_links(text: str) -> Dict[str, Any]:
    """Basic phishing link detector."""
    urls = URL_RE.findall(text or "")
    suspicious = [u for u in urls if "@" in u or u.count("//") > 1 or len(u) > 250]
    return {"found": len(urls), "suspicious": suspicious}


# ============================================================
# ⏱️ Simple Rate Limiter
# ============================================================
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))  # seconds
RATE_LIMIT_MAX = int(os.getenv("RATE_LIMIT_MAX", "30"))  # max requests
_rate_store = defaultdict(list)

def check_rate_limit(ip: str, route: str) -> bool:
    """Check and enforce request rate limits."""
    now = datetime.utcnow().timestamp()
    key = f"{ip}:{route}"
    _rate_store[key] = [t for t in _rate_store[key] if now - t < RATE_LIMIT_WINDOW]
    if len(_rate_store[key]) >= RATE_LIMIT_MAX:
        return False
    _rate_store[key].append(now)
    return True


# ============================================================
# 🔒 Password Reset Token System
# ============================================================
def create_reset_token(email: str) -> str:
    """Create a short-lived JWT for password reset (15 min expiry)."""
    expire = datetime.utcnow() + timedelta(minutes=15)
    payload = {"sub": email, "purpose": "reset_password", "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)


def verify_reset_token(token: str) -> str:
    """Validate reset token and extract email."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
        if payload.get("purpose") != "reset_password":
            raise HTTPException(status_code=400, detail="Invalid token purpose")
        return payload.get("sub")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Reset link expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=400, detail="Invalid or tampered token")



async def get_current_user(token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing token"
        )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])

        user_id = payload.get("sub")
        user_name = payload.get("name")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )

        # 🔁 Fallback: fetch from DB if name missing in token
        if not user_name:
            user = await user_collection.find_one(
                {"_id": ObjectId(user_id)},
                {"name": 1}
            )

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )

            user_name = user.get("name")

        return {
            "id": str(user_id),
            "name": user_name
        }

    except JWTError as e:
        print("JWT ERROR:", str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
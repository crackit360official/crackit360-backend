# utils.py
import os
import smtplib
from email.mime.text import MIMEText
from fastapi import BackgroundTasks, HTTPException
from dotenv import load_dotenv
from security import detect_phishing_links  # Anti-phishing integration
import requests
import base64
# -----------------------------
# Load environment variables
# -----------------------------
load_dotenv()

SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
FRONTEND_URL = os.getenv("FRONTEND_URL")
USE_REAL_EMAIL = os.getenv("USE_REAL_EMAIL").lower() == "true"
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT"))

# -----------------------------
# Secure Email Sender
# -----------------------------
async def send_email(to_email: str, subject: str, html_body: str):
    """
    Send email securely via SMTP with TLS.
    Uses .env configuration for credentials and server.
    """
    if not USE_REAL_EMAIL:
        print("=== EMAIL SIMULATION ===")
        print(f"To: {to_email}")
        print(f"Subject: {subject}")
        print(f"Body:\n{html_body}")
        print("========================")
        return

    try:
        msg = MIMEText(html_body, "html")
        msg["Subject"] = subject
        msg["From"] = SENDER_EMAIL
        msg["To"] = to_email

        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)

        print(f"✅ Email sent securely to {to_email}")

    except Exception as e:
        print(f"❌ Email sending failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Email sending failed: {str(e)}")

# -----------------------------
# Secure HTTPS Verification Link Generator
# -----------------------------
def make_verify_link(token: str) -> str:
    backend_url = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
    backend_url = backend_url.strip("/")
    return f"{backend_url}/api/auth/verify-email?token={token}"


# -----------------------------
# Background Email Scheduler (Phishing-Protected)
# -----------------------------
def schedule_email(background_tasks: BackgroundTasks, to_email: str, subject: str, html_body: str):
    """
    Schedules secure email sending with phishing link check.
    """
    phishing = detect_phishing_links(html_body)
    if phishing.get("suspicious"):
        raise HTTPException(status_code=400, detail="⚠️ Suspicious content detected in email body")

    background_tasks.add_task(send_email, to_email, subject, html_body)

def make_reset_link(token: str) -> str:
    base_url = FRONTEND_URL.strip("/")
    return f"{base_url}/reset-password?token={token}"


# ✅ Crackit 360 Welcome Email Template
def build_welcome_email(user_email: str) -> str:
    """
    Build HTML welcome email for Crackit 360.
    (No verification link — verification handled inside UI)
    """
    return f"""
    <html>
      <body style="font-family:'Segoe UI',sans-serif;background-color:#f3f4f6;padding:30px;">
        <div style="max-width:600px;margin:auto;background:#fff;border-radius:16px;
                    box-shadow:0 4px 12px rgba(0,0,0,0.1);overflow:hidden;">
          <div style="background:linear-gradient(135deg,#4f46e5,#3b82f6);color:white;
                      padding:25px;text-align:center;">
            <h1 style="margin:0;">Welcome to <span style="color:#fde047;">Crackit 360°</span> 🎉</h1>
          </div>
          <div style="padding:25px;color:#333;">
            <p>Hi <b>{user_email}</b>,</p>
            <p>Welcome to <b>Crackit 360</b> 🚀</p>
            <p>Your account has been created successfully.  
               Please verify your email directly inside the Crackit 360 portal.</p>
            <p style="margin-top:25px;">Cheers,<br><b>Team Crackit 360</b></p>
          </div>
          <div style="background:#f9fafb;padding:15px;text-align:center;
                      font-size:12px;color:#777;">
            © 2025 Crackit 360. All rights reserved.
          </div>
        </div>
      </body>
    </html>
    """

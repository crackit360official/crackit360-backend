import os
from dotenv import load_dotenv
import smtplib
from email.message import EmailMessage

load_dotenv()   # reads .env in working directory

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

SENDER = os.getenv("SENDER_EMAIL")
RECIPIENT = os.getenv("RECIPIENT_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")

msg = EmailMessage()
msg["From"] = SENDER
msg["To"] = RECIPIENT
msg["Subject"] = "SMTP test — verification email"
msg.set_content("This is a test message to check SMTP sending.")

try:
    server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20)
    server.set_debuglevel(1)
    server.ehlo()
    server.starttls()
    server.ehlo()
    server.login(SENDER, SENDER_PASSWORD)
    server.send_message(msg)
    print("Email sent (server accepted message).")
    server.quit()
except Exception:
    import traceback
    print("Failed to send — exception:")
    traceback.print_exc()

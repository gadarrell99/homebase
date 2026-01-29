#!/usr/bin/env python3
import os
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

smtp_server = os.getenv("SMTP_SERVER")
smtp_port = int(os.getenv("SMTP_PORT", 587))
smtp_user = os.getenv("SMTP_USER")
smtp_pass = os.getenv("SMTP_PASS")
alert_to = os.getenv("ALERT_TO")

print(f"SMTP: {smtp_server}:{smtp_port}")
print(f"User: {smtp_user}")
print(f"To: {alert_to}")

try:
    print("Connecting...")
    server = smtplib.SMTP(smtp_server, smtp_port, timeout=30)
    server.starttls()
    print("Logging in...")
    server.login(smtp_user, smtp_pass)
    
    msg = MIMEText("Homebase email alerts are now configured and working!\n\nThis is a test alert from the infrastructure monitoring dashboard.")
    msg["Subject"] = "[HOMEBASE] Email Alerts Configured Successfully"
    msg["From"] = smtp_user
    msg["To"] = alert_to
    
    print("Sending...")
    server.send_message(msg)
    server.quit()
    print("TEST EMAIL SENT!")
except Exception as e:
    print(f"FAILED: {e}")
    exit(1)

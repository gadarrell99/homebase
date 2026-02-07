"""
Homebase Email Alert Service
Sends alerts on server state changes (UP -> DOWN, DOWN -> UP)
"""
import smtplib
import json
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# Configuration
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.office365.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USER = os.getenv('SMTP_USER', 'aidev@rize.bm')
SMTP_PASS = os.getenv('SMTP_PASS', '')
ALERT_TO = os.getenv('ALERT_TO', 'artiedarrell@gmail.com')
ALERT_FROM = os.getenv('ALERT_FROM', 'aidev@rize.bm')

# State file for tracking last known states
STATE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'server_states.json')


def load_states():
    """Load last known server states"""
    try:
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_states(states):
    """Save server states"""
    with open(STATE_FILE, 'w') as f:
        json.dump(states, f, indent=2)


def send_alert(server_name: str, ip: str, new_status: str, details: str = None):
    """Send email alert for server state change"""
    if not SMTP_PASS:
        print(f"[EmailAlert] SMTP_PASS not configured, skipping alert for {server_name}")
        return False
    
    status_emoji = "🔴" if new_status == "DOWN" else "🟢"
    subject = f"[HOMEBASE] {status_emoji} Server {server_name} is {new_status}"
    
    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif;">
        <h2 style="color: {'#dc3545' if new_status == 'DOWN' else '#28a745'};">{status_emoji} Server Alert</h2>
        <table style="border-collapse: collapse; margin: 20px 0;">
            <tr><td style="padding: 8px; font-weight: bold;">Server:</td><td style="padding: 8px;">{server_name}</td></tr>
            <tr><td style="padding: 8px; font-weight: bold;">IP Address:</td><td style="padding: 8px;">{ip}</td></tr>
            <tr><td style="padding: 8px; font-weight: bold;">Status:</td><td style="padding: 8px;">{new_status}</td></tr>
            <tr><td style="padding: 8px; font-weight: bold;">Time:</td><td style="padding: 8px;">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</td></tr>
        </table>
        {f'<p><strong>Details:</strong> {details}</p>' if details else ''}
        <p style="color: #666; font-size: 12px;">Sent by Homebase Monitoring System</p>
    </body>
    </html>
    """
    
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = ALERT_FROM
    msg['To'] = ALERT_TO
    msg.attach(MIMEText(html, 'html'))
    
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        print(f"[EmailAlert] Alert sent for {server_name}: {new_status}")
        return True
    except Exception as e:
        print(f"[EmailAlert] Failed to send alert: {e}")
        return False


def check_and_alert(server_name: str, ip: str, current_status: str, details: str = None):
    """Check if state changed and send alert if needed"""
    states = load_states()
    last_status = states.get(server_name, {}).get('status', None)
    
    # Normalize status
    is_up = current_status.lower() in ['online', 'up', 'ok', 'running']
    new_status = 'UP' if is_up else 'DOWN'
    
    # Check for state change
    if last_status is not None and last_status != new_status:
        print(f"[EmailAlert] State change detected: {server_name} {last_status} -> {new_status}")
        send_alert(server_name, ip, new_status, details)
    
    # Update state
    states[server_name] = {
        'status': new_status,
        'ip': ip,
        'last_check': datetime.now().isoformat()
    }
    save_states(states)


if __name__ == '__main__':
    # Test alert
    print("Testing email alert...")
    send_alert("Test Server", "192.168.1.1", "DOWN", "This is a test alert")

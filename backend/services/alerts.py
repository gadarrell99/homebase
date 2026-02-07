"""
Homebase Alert Service
Email notifications for critical server events
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import os
import json

# SMTP Configuration
SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.office365.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
SMTP_USER = os.environ.get('SMTP_USER', '')
SMTP_PASS = os.environ.get('SMTP_PASS', '')
DEFAULT_RECIPIENT = os.environ.get('ALERT_RECIPIENT', 'artiedarrell@gmail.com')

# Alert cooldown tracking (in memory - persists per process)
COOLDOWN_FILE = os.path.join(os.path.dirname(__file__), 'alert_cooldowns.json')
COOLDOWN_MINUTES = 15


def load_cooldowns():
    """Load cooldown timestamps from file"""
    try:
        if os.path.exists(COOLDOWN_FILE):
            with open(COOLDOWN_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return {}


def save_cooldowns(cooldowns):
    """Save cooldown timestamps to file"""
    try:
        with open(COOLDOWN_FILE, 'w') as f:
            json.dump(cooldowns, f)
    except:
        pass


def is_in_cooldown(server_name: str) -> bool:
    """Check if server is in alert cooldown period"""
    cooldowns = load_cooldowns()
    if server_name in cooldowns:
        last_alert = datetime.fromisoformat(cooldowns[server_name])
        if datetime.now() - last_alert < timedelta(minutes=COOLDOWN_MINUTES):
            return True
    return False


def set_cooldown(server_name: str):
    """Set cooldown timestamp for server"""
    cooldowns = load_cooldowns()
    cooldowns[server_name] = datetime.now().isoformat()
    save_cooldowns(cooldowns)


def send_email(subject: str, html_body: str, to: str = DEFAULT_RECIPIENT) -> bool:
    """Send an email notification"""
    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = f'Homebase <{SMTP_USER}>'
        msg['To'] = to
        msg['Subject'] = subject

        msg.attach(MIMEText(html_body, 'html'))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)

        print(f'[Alerts] Email sent to {to}')
        return True
    except Exception as e:
        print(f'[Alerts] Email error: {e}')
        return False


def alert_server_critical(server_name: str, server_ip: str, metrics: dict) -> bool:
    """Send alert for critical server status"""
    # Check cooldown
    if is_in_cooldown(server_name):
        print(f'[Alerts] {server_name} in cooldown, skipping alert')
        return False

    cpu = metrics.get('cpu_percent', 0)
    memory = metrics.get('memory_percent', 0)
    disk = metrics.get('disk_percent', 0)

    # Determine what's critical
    critical_items = []
    if cpu and cpu > 90:
        critical_items.append(f'CPU: {cpu:.1f}%')
    if memory and memory > 90:
        critical_items.append(f'Memory: {memory:.1f}%')
    if disk and disk > 90:
        critical_items.append(f'Disk: {disk:.1f}%')

    if not critical_items:
        return False

    subject = f'[Homebase] CRITICAL: {server_name} needs attention'

    html = f'''
    <h2 style="color: red;">Critical Server Alert</h2>
    <p><strong>{server_name}</strong> ({server_ip}) has critical resource usage:</p>

    <table style="border-collapse: collapse; margin: 20px 0;">
        <tr><td style="padding: 8px; font-weight: bold;">Server:</td><td style="padding: 8px;">{server_name}</td></tr>
        <tr><td style="padding: 8px; font-weight: bold;">IP:</td><td style="padding: 8px;">{server_ip}</td></tr>
        <tr><td style="padding: 8px; font-weight: bold;">CPU:</td><td style="padding: 8px; color: {'red' if cpu and cpu > 90 else 'inherit'};">{cpu:.1f}%</td></tr>
        <tr><td style="padding: 8px; font-weight: bold;">Memory:</td><td style="padding: 8px; color: {'red' if memory and memory > 90 else 'inherit'};">{memory:.1f}%</td></tr>
        <tr><td style="padding: 8px; font-weight: bold;">Disk:</td><td style="padding: 8px; color: {'red' if disk and disk > 90 else 'inherit'};">{disk:.1f}%</td></tr>
        <tr><td style="padding: 8px; font-weight: bold;">Time:</td><td style="padding: 8px;">{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</td></tr>
    </table>

    <p style="color: red;"><strong>Critical: {', '.join(critical_items)}</strong></p>

    <hr>
    <p style="color: #666; font-size: 12px;">Homebase Infrastructure Monitor - Next alert in {COOLDOWN_MINUTES} minutes</p>
    '''

    result = send_email(subject, html)
    if result:
        set_cooldown(server_name)
    return result


def alert_server_offline(server_name: str, server_ip: str) -> bool:
    """Send alert for server going offline"""
    if is_in_cooldown(f'{server_name}_offline'):
        return False

    subject = f'[Homebase] OFFLINE: {server_name} is unreachable'

    html = f'''
    <h2 style="color: red;">Server Offline Alert</h2>
    <p><strong>{server_name}</strong> ({server_ip}) is not responding:</p>

    <table style="border-collapse: collapse; margin: 20px 0;">
        <tr><td style="padding: 8px; font-weight: bold;">Server:</td><td style="padding: 8px;">{server_name}</td></tr>
        <tr><td style="padding: 8px; font-weight: bold;">IP:</td><td style="padding: 8px;">{server_ip}</td></tr>
        <tr><td style="padding: 8px; font-weight: bold;">Status:</td><td style="padding: 8px; color: red;">OFFLINE</td></tr>
        <tr><td style="padding: 8px; font-weight: bold;">Time:</td><td style="padding: 8px;">{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</td></tr>
    </table>

    <hr>
    <p style="color: #666; font-size: 12px;">Homebase Infrastructure Monitor</p>
    '''

    result = send_email(subject, html)
    if result:
        set_cooldown(f'{server_name}_offline')
    return result


if __name__ == '__main__':
    # Test alert
    result = alert_server_critical(
        'Test Server',
        '192.168.1.1',
        {'cpu_percent': 95, 'memory_percent': 88, 'disk_percent': 45}
    )
    print(f'Test alert result: {result}')

import pyotp, qrcode, jwt, json, os, io, base64
from datetime import datetime, timedelta

BASE = os.path.join(os.path.dirname(__file__), '..', '..')
TOTP_FILE = os.path.join(BASE, 'data', '.totp-secret')
JWT_SECRET = 'homebase-vault-cobalt'

def get_or_create_secret():
    if os.path.exists(TOTP_FILE):
        with open(TOTP_FILE) as f: return f.read().strip()
    secret = pyotp.random_base32()
    with open(TOTP_FILE, 'w') as f: f.write(secret)
    os.chmod(TOTP_FILE, 0o600)
    return secret

def is_setup():
    return os.path.exists(TOTP_FILE)

def get_qr_code():
    secret = get_or_create_secret()
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(name="admin", issuer_name="Homebase Vault")
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    b64 = base64.b64encode(buf.getvalue()).decode()
    return {"qr_base64": b64, "secret": secret, "uri": uri}

def verify_code(code):
    if not is_setup():
        return {"valid": False, "error": "TOTP not set up"}
    secret = get_or_create_secret()
    totp = pyotp.TOTP(secret)
    if totp.verify(code, valid_window=1):
        token = jwt.encode({"sub": "vault-admin", "exp": datetime.utcnow() + timedelta(minutes=10)}, JWT_SECRET, algorithm="HS256")
        return {"valid": True, "token": token}
    return {"valid": False, "error": "Invalid code"}

def verify_token(token):
    try:
        jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return True
    except:
        return False

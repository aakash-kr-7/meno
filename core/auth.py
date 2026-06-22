"""
API key auth logic. V1 uses single master key from settings.secret_key. secrets.compare_digest prevents timing attacks. Development mode skips auth with a startup WARNING.
"""

import hashlib
import secrets
from core.config import settings

def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()

def verify_key(provided: str) -> bool:
    return secrets.compare_digest(hash_key(provided), hash_key(settings.secret_key))

def generate_key() -> str:
    return "meno_sk_" + secrets.token_urlsafe(32)

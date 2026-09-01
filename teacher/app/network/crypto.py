"""AES-GCM encryption for network payloads.

Usage:
    ciphertext = encrypt(plaintext_str, password)
    plaintext  = decrypt(ciphertext_str, password)

When password is empty, both functions pass data through unchanged.
"""

import json
import os
import base64
import socket
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

SALT = b"mainpixel_crypto_2026"
_ITERS = 100_000


def _derive_key(password: str) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=SALT,
        iterations=_ITERS,
    )
    return kdf.derive(password.encode())


def encrypt(plaintext: str, password: str) -> str:
    """Encrypt plaintext with password-derived AES-GCM key.

    Returns a JSON string: {"c": "<base64 ciphertext>", "n": "<base64 nonce>"}
    If password is empty, returns plaintext unchanged.
    """
    if not password:
        return plaintext
    key = _derive_key(password)
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ct = aesgcm.encrypt(nonce, plaintext.encode(), None)
    return json.dumps(
        {"c": base64.b64encode(ct).decode(), "n": base64.b64encode(nonce).decode()},
        separators=(",", ":"),
    )


def decrypt(envelope: str, password: str) -> str:
    """Reverse of encrypt.

    If password is empty, returns envelope unchanged.
    If envelope is not encrypted JSON (no 'c' key), returns envelope unchanged.
    """
    if not password:
        return envelope
    try:
        data = json.loads(envelope)
    except (json.JSONDecodeError, ValueError):
        return envelope  # not JSON -> pass through
    if not isinstance(data, dict) or "c" not in data or "n" not in data:
        return envelope  # not an encrypted envelope -> pass through
    key = _derive_key(password)
    ct = base64.b64decode(data["c"])
    nonce = base64.b64decode(data["n"])
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ct, None).decode()


def get_local_ip() -> str:
    """Return the device's LAN IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        s.connect(("10.254.254.254", 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

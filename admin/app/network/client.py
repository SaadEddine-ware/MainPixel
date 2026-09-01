"""Teacher client: register with admin registry & push assignment data.

Usage (teacher):
    from app.network.client import RegistryClient
    client = RegistryClient(teacher_name="Ahmed")
    client.register(admin_host="192.168.1.100", port=8765)
    client.push_data({"assignments": [...], "grades": {...}})
"""

import json
import socket
from typing import Optional
from app.repositories.database import get_cfg, save_cfg
from app.network.crypto import encrypt, decrypt


DEFAULT_PORT = 8765


class RegistryClient:
    def __init__(self, teacher_name: str = ""):
        self.teacher_name = teacher_name or ""
        self.admin_host: Optional[str] = None
        self.admin_port: int = DEFAULT_PORT
        self._password: str = ""

    def set_password(self, pwd: str):
        self._password = pwd

    def load_config(self):
        """Load admin_host from config.json (persists across sessions)."""
        cfg = get_cfg()
        self.admin_host = cfg.get("admin_host", "").strip()
        self.teacher_name = cfg.get("teacher_name", "").strip()
        self.admin_port = cfg.get("admin_port", DEFAULT_PORT)

    def save_config(self):
        """Save admin_host + teacher_name to config.json."""
        cfg = get_cfg()
        if self.admin_host:
            cfg["admin_host"] = self.admin_host
        if self.teacher_name:
            cfg["teacher_name"] = self.teacher_name
        cfg["admin_port"] = self.admin_port
        save_cfg(cfg)

    def _send(self, payload: dict, host: Optional[str] = None,
              port: Optional[int] = None) -> dict:
        h = host or self.admin_host
        p = port or self.admin_port
        if not h:
            raise ConnectionError("Admin host not configured")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        try:
            sock.connect((h, p))
            plain = json.dumps(payload, separators=(",", ":"))
            outgoing = encrypt(plain, self._password)
            sock.sendall(outgoing.encode() if isinstance(outgoing, str)
                         else outgoing)
            sock.shutdown(socket.SHUT_WR)  # signal EOF to server
            response = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk
            if not response:
                raise ConnectionError("Empty response")
            raw = response.decode()
            decrypted = decrypt(raw, self._password)
            result = json.loads(decrypted)
            if "error" in result:
                raise ConnectionError(result["error"])
            return result
        finally:
            sock.close()

    def register(self, host: Optional[str] = None,
                 port: Optional[int] = None) -> dict:
        """Register this teacher with the admin registry server."""
        if not self.teacher_name:
            raise ValueError("teacher_name is not set")
        return self._send(
            {"action": "register", "name": self.teacher_name},
            host, port,
        )

    def push_data(self, data: dict, host: Optional[str] = None,
                  port: Optional[int] = None) -> dict:
        """Push assignment data to the admin registry server."""
        if not self.teacher_name:
            raise ValueError("teacher_name is not set")
        return self._send(
            {"action": "push", "name": self.teacher_name, "data": data},
            host, port,
        )

    def fetch_teachers(self, host: Optional[str] = None,
                       port: Optional[int] = None) -> list:
        """Ask registry for connected teachers (admin-only)."""
        result = self._send({"action": "list"}, host, port)
        return result.get("teachers", [])

    def pull_data(self, teacher_name: str, host: Optional[str] = None,
                  port: Optional[int] = None) -> Optional[dict]:
        """Pull buffered data for a specific teacher (admin-only)."""
        result = self._send(
            {"action": "pull", "name": teacher_name},
            host, port,
        )
        return result.get("data")

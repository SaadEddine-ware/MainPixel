"""Teacher client: register with admin, push data, and fetch class/student/subject lists."""
import json
import socket
from typing import Optional, Dict, List
from app.network.crypto import encrypt, decrypt


DEFAULT_PORT = 8765
TIMEOUT = 30  # generous for large payloads


class RegistryClient:
    def __init__(self, teacher_name: str = ""):
        self.teacher_name = teacher_name or ""
        self.admin_host: Optional[str] = None
        self.admin_port: int = DEFAULT_PORT
        self._password: str = ""

    def set_password(self, pwd: str):
        self._password = pwd

    # ── Low-level send ────────────────────────────────────────────────

    def _send(self, payload: dict, host: Optional[str] = None,
              port: Optional[int] = None) -> dict:
        h = host or self.admin_host
        p = port or self.admin_port
        if not h:
            raise ConnectionError("Admin host not configured")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(TIMEOUT)
        try:
            sock.connect((h, p))
            plain = json.dumps(payload, separators=(",", ":"))
            outgoing = encrypt(plain, self._password)
            sock.sendall(outgoing.encode() if isinstance(outgoing, str)
                         else outgoing)
            sock.shutdown(socket.SHUT_WR)
            response = b""
            while True:
                chunk = sock.recv(65536)
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

    # ── Teacher commands ──────────────────────────────────────────────

    def register(self, host: Optional[str] = None,
                 port: Optional[int] = None) -> dict:
        if not self.teacher_name:
            raise ValueError("teacher_name is not set")
        return self._send(
            {"action": "register", "name": self.teacher_name},
            host, port,
        )

    def push_data(self, data: dict, host: Optional[str] = None,
                  port: Optional[int] = None) -> dict:
        if not self.teacher_name:
            raise ValueError("teacher_name is not set")
        return self._send(
            {"action": "push", "name": self.teacher_name, "data": data},
            host, port,
        )

    # ── Fetch commands (teacher pulls data from admin DB) ─────────────

    def fetch_classes(self, host: Optional[str] = None,
                      port: Optional[int] = None) -> List[dict]:
        result = self._send({"action": "fetch_classes"}, host, port)
        return result.get("classes", [])

    def fetch_students(self, class_id: int, host: Optional[str] = None,
                       port: Optional[int] = None) -> List[dict]:
        result = self._send(
            {"action": "fetch_students", "class_id": class_id},
            host, port,
        )
        return result.get("students", [])

    def fetch_subjects(self, class_id: int, host: Optional[str] = None,
                       port: Optional[int] = None) -> List[dict]:
        result = self._send(
            {"action": "fetch_subjects", "class_id": class_id},
            host, port,
        )
        return result.get("subjects", [])

    def fetch_assignments(self, class_id: int, matiere_id: int,
                          semester: int = 1, host: Optional[str] = None,
                          port: Optional[int] = None) -> dict:
        return self._send({
            "action": "fetch_assignments",
            "class_id": class_id,
            "matiere_id": matiere_id,
            "semester": semester,
        }, host, port)

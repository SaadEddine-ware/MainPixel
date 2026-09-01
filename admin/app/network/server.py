"""Registry server: admin-side listener for teacher registration & data relay.

Protocol (JSON over TCP):
  Teacher → Server:
    {"action": "register", "name": "Ahmed"}
    {"action": "push",     "name": "Ahmed", "data": {...}}

  Admin → Server (same port, same socket):
    {"action": "list"}
    {"action": "pull", "name": "Ahmed"}

Usage (admin):
    from app.network.server import RegistryServer
    server = RegistryServer()
    server.start(port=8765)
    ...
    server.stop()
"""

import json
import socket
import threading
from datetime import datetime
from typing import Optional, Dict, List
from app.network.crypto import encrypt, decrypt


class RegistryServer:
    def __init__(self):
        self._socket: Optional[socket.socket] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None

        self._password: str = ""
        # name -> {"ip": str, "last_seen": str, "data": Optional[dict]}
        self._teachers: Dict[str, Dict] = {}
        self._lock = threading.Lock()

    # ── Public API ──────────────────────────────────────────────────────

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def teachers(self) -> List[dict]:
        with self._lock:
            return [
                {"name": name, **info}
                for name, info in self._teachers.items()
            ]

    def get_teacher_data(self, name: str) -> Optional[dict]:
        with self._lock:
            info = self._teachers.get(name)
            if info and info["data"] is not None:
                return info["data"]
            return None

    def clear_teacher_data(self, name: str):
        with self._lock:
            if name in self._teachers:
                self._teachers[name]["data"] = None

    def set_password(self, pwd: str):
        self._password = pwd

    def start(self, host: str = "0.0.0.0", port: int = 8765):
        if self._running:
            return
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind((host, port))
        self._socket.listen(5)
        self._socket.settimeout(1.0)  # allow periodic stop checks
        self._running = True
        self._thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)

    # ── Internal ────────────────────────────────────────────────────────

    def _accept_loop(self):
        while self._running:
            try:
                conn, addr = self._socket.accept()
            except socket.timeout:
                continue
            except Exception:
                break
            threading.Thread(
                target=self._handle_client, args=(conn, addr), daemon=True
            ).start()

    def _handle_client(self, conn: socket.socket, addr):
        ip = addr[0]
        was_encrypted = False
        try:
            raw = b""
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                raw += chunk
            if not raw:
                return

            raw_str = raw.decode()
            if self._password:
                try:
                    env = json.loads(raw_str)
                    was_encrypted = isinstance(env, dict) and "c" in env and "n" in env
                except (json.JSONDecodeError, TypeError):
                    pass

            decrypted = decrypt(raw_str, self._password)
            payload = json.loads(decrypted)
            action = payload.get("action")
            response = self._dispatch(action, payload, ip)
            response_str = json.dumps(response, separators=(",", ":"))
            outgoing = encrypt(response_str, self._password) if was_encrypted else response_str
            conn.sendall(outgoing.encode() if isinstance(outgoing, str)
                         else outgoing)
        except Exception as e:
            try:
                err = json.dumps({"error": str(e)}, separators=(",", ":"))
                outgoing = encrypt(err, self._password) if was_encrypted else err
                conn.sendall(outgoing.encode() if isinstance(outgoing, str)
                             else outgoing)
            except Exception:
                pass
        finally:
            conn.close()

    def _dispatch(self, action: str, payload: dict, ip: str) -> dict:
        if action == "register":
            return self._cmd_register(payload, ip)
        elif action == "push":
            return self._cmd_push(payload)
        elif action == "list":
            return self._cmd_list()
        elif action == "pull":
            return self._cmd_pull(payload)
        elif action == "fetch_classes":
            return self._cmd_fetch_classes()
        elif action == "fetch_students":
            return self._cmd_fetch_students(payload)
        elif action == "fetch_subjects":
            return self._cmd_fetch_subjects(payload)
        elif action == "fetch_assignments":
            return self._cmd_fetch_assignments(payload)
        else:
            return {"error": f"Unknown action: {action}"}

    def _cmd_register(self, payload: dict, ip: str) -> dict:
        name = payload.get("name", "").strip()
        if not name:
            return {"error": "name is required"}
        now = datetime.now().isoformat()
        with self._lock:
            existing = self._teachers.get(name)
            if existing:
                existing["ip"] = ip
                existing["last_seen"] = now
            else:
                self._teachers[name] = {
                    "ip": ip,
                    "last_seen": now,
                    "data": None,
                }
        return {"status": "ok", "name": name}

    def _cmd_push(self, payload: dict) -> dict:
        name = payload.get("name", "").strip()
        data = payload.get("data")
        if not name:
            return {"error": "name is required"}
        if data is None:
            return {"error": "data is required"}
        with self._lock:
            if name not in self._teachers:
                return {"error": f"Teacher '{name}' not registered"}
            self._teachers[name]["data"] = data
            self._teachers[name]["last_seen"] = datetime.now().isoformat()
        return {"status": "ok"}

    def _cmd_list(self) -> dict:
        with self._lock:
            teachers = [
                {
                    "name": name,
                    "ip": info["ip"],
                    "last_seen": info["last_seen"],
                    "has_data": info["data"] is not None,
                }
                for name, info in self._teachers.items()
            ]
        return {"teachers": teachers}

    def _cmd_pull(self, payload: dict) -> dict:
        name = payload.get("name", "").strip()
        if not name:
            return {"error": "name is required"}
        data = self.get_teacher_data(name)
        if data is None:
            # Maybe the teacher has data but it's None
            with self._lock:
                if name in self._teachers:
                    return {"status": "ok", "data": None, "message": "no data available"}
                return {"error": f"Teacher '{name}' not found"}
        return {"status": "ok", "data": data}


    # ── Teacher fetch commands (query admin DB) ──────────────────────────

    def _cmd_fetch_classes(self) -> dict:
        from app.services.class_service import list_all_classes
        classes = list_all_classes()
        return {"classes": [
            {
                "id": cid,
                "level_name": lv,
                "year": yr,
                "name": nm,
                "count": ct,
                "branch": br or "",
            }
            for cid, lv, yr, nm, ct, br in classes
        ]}

    def _cmd_fetch_students(self, payload: dict) -> dict:
        class_id = payload.get("class_id")
        if not class_id:
            return {"error": "class_id is required"}
        from app.services.student_service import list_students_for_class
        students = list_students_for_class(class_id)
        return {"students": [
            {
                "id": s.id,
                "full_name": s.full_name,
                "code_massar": s.code_massar or "",
            }
            for s in students
        ]}

    def _cmd_fetch_subjects(self, payload: dict) -> dict:
        class_id = payload.get("class_id")
        if not class_id:
            return {"error": "class_id is required"}
        from app.repositories.database import get_session
        from app.models.classe import Classe
        with get_session() as session:
            cls = session.get(Classe, class_id)
            if not cls:
                return {"error": "class not found"}
            level_key = cls.level_key
            year_name = cls.year_name
            branch = cls.branch or ""
        from app.services.grade_service import list_matieres
        matieres = list_matieres(level_key, year_name, branch=branch)
        return {"subjects": [
            {"id": m.id, "name": m.name, "coefficient": m.coefficient}
            for m in matieres
        ]}

    def _cmd_fetch_assignments(self, payload: dict) -> dict:
        class_id = payload.get("class_id")
        matiere_id = payload.get("matiere_id")
        semester = payload.get("semester", 1)
        if not class_id or not matiere_id:
            return {"error": "class_id and matiere_id are required"}
        from app.services.assignment_service import (
            list_assignments, get_assignment_grades,
        )
        assignments = list_assignments(class_id, matiere_id, semester)
        result = {"assignments": []}
        for a in assignments:
            grades = get_assignment_grades(a.id)
            result["assignments"].append({
                "id": a.id,
                "title": a.title,
                "coefficient": a.coefficient,
                "date": a.date or "",
            })
            result.setdefault("grades", {})[str(a.id)] = {
                str(sid): v for sid, v in grades.items()
            }
        return result

# ── Module-level singleton ─────────────────────────────────────────────

_registry: Optional[RegistryServer] = None


def get_registry() -> RegistryServer:
    global _registry
    if _registry is None:
        _registry = RegistryServer()
    return _registry

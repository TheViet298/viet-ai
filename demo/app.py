"""Serve the standalone website and its local demo API."""
import json
import mimetypes
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from engine import Engine
from store import Store

ROOT = Path(__file__).resolve().parent


def load_env():
    path = ROOT / ".env"
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip() and not line.lstrip().startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def create_server(host="127.0.0.1", port=8765, database=None):
    store = Store(database or ROOT / "data/demo.db", ROOT / "datasets/knowledge.json")
    engine = Engine(store, ROOT / "datasets/rules.json")

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def send_json(self, status, payload):
            raw = json.dumps(payload, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            path = urlparse(self.path).path
            if path == "/api/health":
                self.send_json(200, {"status": "ok", "mode": "standalone-demo", "api_key_required": False})
            elif path == "/api/cases":
                self.send_json(200, {"cases": store.cases()})
            else:
                files = {"/": "index.html", "/styles.css": "styles.css", "/app.js": "app.js"}
                if path not in files:
                    self.send_json(404, {"error": "Không tìm thấy đường dẫn"})
                    return
                file = ROOT / "static" / files[path]
                raw = file.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", (mimetypes.guess_type(file.name)[0] or "text/plain") + "; charset=utf-8")
                self.send_header("Content-Length", str(len(raw)))
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(raw)

        def do_POST(self):
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > 12000:
                    raise ValueError("Nội dung yêu cầu không hợp lệ hoặc quá dài")
                payload = json.loads(self.rfile.read(length))
                if not isinstance(payload, dict):
                    raise ValueError("Yêu cầu phải là JSON object")
                path = urlparse(self.path).path
                if path == "/api/chat":
                    message = payload.get("message")
                    session_id = payload.get("session_id")
                    if not isinstance(message, str) or not message.strip() or len(message) > 5000:
                        raise ValueError("Tin nhắn phải có từ 1 đến 5000 ký tự")
                    if session_id is not None and (not isinstance(session_id, str) or len(session_id) > 64):
                        raise ValueError("Session ID không hợp lệ")
                    self.send_json(200, engine.respond(message, session_id))
                elif path == "/api/cases/action":
                    case_id, action = payload.get("case_id"), payload.get("action")
                    if not isinstance(case_id, str) or not isinstance(action, str):
                        raise ValueError("Thiếu mã hồ sơ hoặc hành động")
                    self.send_json(200, {"status": store.update_case(case_id, action)})
                else:
                    self.send_json(404, {"error": "Không tìm thấy đường dẫn"})
            except (ValueError, TypeError, json.JSONDecodeError) as error:
                self.send_json(400, {"error": str(error)})
            except Exception:
                self.send_json(500, {"error": "Demo gặp lỗi xử lý. Vui lòng thử lại."})

    return ThreadingHTTPServer((host, port), Handler)


def main():
    load_env()
    url = os.environ.get("DATABASE_URL", "sqlite:///./data/demo.db")
    if not url.startswith("sqlite:///"):
        raise SystemExit("Demo sử dụng DATABASE_URL dạng sqlite:///...")
    path = Path(url.removeprefix("sqlite:///"))
    if not path.is_absolute():
        path = ROOT / path
    host, port = os.environ.get("DEMO_HOST", "127.0.0.1"), int(os.environ.get("DEMO_PORT", "8765"))
    server = create_server(host, port, path)
    print(f"Demo sẵn sàng: http://{host}:{port} — Ctrl+C để dừng", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

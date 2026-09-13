"""Small local web UI for the VinBus ReAct Agent."""

from __future__ import annotations

import json
import mimetypes
from contextlib import redirect_stdout
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import StringIO
from pathlib import Path
from typing import Any, Callable, Dict, List
from urllib.parse import urlparse

try:
    from .app import run_react_agent
    from .mcp_server import MCPAcademicServer
    from .providers import get_llm_provider
except ImportError:
    from app import run_react_agent
    from mcp_server import MCPAcademicServer
    from providers import get_llm_provider


MAX_MESSAGE_CHARS = 1_500
MAX_BODY_BYTES = 8_192
WEB_ROOT = Path(__file__).resolve().parents[1] / "web"
STATIC_FILES = {
    "/": "index.html",
    "/styles.css": "styles.css",
    "/app.js": "app.js",
}


def validate_chat_message(message: Any) -> str:
    if not isinstance(message, str) or not message.strip():
        raise ValueError("Câu hỏi không được để trống.")

    normalized = message.strip()
    if len(normalized) > MAX_MESSAGE_CHARS:
        raise ValueError(f"Câu hỏi quá dài (tối đa {MAX_MESSAGE_CHARS} ký tự).")
    return normalized


def run_agent_request(
    message: str,
    provider: Any,
    mcp_server: MCPAcademicServer,
    agent_runner: Callable[[str, Any, MCPAcademicServer], List[Dict[str, Any]]] = run_react_agent,
) -> Dict[str, Any]:
    # The CLI agent prints its full trace, which can contain registration
    # details. The web endpoint intentionally returns only a reduced trace.
    with redirect_stdout(StringIO()):
        traces = agent_runner(message, provider, mcp_server)
    final_trace = next(
        (trace for trace in reversed(traces) if trace["action_type"] == "FINAL_ANSWER"),
        {},
    )
    trace_summary = []
    for trace in traces:
        entry = {
            "step": trace["step"],
            "action_type": trace["action_type"],
        }
        if trace["action_type"] == "TOOL_EXECUTION":
            entry["tool_name"] = trace.get("tool_name", "unknown")
            entry["status"] = trace.get("observation", {}).get("status", "UNKNOWN")
        trace_summary.append(entry)

    return {
        "answer": final_trace.get(
            "output",
            "Agent chưa tạo được câu trả lời cuối. Vui lòng thử lại.",
        ),
        "trace": trace_summary,
    }


class VinBusWebHandler(BaseHTTPRequestHandler):
    server_version = "VinBusAgentUI/1.0"

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[WEB] {self.address_string()} - {format % args}")

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/api/health":
            provider = self.server.provider  # type: ignore[attr-defined]
            self._send_json(
                HTTPStatus.OK,
                {
                    "provider": provider.__class__.__name__,
                    "model": getattr(provider, "model_name", "not configured"),
                },
            )
            return

        filename = STATIC_FILES.get(path)
        if not filename:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Không tìm thấy trang."})
            return

        asset_path = WEB_ROOT / filename
        content_type = mimetypes.guess_type(asset_path.name)[0] or "text/plain"
        self._send_bytes(HTTPStatus.OK, asset_path.read_bytes(), content_type)

    def do_POST(self) -> None:  # noqa: N802
        if urlparse(self.path).path != "/api/chat":
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Không tìm thấy API."})
            return

        try:
            content_length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Content-Length không hợp lệ."})
            return
        if content_length <= 0 or content_length > MAX_BODY_BYTES:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Dữ liệu gửi lên không hợp lệ."})
            return

        try:
            payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
            message = validate_chat_message(payload.get("message"))
            result = run_agent_request(
                message,
                self.server.provider,  # type: ignore[attr-defined]
                self.server.mcp_server,  # type: ignore[attr-defined]
            )
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
            return
        except Exception:
            self._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": "Không thể xử lý yêu cầu. Vui lòng thử lại."},
            )
            return

        self._send_json(HTTPStatus.OK, result)

    def _send_json(self, status: HTTPStatus, payload: Dict[str, Any]) -> None:
        self._send_bytes(
            status,
            json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            "application/json; charset=utf-8",
        )

    def _send_bytes(self, status: HTTPStatus, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def create_server(host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), VinBusWebHandler)
    server.daemon_threads = True
    server.provider = get_llm_provider()  # type: ignore[attr-defined]
    server.mcp_server = MCPAcademicServer()  # type: ignore[attr-defined]
    return server


if __name__ == "__main__":
    httpd = create_server()
    print("VinBus UI đang chạy tại http://127.0.0.1:8765")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nĐã dừng VinBus UI.")
    finally:
        httpd.server_close()

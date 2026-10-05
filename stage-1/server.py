"""HTTP boundary. No network clients, external services or runtime dependencies."""
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from urllib.parse import parse_qs, urlsplit

from domain import APIError, Service, require


SERVICE = Service()


def reject_constant(_):
    raise ValueError("Non-JSON numeric constant")


class Server(ThreadingHTTPServer):
    request_queue_size = 128
    daemon_threads = True


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *_):
        # Tokens, fixture passwords and export snapshots never enter access logs.
        pass

    def send_json(self, status, payload):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        if self.command != "HEAD" and payload:
            self.wfile.write(payload)

    def send_error(self, code, message=None, explain=None):
        # BaseHTTPRequestHandler errors also obey the JSON envelope and no5xx rule.
        status = code if 400 <= code < 500 else 404
        err = APIError(status, "not_found" if status == 404 else "malformed_request", "Invalid HTTP request")
        self.close_connection = True
        try:
            self.send_json(status, json.dumps(err.body()).encode("utf-8"))
        except (BrokenPipeError, ConnectionResetError):
            pass

    def body(self):
        require(not self.headers.get("Transfer-Encoding"), 400, "malformed_request", "Content-Length required")
        length_text = self.headers.get("Content-Length", "0")
        require(length_text.isascii() and length_text.isdecimal(), 400, "malformed_request", "Invalid Content-Length")
        length = int(length_text)
        raw = self.rfile.read(length)
        if length == 0 and self.path.split("?")[0].endswith(("/decline", "/cancel")):
            return {}
        value = json.loads(raw.decode("utf-8"), parse_int=Decimal, parse_float=Decimal,
                           parse_constant=reject_constant)
        require(type(value) is dict, 400, "malformed_request", "Body must be a JSON object")
        return value

    def handle_api(self):
        try:
            parsed = urlsplit(self.path)
            body = self.body() if self.command == "POST" else None
            query = parse_qs(parsed.query, keep_blank_values=True)
            # Serialize the response inside the same boundary as domain work. It
            # cannot reference records mutated after the lock has been released.
            with SERVICE.lock:
                status, result = SERVICE.route(self.command, parsed.path, query, body,
                                               self.headers.get("Authorization"),
                                               self.headers.get("Idempotency-Key"))
                payload = b"" if status == 204 else json.dumps(
                    result, ensure_ascii=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        except APIError as exc:
            status, payload = exc.status, json.dumps(exc.body()).encode("utf-8")
        except (ValueError, UnicodeError, TypeError, OverflowError, RecursionError):
            exc = APIError(400, "malformed_request", "Cannot parse request")
            status, payload = exc.status, json.dumps(exc.body()).encode("utf-8")
            self.close_connection = True
        except Exception:
            # Invalid inputs never leak internals or produce a5xx. All normative
            # domain failures use explicit APIError branches above.
            exc = APIError(400, "malformed_request", "Request cannot be processed")
            status, payload = exc.status, json.dumps(exc.body()).encode("utf-8")
            self.close_connection = True
        try:
            self.send_json(status, payload)
        except (BrokenPipeError, ConnectionResetError):
            pass  # A disconnected client may retry using the same idempotency key.

    do_GET = do_POST = do_HEAD = do_PUT = do_PATCH = do_DELETE = do_OPTIONS = handle_api


if __name__ == "__main__":
    Server(("0.0.0.0", int(os.environ.get("PORT", "8080"))), Handler).serve_forever(poll_interval=0.1)

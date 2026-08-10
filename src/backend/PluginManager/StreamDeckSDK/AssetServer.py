"""
Author: Core447
Year: 2025

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This programm comes with ABSOLUTELY NO WARRANTY!

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
import os
import threading
import urllib.parse

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from loguru import logger as log

MIME_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".htm": "text/html; charset=utf-8",
    ".xhtml": "application/xhtml+xml; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8",
    ".cjs": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".map": "application/json; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".ttf": "font/ttf",
    ".otf": "font/otf",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".mp4": "video/mp4",
    ".webm": "video/webm",
}


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    # Set by AssetServer before the server starts
    root: str = None

    def log_message(self, format, *args):  # noqa: A002 - signature comes from the stdlib
        # The default implementation writes to stderr on every request
        pass

    def _resolve(self) -> str | None:
        """
        Turn the request URL into a path on disk. The URL path mirrors the absolute
        filesystem path so that relative references inside a property inspector keep
        working.
        """
        path = urllib.parse.urlparse(self.path).path
        path = urllib.parse.unquote(path)

        if not path.startswith("/"):
            path = "/" + path

        real_root = os.path.realpath(self.root)
        real_path = os.path.realpath(path)

        # Never serve anything outside of the plugin directory
        if real_path != real_root and not real_path.startswith(real_root + os.sep):
            return None

        if not os.path.isfile(real_path):
            return None

        return real_path

    def do_GET(self):
        self._respond(include_body=True)

    def do_HEAD(self):
        self._respond(include_body=False)

    def _respond(self, include_body: bool):
        path = self._resolve()
        if path is None:
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        try:
            with open(path, "rb") as f:
                content = f.read()
        except OSError:
            self.send_response(500)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        mime = MIME_TYPES.get(os.path.splitext(path)[1].lower(), "application/octet-stream")

        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

        if include_body:
            try:
                self.wfile.write(content)
            except OSError:
                pass


class AssetServer:
    """
    Serves the files of the installed Stream Deck SDK plugins over http so that
    property inspectors can be loaded into a WebView with working relative paths.
    """

    def __init__(self, root: str, host: str = "127.0.0.1"):
        self.root = root
        self.host = host
        self.port: int = None

        self._server: ThreadingHTTPServer = None
        self._thread: threading.Thread = None

    def start(self, port: int = 0) -> int:
        handler = type("_BoundHandler", (_Handler,), {"root": self.root})

        self._server = ThreadingHTTPServer((self.host, port), handler)
        self._server.daemon_threads = True
        self.port = self._server.server_address[1]

        self._thread = threading.Thread(target=self._server.serve_forever, name="sd_sdk_asset_server", daemon=True)
        self._thread.start()

        log.info(f"Stream Deck SDK asset server listening on {self.host}:{self.port}")
        return self.port

    def stop(self) -> None:
        if self._server is None:
            return
        self._server.shutdown()
        self._server.server_close()
        self._server = None

    def get_url(self, file_path: str) -> str:
        """Return the http url this server serves ``file_path`` under."""
        quoted = urllib.parse.quote(os.path.abspath(file_path))
        return f"http://{self.host}:{self.port}{quoted}"

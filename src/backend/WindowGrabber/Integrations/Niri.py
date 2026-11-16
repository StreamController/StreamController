import json
import os
import selectors
import subprocess
import threading
import time

from loguru import logger as log

import globals as gl
from src.backend.WindowGrabber.Integration import Integration
from src.backend.WindowGrabber.Window import Window


class Niri(Integration):
    def __init__(self, window_grabber):
        super().__init__(window_grabber)
        self._lock = threading.Lock()
        self._windows = {}
        self._focused_id = None
        self._last_emitted = None
        self._command = ["niri", "msg", "--json", "event-stream"]
        if os.path.isfile("/.flatpak-info"):
            self._command = ["flatpak-spawn", "--host"] + self._command
        threading.Thread(target=self._watch, name="NiriEventStream", daemon=True).start()

    @staticmethod
    def _parse(window):
        return Window(window.get("app_id") or "", window.get("title") or "")

    def get_all_windows(self):
        with self._lock:
            return [self._parse(window) for window in self._windows.values()]

    def get_active_window(self):
        with self._lock:
            window = self._windows.get(self._focused_id)
            return self._parse(window) if window is not None else None

    def _handle(self, event):
        with self._lock:
            if "WindowsChanged" in event:
                self._windows = {window["id"]: window for window in event["WindowsChanged"]["windows"]}
                self._focused_id = next(
                    (window["id"] for window in self._windows.values() if window.get("is_focused")), None
                )
            elif "WindowOpenedOrChanged" in event:
                window = event["WindowOpenedOrChanged"]["window"]
                self._windows[window["id"]] = window
                if window.get("is_focused"):
                    self._focused_id = window["id"]
            elif "WindowClosed" in event:
                window_id = event["WindowClosed"]["id"]
                self._windows.pop(window_id, None)
                if self._focused_id == window_id:
                    self._focused_id = None
            elif "WindowFocusChanged" in event:
                self._focused_id = event["WindowFocusChanged"]["id"]

    def _emit(self):
        active = self.get_active_window()
        if active is None:
            self._last_emitted = None
            return
        if active == self._last_emitted or getattr(gl, "deck_manager", None) is None:
            return
        self.window_grabber.on_active_window_changed(active)
        self._last_emitted = active

    def _watch(self):
        while gl.threads_running:
            try:
                with subprocess.Popen(self._command, stdout=subprocess.PIPE, cwd="/") as process:
                    try:
                        with selectors.DefaultSelector() as selector:
                            selector.register(process.stdout, selectors.EVENT_READ)
                            pending = b""
                            connected = True
                            while gl.threads_running and connected:
                                for key, _ in selector.select(timeout=0.5):
                                    chunk = os.read(key.fd, 65536)
                                    if not chunk:
                                        connected = False
                                        break
                                    pending += chunk
                                    while b"\n" in pending:
                                        line, pending = pending.split(b"\n", 1)
                                        self._handle(json.loads(line))
                                self._emit()
                    finally:
                        if process.poll() is None:
                            process.terminate()
                        try:
                            process.wait(timeout=1)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait()
            except Exception as error:
                log.error(f"niri event stream failed: {error}")
            with self._lock:
                self._windows.clear()
                self._focused_id = None
            self._last_emitted = None
            if gl.threads_running:
                time.sleep(1)

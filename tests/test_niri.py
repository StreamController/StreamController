import ast
import json
import os
import selectors
import subprocess
import sys
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from src.backend.WindowGrabber.Integration import Integration
from src.backend.WindowGrabber.Window import Window


def load_niri():
    path = Path(__file__).resolve().parent.parent / "src/backend/WindowGrabber/Integrations/Niri.py"
    tree = ast.parse(path.read_text())
    nodes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
    state = SimpleNamespace(threads_running=True, deck_manager=object())
    namespace = dict(Integration=Integration, Window=Window, gl=state, log=Mock(),
                     json=json, os=os, selectors=selectors, subprocess=subprocess,
                     threading=threading, time=time)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), namespace)
    return namespace["Niri"], state


class TestNiri(unittest.TestCase):
    def setUp(self):
        backend, self.state = load_niri()
        self.grabber = Mock()
        with patch("threading.Thread"), patch("os.path.isfile", return_value=False):
            self.niri = backend(self.grabber)

    def snapshot(self):
        self.niri._handle({"WindowsChanged": {"windows": [
            {"id": 1, "app_id": "kitty", "title": "Terminal", "is_focused": True},
            {"id": 2, "app_id": "firefox", "title": "Browser", "is_focused": False},
        ]}})

    def test_initial_snapshot(self):
        self.snapshot()
        self.assertEqual(self.niri.get_active_window(), Window("kitty", "Terminal"))
        self.assertEqual(len(self.niri.get_all_windows()), 2)

    def test_focus_and_title_changes(self):
        self.snapshot()
        self.niri._emit()
        self.niri._handle({"WindowFocusChanged": {"id": 2}})
        self.niri._emit()
        self.niri._handle({"WindowOpenedOrChanged": {"window": {
            "id": 2, "app_id": "firefox", "title": "New title", "is_focused": True,
        }}})
        self.niri._emit()
        self.grabber.on_active_window_changed.assert_called_with(Window("firefox", "New title"))
        self.assertEqual(self.grabber.on_active_window_changed.call_count, 3)

    def test_duplicate_events_do_not_reload_page(self):
        self.snapshot()
        self.niri._emit()
        self.niri._emit()
        self.grabber.on_active_window_changed.assert_called_once()

    def test_focus_loss_and_return_emits_again(self):
        self.snapshot()
        self.niri._emit()
        self.niri._handle({"WindowFocusChanged": {"id": None}})
        self.niri._emit()
        self.assertIsNone(self.niri.get_active_window())
        self.niri._handle({"WindowFocusChanged": {"id": 1}})
        self.niri._emit()
        self.assertEqual(self.grabber.on_active_window_changed.call_count, 2)

    def test_close_active_window_and_replace_snapshot(self):
        self.snapshot()
        self.niri._handle({"WindowClosed": {"id": 1}})
        self.assertIsNone(self.niri.get_active_window())
        self.niri._handle({"WindowsChanged": {"windows": []}})
        self.assertEqual(self.niri.get_all_windows(), [])

    def test_missing_metadata(self):
        self.assertEqual(self.niri._parse({"app_id": None, "title": None}), Window("", ""))

    def test_waits_for_deck_manager(self):
        self.snapshot()
        self.state.deck_manager = None
        self.niri._emit()
        self.grabber.on_active_window_changed.assert_not_called()
        self.state.deck_manager = object()
        self.niri._emit()
        self.grabber.on_active_window_changed.assert_called_once()

    def test_flatpak_uses_host_command(self):
        backend, _ = load_niri()
        with patch("threading.Thread"), patch("os.path.isfile", return_value=True):
            niri = backend(Mock())
        self.assertEqual(niri._command[:2], ["flatpak-spawn", "--host"])

    def test_worker_stops_even_when_event_stream_is_idle(self):
        self.niri._command = [sys.executable, "-c", "import time; time.sleep(30)"]
        started = threading.Event()
        processes = []
        popen = subprocess.Popen

        def spawn(*args, **kwargs):
            process = popen(*args, **kwargs)
            processes.append(process)
            started.set()
            return process

        with patch("subprocess.Popen", side_effect=spawn):
            worker = threading.Thread(target=self.niri._watch)
            worker.start()
            try:
                self.assertTrue(started.wait(timeout=3))
            finally:
                self.state.threads_running = False
                worker.join(timeout=3)
        self.assertFalse(worker.is_alive())
        self.assertIsNotNone(processes[0].poll())


if __name__ == "__main__":
    unittest.main()

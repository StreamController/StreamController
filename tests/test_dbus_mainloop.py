"""
Regression guard for the dbus-python GLib main loop crash.

dbus-python's GLib integration (dbus-gmain) is not thread safe. watch_toggled
implements watch enable/disable as a full GSource add/remove, and both paths
mutate an unlocked GSList on the connection from whichever thread sent the
message, while the main loop dispatches those same sources and
io_handler_dispatch dereferences handler->watch with no NULL check.

Installing the main loop attaches every dbus.SessionBus() in the process,
including the shared one plugins get. Because StreamController reaches D-Bus
from the per-deck tick threads via plugin on_tick(), that turns into a random
SIGABRT after hours or days of uptime:

    dbus[3]: arguments to dbus_watch_handle() were incorrect, assertion
    "watch != NULL" failed in file ../dbus/dbus-watch.c line 738.

So dbus-python may only be used for blocking method calls, which work on an
unattached connection. Anything needing signals, async replies or exported
objects must use GDBus (gi.repository.Gio) or dasbus instead.

Run with:

    python3 -m unittest discover -s tests -t .
"""
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

SCAN_FILES = ("main.py", "autostart.py", "globals.py", "permissons.py")
SCAN_DIRS = ("src", "GtkHelper")

# dbus-python APIs that only work once a connection is attached to a main loop.
FORBIDDEN = {
    "DBusGMainLoop": "installs dbus-python's GLib main loop",
    "dbus.mainloop": "installs dbus-python's GLib main loop",
    "set_default_main_loop": "installs dbus-python's GLib main loop",
    "add_signal_receiver": "needs an attached main loop, use Gio signal_subscribe()",
    "connect_to_signal": "needs an attached main loop, use the Gio.DBusProxy 'g-signal'",
    "reply_handler": "async dbus-python calls need an attached main loop",
    "dbus.service.": "exporting objects needs an attached main loop, use Gio or dasbus",
}


def iter_source_files():
    for name in SCAN_FILES:
        path = REPO_ROOT / name
        if path.is_file():
            yield path
    for directory in SCAN_DIRS:
        yield from sorted((REPO_ROOT / directory).rglob("*.py"))


def find_violations(path: Path) -> list[str]:
    violations = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.lstrip().startswith("#"):
            continue
        for token, reason in FORBIDDEN.items():
            if token in line:
                relative = path.relative_to(REPO_ROOT)
                violations.append(f"{relative}:{lineno}: {token!r} {reason}\n    {line.strip()}")
    return violations


class DBusMainLoopTest(unittest.TestCase):
    def test_no_main_loop_dependent_dbus_python_api(self):
        violations = []
        for path in iter_source_files():
            violations += find_violations(path)

        self.assertEqual(
            violations, [],
            "dbus-python may only be used for blocking method calls:\n\n"
            + "\n".join(violations)
        )

    def test_main_py_does_not_import_dbus_mainloop(self):
        source = (REPO_ROOT / "main.py").read_text(encoding="utf-8")
        self.assertNotIn("dbus.mainloop", source)
        self.assertNotIn("DBusGMainLoop", source)


if __name__ == "__main__":
    unittest.main()

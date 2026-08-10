"""
Manual stress tool for the dbus-python GLib main loop crash. Not part of the
automated suite, since it depends on winning a race and can run for a long time
without doing so.

It reproduces the shape of the bug: one shared dbus-python connection attached
to the GLib main loop on the main thread, a signal match on it, and background
threads making blocking calls, which is what the deck tick threads do through
plugin on_tick().

Large payloads matter. libdbus cannot flush them in one write(), so it enables
the write watch, and dbus-python turns every enable/disable into a GSource
add/remove while the main loop is dispatching those same sources.

    ATTACHED=1 python3 tests/manual_dbus_thread_stress.py   # racy, may abort
    ATTACHED=0 python3 tests/manual_dbus_thread_stress.py   # no GSources, safe

A hit looks like this, and takes the whole process down with SIGABRT:

    dbus[3]: arguments to dbus_watch_handle() were incorrect, assertion
    "watch != NULL" failed in file ../dbus/dbus-watch.c line 738.

For a quicker check that the app cannot reach that code path at all, confirm
_dbus_glib_bindings is absent from its address space:

    grep -c _dbus_glib_bindings /proc/<pid>/maps
"""
import os
import threading

import dbus
from dbus.mainloop.glib import DBusGMainLoop

ATTACHED = os.environ.get("ATTACHED", "1") == "1"

if ATTACHED:
    DBusGMainLoop(set_as_default=True)

from gi.repository import GLib

bus = dbus.SessionBus()

stop = threading.Event()
blocking = [0]
async_done = [0]

dbus_obj = bus.get_object("org.freedesktop.DBus", "/org/freedesktop/DBus")
dbus_iface = dbus.Interface(dbus_obj, "org.freedesktop.DBus")

# Big enough that it takes several write() calls to flush.
PAYLOAD = "x" * int(os.environ.get("PAYLOAD", str(256 * 1024)))

if ATTACHED:
    # Catch-all match keeps the read watch hot too.
    bus.add_signal_receiver(lambda *args, **kwargs: None)


def on_done(*_args):
    async_done[0] += 1


def pump_async():
    """Async calls from the main thread, so the main loop owns the watches."""
    if stop.is_set():
        return False
    for _ in range(16):
        try:
            dbus_iface.GetNameOwner(PAYLOAD, reply_handler=on_done, error_handler=on_done)
        except Exception:
            pass
    return True


def sender_thread():
    """Blocking calls off the main thread, like the deck tick threads."""
    while not stop.is_set():
        try:
            dbus_iface.GetNameOwner(PAYLOAD)
        except Exception:
            pass
        blocking[0] += 1


workers = int(os.environ.get("WORKERS", "12"))
duration = int(os.environ.get("DURATION", "300"))

for _ in range(workers):
    threading.Thread(target=sender_thread, daemon=True).start()

loop = GLib.MainLoop()


def finish():
    stop.set()
    loop.quit()
    return False


if ATTACHED:
    GLib.idle_add(pump_async)
GLib.timeout_add_seconds(duration, finish)
loop.run()

print(f"survived  ATTACHED={int(ATTACHED)}  blocking={blocking[0]} async={async_done[0]}")

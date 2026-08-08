"""Bootstrap shim: install the TouchyDeck enumerate hook, then run main.py.

Imported (not executed directly) by the `streamcontroller-run` Justfile
recipe via ``python -c "import touchy_bootstrap; touchy_bootstrap.main()"``.

Honours these environment variables:

* ``TOUCHY_SIM=1`` — also call ``create_sim_device(...)`` so a simulated
  TouchyDeck appears in StreamController's device list.
* ``TOUCHY_SIM_HEADLESS=1`` — pair with TOUCHY_SIM to skip the PySide6
  SimWindow (useful when running headlessly / over SSH).
* ``TOUCHY_SIM_SERIAL`` — override the sim's pseudo-serial.

Must run *before* StreamController's main.py imports ``DeviceManager``;
the monkey-patch attaches to the class, not to a particular instance,
so any later ``from StreamDeck.DeviceManager import DeviceManager`` call
inherits the patched ``enumerate``.
"""

from __future__ import annotations

import logging
import os
import runpy
import sys
from pathlib import Path

_LOG = logging.getLogger("touchy_bootstrap")


def _install_touchydeck() -> None:
    """Apply the TouchyDeck enumerate monkey-patch. Logs and re-raises on failure."""
    from touchy_pad.touchydeck import install

    install()
    _LOG.info("touchy_bootstrap: TouchyDeck enumerate hook installed")


def _maybe_create_sim() -> None:
    """If ``TOUCHY_SIM=1``, spin up an in-process simulated Touchy device."""
    if os.environ.get("TOUCHY_SIM", "") not in ("1", "true", "yes"):
        return
    headless = os.environ.get("TOUCHY_SIM_HEADLESS", "") in ("1", "true", "yes")
    serial = os.environ.get("TOUCHY_SIM_SERIAL", "SIM0000")

    from touchy_pad.api import create_sim_device

    sim = create_sim_device(headless=headless, serial=serial)
    _LOG.info(
        "touchy_bootstrap: sim device created (serial=%s, headless=%s)",
        sim.serial,
        headless,
    )

    # When not headless, also create the PySide6 SimWindow so the user
    # can see/click the simulated screen. We run Qt on a background
    # thread so StreamController's GLib mainloop keeps the main thread.
    if not headless:
        _start_sim_window_thread(sim)


def _start_sim_window_thread(sim) -> None:
    """Open a SimWindow on a daemon thread so Qt doesn't fight GLib for the main loop."""
    import threading

    def _run() -> None:
        try:
            from PySide6.QtWidgets import QApplication

            from touchy_pad.sim.window import SimWindow

            app = QApplication.instance() or QApplication([])
            window = SimWindow(sim)
            window.show()
            app.exec()
        except Exception:
            _LOG.exception("touchy_bootstrap: SimWindow thread crashed")

    t = threading.Thread(target=_run, name="touchy-sim-window", daemon=True)
    t.start()


def main() -> None:
    logging.basicConfig(level=logging.DEBUG) # I want to see extra touchy debug logs
    logging.getLogger("touchy_pad.client.rpc").setLevel(logging.INFO) # but not the RPC - too chatty
    _install_touchydeck()
    _maybe_create_sim()

    # Hand control to StreamController's real entry point. runpy keeps
    # __name__ == "__main__" semantics so its `if __name__ == "__main__"`
    # guards still fire.
    main_py = Path(__file__).with_name("main.py")
    sys.argv[0] = str(main_py)
    runpy.run_path(str(main_py), run_name="__main__")


if __name__ == "__main__":
    main()

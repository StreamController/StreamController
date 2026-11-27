"""
Manual repro for the memory leak on deck disconnect/reconnect.
Not part of the automated suite: it needs a data dir with a page to load.

    python3 tests/manual_deck_reconnect_leak.py --data data [--page Home] [--cycles 10]

Every reconnect of a deck (USB hiccup, a dock or monitor hub dropping out,
replugging it) goes through DeckManager.remove_controller() and then builds a
new DeckController. Before the fix the old controller was never freed:

  * @lru_cache on DeckController methods kept every instance in a class-wide cache
  * PageManagerBackend.pages kept its cached pages, keyed by the controller
  * delete() wiped the active page's actions without on_removed_from_cache(), so
    e.g. each CPU/RAM graph of the OS plugin left its worker process running
  * SignalManager callbacks and GenerativeUI GObject handlers pinned the actions

With a page holding three graph actions that was ~500 MB and three orphaned
processes per reconnect. A pass prints a flat line: no controllers and no child
processes left behind, whatever the cycle count.
"""
import argparse
import gc
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

parser = argparse.ArgumentParser()
parser.add_argument("--data", required=True)
parser.add_argument("--page", default=None, help="page name to load, default: the first one")
parser.add_argument("--cycles", type=int, default=10)
args = parser.parse_args()
# globals.py parses argv itself on import
sys.argv = [sys.argv[0], "--data", args.data]

import globals as gl
from gi.repository import GLib

from locales.LocaleManager import LocaleManager
from src.backend.MediaManager import MediaManager
from src.backend.PageManagement.PageManagerBackend import PageManagerBackend
from src.backend.PluginManager.PluginManager import PluginManager
from src.backend.SettingsManager import SettingsManager
from src.Signals.SignalManager import SignalManager


class StubDeckManager:
    """Only the parts DeckController touches on this path."""
    beta_resume_mode = False

    def __init__(self):
        self.deck_controller = []
        self.fake_deck_controller = []


def build_globals() -> None:
    main_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    gl.lm = LocaleManager(csv_path=os.path.join(main_path, "locales", "locales.csv"))
    gl.lm.set_to_os_default()
    gl.lm.set_fallback_language("en_US")

    gl.settings_manager = SettingsManager()
    gl.signal_manager = SignalManager()
    gl.media_manager = MediaManager()
    gl.page_manager = PageManagerBackend(gl.settings_manager)
    gl.plugin_manager = PluginManager()
    gl.plugin_manager.load_plugins()
    gl.plugin_manager.generate_action_index()


def child_pids() -> list[int]:
    me = str(os.getpid())
    pids = []
    for pid in filter(str.isdigit, os.listdir("/proc")):
        try:
            with open(f"/proc/{pid}/stat") as f:
                fields = f.read().rsplit(")", 1)[1].split()
        except OSError:
            continue
        # Exited workers that are only waiting to be reaped do not count
        if fields[1] == me and fields[0] != "Z":
            pids.append(int(pid))
    return pids


def settle() -> None:
    """Run what the GTK main loop would have run by now, then collect."""
    context = GLib.MainContext.default()
    while context.iteration(False):
        pass
    gc.collect()


def main() -> int:
    build_globals()

    # Imported after the globals exist, since the module reads them at class creation
    from src.backend.DeckManagement.DeckController import DeckController
    from src.backend.DeckManagement.Subclasses.FakeDeck import FakeDeck

    pages = gl.page_manager.get_pages()
    if args.page:
        pages = [p for p in pages if os.path.splitext(os.path.basename(p))[0] == args.page]
    if not pages:
        print(f"No matching page in {gl.DATA_PATH} - point --data at a real data dir")
        return 2

    deck_manager = StubDeckManager()
    for cycle in range(1, args.cycles + 1):
        controller = DeckController(deck_manager, FakeDeck(serial_number="fake-deck-leak"))
        deck_manager.deck_controller.append(controller)
        controller.load_page(gl.page_manager.get_page(pages[0], controller))
        time.sleep(1)

        # What DeckManager.remove_controller() does, minus the GTK page removal
        deck_manager.deck_controller.remove(controller)
        controller.delete()
        if controller.deck.is_open():
            controller.deck.close()
        del controller

        time.sleep(1.5)
        settle()
        n_controllers = sum(1 for o in gc.get_objects() if isinstance(o, DeckController))
        n_children = len(child_pids())
        print(f"cycle {cycle:3d}: live DeckControllers={n_controllers} live child processes={n_children}", flush=True)

    leaked = n_controllers > 0 or n_children > 0
    print("LEAK" if leaked else "OK")
    # Plugin backends and the deck reader are not daemon threads
    os._exit(1 if leaked else 0)


if __name__ == "__main__":
    main()

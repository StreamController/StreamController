"""
Manual repro for the screen saver / lock screen input swap race (issue #535).
Not part of the automated suite: it needs a data dir with at least one page and
it depends on winning a race, so a clean run is not proof of much on its own.

    python3 tests/manual_screensaver_race.py --data data

ScreenSaver.show() replaces DeckController.inputs while MediaPlayerThread.run()
and tick_actions() are reading it without a lock. Before the fix, filling the
dict one input type at a time let those threads see it without the type they
were about to index, and since neither loop caught exceptions, the KeyError
ended the thread for good - the deck stays frozen until the app is restarted,
which is what a resume from the lock screen looks like from the outside.

A hit looks like this, printed by threading.excepthook:

    File ".../DeckController.py", line 357, in run
        for dial in self.deck_controller.inputs[Input.Dial]:
    KeyError: <class '...InputIdentifier.Input.Dial'>

It took ~50-90 lock/unlock cycles here before the fix and survived 683 after.
"""
import os
import sys
import threading
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import globals as gl

from locales.LocaleManager import LocaleManager
from src.backend.MediaManager import MediaManager
from src.backend.PageManagement.PageManagerBackend import PageManagerBackend
from src.backend.PluginManager.PluginManager import PluginManager
from src.backend.SettingsManager import SettingsManager
from src.Signals.SignalManager import SignalManager

CYCLES = 2000
TIME_BUDGET = 120


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
    gl.plugin_manager.generate_action_index()


def main() -> int:
    build_globals()

    # Imported after the globals exist, since the module reads them at class creation
    from src.backend.DeckManagement.DeckController import DeckController
    from src.backend.DeckManagement.Subclasses.FakeDeck import FakeDeck

    pages = gl.page_manager.get_pages()
    if not pages:
        print(f"No pages in {gl.DATA_PATH}, nothing to load - point --data at a real data dir")
        return 2

    deck_manager = StubDeckManager()
    controller = DeckController(deck_manager, FakeDeck(serial_number="fake-deck-race"))
    deck_manager.deck_controller.append(controller)
    controller.load_page(gl.page_manager.get_page(pages[0], controller))
    time.sleep(2)

    # Model a page with animated content (a scrolling label or an animated icon),
    # which is what puts the media player on the branch that indexes the inputs
    type(controller.media_player)._needs_key_ticks = lambda self: True

    dead_threads = []
    threading.excepthook = lambda args: dead_threads.append((args.thread.name, "".join(
        traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback))))

    screen_saver = controller.screen_saver
    screen_saver.enable = True

    start = time.time()
    for cycle in range(CYCLES):
        screen_saver.show()   # lock
        screen_saver.hide()   # unlock
        if not controller.media_player.is_alive() or not controller.tick_thread.is_alive():
            break
        if time.time() - start > TIME_BUDGET:
            print(f"Survived {cycle + 1} lock/unlock cycles")
            break

    time.sleep(1)
    for name, tb in dead_threads:
        print(f"--- {name} died ---\n{tb}")
    print(f"media player alive: {controller.media_player.is_alive()}")
    print(f"tick thread alive:  {controller.tick_thread.is_alive()}")

    # The threads are daemons, but the deck reader and plugin backends are not
    os._exit(1 if dead_threads else 0)


if __name__ == "__main__":
    main()

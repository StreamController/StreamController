# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Scope of changes

Implement what was asked in the least intrusive way possible. A small request means a small diff — no drive-by refactors, no renaming, no restructuring surrounding code, no "while I was in there" cleanups. Touch the lines that have to change and leave the rest alone, even if the existing code is not how you would have written it.

If a larger change genuinely makes sense (the small fix would paper over a real problem, or the same bug exists in five other places), say so and ask whether the bigger edit is wanted — then do the small version unless the answer is yes.

## What this is

StreamController is a GTK4/libadwaita desktop app (Python 3.14) that drives Elgato Stream Deck hardware on Linux. It ships primarily as a Flatpak (`com.core447.StreamController`) and has a plugin system where third-party plugins are downloaded from a store into the user's data dir and loaded at runtime.

## Commands

Run the app for development (matches `.vscode/launch.json`):

```sh
python3 main.py --devel --data data --close-running
```

- `--devel` disables auto-update of store assets and forces the default data path logic to be skipped.
- `--data <dir>` points the data dir at the repo-local `data/` folder instead of `~/.var/app/com.core447.StreamController/data`.
- `--close-running` quits an already-running instance over D-Bus instead of just re-focusing it (without it, a second launch activates `reopen` on the existing instance and exits).
- Other useful flags: `--skip-load-hardware-decks`, `--daemon-only`, `-b` (start in background), `--list-devices`, `--list-pages`, `--list-actions PAGE COORDS STATE`, `--change-page SERIAL PAGE`, `--change-state SERIAL PAGE COORDS STATE`, `--emulate-input press|long-press SERIAL PAGE COORDS`, plus the page/label/icon/state/brightness get/set flags (`--set-icon PAGE COORDS STATE PATH` & co, `--json` for machine-readable reads).

Tests (stdlib `unittest`, no pytest config in the repo):

```sh
python3 -m unittest discover -s tests -t .      # all tests
python3 -m unittest tests.test_dbus_mainloop    # single module
```

Flatpak build:

```sh
git submodule update --init   # needed if flatpak/shared-modules is empty
flatpak-builder --repo=repo --force-clean --install --user build-dir com.core447.StreamController.yml
bash flatpak/install.sh --repo=current --branch=<branch>   # build the local checkout as a flatpak
```

Releasing a version: bump `app_version` and `release_notes` in `globals.py`, then run `python3 scripts/update_metainfo.py` to regenerate `flatpak/com.core447.StreamController.metainfo.xml` from them. The flatpak manifest's `StreamController` module pins a git `tag` that also needs updating.

There is no linter or formatter configured.

## Hard constraints (violating these causes crashes that have already been fixed once)

**GTK/Adw widget calls must happen on the main thread.** The app runs many background threads (per-deck `tick_actions`, `MediaPlayerThread`, udev/USB callbacks, store update threads, plugin RPyC threads, `threading.Timer`s). Any widget mutation from those must go through `GLib.idle_add`. Symptom of getting this wrong is a silent SIGSEGV with no Python traceback.

**dbus-python must never be attached to a GLib main loop.** `dbus-gmain` is not thread safe and the app calls D-Bus from tick threads, so an attached connection produces random `SIGABRT` in `dbus_watch_handle`. dbus-python is only used for blocking method calls (see `quit_running()` / `make_api_calls()` in `main.py`). Anything needing signals, async replies, or exported objects must use GDBus (`gi.repository.Gio`) or dasbus. `tests/test_dbus_mainloop.py` greps the tree for the forbidden APIs and fails the build if they reappear.

**Writes to user data go through `src/backend/Utils/AtomicSaveUtils.py`** (`atomic_write` / `atomic_save_json`), so a crash mid-write cannot truncate pages or settings.

## Architecture

### Global singletons

`globals.py` (imported everywhere as `import globals as gl`) is the service locator: `gl.deck_manager`, `gl.page_manager`, `gl.plugin_manager`, `gl.settings_manager`, `gl.media_manager`, `gl.signal_manager`, `gl.app`, etc. They are all `None` until `create_global_objects()` in `main.py` fills them in — that function defines the real startup order, and anything constructed earlier cannot rely on them. `globals.py` also owns the `argparser` object (built by `build_argparser()` in `src/CLI.py`), `DATA_PATH`/`PLUGIN_DIR` resolution, and `app_version`.

`main.py` bootstraps in this order: **CLI fast path** → patcher → listing CLI commands (which exit early without full init) → buffering of `--change-page`/`--change-state`/`--emulate-input` for the instance about to start → offline page-editing commands → single-instance check over D-Bus → USB reset → logging → migrations → `create_global_objects()` → autostart → `load()` (creates `DeckManager`, loads decks, starts the `Adw.Application`).

### CLI

`src/CLI.py` holds the argparser and `run_against_running_instance()`, which `main.py` calls **before any other import**. Importing main.py costs ~2.4s (GTK, deck/plugin/store backends, and matplotlib/cairosvg via `globals` → `HelperMethods`), which used to dominate every CLI invocation. When an instance is already running, the fast path answers the command over the DBus API in `src/api.py` in ~80ms and exits; anything it cannot handle (no instance, `--close-running`, macOS, `--list-*`) returns False and main.py takes over, editing the page json directly through `HeadlessPageOps`. Keep `src/CLI.py` free of heavy imports — that is the whole point of the file.

### Deck layer

`src/backend/DeckManagement/`:
- `DeckManager` enumerates hardware decks (via `streamcontroller-streamdeck`), fake decks, and remote decks; handles hotplug (udev / usb-monitor), suspend/resume, and flatpak disconnect quirks.
- `DeckController` (~3.7k lines, the core of the app) owns one deck: its `Background`, `ScreenSaver`, brightness, rotation (`RotatedDeck`), the `MediaPlayerThread` render queue, and a `tick_actions` thread that calls `on_tick` on every action.
- Inputs are modeled as `ControllerInput` subclasses (`ControllerKey`, `ControllerDial`, `ControllerTouchScreen`), each holding a list of `ControllerInputState` objects (one per configured state). Rendering composes `Background` + `SingleKeyAsset` (image/video/GIF) + `LabelManager` labels through `LayoutManager`.

`InputIdentifier.py` is the addressing scheme used by everything else: `Input.Key`/`Input.Dial`/`Input.Touchscreen`, each with a `json_identifier` (`"0x0"` for keys) and an `Events` enum (`DOWN`, `UP`, `SHORT_UP`, `HOLD_START`, …). Page JSON is keyed by `input_type` → `json_identifier` → `states` → `actions`.

### Pages

`src/backend/PageManagement/`. A `Page` wraps one JSON file in `<data>/pages/`. `page.dict` is the serialized config; `load_action_objects()` instantiates live `ActionCore` objects from the `id` strings (`"<plugin_id>::<ActionName>"`). Several `DeckController`s can have separate `Page` objects backed by the same JSON file — `get_pages_with_same_json()` / `reload_similar_pages()` exist to keep them in sync. `PageManagerBackend` handles page discovery, per-deck default pages, backups, and auto page switching driven by `WindowGrabber`.

### Plugins

`src/backend/PluginManager/`:
- `PluginBase` is subclassed by every plugin's `main.py`. It registers `ActionHolder`s, owns plugin settings/assets/locales, and can spawn a **backend**: a separate Python process (optionally in its own venv, recreated automatically when the system Python version changes) connected over RPyC. Both `PluginBase` and `ActionCore` are `rpyc.Service`s and queue events while a backend connection is pending.
- `ActionHolder` is the uninstantiated descriptor (name, id, icon, `min_app_version`, per-input-type `ActionInputSupport`); `ActionCore` is the live instance bound to a `DeckController` + `Page` + input + state. `ActionBase` is a deprecated `ActionCore` subclass kept for older plugins — it pre-registers the legacy `on_key_down`-style event assigners.
- Events reach actions through `EventAssigner`/`EventManager`: an action declares named assigners, and the page config maps `InputEvent`s to them, so users can rebind which physical event triggers which action callback.
- `PluginManager.load_plugins()` imports plugin folders from `gl.PLUGIN_DIR` and builds `action_index`. In `--daemon-only` mode only plugins referenced by the active pages are loaded.

`GtkHelper/GenerativeUI/` is the declarative settings-widget layer plugins use (`SwitchRow`, `ComboRow`, `ScaleRow`, …): each widget is bound to a settings key on an `ActionCore` and persists itself automatically.

### UI

`src/app.py` is the `Adw.Application`. It also exposes the `org.gtk.Actions` entry points (`quit`, `reopen`, `change_page`, `change_state`, `trigger_action`) that the CLI flags call into on an already-running instance. `src/windows/mainWindow/` holds the deck view (`DeckStack` → `DeckStackChild` → `KeyGrid`, plus `DeckPlus`/`DeckNeo` variants) and the right-hand `Sidebar` where action settings are edited. Other windows: Store, AssetManager, Settings, PageManager, Onboarding, Permissions.

### Cross-cutting

- `src/Signals/` is a small app-wide pub/sub (`PageRename`, `ChangePage`, `PluginInstall`, `AppQuit`, …). `SignalManager.trigger_signal()` dispatches via `GLib.idle_add` for everything except `AppQuit`, which runs synchronously.
- `src/api.py` exposes the dasbus/GDBus API at `com.core447.StreamController` for external tools (controllers, pages, active window, icon packs).
- `src/backend/Store/StoreBackend.py` talks to the plugin/icon/wallpaper store (GitHub-hosted), with `StoreCache` for offline use.
- `src/backend/Migration/` runs versioned migrators over the data dir at startup; add a new `Migrator_x_y_z` and register it in `main()` when the on-disk format changes.
- Localization: `locales/locales.csv` (semicolon-separated, `key;de_DE;en_US;…`) via `LocaleManager`; plugins may use the older per-folder JSON `LegacyLocaleManager`.
- Logging is loguru (`from loguru import logger as log`), with `@log.catch` on top-level entry points and a separate `gl.loggers["plugins"]` sink for plugin output.

## Conventions

- Commit subjects follow `Feat: …`, `Fix: …`, `Fix(Component): …` (go-semantic-release consumes them).
- Data path layout: `<data>/pages/`, `plugins/`, `settings/`, `Assets/`, `cache/`, `logs/`, `wallpapers/`, `icons/` (store icon packs), `custom_icons/` (locally created packs, see `src/backend/IconPackManagement/CustomIconPack.py`), `sticky/` (one hidden page per deck serial holding its sticky actions).
- macOS is partially supported: `gl.IS_MAC` guards all D-Bus usage.

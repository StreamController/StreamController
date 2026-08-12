"""
Author: Core447
Year: 2026

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This programm comes with ABSOLUTELY NO WARRANTY!

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
"""
Link between a page on disk and the store entry it was installed from.

A page installed from the store carries a "store" block in its json:

    "store": {
        "id": "com_core447_MediaPlugin_NowPlaying",
        "url": "https://github.com/StreamController/MediaPlugin",
        "path": "store-pages/now-playing.scpage",
        "commit": "f4be6cb..."
    }

That is what lets the store show whether a page is installed and whether a newer
commit is available. It travels with the page json instead of living in a separate
index, so renaming or duplicating a page in the page manager cannot break the link.
"""
import os

from loguru import logger as log

import globals as gl

STORE_KEY = "store"


def get_store_origin(page_path: str) -> dict | None:
    """Returns the store block of the page, None if it was not installed from the store."""
    if page_path is None or not os.path.isfile(page_path):
        return None

    origin = gl.page_manager.get_page_data(page_path, use_backup=False).get(STORE_KEY)
    if not isinstance(origin, dict) or not origin.get("id"):
        return None
    return origin


def set_store_origin(page_path: str, page_id: str, url: str, path: str, commit: str) -> None:
    """Marks the page as installed from the given store entry."""
    page_dict = gl.page_manager.get_page_data(page_path, use_backup=False)
    page_dict[STORE_KEY] = {
        "id": page_id,
        "url": url,
        "path": path,
        "commit": commit
    }

    # Nothing the deck renders changed, so there is no reason to reload the page
    gl.page_manager.set_page_data(page_path, page_dict,
                                  reload_brightness=False, reload_screensaver=False,
                                  reload_background=False, reload_inputs=False)

    log.info(f"Marked {os.path.basename(page_path)} as installed from the store")


def find_installed_page(page_id: str) -> str | None:
    """Returns the path of the page installed for the given store id, None if there is none."""
    if page_id in (None, ""):
        return None

    for page_path in gl.page_manager.get_pages(add_custom_pages=False):
        origin = get_store_origin(page_path)
        if origin is not None and origin.get("id") == page_id:
            return page_path

    return None


def get_installed_commits() -> dict[str, str]:
    """
    Returns {store id: installed commit} for every page that came from the store.
    Scanned in one go so the store does not have to read every page for every entry.
    """
    commits: dict[str, str] = {}

    for page_path in gl.page_manager.get_pages(add_custom_pages=False):
        origin = get_store_origin(page_path)
        if origin is not None:
            commits[origin["id"]] = origin.get("commit")

    return commits


def unique_page_name(name: str) -> str:
    """Returns a page name that is not taken yet, so an install never overwrites a page."""
    existing = gl.page_manager.get_page_names()
    if name not in existing:
        return name

    index = 1
    while f"{name} ({index})" in existing:
        index += 1

    return f"{name} ({index})"

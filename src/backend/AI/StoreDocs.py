"""
Fetches `actions.json` from the store's plugin repos.

The point of putting that file at a plugin's repo root is that it can be read without
installing the plugin. This module walks the store's plugin list, grabs whatever
`actions.json` files exist and caches them, so the assistant knows what an action does
even when the user does not have it - and can tell them which plugin to install.

Kicked off the first time the assistant is opened in a session, on a worker thread. The
cache only lives in memory, so a restart always picks up store changes.
"""

import threading
from concurrent.futures import ThreadPoolExecutor

import requests
from loguru import logger as log

STORE_PLUGIN_LIST_URL = "https://raw.githubusercontent.com/StreamController/StreamController-Store/main/Plugins.json"
BRANCHES = ("main", "master")
REQUEST_TIMEOUT = 10
MAX_WORKERS = 12

_cache: dict | None = None
_cache_lock = threading.Lock()


def load_cache() -> dict | None:
    with _cache_lock:
        return _cache


def save_cache(data: dict) -> None:
    global _cache
    with _cache_lock:
        _cache = data


def _raw_url(repo_url: str, branch: str, file_name: str) -> str:
    owner_repo = repo_url.rstrip("/").removeprefix("https://github.com/").removesuffix(".git")
    return f"https://raw.githubusercontent.com/{owner_repo}/{branch}/{file_name}"


def _fetch_json(repo_url: str, file_name: str) -> dict | None:
    """Tries the usual default branches; a 404 just means the plugin has no such file."""
    for branch in BRANCHES:
        try:
            response = requests.get(_raw_url(repo_url, branch, file_name), timeout=REQUEST_TIMEOUT)
        except requests.exceptions.RequestException:
            return None

        if response.status_code == 404:
            continue
        if response.status_code >= 400:
            return None

        try:
            return response.json()
        except ValueError:
            return None

    return None


def fetch_plugin_list() -> list[str]:
    try:
        response = requests.get(STORE_PLUGIN_LIST_URL, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return [entry["url"] for entry in response.json() if entry.get("url")]
    except (requests.exceptions.RequestException, ValueError, KeyError, TypeError) as e:
        log.warning(f"Could not fetch the store plugin list: {e}")
        return []


def _fetch_one(repo_url: str) -> tuple[str, dict] | None:
    docs = _fetch_json(repo_url, "actions.json")
    if not docs or not isinstance(docs, dict):
        return None

    plugin_id = docs.get("plugin", {}).get("id") if isinstance(docs.get("plugin"), dict) else None

    if not plugin_id:
        # Action keys may already carry the full id
        for key in (docs.get("actions") or {}):
            if "::" in key:
                plugin_id = key.split("::")[0]
                break

    if not plugin_id:
        # Last resort: the manifest, which every plugin has
        manifest = _fetch_json(repo_url, "manifest.json") or {}
        plugin_id = manifest.get("id")

    if not plugin_id:
        return None

    docs["repository"] = repo_url
    return plugin_id, docs


def fetch_all(force: bool = False) -> dict:
    """
    Returns {plugin_id: actions.json}. Blocking - call from a worker thread.

    Uses this session's cached copy unless `force` is set.
    """
    if not force:
        cached = load_cache()
        if cached is not None:
            return cached

    repo_urls = fetch_plugin_list()
    if not repo_urls:
        return load_cache() or {}

    results: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        for result in pool.map(_fetch_one, repo_urls):
            if result:
                plugin_id, docs = result
                results[plugin_id] = docs

    log.info(f"Fetched actions.json from {len(results)} of {len(repo_urls)} store plugins")
    save_cache(results)
    return results

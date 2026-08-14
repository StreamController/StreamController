"""
Installs a store plugin the assistant needs.

The assistant can see actions from plugins the user has not installed (their actions.json
is fetched from GitHub, see StoreDocs.py). When its answer needs one of them, this puts
it on disk - through the normal store install path, so the plugin gets its pinned commit,
its requirements and its place in the plugin manager exactly like a store install.

Never called without the user pressing the install button first: this downloads and then
runs third party code.
"""

import asyncio

import requests
from loguru import logger as log

import globals as gl
from src.backend.AI.StoreDocs import STORE_PLUGIN_LIST_URL, REQUEST_TIMEOUT


class InstallError(Exception):
    """Anything the user needs to see in the chat."""
    pass


def get_store_entry(plugin_id: str) -> dict | None:
    """
    The store's entry (url + pinned commit) for a plugin id.

    The store list is keyed by repository url, so we match it against the repository we
    recorded while fetching that plugin's actions.json.
    """
    registry = gl.action_doc_registry
    if registry is None:
        return None

    repository = (registry.store_plugins.get(plugin_id, {}) or {}).get("repository", "")
    if not repository:
        return None

    try:
        response = requests.get(STORE_PLUGIN_LIST_URL, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        entries = response.json()
    except (requests.exceptions.RequestException, ValueError) as e:
        raise InstallError(f"Could not reach the store: {e}") from e

    wanted = repository.rstrip("/").removesuffix(".git").lower()
    for entry in entries:
        if str(entry.get("url", "")).rstrip("/").removesuffix(".git").lower() == wanted:
            return {"url": entry["url"], "commit_sha": entry.get("hash")}

    return None


def is_installed(plugin_id: str) -> bool:
    if gl.plugin_manager is None:
        return False
    return plugin_id in gl.plugin_manager.get_plugins()


def describe(plugin_id: str) -> str:
    """What the user is agreeing to, for the confirmation button."""
    plugin_doc = (gl.action_doc_registry.store_plugins.get(plugin_id, {})
                  if gl.action_doc_registry else {})
    repository = plugin_doc.get("repository", "")
    return f"{plugin_id} ({repository})" if repository else plugin_id


def install(plugin_id: str) -> None:
    """
    Blocking - call from a worker thread. Raises InstallError with a message for the chat.
    """
    if is_installed(plugin_id):
        return

    if gl.store_backend is None:
        raise InstallError("The store is not available, so plugins cannot be installed right now.")

    entry = get_store_entry(plugin_id)
    if entry is None:
        raise InstallError(f"{plugin_id} is not in the store, so it cannot be installed automatically.")

    from src.windows.Store.StoreData import PluginData

    plugin_data = PluginData(
        plugin_id=plugin_id,
        github=entry["url"],
        commit_sha=entry.get("commit_sha"),
    )

    log.info(f"AI assistant: installing {plugin_id} from {entry['url']}")

    try:
        result = asyncio.run(gl.store_backend.install_plugin(plugin_data))
    except Exception as e:
        log.error(f"AI assistant: installing {plugin_id} failed: {e}")
        raise InstallError(f"Installing {plugin_id} failed: {e}") from e

    if result == 404:
        raise InstallError(f"Could not download {plugin_id} from {entry['url']}.")

    if not is_installed(plugin_id):
        raise InstallError(f"{plugin_id} was downloaded but did not load. "
                           "It may need a newer StreamController.")

    log.success(f"AI assistant: installed {plugin_id}")

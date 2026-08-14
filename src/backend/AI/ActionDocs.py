"""
Reads the `actions.json` a plugin ships in its repo root.

A plugin's settings keys are not discoverable from its code - `get_config_rows()` builds
arbitrary widgets and writes whatever keys it likes. So a plugin describes itself in one
file next to its manifest, and the AI assistant reads that instead of guessing.

Format (every field optional except the action keys themselves):

    {
      "plugin": {
        "description": "Control OBS Studio from your deck.",
        "requirements": "OBS with obs-websocket 5 enabled."
      },
      "actions": {
        "RunCommand": {
          "description": "Runs a shell command.",
          "requirements": "The command has to exist on the host.",
          "settings": {
            "command": {
              "type": "string",
              "required": true,
              "description": "What to run.",
              "example": "firefox"
            },
            "detached": {"type": "boolean", "default": true}
          }
        }
      }
    }

Action keys may be the bare suffix ("RunCommand") or the full id
("com_core447_OSPlugin::RunCommand").

Because the file sits at the repo root next to manifest.json it can also be fetched from
the store without installing the plugin, which is what lets the assistant know about
actions the user does not have yet.
"""

import json
import os

from loguru import logger as log

import globals as gl

DOCS_FILE_NAME = "actions.json"


class ActionDoc:
    """What one action says about itself."""

    def __init__(self, action_id: str, data: dict, plugin_id: str = "", plugin_doc: dict = None):
        self.action_id = action_id
        self.plugin_id = plugin_id
        self.description: str = data.get("description", "")
        self.requirements: str = data.get("requirements", "")
        self.settings: dict = data.get("settings", {}) or {}
        self.plugin_doc: dict = plugin_doc or {}

    def render(self) -> str:
        """The lines that go into the catalog handed to the model."""
        lines: list[str] = []

        if self.description:
            lines.append(f"      what it does: {self.description}")

        requirements = self.requirements or self.plugin_doc.get("requirements", "")
        if requirements:
            lines.append(f"      requires: {requirements}")

        if self.settings:
            lines.append("      settings:")
            for key, spec in self.settings.items():
                lines.append("        " + _render_setting(key, spec))

        return "\n".join(lines)


def _render_setting(key: str, spec) -> str:
    if not isinstance(spec, dict):
        return f'"{key}": {spec}'

    parts = []
    if spec.get("type"):
        parts.append(str(spec["type"]))
    if spec.get("required"):
        parts.append("required")
    if "default" in spec:
        parts.append(f"default {json.dumps(spec['default'])}")
    if spec.get("values"):
        parts.append(f"one of {json.dumps(spec['values'])}")
    if spec.get("example") is not None:
        parts.append(f"e.g. {json.dumps(spec['example'])}")

    detail = ", ".join(parts)
    description = spec.get("description", "")

    return f'"{key}"' + (f" ({detail})" if detail else "") + (f": {description}" if description else "")


class ActionDocRegistry:
    """
    All the `actions.json` files we could find, keyed by action id.

    Loaded once at startup from the installed plugins; `reload()` picks up plugins that
    were installed while the app was running.
    """

    def __init__(self):
        self.docs: dict[str, ActionDoc] = {}
        self.plugin_docs: dict[str, dict] = {}
        self.loaded = False

        # Docs fetched from the store for plugins that are not installed
        self.store_docs: dict[str, ActionDoc] = {}
        self.store_plugins: dict[str, dict] = {}
        self.store_loaded = False

    def reload(self) -> None:
        self.docs.clear()
        self.plugin_docs.clear()

        plugin_dir = gl.PLUGIN_DIR
        if not plugin_dir or not os.path.isdir(plugin_dir):
            self.loaded = True
            return

        for folder in sorted(os.listdir(plugin_dir)):
            path = os.path.join(plugin_dir, folder, DOCS_FILE_NAME)
            if not os.path.isfile(path):
                continue

            try:
                with open(path, "r") as f:
                    data = json.load(f)
            except (OSError, json.JSONDecodeError) as e:
                log.warning(f"Could not read {path}: {e}")
                continue

            self.add_plugin_docs(self.get_plugin_id(plugin_dir, folder), data)

        self.loaded = True
        log.info(f"Loaded AI documentation for {len(self.docs)} actions "
                 f"from {len(self.plugin_docs)} plugins")

    @staticmethod
    def get_plugin_id(plugin_dir: str, folder: str) -> str:
        """The manifest wins over the folder name, matching PluginBase."""
        manifest_path = os.path.join(plugin_dir, folder, "manifest.json")
        try:
            with open(manifest_path, "r") as f:
                return json.load(f).get("id") or folder
        except (OSError, json.JSONDecodeError):
            return folder

    def add_plugin_docs(self, plugin_id: str, data: dict) -> None:
        plugin_doc = data.get("plugin", {}) or {}
        self.plugin_docs[plugin_id] = plugin_doc

        for key, action_data in (data.get("actions", {}) or {}).items():
            if not isinstance(action_data, dict):
                continue
            action_id = key if "::" in key else f"{plugin_id}::{key}"
            self.docs[action_id] = ActionDoc(action_id, action_data, plugin_id, plugin_doc)

    def get(self, action_id: str) -> ActionDoc | None:
        if not self.loaded:
            self.reload()
        return self.docs.get(action_id)

    def get_plugin_doc(self, plugin_id: str) -> dict:
        if not self.loaded:
            self.reload()
        return self.plugin_docs.get(plugin_id, {})

    # ------------------------------------------------------------------ #
    # Store side - plugins the user has not installed                    #
    # ------------------------------------------------------------------ #

    def load_store_docs(self, force: bool = False) -> None:
        """Blocking - call from a worker thread. Safe to call repeatedly."""
        from src.backend.AI.StoreDocs import fetch_all

        fetched = fetch_all(force=force)

        self.store_docs.clear()
        self.store_plugins.clear()

        for plugin_id, data in fetched.items():
            plugin_doc = data.get("plugin", {}) or {}
            plugin_doc["repository"] = data.get("repository", "")
            self.store_plugins[plugin_id] = plugin_doc

            for key, action_data in (data.get("actions", {}) or {}).items():
                if not isinstance(action_data, dict):
                    continue
                action_id = key if "::" in key else f"{plugin_id}::{key}"
                self.store_docs[action_id] = ActionDoc(action_id, action_data, plugin_id, plugin_doc)

        self.store_loaded = True

    def get_uninstalled(self, installed_plugin_ids: set[str]) -> dict[str, list[ActionDoc]]:
        """The store actions the user does not have, grouped by plugin id."""
        grouped: dict[str, list[ActionDoc]] = {}

        for action_id, doc in self.store_docs.items():
            if doc.plugin_id in installed_plugin_ids:
                continue
            grouped.setdefault(doc.plugin_id, []).append(doc)

        return grouped

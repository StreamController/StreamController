"""
Author: Core447
Year: 2025

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This programm comes with ABSOLUTELY NO WARRANTY!

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
"""
Self contained page bundles.

A bundle is a zip file that contains one or more pages together with every
asset they reference, so that it can be moved to another machine without
ending up with broken media paths.

Layout:
    manifest.json           - format, version, required plugins and asset metadata
    page.json               - the page (single page bundles only)
    pages/<name>.json       - the pages (multi page bundles only)
    assets/<sha256><ext>    - the referenced assets

Inside the bundle every media path is replaced by its "assets/..." archive name.
On import the paths are rewritten to point to local copies: assets belonging to
an installed icon/wallpaper pack are used from that pack, everything else is
added to the asset manager.

The manifest also lists the plugins and packs the pages need, so only those can
be installed from the store on import - never the whole setup of the exporting
machine.
"""
import asyncio
import copy
import json
import os
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime
from typing import Iterator

from loguru import logger as log

import globals as gl
from src.backend.DeckManagement.HelperMethods import sha256
from src.backend.DeckManagement.InputIdentifier import Input

BUNDLE_VERSION = 1

FORMAT_PAGE = "streamcontroller-page"
FORMAT_PAGES = "streamcontroller-pages"

PAGE_EXTENSION = ".scpage"
PAGES_EXTENSION = ".zip"

MANIFEST_NAME = "manifest.json"
SINGLE_PAGE_NAME = "page.json"
ASSET_DIR = "assets"
PAGE_DIR = "pages"

PACK_TYPE_ICONS = "icons"
PACK_TYPE_WALLPAPERS = "wallpapers"
PACK_TYPES = (PACK_TYPE_ICONS, PACK_TYPE_WALLPAPERS)


REQUIREMENT_TYPE_LABELS = {
    "plugin": "Plugin",
    PACK_TYPE_ICONS: "Icon pack",
    PACK_TYPE_WALLPAPERS: "Wallpaper pack"
}


@dataclass
class Requirement:
    """Something from the store a bundle needs to work."""
    type: str  # "plugin", "icons" or "wallpapers"
    id: str
    name: str | None = None

    @property
    def label(self) -> str:
        return self.name or self.id

    @property
    def type_label(self) -> str:
        return REQUIREMENT_TYPE_LABELS.get(self.type, self.type)


def _media_extensions() -> set[str]:
    return {ext.lower() for ext in gl.image_extensions + gl.video_extensions + gl.svg_extensions}


def _is_media_file(path) -> bool:
    if not isinstance(path, str) or path == "":
        return False
    if not os.path.isfile(path):
        return False
    return os.path.splitext(path)[1][1:].lower() in _media_extensions()


def _iter_string_refs(data, _depth: int = 0) -> Iterator[tuple]:
    """Yields (container, key) for every string value inside nested dicts/lists."""
    if _depth > 10:
        return
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, str):
                yield data, key
            else:
                yield from _iter_string_refs(value, _depth + 1)
    elif isinstance(data, list):
        for index, value in enumerate(data):
            if isinstance(value, str):
                yield data, index
            else:
                yield from _iter_string_refs(value, _depth + 1)


def iter_media_refs(page_dict: dict) -> Iterator[tuple]:
    """
    Yields (container, key) for every place in a page that can hold a media
    path. The caller decides which of them actually point to an asset.
    """
    settings = page_dict.get("settings") or {}
    for section in ("background", "screensaver"):
        section_settings = settings.get(section)
        if isinstance(section_settings, dict) and "media-path" in section_settings:
            yield section_settings, "media-path"

    for input_type in Input.KeyTypes:
        inputs = page_dict.get(input_type) or {}
        if not isinstance(inputs, dict):
            continue
        for input_dict in inputs.values():
            if not isinstance(input_dict, dict):
                continue
            states = input_dict.get("states") or {}
            if not isinstance(states, dict):
                continue
            for state_dict in states.values():
                if not isinstance(state_dict, dict):
                    continue

                media = state_dict.get("media")
                if isinstance(media, dict) and "path" in media:
                    yield media, "path"

                for action in state_dict.get("actions") or []:
                    if isinstance(action, dict):
                        # Plugins may store icon paths in their own settings
                        yield from _iter_string_refs(action.get("settings"))


def _get_asset_origin(path: str) -> dict | None:
    """
    Returns the store pack an asset belongs to, if it is part of one.
    Icon and wallpaper packs live in <data>/icons/<id> and <data>/wallpapers/<id>.
    """
    try:
        relative = os.path.relpath(os.path.abspath(path), os.path.abspath(gl.DATA_PATH))
    except ValueError:
        return None

    parts = relative.split(os.sep)
    if len(parts) < 3 or parts[0] not in PACK_TYPES:
        return None

    return {
        "type": parts[0],
        "id": parts[1],
        "name": _get_pack_name(os.path.join(gl.DATA_PATH, parts[0], parts[1])),
        # Relative to the data path so it can be resolved on the other machine
        "path": "/".join(parts)
    }


def _get_pack_name(pack_path: str) -> str | None:
    """Reads the display name of an icon/wallpaper pack from its manifest."""
    try:
        with open(os.path.join(pack_path, "manifest.json")) as f:
            return json.load(f).get("name")
    except (OSError, ValueError):
        return None


## Export

def _add_asset(zip_file: zipfile.ZipFile, assets: dict, path: str) -> str:
    """Adds the asset to the zip (if not already present) and returns its archive name."""
    file_hash = sha256(path)
    extension = os.path.splitext(path)[1].lower()
    archive_name = f"{ASSET_DIR}/{file_hash}{extension}"

    if archive_name not in assets:
        assets[archive_name] = {
            "name": os.path.basename(path),
            "sha256": file_hash,
            "origin": _get_asset_origin(path)
        }
        zip_file.write(path, archive_name)

    return archive_name


def _get_page_plugins(page_dict: dict) -> dict[str, dict]:
    """Returns {plugin id: {"name": ...}} for every plugin used by the page."""
    plugins: dict[str, dict] = {}

    for input_type in Input.KeyTypes:
        inputs = page_dict.get(input_type) or {}
        if not isinstance(inputs, dict):
            continue
        for input_dict in inputs.values():
            if not isinstance(input_dict, dict):
                continue
            for state_dict in (input_dict.get("states") or {}).values():
                if not isinstance(state_dict, dict):
                    continue
                for action in state_dict.get("actions") or []:
                    action_id = (action or {}).get("id")
                    if not isinstance(action_id, str) or "::" not in action_id:
                        continue
                    plugin_id = action_id.split("::", 1)[0]
                    if plugin_id in plugins:
                        continue

                    name = None
                    plugin = gl.plugin_manager.get_plugin_by_id(plugin_id) if gl.plugin_manager else None
                    if plugin is not None:
                        name = plugin.plugin_name
                    plugins[plugin_id] = {"name": name}

    return plugins


def _bundle_page(zip_file: zipfile.ZipFile, assets: dict, page_dict: dict) -> dict:
    """Returns a copy of the page with all media paths replaced by archive names."""
    page_dict = copy.deepcopy(page_dict)

    for container, key in iter_media_refs(page_dict):
        path = container[key]
        if not _is_media_file(path):
            continue
        try:
            container[key] = _add_asset(zip_file, assets, path)
        except OSError as e:
            log.warning(f"Failed to add asset {path} to bundle: {e}")

    return page_dict


def _write_bundle(dst_path: str, format: str, pages: dict[str, dict]) -> None:
    assets: dict = {}
    plugins: dict = {}

    with zipfile.ZipFile(dst_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
        bundled: dict[str, dict] = {}
        for name, page_dict in pages.items():
            bundled[name] = _bundle_page(zip_file, assets, page_dict)
            plugins.update(_get_page_plugins(page_dict))

        if format == FORMAT_PAGE:
            name, page_dict = next(iter(bundled.items()))
            zip_file.writestr(SINGLE_PAGE_NAME, json.dumps(page_dict, indent=4))
        else:
            for name, page_dict in bundled.items():
                zip_file.writestr(f"{PAGE_DIR}/{name}.json", json.dumps(page_dict, indent=4))

        manifest = {
            "format": format,
            "version": BUNDLE_VERSION,
            "app-version": gl.app_version,
            "created": datetime.now().isoformat(timespec="seconds"),
            "pages": list(bundled.keys()),
            "plugins": plugins,
            "assets": assets
        }
        zip_file.writestr(MANIFEST_NAME, json.dumps(manifest, indent=4))

    log.success(f"Exported {len(pages)} page(s) with {len(assets)} asset(s) to {dst_path}")


def export_page(page_path: str, dst_path: str) -> None:
    """Exports a single page including its assets as a .scpage bundle."""
    name = os.path.splitext(os.path.basename(page_path))[0]
    page_dict = gl.page_manager.get_page_data(page_path)

    _write_bundle(dst_path, FORMAT_PAGE, {name: page_dict})


def export_pages(page_paths: list[str], dst_path: str) -> None:
    """Exports all given pages including their assets as a zip bundle."""
    pages: dict[str, dict] = {}
    for page_path in page_paths:
        name = os.path.splitext(os.path.basename(page_path))[0]
        pages[name] = gl.page_manager.get_page_data(page_path)

    _write_bundle(dst_path, FORMAT_PAGES, pages)


## Import

def is_bundle(path: str) -> bool:
    return os.path.isfile(path) and zipfile.is_zipfile(path)


def read_manifest(path: str) -> dict | None:
    """Returns the manifest of a bundle without importing anything, None if it is no bundle."""
    if not is_bundle(path):
        return None
    try:
        with zipfile.ZipFile(path) as zip_file:
            manifest = json.loads(zip_file.read(MANIFEST_NAME))
    except (KeyError, ValueError, zipfile.BadZipFile, OSError):
        return None

    if manifest.get("format") not in (FORMAT_PAGE, FORMAT_PAGES):
        return None
    return manifest


def _is_pack_installed(pack_type: str, pack_id: str) -> bool:
    return os.path.isdir(os.path.join(gl.DATA_PATH, pack_type, pack_id))


def get_missing_requirements(manifest: dict) -> list[Requirement]:
    """
    Returns everything the bundle needs that is not installed yet, so the user
    can be asked before anything is downloaded from the store.
    """
    missing: list[Requirement] = []

    for plugin_id, plugin_info in (manifest.get("plugins") or {}).items():
        if gl.plugin_manager is not None and gl.plugin_manager.get_plugin_by_id(plugin_id) is not None:
            continue
        missing.append(Requirement("plugin", plugin_id, (plugin_info or {}).get("name")))

    seen: set[tuple[str, str]] = set()
    for asset_info in (manifest.get("assets") or {}).values():
        origin = (asset_info or {}).get("origin")
        if not isinstance(origin, dict):
            continue
        pack_type, pack_id = origin.get("type"), origin.get("id")
        if pack_type not in PACK_TYPES or not pack_id:
            continue
        if (pack_type, pack_id) in seen:
            continue
        seen.add((pack_type, pack_id))

        if not _is_pack_installed(pack_type, pack_id):
            missing.append(Requirement(pack_type, pack_id, origin.get("name")))

    return missing


def install_requirements(requirements: list[Requirement], progress_callback: callable = None) -> list[Requirement]:
    """
    Installs the given requirements from the store. Only what the imported pages
    actually need is installed - never the full setup of the exporting machine.

    Returns the requirements that could not be installed.
    """
    failed: list[Requirement] = []

    for index, requirement in enumerate(requirements):
        if progress_callback is not None:
            progress_callback(index, len(requirements), requirement)

        if gl.store_backend is None:
            failed.append(requirement)
            continue

        try:
            if requirement.type == "plugin":
                data = asyncio.run(gl.store_backend.get_plugin_for_id(requirement.id))
                if data is not None:
                    asyncio.run(gl.store_backend.install_plugin(data))
            elif requirement.type == PACK_TYPE_ICONS:
                data = asyncio.run(gl.store_backend.get_icon_for_id(requirement.id))
                if data is not None:
                    asyncio.run(gl.store_backend.install_icon(data))
            elif requirement.type == PACK_TYPE_WALLPAPERS:
                data = asyncio.run(gl.store_backend.get_wallpaper_for_id(requirement.id))
                if data is not None:
                    asyncio.run(gl.store_backend.install_wallpaper(data))
            else:
                data = None
        except Exception as e:
            log.error(f"Failed to install {requirement.type} {requirement.id}: {e}")
            data = None

        if data is None:
            log.warning(f"Could not install {requirement.type} {requirement.id} from the store")
            failed.append(requirement)
        else:
            log.success(f"Installed {requirement.type} {requirement.id} for the import")

    if progress_callback is not None:
        progress_callback(len(requirements), len(requirements), None)

    return failed


def _is_safe_archive_name(archive_name: str) -> bool:
    if not archive_name.startswith(f"{ASSET_DIR}/"):
        return False
    return ".." not in archive_name.split("/")


def _get_local_pack_path(origin) -> str | None:
    """Returns the local path of an asset that is part of an installed pack, None otherwise."""
    if not isinstance(origin, dict):
        return None
    if origin.get("type") not in PACK_TYPES:
        return None

    relative = origin.get("path")
    if not isinstance(relative, str) or ".." in relative.split("/"):
        return None

    local_path = os.path.join(gl.DATA_PATH, *relative.split("/"))
    return local_path if os.path.isfile(local_path) else None


def _import_assets(zip_file: zipfile.ZipFile, manifest_assets: dict, archive_names: set[str]) -> dict[str, str]:
    """
    Extracts the given assets and adds them to the asset manager.
    Returns a mapping of archive name -> local path.
    """
    paths: dict[str, str] = {}
    if not archive_names:
        return paths

    with tempfile.TemporaryDirectory(prefix="sc-bundle-") as temp_dir:
        for archive_name in sorted(archive_names):
            if not _is_safe_archive_name(archive_name):
                log.warning(f"Skipping unsafe asset name in bundle: {archive_name}")
                continue

            asset_info = manifest_assets.get(archive_name) or {}

            # Assets from an installed icon/wallpaper pack are used from the pack
            # itself instead of being duplicated into the asset manager
            pack_path = _get_local_pack_path(asset_info.get("origin"))
            if pack_path is not None:
                paths[archive_name] = pack_path
                continue

            name = asset_info.get("name")
            file_name = os.path.basename(name) if isinstance(name, str) else ""
            if file_name in ("", ".", ".."):
                file_name = os.path.basename(archive_name)
            temp_path = os.path.join(temp_dir, os.path.basename(archive_name))

            try:
                with zip_file.open(archive_name) as src, open(temp_path, "wb") as dst:
                    dst.write(src.read())
            except KeyError:
                log.warning(f"Asset {archive_name} is missing from the bundle")
                continue

            # Restore the original file name so the asset manager shows it
            named_path = os.path.join(temp_dir, file_name)
            if named_path != temp_path:
                os.replace(temp_path, named_path)

            asset_id = gl.asset_manager_backend.add(named_path)
            if asset_id is None:
                log.warning(f"Failed to import asset {file_name} from bundle")
                continue

            asset = gl.asset_manager_backend.get_by_id(asset_id)
            if asset is None:
                continue
            paths[archive_name] = asset["internal-path"]

    return paths


def load_bundle(path: str) -> dict[str, dict]:
    """
    Reads a bundle, imports its assets into the asset manager and returns
    {page name: page dict} with all media paths pointing to the local copies.
    """
    with zipfile.ZipFile(path) as zip_file:
        try:
            manifest = json.loads(zip_file.read(MANIFEST_NAME))
        except KeyError:
            raise ValueError("The file is not a StreamController bundle")

        format = manifest.get("format")
        if format not in (FORMAT_PAGE, FORMAT_PAGES):
            raise ValueError(f"Unsupported bundle format: {format}")
        if manifest.get("version", 1) > BUNDLE_VERSION:
            raise ValueError("The bundle was created by a newer version of StreamController")

        pages: dict[str, dict] = {}
        if format == FORMAT_PAGE:
            name = (manifest.get("pages") or [os.path.splitext(os.path.basename(path))[0]])[0]
            pages[name] = json.loads(zip_file.read(SINGLE_PAGE_NAME))
        else:
            for info in zip_file.infolist():
                if info.is_dir():
                    continue
                if not info.filename.startswith(f"{PAGE_DIR}/") or not info.filename.endswith(".json"):
                    continue
                name = os.path.splitext(os.path.basename(info.filename))[0]
                pages[name] = json.loads(zip_file.read(info))

        if not pages:
            raise ValueError("The bundle does not contain any pages")

        manifest_assets = manifest.get("assets") or {}

        # Only import the assets that are actually referenced
        referenced: set[str] = set()
        for page_dict in pages.values():
            for container, key in iter_media_refs(page_dict):
                value = container[key]
                if isinstance(value, str) and value in manifest_assets:
                    referenced.add(value)

        asset_paths = _import_assets(zip_file, manifest_assets, referenced)

    for page_dict in pages.values():
        for container, key in iter_media_refs(page_dict):
            local_path = asset_paths.get(container[key])
            if local_path is not None:
                container[key] = local_path

    return pages

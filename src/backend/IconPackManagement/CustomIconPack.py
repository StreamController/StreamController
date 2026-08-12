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
Locally created icon packs.

Unlike the packs from the store (<data>/icons/<id>) these live in
<data>/custom_icons/<id> and are created by the user from a zip file, a folder
or a couple of image files. The layout is the same as the one of a store pack,
so IconPack can read both:

    <data>/custom_icons/<id>/manifest.json
                            /attribution.json
                            /thumbnail.png
                            /icons/<group>/<icon>

Because they cannot be downloaded from the store, page bundles carry custom
packs with them (see src/backend/PageManagement/PageBundle.py).
"""
import json
import os
import re
import shutil
import zipfile
from datetime import datetime

from loguru import logger as log
from PIL import Image

import globals as gl
from src.backend.DeckManagement.HelperMethods import is_svg, svg_to_pil
from src.backend.IconPackManagement.IconPack import IconPack
from src.backend.Utils.AtomicSaveUtils import atomic_save_json, atomic_write

CUSTOM_PACK_DIR_NAME = "custom_icons"

MANIFEST_NAME = "manifest.json"
ATTRIBUTION_NAME = "attribution.json"
ICONS_DIR_NAME = "icons"
THUMBNAIL_NAME = "thumbnail.png"

THUMBNAIL_SIZE = (500, 360)
MAX_BANNER_SIZE = (1000, 1000)


def get_supported_extensions() -> set[str]:
    return {ext.lower() for ext in gl.image_extensions + gl.svg_extensions} | {"gif", "webp"}


def is_supported_image(name: str) -> bool:
    return os.path.splitext(name)[1][1:].lower() in get_supported_extensions()


def get_custom_pack_dir() -> str:
    path = os.path.join(gl.DATA_PATH, CUSTOM_PACK_DIR_NAME)
    os.makedirs(path, exist_ok=True)
    return path


def is_custom_pack_path(path: str) -> bool:
    """Returns whether the given path is inside a custom icon pack."""
    if not isinstance(path, str) or path == "":
        return False
    try:
        relative = os.path.relpath(os.path.abspath(path), get_custom_pack_dir())
    except ValueError:
        return False
    return not relative.startswith("..")


def get_custom_icon_packs() -> dict[str, IconPack]:
    packs: dict[str, IconPack] = {}

    for entry in sorted(os.listdir(get_custom_pack_dir())):
        pack_path = os.path.join(get_custom_pack_dir(), entry)
        if not os.path.isdir(pack_path):
            continue

        pack = IconPack(pack_path)
        if pack.is_valid:
            packs[entry] = pack
        else:
            log.warning(f"Custom icon pack {entry} is not valid.")

    return packs


## Creation

def create_custom_icon_pack(name: str, description: str = "", banner_path: str = None,
                            sources: list[str] = None) -> IconPack:
    """
    Creates a new pack from the given sources (zip files, folders or images).
    Raises on failure, leaving no half written pack behind.
    """
    name = (name or "").strip() or "Custom Pack"
    pack_path = os.path.join(get_custom_pack_dir(), _generate_pack_id(name))

    try:
        os.makedirs(os.path.join(pack_path, ICONS_DIR_NAME), exist_ok=True)

        n_icons = add_sources(pack_path, sources or [])
        _write_manifest(pack_path, name, description)
        _write_attribution(pack_path, description)
        set_banner(pack_path, banner_path)
    except Exception:
        shutil.rmtree(pack_path, ignore_errors=True)
        raise

    log.success(f"Created custom icon pack {os.path.basename(pack_path)} with {n_icons} icon(s)")

    return IconPack(pack_path)


def update_custom_icon_pack(pack_path: str, name: str = None, description: str = None,
                            banner_path: str = None) -> None:
    """Updates the metadata of an existing pack. Everything left out stays as it is."""
    manifest = _read_manifest(pack_path)

    if name is not None and name.strip() != "":
        manifest["name"] = name.strip()
    if description is not None:
        manifest["description"] = description
        manifest["descriptions"] = {"en_US": description}
        _write_attribution(pack_path, description)

    atomic_save_json(os.path.join(pack_path, MANIFEST_NAME), manifest)

    if banner_path is not None:
        set_banner(pack_path, banner_path)


def delete_custom_icon_pack(pack_path: str) -> None:
    if not is_custom_pack_path(pack_path) or not os.path.isdir(pack_path):
        log.warning(f"Refusing to delete {pack_path}: not a custom icon pack")
        return

    shutil.rmtree(pack_path, ignore_errors=True)
    log.info(f"Removed custom icon pack {os.path.basename(pack_path)}")


def _generate_pack_id(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", name).strip("_").lower() or "pack"

    pack_id = slug
    counter = 2
    while os.path.exists(os.path.join(get_custom_pack_dir(), pack_id)):
        pack_id = f"{slug}_{counter}"
        counter += 1

    return pack_id


def _read_manifest(pack_path: str) -> dict:
    path = os.path.join(pack_path, MANIFEST_NAME)
    if not os.path.isfile(path):
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        log.warning(f"Failed to read manifest of {pack_path}: {e}")
        return {}


def _write_manifest(pack_path: str, name: str, description: str) -> None:
    manifest = _read_manifest(pack_path)
    manifest.update({
        "id": os.path.basename(pack_path),
        "name": name,
        "description": description,
        "descriptions": {"en_US": description},
        "thumbnail": THUMBNAIL_NAME,
        "icons": f"{ICONS_DIR_NAME}/",
        "custom": True,
        "version": manifest.get("version", "1.0.0"),
        "app-version": gl.app_version,
        "created": manifest.get("created", datetime.now().isoformat(timespec="seconds"))
    })

    atomic_save_json(os.path.join(pack_path, MANIFEST_NAME), manifest)


def _write_attribution(pack_path: str, description: str) -> None:
    # Without a default entry the info button of an icon has nothing to show
    atomic_save_json(os.path.join(pack_path, ATTRIBUTION_NAME), {
        "default": {
            "copyright": "",
            "license": "",
            "license-url": "",
            "comment": description or ""
        }
    })


## Icons

def add_sources(pack_path: str, sources: list[str]) -> int:
    """
    Adds every image found in the given sources to the pack.
    A source can be a zip file, a folder or a single image.

    Returns the number of added icons.
    """
    icons_dir = os.path.join(pack_path, ICONS_DIR_NAME)
    os.makedirs(icons_dir, exist_ok=True)

    added = 0
    for source in sources:
        if not isinstance(source, str) or not os.path.exists(source):
            continue

        if os.path.isdir(source):
            added += _add_folder(icons_dir, source)
        elif zipfile.is_zipfile(source):
            added += _add_zip(icons_dir, source)
        elif is_supported_image(source):
            added += _add_file(icons_dir, source, "")

    return added


def _add_zip(icons_dir: str, zip_path: str) -> int:
    added = 0

    with zipfile.ZipFile(zip_path) as zip_file:
        members = [info for info in zip_file.infolist()
                   if not info.is_dir() and is_supported_image(info.filename)]
        root = _get_common_root([info.filename for info in members])

        for info in members:
            relative = info.filename[len(root):]
            target_dir = _get_group_dir(icons_dir, os.path.dirname(relative))
            target_path = _get_free_path(target_dir, os.path.basename(relative))

            try:
                with zip_file.open(info) as src, open(target_path, "wb") as dst:
                    shutil.copyfileobj(src, dst)
            except (OSError, zipfile.BadZipFile) as e:
                log.warning(f"Failed to extract {info.filename} from {zip_path}: {e}")
                continue
            added += 1

    return added


def _add_folder(icons_dir: str, folder_path: str) -> int:
    added = 0

    for dir_path, _, file_names in os.walk(folder_path):
        group = os.path.relpath(dir_path, folder_path)
        for file_name in sorted(file_names):
            if not is_supported_image(file_name):
                continue
            added += _add_file(icons_dir, os.path.join(dir_path, file_name), group)

    return added


def _add_file(icons_dir: str, path: str, group: str) -> int:
    target_dir = _get_group_dir(icons_dir, group)
    target_path = _get_free_path(target_dir, os.path.basename(path))

    try:
        shutil.copy2(path, target_path)
    except OSError as e:
        log.warning(f"Failed to add {path} to the pack: {e}")
        return 0

    return 1


def _get_common_root(names: list[str]) -> str:
    """Returns the folder every zip entry lives in, so a wrapping folder is not kept as a group."""
    dir_names = [name.rsplit("/", 1)[0] + "/" if "/" in name else "" for name in names]
    if not dir_names:
        return ""

    common = os.path.commonprefix(dir_names)
    return common[:common.rfind("/") + 1] if "/" in common else ""


def _get_group_dir(icons_dir: str, dir_path: str) -> str:
    """
    Returns the folder the icon has to be placed in. Icon packs only have one
    level of groups, so nested folders are flattened into a single name.
    """
    parts = [re.sub(r"[^\w\-. ]", "_", part).strip(". ")
             for part in re.split(r"[\\/]+", dir_path or "")
             if part not in ("", ".", "..")]
    parts = [part for part in parts if part != ""]

    if not parts:
        return icons_dir

    group_dir = os.path.join(icons_dir, "_".join(parts)[:60])
    os.makedirs(group_dir, exist_ok=True)
    return group_dir


def _get_free_path(directory: str, file_name: str) -> str:
    name, extension = os.path.splitext(re.sub(r"[\\/]", "_", file_name))
    name = name.strip(". ") or "icon"

    path = os.path.join(directory, f"{name}{extension}")
    counter = 2
    while os.path.exists(path):
        path = os.path.join(directory, f"{name}_{counter}{extension}")
        counter += 1

    return path


def get_icon_paths(pack_path: str) -> list[str]:
    paths: list[str] = []
    icons_dir = os.path.join(pack_path, ICONS_DIR_NAME)

    for dir_path, _, file_names in os.walk(icons_dir):
        for file_name in sorted(file_names):
            if is_supported_image(file_name):
                paths.append(os.path.join(dir_path, file_name))

    return paths


## Thumbnail

def set_banner(pack_path: str, banner_path: str = None) -> None:
    """Uses the given image as the pack banner, or builds one from its icons."""
    image = _open_image(banner_path) if banner_path else None
    is_custom_banner = image is not None

    if image is None:
        image = _generate_banner(pack_path)

    image.thumbnail(MAX_BANNER_SIZE)
    with atomic_write(os.path.join(pack_path, THUMBNAIL_NAME), "wb") as f:
        image.save(f, "PNG")

    # Remember it so a later icon addition does not overwrite a chosen banner
    manifest = _read_manifest(pack_path)
    if manifest:
        manifest["thumbnail"] = THUMBNAIL_NAME
        manifest["has-custom-banner"] = is_custom_banner
        atomic_save_json(os.path.join(pack_path, MANIFEST_NAME), manifest)


def _generate_banner(pack_path: str) -> Image.Image:
    """Builds a banner showing the first few icons of the pack in a 2x2 grid."""
    banner = Image.new("RGBA", THUMBNAIL_SIZE, (0, 0, 0, 0))

    cell_width = THUMBNAIL_SIZE[0] // 2
    cell_height = THUMBNAIL_SIZE[1] // 2

    for index, icon_path in enumerate(get_icon_paths(pack_path)[:4]):
        icon = _open_image(icon_path)
        if icon is None:
            continue

        # Fit the icon into its cell, scaling it up if it is smaller
        scale = min(cell_width * 0.7 / icon.width, cell_height * 0.7 / icon.height)
        icon = icon.resize((max(int(icon.width * scale), 1), max(int(icon.height * scale), 1)))

        x = (index % 2) * cell_width + (cell_width - icon.width) // 2
        y = (index // 2) * cell_height + (cell_height - icon.height) // 2
        banner.paste(icon, (x, y), icon if icon.mode == "RGBA" else None)

    return banner


def _open_image(path: str) -> Image.Image | None:
    if not isinstance(path, str) or not os.path.isfile(path):
        return None

    try:
        if is_svg(path):
            return svg_to_pil(path, width=256, height=256).convert("RGBA")
        return Image.open(path).convert("RGBA")
    except Exception as e:
        log.warning(f"Failed to open image {path}: {e}")
        return None

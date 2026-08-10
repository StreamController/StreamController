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
import base64
import binascii
import io
import os
import urllib.parse

from PIL import Image

from loguru import logger as log

from src.backend.DeckManagement.HelperMethods import svg_string_to_pil, svg_to_pil
from src.backend.PluginManager.StreamDeckSDK.Manifest import resolve_icon_path

DEFAULT_RENDER_SIZE = (144, 144)


def parse_color(color: str, default: tuple[int, int, int, int] = (255, 255, 255, 255)) -> list[int]:
    """Parse a ``#rgb``/``#rrggbb``/``#rrggbbaa`` colour into an rgba list."""
    if not isinstance(color, str):
        return list(default)

    value = color.strip().lstrip("#")
    try:
        if len(value) == 3:
            return [int(c * 2, 16) for c in value] + [255]
        if len(value) == 6:
            return [int(value[i:i + 2], 16) for i in (0, 2, 4)] + [255]
        if len(value) == 8:
            return [int(value[i:i + 2], 16) for i in (0, 2, 4, 6)]
    except ValueError:
        pass

    return list(default)


def load_data_uri(uri: str, size: tuple[int, int] = DEFAULT_RENDER_SIZE) -> Image.Image | None:
    """Decode a ``data:`` uri as sent by ``setImage`` into a PIL image."""
    try:
        header, _, data = uri.partition(",")
    except AttributeError:
        return None

    if not data:
        return None

    is_base64 = ";base64" in header.lower()
    is_svg = "svg" in header.lower()

    try:
        if is_base64:
            raw = base64.b64decode(data, validate=False)
        else:
            raw = urllib.parse.unquote(data).encode("utf-8")
    except (binascii.Error, ValueError, UnicodeEncodeError) as e:
        log.warning(f"Failed to decode a data uri: {e}")
        return None

    if is_svg:
        try:
            return svg_string_to_pil(raw.decode("utf-8"), width=size[0], height=size[1])
        except Exception as e:
            log.warning(f"Failed to render an inline svg: {e}")
            return None

    try:
        with Image.open(io.BytesIO(raw)) as image:
            return image.convert("RGBA")
    except Exception as e:
        log.warning(f"Failed to decode an image from a data uri: {e}")
        return None


def load_image(spec: str, plugin_path: str, size: tuple[int, int] = DEFAULT_RENDER_SIZE) -> Image.Image | None:
    """
    Load an image the way the Stream Deck SDK specifies it: either a ``data:`` uri or
    a path relative to the plugin directory, usually without a file extension.
    """
    if not spec:
        return None

    spec = spec.strip()
    if not spec:
        return None

    if spec.startswith("data:"):
        return load_data_uri(spec, size)

    if os.path.isabs(spec):
        candidate = resolve_icon_path(spec)
    else:
        candidate = resolve_icon_path(os.path.join(plugin_path, spec))

    if candidate is None:
        return None

    # Keep plugins from reaching outside of their own directory
    real_plugin_path = os.path.realpath(plugin_path)
    if not os.path.realpath(candidate).startswith(real_plugin_path + os.sep):
        log.warning(f"Refusing to load {candidate} because it is outside of {plugin_path}")
        return None

    if candidate.lower().endswith(".svg"):
        try:
            return svg_to_pil(candidate, width=size[0], height=size[1])
        except Exception as e:
            log.warning(f"Failed to render {candidate}: {e}")
            return None

    try:
        with Image.open(candidate) as image:
            return image.convert("RGBA")
    except Exception as e:
        log.warning(f"Failed to open {candidate}: {e}")
        return None

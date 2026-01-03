"""
Author: Core447
Year: 2023

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This programm comes with ABSOLUTELY NO WARRANTY!

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
from datetime import datetime
from functools import lru_cache
import hashlib
from io import BytesIO
import multiprocessing
import os
import subprocess
import matplotlib.font_manager
import sys
import math
import json
import requests
import cairosvg
import re
from urllib.parse import urlparse
from PIL import Image

import gi
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, Pango

# Import globals
from autostart import is_flatpak
import globals as gl


def sha256(text: str) -> str:
    """
    Calculates the sha256 hash of a file or string.

    Args:
        text (str): The file path or string.

    Returns:
        str: The sha256 hash of the file or string.
    """
    hash_sha256 = hashlib.sha256()
    if os.path.exists(text):
        with open(text, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
    else:
        hash_sha256.update(text.encode('utf-8'))
    return hash_sha256.hexdigest()


def file_in_dir(file_path, directory) -> None:
    """
    Check if a file is present in a directory.

    Args:
        file_path (str): The path of the file to check.
        dir (str, optional): The directory to check. Defaults to None.

    Returns:
        bool: True if the file is present in the directory, False otherwise.
    """
    if not os.path.isdir(directory) and directory is not None:
        return

    return os.path.split(file_path)[1] in os.listdir(directory)


def recursive_hasattr(obj, attr_string):
    """
    Check if an attribute exists in an object.

    Args:
        obj (object): The object to check.
        attr_string (str): The attributes to check separated with dots. e.g.: foo.bar

    Returns:
        bool: True if the attribute exists, False otherwise.
    """
    attrs = attr_string.split('.')
    for attr in attrs:
        if not hasattr(obj, attr):
            return False
        obj = getattr(obj, attr)
    return True


def font_path_from_name(font_name: str):
    return matplotlib.font_manager.findfont(matplotlib.font_manager.FontProperties(family=font_name))


def font_name_from_path(font_path: str):
    font_properties = matplotlib.font_manager.FontProperties(fname=font_path)
    return font_properties.get_family()[0]


def get_last_dir(path: str) -> str:
    if os.path.isdir(path):
        return os.path.basename(os.path.normpath(path))
    elif os.path.isfile(path):
        return os.path.basename(os.path.normpath(os.path.dirname(path)))
    return


def has_dict_recursive(dictionary: dict, *args):
    working_dict = dictionary
    for arg in args:
        working_dict = working_dict.get(arg)
        if working_dict == None:
            return False
    return True


def get_sys_param_value(param_name: str) -> str:
    for i, param in enumerate(sys.argv):
        if param.startswith(param_name):
            if i + 1 < len(sys.argv):
                return sys.argv[i + 1]


def get_sys_args_without_param(param_name: str) -> list:
    args = sys.argv
    for i, param in enumerate(args):
        if param.startswith(param_name):
            if i < len(args):
                args.pop(i + 1)  # to include the value of the param
            args.pop(i)
    return args


def is_video(path: str) -> bool:
    if path is None:
        return
    if os.path.isfile(path):
        return os.path.splitext(path)[1][1:].lower().replace(".", "") in gl.video_extensions

    return False


def is_image(path: str) -> bool:
    if path is None:
        return False
    if os.path.isfile(path):
        return os.path.splitext(path)[1][1:].lower().replace(".", "") in gl.image_extensions

    return False


def is_svg(path: str) -> bool:
    if path is None:
        return False
    if os.path.isfile(path):
        return os.path.splitext(path)[1][1:].lower().replace(".", "") in gl.svg_extensions

    return path.startswith("<svg ")


def get_image_aspect_ratio(img: Image) -> str:
    width, height = img.size
    gcd = math.gcd(width, height)
    aspect_ratio = f"{width//gcd}:{height//gcd}"
    return aspect_ratio


def create_empty_json(path: str, ignore_present: bool = False):
    # Create all dirs
    os.makedirs(os.path.dirname(path), exist_ok=True)

    if not ignore_present and os.path.exists(path):
        return

    # Write empty json
    with open(path, "w") as f:
        json.dump({}, f, indent=4)


def get_file_name_from_url(url: str):
    """
    Extracts the file name from a given URL.

    Args:
        url (str): The URL from which to extract the file name.

    Returns:
        str: The file name extracted from the URL.
    """
    # Parse the url to extract the path
    parsed_url = urlparse(url)
    # Extract the file name from the path
    return os.path.basename(parsed_url.path)


def download_file(url: str, path: str = "", file_name: str = None) -> str:
    """
    Downloads a file from the specified URL and saves it to the specified path.

    Args:
        url (str): The URL of the file to be downloaded.
        path (str): The path of the directory where the file will be saved. If a directory is provided, the filename will be extracted from the URL and appended to the path.

    Returns:
        path (str): The path of the downloaded file.
    """

    if file_name is None:
        file_name = get_file_name_from_url(url)

    path = os.path.join(path, file_name)

    if os.path.dirname(path) != "":
        os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "wb") as f:
        f.write(requests.get(url).content)

    return path

def natural_keys(s):
    return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', s)]


def natural_sort(strings_list: list[str]) -> list[str]:
    return sorted(strings_list, key=natural_keys)


def natural_sort_by_filenames(paths_list: list[str]) -> list[str]:
    sorted_paths = sorted(
        paths_list, key=lambda path: natural_keys(os.path.basename(path)))
    return sorted_paths


def add_default_keys(d: dict, keys: list):
    """
    Add nested default keys to a dictionary.

    :param d: The dictionary to add keys to.
    :param keys: A list of keys to create nested dictionaries for.
    :return: None; the dictionary is modified in place.
    """
    current_level = d
    for key in keys:
        if key not in current_level:
            current_level[key] = {}
        current_level = current_level[key]


@lru_cache()
def find_fallback_font(fallback="DejaVu Sans"):
    """
    TODO: Improve speed - maybe be writing the last one into a file and just checking if it still exists
    """
    # Find system fonts
    font_paths = matplotlib.font_manager.findSystemFonts(
        fontpaths=None, fontext='ttf')

    # Extract font names
    font_names = []
    for font in font_paths:
        try:
            font_name = matplotlib.font_manager.FontProperties(
                fname=font).get_name()
            font_names.append(font_name)
            if font_name == fallback:
                break
        except:
            pass

    # Check for fallback font
    if fallback in font_names:
        return fallback
    else:
        if len(font_names) > 0:
            return font_names[0]
        else:
            return


def color_values_to_gdk(color_values: tuple[int, int, int, int]) -> Gdk.RGBA:
    if len(color_values) == 3:
        color_values.append(255)
    color = Gdk.RGBA()
    color.parse(f"rgba({color_values[0]}, {color_values[1]}, {color_values[2]}, {color_values[3]})")

    return color


def gdk_color_to_values(color: Gdk.RGBA) -> tuple[int, int, int, int]:
    green = round(color.green * 255)
    blue = round(color.blue * 255)
    red = round(color.red * 255)
    alpha = round(color.alpha * 255)

    return red, green, blue, alpha


def get_pango_font_description(font_family: str, font_size: int, font_weight: int, font_style: str) -> Pango.FontDescription:
    if font_style == "italic":
        font_style = Pango.Style.ITALIC
    elif font_style == "oblique":
        font_style = Pango.Style.OBLIQUE
    else:
        font_style = Pango.Style.NORMAL

    desc = Pango.FontDescription()
    desc.set_family(font_family)
    desc.set_absolute_size(font_size * Pango.SCALE)
    desc.set_weight(font_weight)
    desc.set_style(font_style)

    return desc


def get_values_from_pango_font_description(desc: Pango.FontDescription) -> tuple[str, int, int, str]:
    font_family = desc.get_family()
    font_size = desc.get_size() / Pango.SCALE
    font_weight = desc.get_weight()
    font_style = desc.get_style()

    if font_style == Pango.Style.ITALIC:
        font_style = "italic"
    elif font_style == Pango.Style.OBLIQUE:
        font_style = "oblique"
    else:
        font_style = "normal"

    return font_family, font_size, font_weight, font_style


def get_sub_folders(parent: str) -> list[str]:
    if not os.path.isdir(parent):
        return []

    return [folder for folder in os.listdir(parent) if os.path.isdir(os.path.join(parent, folder))]


def sort_times(time_list):
    """
    Sort a list of datetime strings in ascending order.

    Parameters:
    time_list (list of str): List of datetime strings to be sorted.

    Returns:
    list of str: Sorted list of datetime strings.
    """
    return sorted(time_list, key=lambda x: datetime.fromisoformat(x))


def run_command(command):
    if command is None:
        return

    if is_flatpak():
        command = "flatpak-spawn --host " + command

    p = multiprocessing.Process(target=subprocess.Popen, args=[command], kwargs={
                                "shell": True, "start_new_session": True, "stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL, "cwd": os.path.expanduser("~")})
    p.start()

def open_web(url):
    if not url.startswith("http"):
        url = f"https://{url}"
    run_command(f"xdg-open {url}")

def svg_string_to_pil(svg_string, width: int = 96, height: int = 96):
    """
    Convert an SVG string to a PIL Image object.
    
    Args:
        svg_string (str): String containing SVG data
        width (int, optional): Desired width of the output image
        height (int, optional): Desired height of the output image
        
    Returns:
        PIL.Image: The converted image
    """
    # Convert SVG string to PNG using cairosvg
    png_data = cairosvg.svg2png(
        bytestring=svg_string.encode('utf-8'),
        output_width=width,
        output_height=height
    )
    
    # Create PIL Image from PNG data
    img = Image.open(BytesIO(png_data))
    
    return img


def svg_to_pil(svg_path: str, width: int = 96, height: int = 96):
    """
    Convert an SVG file to a PIL Image object.
    
    Args:
        svg_path (str): Path to the SVG file or string containing SVG data
        width (int, optional): Desired width of the output image
        height (int, optional): Desired height of the output image
        
    Returns:
        PIL.Image: The converted image
    """
    # Read SVG file

    if os.path.exists(svg_path):
        with open(svg_path, 'rb') as f:
            svg_data = f.read()
        
        # Convert SVG to PNG using cairosvg
        png_data = cairosvg.svg2png(
            bytestring=svg_data,
            output_width=width,
            output_height=height
        )
        
        # Create PIL Image from PNG data
        img = Image.open(BytesIO(png_data))
        
        return img
    elif svg_path.startswith("<svg "):
        return svg_string_to_pil(svg_path, width, height)
    else:
        raise ValueError(f"Could not create SVG from string or path: {svg_path}")
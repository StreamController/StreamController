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
from functools import lru_cache
import hashlib
import os
import matplotlib.font_manager
import sys
import math
import json
import requests
import cairosvg
import re
from urllib.parse import urlparse
from PIL import Image

# Import globals
import globals as gl

def sha256(file_path):
    """
    Calculates the sha256 hash of a file.

    Args:
        file_path (str): The path to the file.

    Returns:
        str: The sha256 hash of the file.
    """
    hash_sha256 = hashlib.sha256()
    if not os.path.exists(file_path):
        return
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
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
                args.pop(i + 1) # to include the value of the param
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
        return
    if os.path.isfile(path):
        return os.path.splitext(path)[1][1:].lower().replace(".", "") in gl.image_extensions

    return False

def is_svg(path: str) -> bool:
    if path is None:
        return
    if os.path.isfile(path):
        return os.path.splitext(path)[1][1:].lower().replace(".", "") in gl.svg_extensions
    
    return False

def get_image_aspect_ratio(img: Image) -> str:
    width, height = img.size
    gcd = math.gcd(width, height)
    aspect_ratio = f"{width//gcd}:{height//gcd}"
    return aspect_ratio

def create_empty_json(path:str, ignore_present: bool = False):
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

def load_svg_as_pil(file_path):
    hash = sha256(file_path)
    tmp = os.path.join(gl.DATA_PATH, "cache", "svg_to_png", f"{hash}.png")

    if not os.path.exists(tmp):
        os.makedirs(os.path.dirname(tmp), exist_ok=True)
        cairosvg.svg2png(url=file_path, write_to=tmp, output_width=96, output_height=96)

    pil_image = Image.open(tmp)
    return pil_image

def natural_keys(s):
    return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', s)]

def natural_sort(strings_list: list[str]) -> list[str]:
    return sorted(strings_list, key=natural_keys)

def natural_sort_by_filenames(paths_list: list[str]) -> list[str]:
    sorted_paths = sorted(paths_list, key=lambda path: natural_keys(os.path.basename(path)))
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
    TODO: Improve speed
    """
    # Find system fonts
    font_paths = matplotlib.font_manager.findSystemFonts(fontpaths=None, fontext='ttf')

    # Extract font names
    font_names = []
    for font in font_paths:
        try:
            font_name = matplotlib.font_manager.FontProperties(fname=font).get_name()
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
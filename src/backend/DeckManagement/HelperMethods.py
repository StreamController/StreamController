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
import hashlib
import os
def sha256(file_path):
    """
    Calculates the sha256 hash of a file.

    Args:
        file_path (str): The path to the file.

    Returns:
        str: The sha256 hash of the file.
    """
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()

def file_in_dir(file_path, dir=None):
    """
    Check if a file is present in a directory.
    
    Args:
        file_path (str): The path of the file to check.
        dir (str, optional): The directory to check. Defaults to None.
    
    Returns:
        bool: True if the file is present in the directory, False otherwise.
    """
    return os.path.split(file_path)[1] in os.listdir(dir)
"""
Author: gensyn
Year: 2025

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This programm comes with ABSOLUTELY NO WARRANTY!

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
import json
import os
from typing import Dict, List

MDI_FILENAME = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mdi-svg.json")

with open(MDI_FILENAME, "r", encoding="utf-8") as f:
    MDI_ICONS: Dict[str, str] = json.loads(f.read())


def get_icon_names() -> List[str]:
    return list(MDI_ICONS.keys())


def get_icon_path(icon_name: str) -> str:
    return MDI_ICONS.get(icon_name)


def get_icon_svg(name: str, path: str, color: str, opacity: int) -> str:
    """
    Build a complete SVG string from an icons' name and path with the stated color and opacity.
    """
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="300" height="300" viewBox="0 0 24 '
            f'24"><title>{name}</title><path d="{path}" fill="{color}" opacity="{round(opacity/100, 2)}" /></svg>')

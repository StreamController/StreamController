"""
Author: Core447
Year: 2024

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This programm comes with ABSOLUTELY NO WARRANTY!

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
from src.backend.DeckManagement.Subclasses.SingleKeyAsset import SingleKeyAsset
from PIL import Image
from dataclasses import dataclass
import matplotlib.font_manager

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.backend.DeckManagement.DeckController import ControllerKey

@dataclass
class KeyLabel:
    controller_input: "ControllerKey"
    text: str = None
    font_size: int = None
    font_name: str = None
    color: list[int] = None

    def get_font_path(self) -> str:
        return matplotlib.font_manager.findfont(matplotlib.font_manager.FontProperties(family=self.font_name))
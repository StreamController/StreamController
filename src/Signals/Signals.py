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

class Signal:
    pass


class PageRename(Signal):
    """
    Callback:
    old_path: str
    new_path: str
    """

class PageDelete(Signal):
    """
    Callback:
    path: str
    """

class PageAdd(Signal):
    """
    Callback:
    path: str
    """

class ChangePage(Signal):
    """
    Callback:
    controller: DeckController
    old_path: str
    new_path: str
    """

class PluginInstall(Signal):
    """
    Callback:
    id: str
    """

class AppQuit(Signal):
    pass
"""
Author: Core447
Year: 2026

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This programm comes with ABSOLUTELY NO WARRANTY!

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
# Import gtk modules
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

# Import Python modules
import os

# Import globals
import globals as gl

# Import own modules
from GtkHelper.GtkHelper import better_disconnect
from src.backend.DeckManagement.HelperMethods import get_folder_media_paths

SOURCE_FILE = "file"
SOURCE_FOLDER = "folder"
SOURCES = [SOURCE_FILE, SOURCE_FOLDER]

DEFAULT_INTERVAL = 5


class MediaSourceControls:
    """
    The "single asset or folder" controls shared by the background and the screen
    saver: a source chooser, a preview label for the chosen folder and the interval
    the folder is cycled with.

    The deck settings build their rows out of plain labels and widgets while the page
    editor uses libadwaita rows, so the widgets come from a subclass - everything the
    two flavours have in common lives here. Callers append source_widget, folder_label
    and interval_widget wherever they fit into their own layout.
    """

    def get_source(self) -> str:
        return SOURCES[self.get_selected_index()]

    def set_source(self, source: str) -> None:
        if source not in SOURCES:
            source = SOURCE_FILE
        self.set_selected_index(SOURCES.index(source))

    def update_for(self, source: str, folder_path: str, media_path: str) -> str:
        """
        Show or hide the folder only widgets for source and return the path whose
        thumbnail should be previewed - the first file of the folder in folder mode,
        the selected asset otherwise.
        """
        is_folder = source == SOURCE_FOLDER

        self.interval_widget.set_visible(is_folder)
        self.folder_label.set_visible(is_folder)

        if not is_folder:
            return media_path

        media_paths = get_folder_media_paths(folder_path)

        if folder_path in [None, ""]:
            self.folder_label.set_label(gl.lm.get("media-source.no-folder-selected"))
        else:
            # normpath so a trailing separator doesn't turn the name into an empty string
            name = os.path.basename(os.path.normpath(folder_path))
            self.folder_label.set_label(f"{name}\n{gl.lm.get('media-source.media-count').format(count=len(media_paths))}")

        return media_paths[0] if len(media_paths) > 0 else None

    def build_folder_label(self) -> Gtk.Label:
        return Gtk.Label(css_classes=["dim-label"], halign=Gtk.Align.CENTER, margin_top=5,
                         wrap=True, max_width_chars=20, visible=False)


class PlainMediaSourceControls(MediaSourceControls):
    """Label + widget rows, as used by the deck settings."""

    def __init__(self):
        self.source_widget = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True, margin_bottom=15)
        self.source_widget.append(Gtk.Label(label=gl.lm.get("media-source"), hexpand=True, xalign=0))

        self.source_dropdown = Gtk.DropDown.new_from_strings(
            [gl.lm.get("media-source.single"), gl.lm.get("media-source.folder")]
        )
        self.source_widget.append(self.source_dropdown)

        self.folder_label = self.build_folder_label()

        self.interval_widget = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True,
                                       margin_top=15, margin_bottom=15, visible=False)
        self.interval_widget.append(Gtk.Label(label=gl.lm.get("media-source.rotation-interval"), hexpand=True, xalign=0))

        self.interval_spinner = Gtk.SpinButton.new_with_range(1, 24*60, 1)
        self.interval_widget.append(self.interval_spinner)

    def get_selected_index(self) -> int:
        return self.source_dropdown.get_selected()

    def set_selected_index(self, index: int) -> None:
        self.source_dropdown.set_selected(index)

    def get_interval(self) -> int:
        return self.interval_spinner.get_value_as_int()

    def set_interval(self, minutes: int) -> None:
        self.interval_spinner.set_value(minutes)

    def connect_signals(self, on_source_changed: callable, on_interval_changed: callable) -> None:
        self.source_dropdown.connect("notify::selected", on_source_changed)
        self.interval_spinner.connect("value-changed", on_interval_changed)

    def disconnect_signals(self, on_source_changed: callable, on_interval_changed: callable) -> None:
        better_disconnect(self.source_dropdown, on_source_changed)
        better_disconnect(self.interval_spinner, on_interval_changed)


class RowMediaSourceControls(MediaSourceControls):
    """Libadwaita rows, as used by the page editor."""

    def __init__(self):
        self.source_widget = Adw.ComboRow(
            title=gl.lm.get("media-source"),
            model=Gtk.StringList.new([gl.lm.get("media-source.single"), gl.lm.get("media-source.folder")])
        )

        self.folder_label = self.build_folder_label()

        self.interval_widget = Adw.SpinRow.new_with_range(1, 24*60, 1)
        self.interval_widget.set_title(gl.lm.get("media-source.rotation-interval"))
        self.interval_widget.set_visible(False)

    def get_selected_index(self) -> int:
        return self.source_widget.get_selected()

    def set_selected_index(self, index: int) -> None:
        self.source_widget.set_selected(index)

    def get_interval(self) -> int:
        return int(self.interval_widget.get_value())

    def set_interval(self, minutes: int) -> None:
        self.interval_widget.set_value(minutes)

    def connect_signals(self, on_source_changed: callable, on_interval_changed: callable) -> None:
        self.source_widget.connect("notify::selected", on_source_changed)
        self.interval_widget.connect("changed", on_interval_changed)

    def disconnect_signals(self, on_source_changed: callable, on_interval_changed: callable) -> None:
        better_disconnect(self.source_widget, on_source_changed)
        better_disconnect(self.interval_widget, on_interval_changed)

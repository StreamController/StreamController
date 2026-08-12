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
# Import gtk modules
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib

# Import python modules
import os
import threading
from loguru import logger as log

# Import own modules
from src.backend.IconPackManagement import CustomIconPack
from src.backend.IconPackManagement.IconPack import IconPack

# Import globals
import globals as gl

# Import typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.AssetManager.CustomIconPacks.PackChooser import CustomIconPackChooser


class CustomIconPackDialog(Adw.Dialog):
    """Creates a new custom asset pack or edits an existing one."""
    def __init__(self, pack_chooser: "CustomIconPackChooser", pack: IconPack = None, sources: list[str] = None):
        super().__init__(title="Edit Asset Pack" if pack else "New Asset Pack",
                         accessible_role=Gtk.AccessibleRole.DIALOG)
        self.set_presentation_mode(Adw.DialogPresentationMode.FLOATING)
        self.set_content_width(500)

        self.pack_chooser = pack_chooser
        self.pack = pack

        self.sources: list[str] = list(sources or [])
        self.banner_path: str = None

        self.build()
        self.update_rows()

    def build(self):
        self.toolbar_view = Adw.ToolbarView()
        self.set_child(self.toolbar_view)

        self.header_bar = Adw.HeaderBar(show_start_title_buttons=False, show_end_title_buttons=False)
        self.toolbar_view.add_top_bar(self.header_bar)

        self.cancel_button = Gtk.Button(label="Cancel")
        self.cancel_button.connect("clicked", lambda button: self.close())
        self.header_bar.pack_start(self.cancel_button)

        self.apply_button = Gtk.Button(label="Save" if self.pack else "Create", css_classes=["suggested-action"])
        self.apply_button.connect("clicked", self.on_apply)
        self.header_bar.pack_end(self.apply_button)

        self.preferences_page = Adw.PreferencesPage()
        self.toolbar_view.set_content(self.preferences_page)

        self.group = Adw.PreferencesGroup()
        self.preferences_page.add(self.group)

        self.name_row = Adw.EntryRow(title="Name")
        self.name_row.set_text(self.pack.name if self.pack else self.get_suggested_name())
        self.group.add(self.name_row)

        self.description_row = Adw.EntryRow(title="Description")
        if self.pack:
            self.description_row.set_text(self.pack.get_manifest().get("description") or "")
        self.group.add(self.description_row)

        self.banner_row = Adw.ActionRow(title="Banner", subtitle="Generated from the icons")
        self.group.add(self.banner_row)

        self.banner_button = Gtk.Button(label="Choose", valign=Gtk.Align.CENTER)
        self.banner_button.connect("clicked", self.on_choose_banner)
        self.banner_row.add_suffix(self.banner_button)

        self.icons_group = Adw.PreferencesGroup(title="Icons")
        self.preferences_page.add(self.icons_group)

        self.icons_row = Adw.ActionRow(title="Sources")
        self.icons_group.add(self.icons_row)

        self.icons_button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5, valign=Gtk.Align.CENTER)
        self.icons_row.add_suffix(self.icons_button_box)

        self.archive_button = Gtk.Button(label="Archive", tooltip_text="Add all images of a zip file")
        self.archive_button.connect("clicked", self.on_choose_archive)
        self.icons_button_box.append(self.archive_button)

        self.folder_button = Gtk.Button(label="Folder", tooltip_text="Add all images of a folder")
        self.folder_button.connect("clicked", self.on_choose_folder)
        self.icons_button_box.append(self.folder_button)

        self.files_button = Gtk.Button(label="Images", tooltip_text="Add single images")
        self.files_button.connect("clicked", self.on_choose_files)
        self.icons_button_box.append(self.files_button)

        self.error_label = Gtk.Label(css_classes=["error"], wrap=True, visible=False, margin_top=10)
        self.icons_group.add(self.error_label)

    def get_suggested_name(self) -> str:
        """Uses the name of the dropped archive/folder as the default pack name."""
        for source in self.sources:
            if os.path.isdir(source):
                return os.path.basename(os.path.normpath(source))
            if source.lower().endswith(".zip"):
                return os.path.splitext(os.path.basename(source))[0]
        return ""

    def update_rows(self):
        if self.banner_path:
            self.banner_row.set_subtitle(os.path.basename(self.banner_path))
        elif self.pack:
            self.banner_row.set_subtitle("Unchanged")

        if self.sources:
            names = ", ".join(os.path.basename(os.path.normpath(source)) for source in self.sources)
            self.icons_row.set_subtitle(names)
        elif self.pack:
            self.icons_row.set_subtitle(f"{len(self.pack.get_icons())} icons - add more from a zip, a folder or images")
        else:
            self.icons_row.set_subtitle("Add them from a zip file, a folder or single images")

    def set_working(self, working: bool):
        self.set_can_close(not working)
        for button in (self.apply_button, self.cancel_button, self.banner_button,
                       self.archive_button, self.folder_button, self.files_button):
            button.set_sensitive(not working)
        self.apply_button.set_label("Working..." if working else ("Save" if self.pack else "Create"))

    ## Sources

    def on_choose_banner(self, button):
        file_filter = Gtk.FileFilter(name="Images")
        for extension in gl.image_extensions + gl.svg_extensions:
            file_filter.add_pattern(f"*.{extension}")

        dialog = Gtk.FileDialog(title="Select Banner", default_filter=file_filter)
        dialog.open(gl.asset_manager, None, self.on_banner_selected)

    def on_banner_selected(self, dialog, result):
        try:
            file = dialog.open_finish(result)
        except GLib.Error:
            return
        self.banner_path = file.get_path()
        self.update_rows()

    def on_choose_archive(self, button):
        file_filter = Gtk.FileFilter(name="Archives")
        file_filter.add_pattern("*.zip")

        dialog = Gtk.FileDialog(title="Select Archive", default_filter=file_filter)
        dialog.open(gl.asset_manager, None, self.on_archive_selected)

    def on_archive_selected(self, dialog, result):
        try:
            file = dialog.open_finish(result)
        except GLib.Error:
            return
        self.add_sources([file.get_path()])

    def on_choose_folder(self, button):
        dialog = Gtk.FileDialog(title="Select Folder")
        dialog.select_folder(gl.asset_manager, None, self.on_folder_selected)

    def on_folder_selected(self, dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
        except GLib.Error:
            return
        self.add_sources([folder.get_path()])

    def on_choose_files(self, button):
        file_filter = Gtk.FileFilter(name="Images")
        for extension in CustomIconPack.get_supported_extensions():
            file_filter.add_pattern(f"*.{extension}")

        dialog = Gtk.FileDialog(title="Select Images", default_filter=file_filter)
        dialog.open_multiple(gl.asset_manager, None, self.on_files_selected)

    def on_files_selected(self, dialog, result):
        try:
            files = dialog.open_multiple_finish(result)
        except GLib.Error:
            return
        self.add_sources([file.get_path() for file in files])

    def add_sources(self, sources: list[str]):
        for source in sources:
            if source is not None and source not in self.sources:
                self.sources.append(source)

        if self.name_row.get_text().strip() == "":
            self.name_row.set_text(self.get_suggested_name())

        self.update_rows()

    ## Apply

    def on_apply(self, button):
        name = self.name_row.get_text().strip()
        if name == "":
            self.name_row.add_css_class("error")
            return
        self.name_row.remove_css_class("error")

        self.error_label.set_visible(False)
        self.set_working(True)
        threading.Thread(target=self.apply, args=(name, self.description_row.get_text()),
                         name="apply_custom_icon_pack", daemon=True).start()

    @log.catch
    def apply(self, name: str, description: str):
        try:
            if self.pack is None:
                pack = CustomIconPack.create_custom_icon_pack(name, description, self.banner_path, self.sources)
                if not pack.get_icons():
                    CustomIconPack.delete_custom_icon_pack(pack.path)
                    GLib.idle_add(self.show_error, "No images found in the selected sources")
                    return
            else:
                added = CustomIconPack.add_sources(self.pack.path, self.sources)
                CustomIconPack.update_custom_icon_pack(self.pack.path, name, description, self.banner_path)

                if added and self.banner_path is None and not self.pack.get_manifest().get("has-custom-banner"):
                    # Keep the generated banner in sync with the new icons
                    CustomIconPack.set_banner(self.pack.path)
        except Exception as e:
            log.error(f"Failed to save custom icon pack: {e}")
            GLib.idle_add(self.show_error, str(e))
            return

        GLib.idle_add(self.on_applied)

    def show_error(self, message: str):
        self.set_working(False)
        self.error_label.set_label(message)
        self.error_label.set_visible(True)

    def on_applied(self):
        self.set_working(False)
        self.pack_chooser.reload()
        self.close()

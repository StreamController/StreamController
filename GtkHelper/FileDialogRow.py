from dataclasses import dataclass
from typing import Callable

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gdk, GLib, Gio

@dataclass
class FileDialogFilter:
    name: str
    filters: list[str]

class FileDialogRow(Adw.ActionRow):
    def __init__(self,
                 title: str = None,
                 subtitle: str = None,
                 dialog_title: str = None,
                 initial_path: str = None,
                 block_interaction: bool = True,
                 only_show_filename: bool = True,
                 filters: list[FileDialogFilter] = None,
                 file_change_callback: Callable[[Gio.File], None] = None
                 ):
        super().__init__(title=title, subtitle=subtitle)

        self._dialog_title = dialog_title
        self._initial_path = initial_path
        self._block_interaction = block_interaction
        self._only_show_filename = only_show_filename
        self._filters = filters or []
        self._callback = file_change_callback

        self.selected_file: Gio.File = None

        self.open_dialog_button = Gtk.Button(icon_name="folder-symbolic")
        self.open_dialog_button.set_margin_top(5)
        self.open_dialog_button.set_margin_bottom(5)

        self.file_label = Gtk.Label(label="No File Selected", hexpand=True)

        self.open_dialog_button.connect("clicked", self.on_open_dialog_clicked)

        self.add_suffix(self.file_label)
        self.add_prefix(self.open_dialog_button)

    def on_open_dialog_clicked(self, button):
        file_dialog = Gtk.FileDialog.new()
        file_dialog.set_title(self._dialog_title)
        file_dialog.set_modal(self._block_interaction)

        if self._initial_path:
            folder = Gio.File.new_for_path(self._initial_path)
            file_dialog.set_initial_folder(folder)

        filter_list_store = Gio.ListStore.new(Gtk.FileFilter)

        for file_filter in self._filters:
            gtk_filter = Gtk.FileFilter()
            gtk_filter.set_name(file_filter.name)

            for pattern in file_filter.filters:
                gtk_filter.add_pattern(pattern)

            filter_list_store.append(gtk_filter)

        file_dialog.set_filters(filter_list_store)

        file_dialog.open(None, None, self.on_file_dialog_response)

    def on_file_dialog_response(self, dialog: Gtk.FileDialog, task):
        try:
            file = dialog.open_finish(task)
            if not file:
                return

            self.selected_file = file
            self.set_label()

            if self._callback:
                self._callback(self.selected_file)
        except:
            pass

    def load_from_path(self, path: str):
        self.selected_file = Gio.File.new_for_path(path)
        self.file_label.set_label(path)
        self.set_label()

        if self._callback:
            self._callback(self.selected_file)

    def set_label(self):
        if self.selected_file is None:
            self.file_label.set_label("")
            return

        if self._only_show_filename:
            label = self.selected_file.get_basename()
        else:
            label = self.selected_file.get_path()

        self.file_label.set_label(label or "")
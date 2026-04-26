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
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk


class EntryDialog(Gtk.ApplicationWindow):
    def __init__(self, parent_window, dialog_title:str, entry_heading:str = "Name:", default_text:str = None, confirm_label:str = "OK", forbid_answers:list[str] = [],
                 empty_warning:str = "The name cannot be empty", cancel_label:str = "Cancel", already_exists_warning:str = "This name already exists",
                 placeholder:str = None):
        self.default_text = default_text
        self.confirm_label = confirm_label
        self.entry_heading = entry_heading
        self.forbid_answers = forbid_answers
        self.empty_warning = empty_warning
        self.cancel_label = cancel_label
        self.placeholder_text = placeholder
        self.already_exists_warning = already_exists_warning
        super().__init__(transient_for=parent_window, modal=True, default_height=150, default_width=350, title = dialog_title)
        self.callback_func = None
        self.build()

    def build(self):
        # Create title bar
        self.title_bar = Gtk.HeaderBar(show_title_buttons=False, css_classes=["flat"])
        # Cancel button
        self.cancel_button = Gtk.Button(label=self.cancel_label)
        self.cancel_button.connect('clicked', self.on_cancel)
        # Confirm button
        self.confirm_button = Gtk.Button(label=self.confirm_label, css_classes=['confirm-button'], sensitive=False)
        self.confirm_button.connect('clicked', self.on_confirm)
        # Main box
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True, margin_start=20, margin_end=20, margin_top=20, margin_bottom=20)
        # Label
        self.label = Gtk.Label(label=self.entry_heading)
        # Input box
        self.input_box = Gtk.Entry(hexpand=True, margin_top=10, text=self.default_text, placeholder_text=self.placeholder_text)
        self.input_box.connect('changed', self.on_name_change)
        # Warning label
        self.warning_label = Gtk.Label(label=self.empty_warning, css_classes=['warning-label'], margin_top=10)

        # Add objects
        self.set_titlebar(self.title_bar)
        self.title_bar.pack_start(self.cancel_button)
        self.title_bar.pack_end(self.confirm_button)
        self.set_child(self.main_box)
        self.main_box.append(self.label)
        self.main_box.append(self.input_box)
        self.main_box.append(self.warning_label)

        # Set status
        self.on_name_change(self.input_box)

        # Trigger on_confirm on return press
        self.input_box.connect("activate", self.on_confirm)

    def on_cancel(self, button):
        self.destroy()


    def on_name_change(self, entry):
        if entry.get_text() == '':
            self.set_dialog_status(0)
        elif entry.get_text() not in self.forbid_answers:
            self.set_dialog_status(2)
        else:
            self.set_dialog_status(1)

    def set_dialog_status(self, status):
        """
        Sets the status of the dialog

        Args:
            status (int): The status of the dialog: 0: no name; 1:already in use; 2:ok
        """
        if status == 0:
            # Label
            if self.main_box.get_last_child() is not self.warning_label:
                self.main_box.append(self.warning_label)
            self.warning_label.set_text(self.empty_warning)
            # Button
            self.confirm_button.set_sensitive(False)
            self.confirm_button.set_css_classes(['confirm-button'])
        if status == 1:
            # Label
            if self.main_box.get_last_child() is not self.warning_label:
                self.main_box.append(self.warning_label)
            self.warning_label.set_text(self.already_exists_warning)
            # Button
            self.confirm_button.set_sensitive(False)
            self.confirm_button.set_css_classes(['confirm-button-error'])
        if status == 2:
            # Label
            if self.main_box.get_last_child() is self.warning_label:
                self.main_box.remove(self.warning_label)
            # Button
            self.confirm_button.set_sensitive(True)
            self.confirm_button.set_css_classes(['confirm-button'])

    def show(self, callback_func):
        self.callback_func = callback_func
        self.present()

    def on_confirm(self, button):
        self.callback_func(self.input_box.get_text())
        self.destroy()

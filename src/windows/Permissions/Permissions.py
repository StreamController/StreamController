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
import os
import pyclip

# Import gtk modules
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Pango, GdkPixbuf

# Import globals
import globals as gl

# Import typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from windows.mainWindow.mainWindow import MainWindow


class PermissionsWindow(Gtk.ApplicationWindow):
    def __init__(self, application, main_window: "MainWindow"):
        super().__init__(application=application)
        self.set_title("Permissions")
        self.set_transient_for(main_window)
        self.set_modal(True)
        self.set_default_size(700, 700)

        self.command = "flatpak override --user --socket=session-bus com.core447.StreamController"
        self.flatpak_docs_link = "https://docs.flatpak.org/en/latest/sandbox-permissions.html"
        
        self.build()

    def build(self):
        self.header = Adw.HeaderBar(css_classes=["flat"])
        self.set_titlebar(self.header)

        self.overlay = Gtk.Overlay()
        self.set_child(self.overlay)

        self.mark_solved_button = Gtk.Button(label=gl.lm.get("permissions-window.mark-solved"), css_classes=["suggested-action"],
                                             halign=Gtk.Align.END, valign=Gtk.Align.END,
                                             margin_bottom=10, margin_end=10)
        self.mark_solved_button.connect("clicked", self.on_mark_solved)
        self.overlay.add_overlay(self.mark_solved_button)

        self.close_button = Gtk.Button(label=gl.lm.get("permissions-window.close"), css_classes=["destructive-action"],
                                       halign=Gtk.Align.START, valign=Gtk.Align.END,
                                       margin_bottom=10, margin_start=10)
        self.close_button.connect("clicked", self.on_close)
        self.overlay.add_overlay(self.close_button)
                                       

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                                margin_start=15, margin_end=15)
        self.overlay.set_child(self.main_box)

        self.image = Gtk.Image(file=os.path.join("Assets", "images", "archive.png"), css_classes=["permissions-window-icon"],
                               margin_top=20, margin_bottom=10)
        self.main_box.append(self.image)

        ## Labels
        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.main_box.append(self.content_box)

        self.header = Gtk.Label(label="Flatpak detected", css_classes=["permissions-window-header"],
                                margin_bottom=25)
        self.content_box.append(self.header)

        self.description = Gtk.Label(label=gl.lm.get("permissions-window.description"),
                                     wrap=True, wrap_mode=Pango.WrapMode.WORD, justify=Gtk.Justification.CENTER)
        self.content_box.append(self.description)

        self.command_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, css_classes=["linked"], halign=Gtk.Align.CENTER,
                                   margin_top=40)
        self.content_box.append(self.command_box)

        self.command_label = Gtk.Label(label=self.command, css_classes=["permissions-window-command"],
                                       overflow=Gtk.Overflow.HIDDEN)
        self.command_box.append(self.command_label)

        self.copy_button = Gtk.Button(icon_name="com.core447.StreamController_edit-copy", css_classes=["permissions-window-copy"],
                                      tooltip_text=gl.lm.get("permissions-window.copy-tooltip"))
        self.copy_button.connect("clicked", self.on_copy)
        self.command_box.append(self.copy_button)

        self.content_box.append(Gtk.Box(vexpand=True)) # Move info label to the bottom

        self.more_infos_label = Gtk.Label(label=f'{gl.lm.get("permissions-window.info-beginning")}<a href="{self.flatpak_docs_link}">{gl.lm.get("permissions-window.flatpak-docs")}</a>', use_markup=True,
                                          margin_bottom=60)
        self.content_box.append(self.more_infos_label)


    def on_copy(self, button):
        pyclip.copy(self.command)

    def on_mark_solved(self, button):
        with open(os.path.join(gl.DATA_PATH, ".skip-permissions"), "w") as f:
            f.write("")
        self.destroy()

    def on_close(self, button):
        self.destroy()
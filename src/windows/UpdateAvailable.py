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

import gi

from src.windows.ErrorDialog import ErrorDialog
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk, Xdp, Gio

import globals as gl

from loguru import logger as log

class UpdateAvailableDialog(Gtk.ApplicationWindow):

    def __init__(self, parent, *args, **kwargs):
        super().__init__(
            modal=True,
            transient_for=parent,
            default_height=700,
            default_width=450,
            title="Update Available",
            *args,
            **kwargs
        )
        # Things will go here

        self.set_titlebar(Gtk.HeaderBar(css_classes=["flat"]))

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True)
        self.set_child(self.main_box)

        self.icon = Gtk.Image(icon_name="software-update-available-symbolic", pixel_size=200,
                              halign=Gtk.Align.CENTER, margin_top=50)
        self.main_box.append(self.icon)

        self.main_label = Gtk.Label(label="New version of StreamController is available", halign=Gtk.Align.CENTER, css_classes=["bold", "title-1"],
                                    wrap=True, justify=Gtk.Justification.CENTER, margin_top=20)
        self.main_box.append(self.main_label)

        self.description_label = Gtk.Label(label="You're seeing this because StreamController is still in beta and new versions might fix some critical bugs.", halign=Gtk.Align.CENTER,
                                           wrap=True, justify=Gtk.Justification.CENTER, margin_top=20)
        self.main_box.append(self.description_label)

        self.update_button = Gtk.Button(label="Update", halign=Gtk.Align.CENTER, valign=Gtk.Align.END, margin_top=40, css_classes=["circular", "suggested-action"])
        update_button_label = self.update_button.get_child()
        update_button_label.set_margin_top(10)
        update_button_label.set_margin_bottom(10)
        update_button_label.set_margin_start(20)
        update_button_label.set_margin_end(20)
        self.update_button.connect("clicked", self.on_update)
        self.main_box.append(self.update_button)

        self.progress_bar = Gtk.ProgressBar(margin_top=40, margin_start=40, margin_end=40, margin_bottom=40, text="Installing", show_text=True, visible=False)
        self.main_box.append(self.progress_bar)

    def on_update(self, button):
        self.update_button.set_sensitive(False)
        self.progress_bar.set_visible(True)

        gl.portal.connect("update-progress", self.on_update_progress)

        gl.portal.update_install(
            parent=Xdp.Parent,  #FIXME: No idea how to get the parent on python
            flags=Xdp.UpdateInstallFlags.NONE,
            cancellable=Gio.Cancellable()
        )

    def calc_progress(self, n_ops: int, op: int, progress: float) -> float:
        if not (1 <= op <= n_ops):
            raise ValueError("op must be between 1 and n_ops")
        if not (0 <= progress <= 1):
            raise ValueError("progress must be between 0 and 1")

        step_size = 1/max(n_ops, 1)
        total_progress = step_size * max(op - 1, 0) + step_size * progress

        return total_progress

    @log.catch
    def on_update_progress(self, portal, n_ops, op, progress, status, error, error_msg):
        """
        Docs under: https://libportal.org/signal.Portal.update-progress.html
        """
        if status == Xdp.UpdateStatus.DONE:
            self.progress_bar.set_fraction(1)
            self.progress_bar.set_text("Done")
            return
        
        if status in (Xdp.UpdateStatus.ERROR, Xdp.UpdateStatus.EMPTY):
            self.progress_bar.set_fraction(0)
            self.progress_bar.set_text("Error")
            err_dialog = ErrorDialog(self, error_msg)
            err_dialog.show()
            return


        total_progress = 0
        try:
            total_progress = self.calc_progress(n_ops, op, progress)
        except Exception as e:
            log.error(e)

        self.progress_bar.set_fraction(total_progress)
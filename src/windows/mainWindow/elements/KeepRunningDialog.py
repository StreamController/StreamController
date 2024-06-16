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
# Import gtk modules
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

import globals as gl

class KeepRunningDialog(Adw.MessageDialog):
    def __init__(self, parent, callback: callable = None):
        self.callback = callback

        super().__init__(
            transient_for=parent,
            modal=True
        )

        self.set_title("Keep running?")
        self.set_heading("Keep running?")
        
        self.set_body(("Do you want to keep StreamController running in the background "
                       "when closing the main window? To stop the application you can use the option in the hamburger menu. "
                       "This option can be changed "
                       "in the application settings at any time."))
        
        self.add_response("no", "No")
        self.add_response("yes", "Yes")

        self.set_response_appearance("yes", Adw.ResponseAppearance.SUGGESTED)

        self.set_default_response("yes")

        self.connect("response", self.on_response)

    def on_response(self, dialog: Adw.MessageDialog, response: str) -> None:
        app_settings = gl.settings_manager.get_app_settings()
        keep_runnning = (response == "yes")
        app_settings.setdefault("system", {})
        app_settings["system"]["keep-running"] = keep_runnning
        gl.settings_manager.save_app_settings(app_settings)

        if callable(self.callback):
            self.callback(keep_runnning)

        self.destroy()
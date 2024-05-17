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
from gi.repository import Gtk, Adw

import globals as gl

class ResponsibleNotesDialog(Adw.MessageDialog):
    def __init__(self, parent, callback: callable = None):
        self.callback = callback

        super().__init__(
            transient_for=parent,
            modal=True
        )

        self.set_title("Content Responsibility Notes")
        self.set_heading("Content Responsibility Notes")
        self.set_body(("Core447 and other contributors of StreamController are "
                      "not responsible for content in the Store that is not released by Core447."
                      "This also applies to plugins that are from other persons but marked as official."
                      "The official badge only indicates a collaboration, "
                      "it does not mean that the plugin is created by Core447."))
        
        self.add_response("disagree", "Disagree")
        self.add_response("agree", "Agree")

        self.set_response_appearance("disagree", Adw.ResponseAppearance.DESTRUCTIVE)
        self.set_response_appearance("agree", Adw.ResponseAppearance.SUGGESTED)

        self.set_default_response("agree")

        self.connect("response", self.on_response)

    def on_response(self, dialog: Adw.MessageDialog, response: int) -> None:
        app_settings = gl.settings_manager.get_app_settings()
        agreed = (response == "agree")
        app_settings.setdefault("store", {})
        app_settings["store"]["responsibility-notes-agreed"] = agreed
        gl.settings_manager.save_app_settings(app_settings)

        if callable(self.callback):
            self.callback(agreed)

        self.destroy()
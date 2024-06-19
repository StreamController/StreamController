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
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw


class ErrorDialog(Adw.MessageDialog):

    def __init__(self, parent, error_msg: str, *args, **kwargs):
        super().__init__(
            transient_for=parent,
            *args,
            **kwargs
        )

        self.set_title("Error")
        self.set_heading("Error")
        self.set_body(error_msg)

        self.add_response("close", "Close")

        self.connect("response", self.on_response)

    def on_response(self, dialog: Adw.MessageDialog, response: int) -> None:
        self.destroy()
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

from os import remove
import globals as gl

import gi
from gi.repository import Xdp

from src.windows.UpdateAvailable import UpdateAvailableDialog

from loguru import logger as log

class UpdateManager:
    def __init__(self):
        self.on_update_available(1, 2, 3) #for testing

        gl.portal.connect("update-available", self.on_update_available)

    @log.catch
    def on_update_available(self, running_commit, local_commit, remote_commit):
        if remote_commit == local_commit:
            return
        
        if gl.app.loaded:
            self.show_dialog()
        else:
            gl.app_loading_finished_tasks.append(self.show_dialog)
        
    def show_dialog(self):
        dialog = UpdateAvailableDialog(gl.app.main_win)
        dialog.present()
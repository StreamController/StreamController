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
# Import gtk modules
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio

# Import own modules
from src.backend.WindowGrabber.Window import Window
from GtkHelper.GtkHelper import BetterExpander, EntryDialog
from src.windows.PageManager.elements.PageSelector import PageSelector
from src.windows.PageManager.elements.PageEditor import PageEditor

# Import typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.mainWindow.mainWindow import MainWindow

# Import signals
from src.Signals import Signals

# Import globals
import globals as gl

class PageManager(Adw.ApplicationWindow):
    def __init__(self, main_win: "MainWindow"):
        super().__init__(title=gl.lm.get("page-manager.title"), default_width=400, default_height=600)
        self.set_transient_for(main_win)
        #self.set_modal(True) Removed to allow other popups in the PageEditor

        self.build()

        self.page_selector.load_pages()

        self.set_size_request(1300, 800)

        self.connect("close-request", self.on_close)

    def on_close(self, *args, **kwargs):
        gl.page_manager_window = None
        self.destroy()


    def build(self):
        # Split view
        self.split = Adw.NavigationSplitView(vexpand=True, sidebar_width_fraction=0.4, min_sidebar_width=300)
        self.set_content(self.split)

        self.page_editor = PageEditor(self)
        self.split.set_content(self.page_editor)

        self.page_selector = PageSelector(self)
        self.split.set_sidebar(self.page_selector)

    def add_page_from_name(self, page_name: str) -> None:
        page_path = os.path.join(gl.DATA_PATH, "pages", f"{page_name}.json")
        if os.path.exists(page_path):
            return
        
        gl.page_manager.add_page(page_name)
        
        self.page_selector.add_row_by_path(page_path)

        # Emit signal
        gl.signal_manager.trigger_signal(Signals.PageAdd, page_path)

    def remove_page_by_path(self, page_path: str) -> None:
        if page_path in gl.page_manager.custom_pages:
            dial = CantDeletePluginPage(self)
            dial.show()
            return
        if self.get_number_of_user_pages() <= 1:
            dial = CantDeleteLastPageError(self)
            dial.show()
            return
        
        self.page_selector.remove_row_with_path(page_path)

        gl.page_manager.remove_page(page_path)

        # Emit signal
        gl.signal_manager.trigger_signal(Signals.PageDelete, page_path)

    def rename_page_by_path(self, old_path: str, new_path: str) -> None:
        self.page_selector.rename_page_row(old_path=old_path, new_path=new_path)

        gl.page_manager.move_page(old_path, new_path)

        # Emit signal
        gl.signal_manager.trigger_signal(Signals.PageRename, old_path, new_path)

    def get_number_of_user_pages(self) -> int:
        return len(gl.page_manager.get_pages(add_custom_pages=False))
    
class CantDeleteLastPageError(Adw.MessageDialog):
    def __init__(self, page_manager: PageManager):
        super().__init__()
        self.set_transient_for(page_manager)
        self.set_modal(True)
        self.set_title("Error")
        self.set_body("You have to have at least one user page.")
        self.add_response("ok", "OK")
        self.set_default_response("ok")

class CantDeletePluginPage(Adw.MessageDialog):
    def __init__(self, page_manager: PageManager):
        super().__init__()
        self.set_transient_for(page_manager)
        self.set_modal(True)
        self.set_title("Error")
        self.set_body("You can't delete plugin pages.")
        self.add_response("ok", "OK")
        self.set_default_response("ok")
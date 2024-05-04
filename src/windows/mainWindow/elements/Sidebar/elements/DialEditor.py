from gi.repository import Gtk

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.mainWindow.elements.Sidebar.Sidebar import Sidebar

class DialEditor(Gtk.ScrolledWindow):
    def __init__(self, sidebar: "Sidebar"):
        self.sidebar = sidebar
        super().__init__(hexpand=True, vexpand=True)

        self.build()

    def build(self):
        self.main_box = Gtk.Box(halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        self.set_child(self.main_box)

        self.main_box.append(Gtk.Label(label="Coming soon", halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER))

    def load_for_dial(self, n: int):
        pass
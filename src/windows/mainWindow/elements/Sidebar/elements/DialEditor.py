from gi.repository import Gtk, Adw

from typing import TYPE_CHECKING

from src.windows.mainWindow.elements.Sidebar.elements.ActionManager import ActionManager

if TYPE_CHECKING:
    from src.windows.mainWindow.elements.Sidebar.Sidebar import Sidebar

class DialEditor(Gtk.ScrolledWindow):
    def __init__(self, sidebar: "Sidebar"):
        self.sidebar = sidebar
        super().__init__(hexpand=True, vexpand=True)

        self.build()

    def build(self):
        self.clamp = Adw.Clamp(hexpand=True, vexpand=True)
        self.set_child(self.clamp)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.clamp.set_child(self.main_box)

        self.turn_cw_group = Adw.PreferencesGroup(title="Turn Clockwise")
        self.main_box.append(self.turn_cw_group)

        self.turn_ccw_group = Adw.PreferencesGroup(title="Turn Counterclockwise", margin_top=10)
        self.main_box.append(self.turn_ccw_group)

        self.turn_cw_configurator = ActionManager(self.sidebar)
        self.turn_cw_group.add(self.turn_cw_configurator)

        self.turn_ccw_configurator = ActionManager(self.sidebar)
        self.turn_ccw_group.add(self.turn_ccw_configurator)

    def load_for_dial(self, n: int, state: int):
        self.turn_cw_configurator.load_for_dial(n, "cw", state)
        self.turn_ccw_configurator.load_for_dial(n, "ccw", state)
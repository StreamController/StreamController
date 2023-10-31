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
# Import gtk modules
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

# Import Python modules
from loguru import logger as log

# Import own modules
from src.windows.mainWindow.elements.RightArea.elements.IconSelector import IconSelector
from src.windows.mainWindow.elements.RightArea.elements.LabelEditor import LabelEditor
from src.windows.mainWindow.elements.RightArea.elements.ActionManager import ActionManager
from src.windows.mainWindow.elements.RightArea.elements.ActionChooser import ActionChooser
from src.windows.mainWindow.elements.RightArea.elements.ActionConfigurator import ActionConfigurator

class RightArea(Gtk.Stack):
    def __init__(self, main_window, **kwargs):
        super().__init__(hexpand=True, **kwargs)
        self.main_window = main_window
        self.build()

    def build(self):
        self.key_editor = RightAreaKeyEditor(self)
        self.add_named(self.key_editor, "key_editor")

        self.action_chooser = ActionChooser(self)
        self.add_named(self.action_chooser, "action_chooser")

        self.action_configurator = ActionConfigurator(self)
        self.add_named(self.action_configurator, "action_configurator")

        # Config transition
        self.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.set_transition_duration(200)

    def let_user_select_action(self, callback_function, callback_args):
        self.action_chooser.show(callback_function=callback_function, callback_args=callback_args)

    def show_action_configurator(self):
        self.set_visible_child(self.action_configurator)

class RightAreaKeyEditor(Gtk.Box):
    def __init__(self, right_area, **kwargs):
        super().__init__(**kwargs)
        self.scrolled_window = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        self.append(self.scrolled_window)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True)
        self.scrolled_window.set_child(self.main_box)

        self.icon_selector = IconSelector(right_area, halign=Gtk.Align.CENTER, margin_top=75)
        self.main_box.append(self.icon_selector)

        self.label_editor = LabelEditor(right_area, margin_top=25)
        self.main_box.append(self.label_editor)

        self.action_editor = ActionManager(right_area, margin_top=25, width_request=400)
        self.main_box.append(self.action_editor)
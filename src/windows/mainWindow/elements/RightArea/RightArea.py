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
from src.windows.mainWindow.elements.RightArea.elements.BackgroundEditor import BackgroundEditor
from GtkHelper.GtkHelper import ErrorPage

# Import globals
import globals as gl

class RightArea(Gtk.Stack):
    def __init__(self, main_window, **kwargs):
        super().__init__(hexpand=True, **kwargs)
        self.main_window = main_window
        self.active_coords: tuple = None
        self.build()

    def build(self):
        self.key_editor = RightAreaKeyEditor(self)
        self.add_named(self.key_editor, "key_editor")

        self.action_chooser = ActionChooser(self)
        self.add_named(self.action_chooser, "action_chooser")

        self.action_configurator = ActionConfigurator(self)
        self.add_named(self.action_configurator, "action_configurator")

        self.error_page = ErrorPage(self)
        self.add_named(self.error_page, "error_page")

        # Config transition
        self.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.set_transition_duration(200)

        self.load_for_coords((0, 0))

    def let_user_select_action(self, callback_function, *callback_args, **callback_kwargs):
        """
        Show the action chooser to let the user select an action.
        The callback_function will be called with the following parameters:
             - action_object: The action object that was selected.
             - args: The args passed to this function
             - kwargs: The kwargs passed to this function

        Parameters:
            callback_function (function): The callback function to be called after the action is selected.
            *callback_args: Variable length argument list to be passed to the callback function.
            **callback_kwargs: Arbitrary keyword arguments to be passed to the callback function.

        Returns:
            None
        """
        self.action_chooser.show(callback_function=callback_function, current_stack_page=self.get_visible_child(), callback_args=callback_args, callback_kwargs=callback_kwargs)

    def show_action_configurator(self):
        self.set_visible_child(self.action_configurator)

    def load_for_coords(self, coords):
        self.active_coords = coords
        # Verify that a controller is selected
        if self.main_window.leftArea.deck_stack.get_visible_child() is None:
            self.error_page.set_error_text(gl.lm.get("right-area-no-deck-selected-error"))
            # self.error_page.set_reload_func(self.main_window.rightArea.load_for_coords)
            # self.error_page.set_reload_args([coords])
            self.show_error()
            return
        # Verify is page is loaded on current controller
        controller = self.main_window.leftArea.deck_stack.get_visible_child().deck_controller
        if controller.active_page == None:
            # self.error_page.set_error_text(gl.lm.get("right-area-no-page-selected-error"))
            # self.error_page.set_reload_args([None])
            self.show_error()
            return

        self.hide_error()        

        self.key_editor.load_for_coords(coords)

        if self.get_visible_child() != self.key_editor:
            self.set_visible_child(self.key_editor)

    def show_error(self):
        self.set_transition_duration(0)
        self.set_visible_child(self.error_page)
        self.set_transition_duration(200)


    def hide_error(self):
        if self.get_visible_child() == self.error_page:
            self.set_transition_duration(0)
            self.set_visible_child(self.key_editor)
            self.set_transition_duration(200)

    def reload(self):
        self.load_for_coords(self.active_coords)


class RightAreaKeyEditor(Gtk.Box):
    def __init__(self, right_area, **kwargs):
        super().__init__(**kwargs)
        self.right_area:RightArea = right_area

        self.scrolled_window = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        self.append(self.scrolled_window)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True)
        self.scrolled_window.set_child(self.main_box)

        self.icon_selector = IconSelector(right_area, halign=Gtk.Align.CENTER, margin_top=75)
        self.main_box.append(self.icon_selector)

        self.background_editor = BackgroundEditor(right_area, margin_top=25)
        self.main_box.append(self.background_editor)

        self.label_editor = LabelEditor(right_area, margin_top=25)
        self.main_box.append(self.label_editor)

        self.action_editor = ActionManager(right_area, margin_top=25, width_request=400)
        self.main_box.append(self.action_editor)

    def load_for_coords(self, coords):
        self.right_area.active_coords = coords
        self.icon_selector.load_for_coords(coords)
        self.label_editor.load_for_coords(coords)
        self.action_editor.load_for_coords(coords)
        self.background_editor.load_for_coords(coords)
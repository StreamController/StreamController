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
import gi

import globals as gl
from GtkHelper.GtkHelper import ErrorPage
from src.backend.DeckManagement.InputIdentifier import Input, InputIdentifier
from src.windows.mainWindow.elements.PageSelector import PageSelector
from src.windows.mainWindow.elements.Sidebar.elements.ActionChooser import ActionChooser
from src.windows.mainWindow.elements.Sidebar.elements.ActionConfigurator import ActionConfigurator
from src.windows.mainWindow.elements.Sidebar.elements.DialEditor import DialEditor
from src.windows.mainWindow.elements.Sidebar.elements.ScreenEditor import ScreenEditor
from src.windows.mainWindow.elements.Sidebar.Parts.KeyEditor import (
    KeyEditor,
    KeyEditorKeyBox,
    TestStack,
)
from src.windows.mainWindow.elements.Sidebar.Parts.PageEditor import PageEditor
from src.windows.mainWindow.elements.Sidebar.Parts.Pages import (
    AdwPageRow,
    PageRow,
    PagesGroup,
)

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

__all__ = [
    "AdwPageRow",
    "KeyEditor",
    "KeyEditorKeyBox",
    "PageEditor",
    "PageRow",
    "PagesGroup",
    "Sidebar",
    "TestStack",
]


class Sidebar(Adw.NavigationPage):
    def __init__(self, main_window, **kwargs):
        super().__init__(hexpand=True, title="Sidebar", **kwargs)
        self.main_window = main_window
        self.active_identifier: InputIdentifier = None
        self.active_state: int = None
        
        """
        To save performance and memory, we only load the thumbnail when the user sees the row
        """
        self.on_map_tasks: list = []
        self.connect("map", self.on_map)

        self.build()

    def on_map(self, widget):
        for f in self.on_map_tasks:
            f()
        self.on_map_tasks.clear()

    def build(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.set_child(self.main_box)

        self.header = Adw.HeaderBar(css_classes=["flat"], show_back_button=False)
        self.main_box.append(self.header)

        self.main_stack = Gtk.Stack(transition_duration=200, transition_type=Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.main_box.append(self.main_stack)

        self.configurator_stack = Gtk.Stack()
        self.main_stack.add_named(self.configurator_stack, "configurator_stack")

        self.key_editor = KeyEditor(self)
        self.configurator_stack.add_named(self.key_editor, "key_editor")

        self.dial_editor = DialEditor(self)
        self.configurator_stack.add_named(self.dial_editor, "dial_editor")

        self.screen_editor = ScreenEditor(self)
        self.configurator_stack.add_named(self.screen_editor, "screen_editor")

        self.action_chooser = ActionChooser(self)
        self.main_stack.add_named(self.action_chooser, "action_chooser")

        self.action_configurator = ActionConfigurator(self)
        self.main_stack.add_named(self.action_configurator, "action_configurator")

        self.error_page = ErrorPage(self)
        self.main_stack.add_named(self.error_page, "error_page")

        self.page_selector = PageSelector(self.main_window, gl.page_manager, halign=Gtk.Align.CENTER)
        self.header.set_title_widget(self.page_selector)

        self.load_for_identifier(Input.Key("0x0"), 0)

    def let_user_select_action(self, callback_function, identifier: InputIdentifier, *callback_args, **callback_kwargs):
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
        self.action_chooser.show(callback_function=callback_function,
                                 current_stack_page=self.main_stack.get_visible_child(),
                                 identifier=identifier,
                                 callback_args=callback_args,
                                 callback_kwargs=callback_kwargs)

    def show_action_configurator(self):
        self.main_stack.set_visible_child(self.action_configurator)

    def load_for_key(self, identifier: Input.Key, state: int):
        if not isinstance(identifier, Input.Key):
            raise ValueError
        self.active_identifier = identifier
        self.active_state = state

        self.main_stack.set_visible_child(self.configurator_stack)
        self.configurator_stack.set_visible_child(self.key_editor)
        self.key_editor.state_switcher.select_state(state)
        if not self.get_mapped():
            self.on_map_tasks.clear()
            self.on_map_tasks.append(lambda: self.load_for_key(identifier, state))
            return
        # Verify that a controller is selected
        if self.main_window.leftArea.deck_stack.get_visible_child() is None:
            self.error_page.set_error_text(gl.lm.get("right-area-no-deck-selected-error"))
            # self.error_page.set_reload_func(self.main_window.sidebar.load_for_coords)
            # self.error_page.set_reload_args([coords])
            self.show_error()
            return
        # Verify is page is loaded on current controller
        visible_child = gl.app.main_win.leftArea.deck_stack.get_visible_child()
        if visible_child is None:
            return
        controller = visible_child.deck_controller
        if controller is None:
            return
        if controller.active_page == None:
            # self.error_page.set_error_text(gl.lm.get("right-area-no-page-selected-error"))
            # self.error_page.set_reload_args([None])
            #FIXME: User is unable to change or create pages when the error is shown
            self.show_error()
            return

        self.hide_error()

        self.key_editor.load_for_identifier(identifier, state)

    def load_for_dial(self, identifier: Input.Dial, state: int):
        self.active_identifier = identifier
        self.active_state = state
        self.main_stack.set_visible_child(self.configurator_stack)
        self.configurator_stack.set_visible_child(self.key_editor)
        self.key_editor.load_for_identifier(identifier, state)

    def load_for_touchscreen(self, identifier: Input.Touchscreen, state: int):
        self.active_identifier = identifier
        self.active_state = state
        self.main_stack.set_visible_child(self.configurator_stack)
        self.configurator_stack.set_visible_child(self.screen_editor)
        self.screen_editor.load_for_identifier(identifier, state)

    def load_for_identifier(self, identifier: InputIdentifier, state: int):
        if isinstance(identifier, Input.Key):
            self.load_for_key(identifier, state)
        elif isinstance(identifier, Input.Dial):
            self.load_for_dial(identifier, state)
        elif isinstance(identifier, Input.Touchscreen):
            self.load_for_touchscreen(identifier, state)

    def show_error(self):
        if self.main_stack.get_visible_child() == self.error_page:
            return
        
        self.main_stack.set_transition_duration(0)
        self.main_stack.set_visible_child(self.error_page)
        self.main_stack.set_transition_duration(200)


    def hide_error(self):
        if self.main_stack.get_visible_child() != self.error_page:
            return
        
        self.main_stack.set_transition_duration(0)
        self.main_stack.set_visible_child(self.key_editor)
        self.main_stack.set_transition_duration(200)

    def update(self):
        self.load_for_identifier(self.active_identifier, self.active_state)

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
import os
import gi

from src.backend.DeckManagement.DeckController import DeckController
from src.windows.mainWindow.elements.PageSelector import PageSelector
from src.windows.mainWindow.elements.Sidebar.elements.DialEditor import DialEditor
from src.windows.mainWindow.elements.Sidebar.elements.StateSwitcher import StateSwitcher
from src.windows.mainWindow.elements.Sidebar.elements.ScreenEditor import ScreenEditor


gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

# Import Python modules
from loguru import logger as log

# Import own modules
from src.windows.mainWindow.elements.Sidebar.elements.IconSelector import IconSelector
from src.windows.mainWindow.elements.Sidebar.elements.LabelEditor import LabelEditor
from src.windows.mainWindow.elements.Sidebar.elements.ActionManager import ActionManager
from src.windows.mainWindow.elements.Sidebar.elements.ActionChooser import ActionChooser
from src.windows.mainWindow.elements.Sidebar.elements.ActionConfigurator import ActionConfigurator
from src.windows.mainWindow.elements.Sidebar.elements.BackgroundEditor import BackgroundEditor
from src.windows.mainWindow.elements.Sidebar.elements.ImageEditor import ImageEditor
from GtkHelper.GtkHelper import BetterPreferencesGroup, ErrorPage

# Import globals
import globals as gl

class Sidebar(Adw.NavigationPage):
    def __init__(self, main_window, **kwargs):
        super().__init__(hexpand=True, title="Sidebar", **kwargs)
        self.main_window = main_window
        self.active_coords: tuple = None
        self.active_dial: int = None
        self.screen_active: bool = None
        self.active_state: int = 0
        
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

        self.load_for_coords((0, 0), 0)

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
        self.action_chooser.show(callback_function=callback_function, current_stack_page=self.main_stack.get_visible_child(), callback_args=callback_args, callback_kwargs=callback_kwargs)

    def show_action_configurator(self):
        self.main_stack.set_visible_child(self.action_configurator)

    def load_for_coords(self, coords: tuple[int, int], state: int):
        self.active_dial = None
        self.active_coords = coords
        self.active_state = state
        self.screen_active = False

        self.main_stack.set_visible_child(self.configurator_stack)
        self.configurator_stack.set_visible_child(self.key_editor)
        self.key_editor.state_switcher.select_state(state)
        if not self.get_mapped():
            self.on_map_tasks.clear()
            self.on_map_tasks.append(lambda: self.load_for_coords(coords, state))
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

        self.key_editor.load_for_coords(coords, state)

    def load_for_dial(self, n: int):
        self.active_coords = None
        self.active_dial = n
        self.screen_active = False
        self.main_stack.set_visible_child(self.configurator_stack)
        self.configurator_stack.set_visible_child(self.dial_editor)
        self.dial_editor.load_for_dial(n)

    def load_for_screen(self):
        self.active_coords = None
        self.active_dial = None
        self.screen_active = True
        self.main_stack.set_visible_child(self.configurator_stack)
        self.configurator_stack.set_visible_child(self.screen_editor)
        self.screen_editor.load()

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

    def reload(self):
        self.load_for_coords(self.active_coords, self.active_state)


class KeyEditor(Gtk.Box):
    def __init__(self, sidebar: Sidebar, **kwargs):
        self.sidebar:Sidebar = sidebar
        super().__init__(**kwargs)
        self.set_orientation(Gtk.Orientation.VERTICAL)

        self.scrolled_window = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        self.append(self.scrolled_window)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True)
        self.scrolled_window.set_child(self.main_box)

        self.state_switcher = StateSwitcher(margin_start=20, margin_end=20, margin_top=10, margin_bottom=10, hexpand=True)
        self.state_switcher.add_switch_callback(self.on_state_switch)
        self.state_switcher.add_add_new_callback(self.on_add_new_state)
        self.state_switcher.set_n_states(0)
        self.main_box.append(self.state_switcher)

        self.icon_selector = IconSelector(sidebar, halign=Gtk.Align.CENTER, margin_top=40)
        self.main_box.append(self.icon_selector)

        self.image_editor = ImageEditor(sidebar, margin_top=100)
        self.main_box.append(self.image_editor)

        self.background_editor = BackgroundEditor(sidebar, margin_top=25)
        self.main_box.append(self.background_editor)

        self.label_editor = LabelEditor(sidebar, margin_top=25)
        self.main_box.append(self.label_editor)

        self.action_editor = ActionManager(sidebar, margin_top=25, width_request=400)
        self.main_box.append(self.action_editor)

        self.remove_state_button = Gtk.Button(label="Remove State", css_classes=["destructive-action"], margin_top=15, margin_bottom=15, margin_start=15, margin_end=15)
        self.remove_state_button.connect("clicked", self.on_remove_state)
        self.append(self.remove_state_button)



    def on_state_switch(self, *args):
        print("on_state_switch")
        state = self.state_switcher.get_selected_state()
        # self.sidebar.active_state = self.state_switcher.get_selected_state()

        visible_child = gl.app.main_win.leftArea.deck_stack.get_visible_child()
        if visible_child is None:
            return
        controller = visible_child.deck_controller
        if controller is None:
            return
        
        key = controller.keys[controller.coords_to_index(self.sidebar.active_coords)]

        key.set_state(state, update_sidebar=True)
        print(state)
        print("on_state_switch end")

    def on_add_new_state(self, state):
        controller = gl.app.main_win.get_active_controller()
        if controller is None:
            return
        
        key = controller.keys[controller.coords_to_index(self.sidebar.active_coords)]
        key.add_new_state()

        self.remove_state_button.set_visible(self.state_switcher.get_n_states() > 1)

    def on_remove_state(self, button):
        if self.state_switcher.get_n_states() <= 1:
            return

        controller = gl.app.main_win.get_active_controller()
        if controller is None:
            return
        
        active_state = self.state_switcher.get_selected_state()
        
        key = controller.keys[controller.coords_to_index(self.sidebar.active_coords)]
        key.remove_state(active_state)

        self.remove_state_button.set_visible(self.state_switcher.get_n_states() > 1)

    def load_for_coords(self, coords: tuple[int, int], state: int):

        visible_child = gl.app.main_win.leftArea.deck_stack.get_visible_child()
        if visible_child is None:
            return
        controller: DeckController = visible_child.deck_controller
        if controller is None:
            return
        
        key = controller.keys[controller.coords_to_index(coords)]

        self.state_switcher.set_n_states(len(key.states.keys()))
        self.state_switcher.select_state(state)
        key.set_state(state)

        self.remove_state_button.set_visible(self.state_switcher.get_n_states() > 1)

        self.sidebar.active_coords = coords
        self.icon_selector.load_for_coords(coords, state)
        self.image_editor.load_for_coords(coords, state)
        self.label_editor.load_for_coords(coords, state)
        self.action_editor.load_for_coords(coords, state)
        self.background_editor.load_for_coords(coords, state)

class PageEditor(Gtk.Box):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.clamp = Adw.Clamp()
        self.set_margin_top(40)
        self.append(self.clamp)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.clamp.set_child(self.main_box)

        self.pages_group = PagesGroup()
        self.main_box.append(self.pages_group)


class PagesGroup(BetterPreferencesGroup):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.load_pages()

    def load_pages(self):
        pages = gl.page_manager.get_pages()
        for page_path in pages:
            if os.path.dirname(page_path) != os.path.join(gl.DATA_PATH, "pages"):
                continue
            page_row = AdwPageRow(pages_group=self, page_path=page_path)
            self.add(page_row)

        row1 = Adw.EntryRow(title="Title")
        self.add(row1)

        child:Gtk.Box = row1.get_child() # Box
        prefix_box:Gtk.Box = child.get_first_child()
        gizmo = prefix_box.get_next_sibling()
        empty_title = gizmo.get_first_child()
        title = empty_title.get_next_sibling()

        empty_title.set_visible(False)
        title.set_visible(False)

        row1.add_suffix(Gtk.Button(icon_name="view-more-symbolic", css_classes=["flat"], vexpand=False, valign=Gtk.Align.CENTER))


class AdwPageRow(Adw.PreferencesRow):
    def __init__(self, pages_group:PagesGroup, page_path:str = None):
        super().__init__(overflow=Gtk.Overflow.HIDDEN, css_classes=["no-padding"])

        self.pages_group = pages_group
        self.page_path = page_path

        # self.toggle_button = Gtk.ToggleButton(hexpand=True, vexpand=True, css_classes=["no-rounded-corners", "flat"])
        # self.toggle_button.connect("toggled", self.on_toggled)
        # self.set_child(self.toggle_button)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True, margin_bottom=6, margin_top=6,
                                margin_start=10, margin_end=10)
        self.set_child(self.main_box)
        # self.toggle_button.set_child(self.main_box)

        self.label = Gtk.Label(xalign=0, label=os.path.splitext(os.path.basename(page_path))[0], hexpand=False,
                               visible=True, margin_start=2)
        self.main_box.append(self.label)

        self.entry = Gtk.Entry(text=os.path.splitext(os.path.basename(page_path))[0], hexpand=False, xalign=0,
                               css_classes=["flat", "no-border", "no-outline"], has_frame=False,
                               visible=False)
        self.main_box.append(self.entry)

        self.active_icon = Gtk.Image(icon_name="selection-mode-symbolic", css_classes=["flat"], margin_start=3, visible=False)
        self.main_box.append(self.active_icon)

        self.edit_button = Gtk.Button(icon_name="document-edit-symbolic", halign=Gtk.Align.END, css_classes=["flat"], hexpand=True)
        self.edit_button.connect("clicked", self.on_edit_clicked)
        self.main_box.append(self.edit_button)

        # Click ctrl
        self.click_ctrl = Gtk.GestureClick.new()
        self.click_ctrl.set_button(1)
        self.click_ctrl.connect("pressed", self.on_click)
        self.main_box.add_controller(self.click_ctrl)

        # Focus ctrl
        self.focus_ctrl = Gtk.EventControllerFocus()
        self.main_box.add_controller(self.focus_ctrl)
        # self.focus_ctrl.connect("enter", self.on_focus_in)
        self.focus_ctrl.connect("leave", self.on_focus_out)

    def on_toggled(self, button):
        self.active_icon.set_visible(button.get_active())

    def on_loose_focus(self, *args):
        self.set_active(False)
        self.remove_css_class("active-border")
        self.label.set_visible(True)
        self.entry.set_visible(False)
        self.entry.set_hexpand(False)
        self.active_icon.set_visible(False)
        self.active_icon.set_hexpand(True)


    def on_focus_out(self, *args):
        return
        self.on_loose_focus()

    def remove_focus_from_other_pages(self):
        page_rows = self.pages_group.get_rows()
        for row in page_rows:
            if row != self:
                row.on_loose_focus()

    def on_click(self, gesture, n_press, x, y):
        self.remove_focus_from_other_pages()
        if n_press == 1:
            self.set_active(True)
            return

        elif n_press == 2:
            self.on_edit_clicked(self)

    def on_edit_clicked(self, button):
        self.add_css_class("active-border")
        show_label = not self.label.get_visible()
        self.label.set_visible(show_label)
        self.entry.set_visible(not show_label)
        self.entry.grab_focus_without_selecting()
        self.entry.set_position(-1)
        self.active_icon.set_hexpand(False)
        self.entry.set_hexpand(True)

    def set_active(self, active: bool):
        if active:
            self.set_other_rows_inactive()

        self.active_icon.set_visible(active)
        if active:
            self.add_css_class("page-row-active")
        else:
            self.remove_css_class("page-row-active")

    def set_other_rows_inactive(self):
        page_rows = self.pages_group.get_rows()
        for row in page_rows:
            if row != self:
                if hasattr(row, "set_active"):
                    row.set_active(False)
        




class PageRow(Gtk.Overlay):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_halign(Gtk.Align.CENTER)
        self.set_size_request(300, -1)
        self.build()

    def build(self):
        self.toggle_button = Gtk.ToggleButton(hexpand=False, css_classes=["flat"])
        self.set_child(self.toggle_button)

        self.label = Gtk.Label(xalign=0, label="Page Row")
        self.toggle_button.set_child(self.label)

        self.menu_button = Gtk.Button(icon_name="view-more-symbolic", halign=Gtk.Align.END, css_classes=["flat"])
        self.add_overlay(self.menu_button)


class KeyEditorKeyBox(Gtk.Box):
    def __init__(self, sidebar: Sidebar, **kwargs):
        super().__init__(**kwargs)
        self.sidebar:Sidebar = sidebar

        self.scrolled_window = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        self.append(self.scrolled_window)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True)
        self.scrolled_window.set_child(self.main_box)

        self.icon_selector = IconSelector(sidebar, halign=Gtk.Align.CENTER, margin_top=75)
        self.main_box.append(self.icon_selector)

        self.image_editor = ImageEditor(sidebar, margin_top=25)
        self.main_box.append(self.image_editor)

        self.background_editor = BackgroundEditor(sidebar, margin_top=25)
        self.main_box.append(self.background_editor)

        self.label_editor = LabelEditor(sidebar, margin_top=25)
        self.main_box.append(self.label_editor)

        self.action_editor = ActionManager(sidebar, margin_top=25, width_request=400)
        self.main_box.append(self.action_editor)

    def load_for_coords(self, coords: tuple[int, int], state: int):
        self.sidebar.active_coords = coords
        self.sidebar.active_state = state
        self.icon_selector.load_for_coords(coords, state)
        self.image_editor.load_for_coords(coords, state)
        self.label_editor.load_for_coords(coords, state)
        self.action_editor.load_for_coords(coords, state)
        self.background_editor.load_for_coords(coords, state)

class TestStack(Gtk.Stack):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.add_titled(Gtk.Label(), "key", "Key")
        self.add_titled(Gtk.Label(), "pages", "Pages")
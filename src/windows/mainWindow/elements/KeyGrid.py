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
from gi.repository import Gtk, Adw, Gdk, GLib, Gio

# Import Python modules 
from loguru import logger as log
import os

# Imort globals
import globals as gl

# Import own modules
from src.backend.DeckManagement.ImageHelpers import image2pixbuf
from src.backend.DeckManagement.HelperMethods import recursive_hasattr

class KeyGrid(Gtk.Grid):
    """
    Child of PageSettingsPage
    Key grid for the button config
    """
    def __init__(self, deck_controller, deck_page, **kwargs):
        super().__init__(**kwargs)
        self.set_halign(Gtk.Align.CENTER)
        self.set_valign(Gtk.Align.CENTER)
        self.deck_controller = deck_controller
        self.deck_page = deck_page

        self.selected_key = None # The selected key, indicated by a blue frame around it

        self.buttons = [[None] * deck_controller.deck.key_layout()[1] for i in range(deck_controller.deck.key_layout()[0])]

        # Store the copied key from the page
        self.copied_key:dict = None

        self.build()

        self.connect("map", self.on_map)
        self.connect("unmap", self.on_unmap)

        self.load_from_changes()

        GLib.idle_add(self.select_key, 0, 0)

    def regenerate_buttons(self):
        self.buttons = [[None] * self.deck_controller.deck.key_layout()[1] for i in range(self.deck_controller.deck.key_layout()[0])]
    
    def build(self):
        self.clear()

        layout = self.deck_controller.deck.key_layout()
        for x in range(layout[0]):
            for y in range(layout[1]):
                button = KeyButton(self, (layout[0] - x - 1, y))
                self.attach(button, y, layout[0] - x, 1, 1)
                button._set_visible(False) # Hide buttons per default - they will be shown when the the grid is mapped to prevent large grids to resize every child
                x = layout[0] - 1 - x
                self.buttons[x][y] = button
        return
        log.debug(self.deck_controller.deck.key_layout())
        l = Gtk.Label(label="Key Grid")
        self.attach(l, 0, 0, 1, 1)

    def load_from_changes(self):
        # Applt changes made before creation of self
        if not hasattr(self.deck_controller, "ui_grid_buttons_changes_while_hidden"):
            return
        tasks = self.deck_controller.ui_grid_buttons_changes_while_hidden
        for coords, image in list(tasks.items()):
            try:
                self.buttons[coords[0]][coords[1]].set_image(image)
            except IndexError:
                # This happens if the fake deck layout got changed while the app was running
                pass
        
        # Clear tasks
        self.deck_controller.ui_grid_buttons_changes_while_hidden.clear()

    def select_key(self, x: int, y: int):
        self.buttons[x][y].on_focus_in()
        self.buttons[x][y].image.grab_focus()

    def on_map(self, widget):
        self.load_from_changes()

        # Only show buttons when the grid is mapped to prevent large grids to resize every child
        self.set_buttons_visible(True)

    def on_unmap(self, widget):
        # Only show buttons when the grid is mapped to prevent large grids to resize every child
        self.set_buttons_visible(False)

    def clear(self):
        while self.get_first_child() is not None:
            self.remove(self.get_first_child())

    def set_buttons_visible(self, visible):
        for x in range(self.deck_controller.deck.key_layout()[0]):
            for y in range(self.deck_controller.deck.key_layout()[1]):
                self.buttons[x][y]._set_visible(visible)


class KeyButton(Gtk.Frame):
    def __init__(self, key_grid:KeyGrid, coords, **kwargs):
        super().__init__(**kwargs)
        self.set_css_classes(["key-button-frame-hidden"])
        self.coords = coords
        self.state = 0
        self.key_grid = key_grid

        self.pixbuf = None

        # self.button = Gtk.Button(hexpand=True, vexpand=True, css_classes=["key-button"])
        # self.set_child(self.button)

        self.image = Gtk.Image(hexpand=True, vexpand=True, css_classes=["key-image", "key-button"])
        self.image.set_overflow(Gtk.Overflow.HIDDEN)
        self.set_child(self.image)

        # self.button.connect("clicked", self.on_click)

        focus_controller = Gtk.EventControllerFocus()
        self.add_controller(focus_controller)
        focus_controller.connect("enter", self.on_focus_in)

        # Click ctrl
        self.right_click_ctrl = Gtk.GestureClick().new()
        self.right_click_ctrl.connect("pressed", self.on_click)
        self.right_click_ctrl.set_button(0)
        self.image.add_controller(self.right_click_ctrl)

        # Make image focusable
        self.set_focus_child(self.image)
        self.image.set_focusable(True)

        self.init_actions()

        self.init_dnd()

        self.init_shortcuts()

    def init_dnd(self) -> None:
        self.drag_source = Gtk.DragSource()
        self.drag_source.connect("prepare", self.on_drag_prepare)
        self.drag_source.connect("drag-begin", self.on_drag_begin)
        # self.drag_source.connect("drag-end", self.on_drag_end)
        self.add_controller(self.drag_source)

        self.button_dnd_target = Gtk.DropTarget.new(KeyButton, Gdk.DragAction.COPY)
        self.button_dnd_target.set_gtypes([KeyButton, Gdk.FileList])
        self.button_dnd_target.connect("accept", self.on_button_accept)
        self.button_dnd_target.connect("drop", self.on_button_drop)
        self.add_controller(self.button_dnd_target)

    def on_button_accept(self, drop: Gtk.DropTarget, user_data):
        return True

    def on_button_drop(self, drop: Gtk.DropTarget, value: Gdk.ContentProvider, x, y):
        if isinstance(drop.get_value(), KeyButton):
            self.handle_key_button_drop(drop, value, x, y)
       
        elif isinstance(drop.get_value(), Gdk.FileList):
            self.handle_file_drop(drop, value, x, y)

        else:
            drop.reject()
            return False
        
    def handle_key_button_drop(self, drop: Gtk.DropTarget, value: Gdk.ContentProvider, x, y):
        active_page = self.key_grid.deck_controller.active_page
        if active_page is None:
            return
        
        ## Fetch own key_dict
        target_y, target_x = self.coords
        target_key_dict = active_page.dict.get("keys", {}).get(f"{target_x}x{target_y}", {})

        ## Fetch dropped key_dict
        dropped_button = drop.get_value()
        dropped_y, dropped_x = dropped_button.coords
        dropped_key_dict = active_page.dict.get("keys", {}).get(f"{dropped_x}x{dropped_y}", {})

        # Swap keys in the page dict
        active_page.dict.setdefault("keys", {"states": {self.state: {}}})
        active_page.dict["keys"][f"{target_x}x{target_y}"] = dropped_key_dict
        active_page.dict["keys"][f"{dropped_x}x{dropped_y}"] = target_key_dict
        active_page.save()

        active_page.switch_actions_of_keys(f"{target_x}x{target_y}", f"{dropped_x}x{dropped_y}")

        active_page.reload_similar_pages(page_coords=f"{target_x}x{target_y}", reload_self=True)
        active_page.reload_similar_pages(page_coords=f"{dropped_x}x{dropped_y}", reload_self=True)

        # Reload sidebar
        gl.app.main_win.sidebar.load_for_coords(gl.app.main_win.sidebar.active_coords)

    def handle_file_drop(self, drop: Gtk.DropTarget, value: Gdk.ContentProvider, x, y):
        files = value.get_files()
        if len(files) > 1:
            drop.reject()
            return False
        
        file = files[0]
        url = file.get_uri()
        path = file.get_path()

        internal_path = gl.asset_manager_backend.add_custom_media_set_by_ui(url=url, path=path)
        if internal_path is None:
            return False

        # Set media to key
        active_page = self.key_grid.deck_controller.active_page

        page_coords = f"{self.coords[1]}x{self.coords[0]}"
        
        active_page.dict.setdefault("keys", {"states": {self.state: {}}})
        active_page.dict["keys"].setdefault(page_coords, {})
        active_page.dict["keys"][page_coords].setdefault("media", {
            "path": None,
            "loop": True,
            "fps": 30
        })
        active_page.dict["keys"][page_coords]["media"]["path"] = internal_path
        # Save page
        active_page.save()
        key_index = self.key_grid.deck_controller.coords_to_index(reversed(self.coords))
        self.key_grid.deck_controller.load_key(key_index, page=active_page)

        # Update icon selector if current key is selected
        active_coords = gl.app.main_win.sidebar.active_coords
        if active_coords == (self.coords[1], self.coords[0]):
            gl.app.main_win.sidebar.key_editor.icon_selector.load_for_coords((self.coords[1], self.coords[0]))

        
    def on_drag_begin(self, drag_source, data):
        content = data.get_content()

    def on_drag_prepare(self, drag_source, x, y):
        drag_source.set_icon(self.image.get_paintable(), self.get_width() // 2, self.get_height() // 2)
        content = Gdk.ContentProvider.new_for_value(self)
        return content

    def on_dnd_accept(self, drop, user_data):
        return True

        

    def set_image(self, image):
        # Check if we can perform the next checks
        if recursive_hasattr(self, "key_grid.deck_page.grid_page"):
            # Check if this keygrid is on the screen
            if self.key_grid.deck_page.stack.get_visible_child() != self.key_grid.deck_page.grid_page:
                self.key_grid.deck_controller.ui_grid_buttons_changes_while_hidden[self.coords] = image
            # Check if this deck is on the screen
            if self.key_grid.deck_page.deck_stack_child.stack.get_visible_child() != self.key_grid.deck_page:
                self.key_grid.deck_controller.ui_grid_buttons_changes_while_hidden[self.coords] = image

        self.pixbuf = image2pixbuf(image.convert("RGBA"), force_transparency=True)
        GLib.idle_add(self.show_pixbuf, self.pixbuf, priority=GLib.PRIORITY_HIGH)
        # image.close()
        # image = None
        # del image

        # update righthand side key preview if possible
        if recursive_hasattr(gl, "app.main_win.sidebar"):
            self.set_icon_selector_previews(self.pixbuf)

    def set_icon_selector_previews(self, pixbuf):
        if not recursive_hasattr(gl, "app.main_win.sidebar"):
            return
        sidebar = gl.app.main_win.sidebar
        if pixbuf is None:
            return
        if sidebar.key_editor.label_editor.label_group.expander.active_coords != (self.coords[1], self.coords[0]):
            return
        child = gl.app.main_win.leftArea.deck_stack.get_visible_child()
        if child is None:
            return
        if child.deck_controller != self.key_grid.deck_controller:
            return
        # Update icon selector on the top of the right are
        GLib.idle_add(sidebar.key_editor.icon_selector.image.set_from_pixbuf, pixbuf, priority=GLib.PRIORITY_HIGH)
        # Update icon selector in margin editor
        # GLib.idle_add(sidebar.key_editor.image_editor.image_group.expander.margin_row.icon_selector.image.set_from_pixbuf, pixbuf)

    def show_pixbuf(self, pixbuf):
        self.pixbuf = pixbuf
        self.image.set_from_pixbuf(self.pixbuf)

    def on_click(self, gesture, n_press, x, y):
        if gesture.get_current_button() == 1 and n_press == 1:
            # Single left click
            # Select key
            self.image.grab_focus()

        elif gesture.get_current_button() == 1 and n_press == 2:
            # Double left click
            # Simulate key press
            self.simulate_press()
            
        elif gesture.get_current_button() == 3 and n_press == 1:
            # Single right click
            # Open context menu
            popover = KeyButtonContextMenu(self)
            popover.on_open()
            popover.popup()

    def simulate_press(self):
        ## Check if double click to emulate is turned on in the settings
        settings = gl.settings_manager.load_settings_from_file(os.path.join(gl.DATA_PATH, "settings", "settings.json"))
        if not settings.get("key-grid", {}).get("emulate-at-double-click", True):
            return
        
        deck = self.key_grid.deck_controller.deck
        key = self.key_grid.deck_controller.coords_to_index(reversed(self.coords))
        self.key_grid.deck_controller.key_change_callback(deck, key, True)
        # Release key after 100ms
        GLib.timeout_add(100, self.key_grid.deck_controller.key_change_callback, deck, key, False)

    def set_visible(self, visible):
        if visible:
            # Hide other frames
            if self.key_grid.selected_key not in [self, None]:
                # self.key_grid.selected_key.set_css_classes(["key-button-frame-hidden"])
                self.key_grid.selected_key.set_visible(False)
            self.set_css_classes(["key-button-frame"])
            self.key_grid.selected_key = self
        else:
            self.set_css_classes(["key-button-frame-hidden"])
            self.key_grid.selected_key = None

    def on_focus_in(self, *args):
        # Update settings on the righthand side of the screen
        self.update_sidebar()
        # Update preview
        if self.pixbuf is not None:
            self.set_icon_selector_previews(self.pixbuf)
        # self.set_css_classes(["key-button-frame"])
        # self.button.set_css_classes(["key-button-new-small"])
        self.set_visible(True)

    def update_sidebar(self):
        if not recursive_hasattr(gl, "app.main_win.sidebar"):
            return
        sidebar = gl.app.main_win.sidebar
        # Check if already loaded for this coords
        if sidebar.active_coords == (self.coords[1], self.coords[0]):
            if not self.get_mapped():
                return
        sidebar.load_for_coords((self.coords[1], self.coords[0]), self.state)

    # Modifier
    def on_copy(self, *args):
        active_page = self.key_grid.deck_controller.active_page
        if active_page is None:
            return
        y, x = self.coords
        key_dict = active_page.dict["keys"][f"{x}x{y}"]
        gl.app.main_win.key_dict = key_dict
        content = Gdk.ContentProvider.new_for_value(key_dict)
        gl.app.main_win.key_clipboard.set_content(content)

    def on_cut(self, *args):
        self.on_copy()
        self.on_remove()

    def on_paste(self, *args):
        # Check if clipboard is from this StreamController
        if not gl.app.main_win.key_clipboard.is_local():
            #TODO: Use read_value_async to read it instead - This is more like a temporary hack
            return
        
        active_page = self.key_grid.deck_controller.active_page
        if active_page is None:
            return
        y, x = self.coords
        
        active_page.dict["keys"][f"{x}x{y}"] = gl.app.main_win.key_dict
        active_page.reload_similar_pages(page_coords=f"{x}x{y}", reload_self=True)

        # Reload ui
        gl.app.main_win.sidebar.load_for_coords((x, y))

    def on_paste_finished(self, result, data, user_data):
        print(f"result: {result}, data: {data} user_data: {user_data}")
        value = gl.app.main_win.key_clipboard.read_value_finish(result=data)
        print()

    def on_remove(self, *args):
        active_page = self.key_grid.deck_controller.active_page
        if active_page is None:
            return
        y, x = self.coords
        
        if f"{x}x{y}" not in active_page.dict["keys"]:
            return
        del active_page.dict["keys"][f"{x}x{y}"]
        active_page.save()
        active_page.load()


        # Remove media from key
        key_index = self.key_grid.deck_controller.coords_to_index(reversed(self.coords))
        self.key_grid.deck_controller.keys[key_index].set_key_image(None)

        active_page.reload_similar_pages(page_coords=f"{x}x{y}", reload_self=True)

        # Reload ui
        gl.app.main_win.sidebar.load_for_coords((x, y))

    def remove_media(self):
        active_page = self.key_grid.deck_controller.active_page
        if active_page is None:
            return
        y, x = self.coords

        if f"{x}x{y}" not in active_page.dict["keys"]:
            return
        
        active_page.dict["keys"][f"{x}x{y}"]["media"]["path"] = None
        active_page.save()

        active_page.reload_similar_pages(page_coords=f"{x}x{y}", reload_self=True)

        # Reload ui

    def _set_visible(self, visible: bool):
        self.set_visible(visible)
        self.image.set_visible(visible)

    def init_actions(self):
        self.action_group = Gio.SimpleActionGroup()
        self.insert_action_group("key", self.action_group)

        self.copy_action = Gio.SimpleAction.new("copy", None)
        self.cut_action = Gio.SimpleAction.new("cut", None)
        self.paste_action = Gio.SimpleAction.new("paste", None)
        self.remove_action = Gio.SimpleAction.new("remove", None)

        self.copy_action.connect("activate", self.on_copy)
        self.cut_action.connect("activate", self.on_cut)
        self.paste_action.connect("activate", self.on_paste)
        self.remove_action.connect("activate", self.on_remove)

        self.action_group.add_action(self.copy_action)
        self.action_group.add_action(self.cut_action)
        self.action_group.add_action(self.paste_action)
        self.action_group.add_action(self.remove_action)


    def init_shortcuts(self):
        self.shortcut_controller = Gtk.ShortcutController()

        self.copy_shortcut_action = Gtk.CallbackAction.new(self.on_copy)
        self.cut_shortcut_action = Gtk.CallbackAction.new(self.on_cut)
        self.paste_shortcut_action = Gtk.CallbackAction.new(self.on_paste)
        self.remove_shortcut_action = Gtk.CallbackAction.new(self.on_remove)

        self.copy_shortcut = Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string("<Primary>c"), self.copy_shortcut_action)
        self.cut_shortcut = Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string("<Primary>x"), self.cut_shortcut_action)
        self.paste_shortcut = Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string("<Primary>v"), self.paste_shortcut_action)
        self.remove_shortcut = Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string("Delete"), self.remove_shortcut_action)

        self.shortcut_controller.add_shortcut(self.copy_shortcut)
        self.shortcut_controller.add_shortcut(self.cut_shortcut)
        self.shortcut_controller.add_shortcut(self.paste_shortcut)
        self.shortcut_controller.add_shortcut(self.remove_shortcut)

        self.add_controller(self.shortcut_controller)

    def on_update(self, *args, **kwargs):
        pass


class KeyButtonContextMenu(Gtk.PopoverMenu):
    def __init__(self, key_button:KeyButton, **kwargs):
        super().__init__(**kwargs)
        self.key_button = key_button
        self.build()

        self.connect("closed", self.on_close)

        # gl.app.set_accels_for_action("context.test", ["<Primary>t"])

    def on_test(self, *args, **kwargs):
        pass

    def build(self):
        self.set_parent(self.key_button)
        self.set_has_arrow(False)

        self.main_menu = Gio.Menu.new()

        self.copy_paste_menu = Gio.Menu.new()
        self.remove_menu = Gio.Menu.new()

        # Add actions to menus
        self.copy_paste_menu.append("Copy", "key.copy")
        self.copy_paste_menu.append("Cut", "key.cut")
        self.copy_paste_menu.append("Paste", "key.paste")
        self.remove_menu.append("Remove", "key.remove")
        self.remove_menu.append("Update", "key.update")

        # Add sections to menu
        self.main_menu.append_section(None, self.copy_paste_menu)
        self.main_menu.append_section(None, self.remove_menu)

        self.set_menu_model(self.main_menu)

    def on_close(self, *args, **kwargs):
        return
        gl.app.main_win.remove_accel_actions()
    
    def on_open(self, *args, **kwargs):
        return
        gl.app.main_win.add_accel_actions()
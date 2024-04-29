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

from src.backend.DeckManagement.a import add_default_keys

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gdk, Pango, GLib

# Import Python modules
from loguru import logger as log

# Import own modules
from src.backend.DeckManagement.HelperMethods import font_path_from_name, font_name_from_path
from src.backend.PageManagement.Page import NoActionHolderFound, Page
from src.backend.DeckManagement.DeckController import ControllerKey, KeyLabel
from GtkHelper.GtkHelper import RevertButton

# Import globals
import globals as gl

class LabelEditor(Gtk.Box):
    def __init__(self, sidebar, **kwargs):
        self.sidebar = sidebar
        super().__init__(**kwargs)
        self.build()

    def build(self):
        self.clamp = Adw.Clamp()
        self.append(self.clamp)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.clamp.set_child(self.main_box)

        self.label_group = LabelGroup(self.sidebar)
        self.main_box.append(self.label_group)

    def load_for_coords(self, coords: tuple[int, int], state: int):
        self.label_group.load_for_coords(coords, state)


class LabelGroup(Adw.PreferencesGroup):
    def __init__(self, sidebar, **kwargs):
        super().__init__(**kwargs)
        self.sidebar = sidebar

        self.build()

    def build(self):
        self.expander = LabelExpanderRow(self)
        self.add(self.expander)

        return

    def load_for_coords(self, coords: tuple[int, int], state: int):
        self.expander.load_for_coords(coords, state)

class LabelExpanderRow(Adw.ExpanderRow):
    def __init__(self, label_group):
        super().__init__(title=gl.lm.get("label-editor-header"), subtitle=gl.lm.get("label-editor-expander-subtitle"))
        self.label_group = label_group
        self.active_coords = None
        self.build()

    def build(self):
        self.top_row = LabelRow(gl.lm.get("label-editor-top-name"), 0, self.label_group.sidebar, key_name="top")
        self.center_row = LabelRow(gl.lm.get("label-editor-center-name"), 1, self.label_group.sidebar, key_name="center")
        self.bottom_row = LabelRow(gl.lm.get("label-editor-bottom-name"), 2, self.label_group.sidebar, key_name="bottom")

        self.add_row(self.top_row)
        self.add_row(self.center_row)
        self.add_row(self.bottom_row)

    def load_for_coords(self, coords: tuple[int, int], state: int):
        self.active_coords = coords

        self.top_row.load_for_coords(coords, state)
        self.center_row.load_for_coords(coords, state)
        self.bottom_row.load_for_coords(coords, state)

class LabelRow(Adw.PreferencesRow):
    def __init__(self, label_text, label_index: int, sidebar, key_name: str, **kwargs):
        super().__init__(**kwargs)
        self.label_text = label_text
        self.sidebar = sidebar
        self.active_coords = None
        self.state: int = 0
        self.label_index = label_index
        self.key_name = key_name
        self.build()

    def build(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True,
                                margin_start=15, margin_end=15, margin_top=15, margin_bottom=15)
        self.set_child(self.main_box)

        self.label = Gtk.Label(label=self.label_text, xalign=0, margin_bottom=3, css_classes=["bold"])
        self.main_box.append(self.label)

        self.controlled_by_action_label = Gtk.Label(label=gl.lm.get("label-editor-warning-controlled-by-action"), css_classes=["bold", "red-color"], xalign=0,
                                                    margin_bottom=3, visible=False)
        self.main_box.append(self.controlled_by_action_label)

        self.text_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        self.main_box.append(self.text_box)

        self.text_entry = TextEntry()
        # self.text_entry.entry.connect("changed", self.on_change_text)
        self.text_box.append(self.text_entry)

        self.color_chooser_button = ColorChooserButton()
        # self.color_chooser_button.button.connect("color-set", self.on_change_color)
        self.text_box.append(self.color_chooser_button)

        self.font_chooser_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True, margin_top=6)
        self.main_box.append(self.font_chooser_box)

        self.font_chooser_label = Gtk.Label(label=gl.lm.get("label-editor-font-chooser-label"), xalign=0, hexpand=True, margin_start=2)
        self.font_chooser_box.append(self.font_chooser_label)

        self.font_chooser_button = FontChooserButton()
        # self.font_chooser_button.button.connect("font-set", self.on_change_font)
        self.font_chooser_box.append(self.font_chooser_button)

        self.stroke_width_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True, margin_top=6)
        self.main_box.append(self.stroke_width_box)

        self.stroke_width_label = Gtk.Label(label=gl.lm.get("label-editor-font-weight-label"), xalign=0, hexpand=True)
        # self.stroke_width_box.append(self.stroke_width_label)

        self.stroke_width_button = Gtk.SpinButton.new_with_range(0, 5, 1)
        self.stroke_width_button.connect("value-changed", self.on_change_stroke_width)
        # self.stroke_width_box.append(self.stroke_width_button)

        ## Connect reset buttons
        self.text_entry.revert_button.connect("clicked", self.on_reset_text)
        self.color_chooser_button.revert_button.connect("clicked", self.on_reset_color)
        self.font_chooser_button.revert_button.connect("clicked", self.on_reset_font)

        ## Connect set signals
        self.connect_signals()

    def connect_signals(self):
        self.text_entry.entry.connect("changed", self.on_change_text)
        self.color_chooser_button.button.connect("color-set", self.on_change_color)
        self.font_chooser_button.button.connect("font-set", self.on_change_font)

    def disconnect_signals(self):
        try:
            self.text_entry.entry.disconnect_by_func(self.on_change_text)
            self.color_chooser_button.button.disconnect_by_func(self.on_change_color)
            self.font_chooser_button.button.disconnect_by_func(self.on_change_font)
        except Exception as e:
            log.error(f"Failed to disconnect signals. Error: {e}")

    def get_controller_key(self) -> ControllerKey:
        visible_child = gl.app.main_win.leftArea.deck_stack.get_visible_child()
        if visible_child is None:
            return
        controller = visible_child.deck_controller
        if controller is None:
            return
        x, y = self.active_coords

        return controller.keys[controller.coords_to_index((x, y))]

    def load_for_coords(self, coords: tuple[int, int], state: int):
        self.active_coords = coords
        self.state = state
        visible_child = gl.app.main_win.leftArea.deck_stack.get_visible_child()
        if visible_child is None:
            return
        controller = visible_child.deck_controller
        if controller is None:
            return
        page = controller.active_page


        if page == None:
            #TODO: Show error
            return
        
        controller_key = self.get_controller_key()

        use_page_label_properties = controller_key.get_active_state().label_manager.get_use_page_label_properties(position=self.key_name)

        ## Set visibility of revert buttons
        self.text_entry.revert_button.set_visible(use_page_label_properties.get("text", False))
        self.color_chooser_button.revert_button.set_visible(use_page_label_properties.get("color", False))

        font_combined = use_page_label_properties.get("font-family", False) and use_page_label_properties.get("font-size", False)
        self.font_chooser_button.revert_button.set_visible(font_combined)

        ## Set properties
        self.update_values()


    def update_values(self, composed_label: KeyLabel = None):
        self.disconnect_signals()
        if composed_label is None:
            controller_key = self.get_controller_key()
            composed_label = controller_key.get_active_state().label_manager.get_composed_label(position=self.key_name)

        if self.text_entry.entry.get_text() != composed_label.text:
            pos = self.text_entry.entry.get_position()
            
            self.text_entry.entry.set_text(composed_label.text)

            pos = min(pos, len(composed_label.text))
            self.text_entry.entry.set_position(pos)

        hide_details = composed_label.text.strip() == ""
        self.font_chooser_box.set_visible(not hide_details)

        self.set_color(composed_label.color)

        self.font_chooser_button.button.set_font(composed_label.font_name + " " + str(composed_label.font_size) + "px")

        self.connect_signals()


    def set_color(self, color_values: list):
        if len(color_values) == 3:
            color_values.append(255)
        color = Gdk.RGBA()
        color.parse(f"rgba({color_values[0]}, {color_values[1]}, {color_values[2]}, {color_values[3]})")
        self.color_chooser_button.button.set_rgba(color)

    def on_change_color(self, button):
        color = self.color_chooser_button.button.get_rgba()
        green = round(color.green * 255)
        blue = round(color.blue * 255)
        red = round(color.red * 255)

        visible_child = gl.app.main_win.leftArea.deck_stack.get_visible_child()
        if visible_child is None:
            return
        current_deck_controller = visible_child.deck_controller
        if current_deck_controller is None:
            return

        # Set defaults
        add_default_keys(page.dict, ["keys", f"{self.active_coords[0]}x{self.active_coords[1]}", "states", str(self.state), "labels", self.key_name])

        # Get active page
        page = current_deck_controller.active_page
        page.dict["keys"][f"{self.active_coords[0]}x{self.active_coords[1]}"]["states"][str(self.state)]["labels"][self.key_name]["color"] = [red, green, blue]
        page.save()

        # Reload key on all decks that have this page loaded
        for deck_controller in gl.deck_manager.deck_controller:
            if current_deck_controller.active_page.json_path != deck_controller.active_page.json_path:
                continue
            key_index = deck_controller.coords_to_index(self.active_coords)
            if key_index >= len(deck_controller.keys):
                continue
            controller_key = deck_controller.keys[key_index]

            page_label = controller_key.label_manager.page_labels.get(self.key_name)
            if page_label is not None:
                page_label.color = [red, green, blue]
            controller_key.label_manager.update_label(position=self.key_name)

        self.color_chooser_button.revert_button.set_visible(True)

    def get_page(self) -> Page:
        visible_child = gl.app.main_win.leftArea.deck_stack.get_visible_child()
        if visible_child is None:
            return
        controller = visible_child.deck_controller
        if controller is None:
            return None
        return controller.active_page
        


    def on_change_font(self, button):
        font = self.font_chooser_button.button.get_font()

        pango_font = Pango.font_description_from_string(font)

        font_path = font_path_from_name(pango_font.get_family())
        font_size = pango_font.get_size()

        visible_child = gl.app.main_win.leftArea.deck_stack.get_visible_child()
        if visible_child is None:
            return
        current_deck_controller = visible_child.deck_controller
        if current_deck_controller is None:
            return
        # Get active page
        page = current_deck_controller.active_page

        # Set defaults
        add_default_keys(page.dict, ["keys", f"{self.active_coords[0]}x{self.active_coords[1]}", "states", str(self.state), "labels", self.key_name])

        page.dict["keys"][f"{self.active_coords[0]}x{self.active_coords[1]}"]["states"][str(self.state)]["labels"][self.key_name]["font-family"] = pango_font.get_family()
        page.dict["keys"][f"{self.active_coords[0]}x{self.active_coords[1]}"]["states"][str(self.state)]["labels"][self.key_name]["font-size"] = round(font_size/Pango.SCALE)

        page.save()

        # Reload key on all decks that have this page loaded
        for deck_controller in gl.deck_manager.deck_controller:
            if current_deck_controller.active_page.json_path != deck_controller.active_page.json_path:
                continue
            key_index = deck_controller.coords_to_index(self.active_coords)
            if key_index >= len(deck_controller.keys):
                continue
            controller_key = deck_controller.keys[key_index]

            page_label = controller_key.label_manager.page_labels.get(self.key_name)
            if page_label is not None:
                page_label.font_name = pango_font.get_family()
                page_label.font_size = round(font_size/Pango.SCALE)
            controller_key.label_manager.update_label(position=self.key_name)

        self.font_chooser_button.revert_button.set_visible(True)

    def on_reset_font(self, button):
        #FIXME: gets called multiple times
        # Update
        # Set to null
        # Hide
        page = self.get_page()
        page.dict["keys"][f"{self.active_coords[0]}x{self.active_coords[1]}"]["states"][str(self.state)]["labels"][self.key_name]["font-family"] = None
        page.dict["keys"][f"{self.active_coords[0]}x{self.active_coords[1]}"]["states"][str(self.state)]["labels"][self.key_name]["font-size"] = None

        page.save()

        # Reload key on all decks that have this page loaded
        visible_child = gl.app.main_win.leftArea.deck_stack.get_visible_child()
        if visible_child is None:
            return
        current_deck_controller = visible_child.deck_controller
        if current_deck_controller is None:
            return
        for deck_controller in gl.deck_manager.deck_controller:
            if current_deck_controller.active_page.json_path != deck_controller.active_page.json_path:
                continue
            key_index = deck_controller.coords_to_index(self.active_coords)
            if key_index >= len(deck_controller.keys):
                continue
            controller_key = deck_controller.keys[key_index]

            self.update_values()

            label = controller_key.label_manager.page_labels.get(self.key_name)
            if label is not None:
                label.font_name = None
                label.font_size = None
            controller_key.label_manager.update_label(position=self.key_name)
            

        self.font_chooser_button.revert_button.set_visible(False)

    def on_reset_text(self, button):
        page = self.get_page()
        page.dict["keys"][f"{self.active_coords[0]}x{self.active_coords[1]}"]["states"][str(self.state)]["labels"][self.key_name]["text"] = None

        page.save()

        gl.page_manager.update_dict_of_pages_with_path(page.json_path)

        # Reload key on all decks that have this page loaded
        visible_child = gl.app.main_win.leftArea.deck_stack.get_visible_child()
        if visible_child is None:
            return
        current_deck_controller = visible_child.deck_controller
        if current_deck_controller is None:
            return
        for deck_controller in gl.deck_manager.deck_controller:
            if current_deck_controller.active_page.json_path != deck_controller.active_page.json_path:
                continue
            key_index = deck_controller.coords_to_index(self.active_coords)
            if key_index >= len(deck_controller.keys):
                continue
            controller_key = deck_controller.keys[key_index]

            label = controller_key.get_active_state().label_manager.page_labels.get(self.key_name)
            if label is not None:
                label.text = None
            controller_key.get_active_state().label_manager.update_label(position=self.key_name)

        self.text_entry.revert_button.set_visible(False)
        self.update_values()

    def on_reset_color(self, button):
        page = self.get_page()
        page.dict["keys"][f"{self.active_coords[0]}x{self.active_coords[1]}"]["states"][str(self.state)]["labels"][self.key_name]["color"] = None

        page.save()

        # Reload key on all decks that have this page loaded
        visible_child = gl.app.main_win.leftArea.deck_stack.get_visible_child()
        if visible_child is None:
            return
        current_deck_controller = visible_child.deck_controller
        if current_deck_controller is None: 
            return
        for deck_controller in gl.deck_manager.deck_controller:
            if current_deck_controller.active_page.json_path != deck_controller.active_page.json_path:
                continue
            key_index = deck_controller.coords_to_index(self.active_coords)
            if key_index >= len(deck_controller.keys):
                continue
            controller_key = deck_controller.keys[key_index]

            self.update_values()

            label = controller_key.label_manager.page_labels.get(self.key_name)
            if label is not None:
                label.color = None
            controller_key.label_manager.update_label(position=self.key_name)

        self.color_chooser_button.revert_button.set_visible(False)

    def on_change_text(self, entry):
        visible_child = gl.app.main_win.leftArea.deck_stack.get_visible_child()
        if visible_child is None:
            return
        current_deck_controller = visible_child.deck_controller
        if current_deck_controller is None:
            return
        page = current_deck_controller.active_page

        # Set defaults
        coords = f"{self.active_coords[0]}x{self.active_coords[1]}"
        add_default_keys(page.dict, ["keys", coords, "states", str(self.state), "labels", self.key_name])
        page.dict["keys"][coords]["states"][str(self.state)]["labels"][self.key_name]["text"] = entry.get_text()
        page.save()

        # Hide settings if text is empty
        vis = entry.get_text() != ""
        self.font_chooser_box.set_visible(vis)
        self.stroke_width_box.set_visible(vis)

        # Reload key on all decks that have this page loaded
        for current_deck_controller in gl.deck_manager.deck_controller:
            if current_deck_controller.active_page.json_path != current_deck_controller.active_page.json_path:
                continue
            key_index = current_deck_controller.coords_to_index(self.active_coords)
            if key_index >= len(current_deck_controller.keys):
                continue
            controller_key = current_deck_controller.keys[key_index]

            page_label = controller_key.get_active_state().label_manager.page_labels.get(self.key_name)
            if page_label is not None:
                page_label.text = entry.get_text()
            controller_key.get_active_state().label_manager.update_label(position=self.key_name)


        self.text_entry.revert_button.set_visible(True)

    def add_new_label_if_needed(self):
        #TODO: Use this method to update everything on change
        visible_child = gl.app.main_win.leftArea.deck_stack.get_visible_child()
        if visible_child is None:
            return
        current_deck_controller = visible_child.deck_controller
        if current_deck_controller is None:
            return
        for deck_controller in gl.deck_manager.deck_controller:
            if current_deck_controller.active_page.json_path != deck_controller.active_page.json_path:
                continue

            key_index = deck_controller.coords_to_index(self.active_coords)
            if key_index >= len(deck_controller.keys):
                continue
            controller_key = deck_controller.keys[key_index]

            if self.key_name in controller_key.labels:
                continue

            # Add new KeyLabel
            label = KeyLabel(
                text=self.text_entry.get_text(),
                controller_key=controller_key
            )
            controller_key.add_label(label, self.key_name, update=False)


    def on_change_stroke_width(self, button):
        self.add_new_label_if_needed()
        visible_child = gl.app.main_win.leftArea.deck_stack.get_visible_child()
        if visible_child is None:
            return
        current_deck_controller = visible_child.deck_controller
        if current_deck_controller is None:
            return
        page = current_deck_controller.active_page
        page.dict["keys"][f"{self.active_coords[0]}x{self.active_coords[1]}"]["states"][str(self.state)]["labels"][self.key_name]["stroke-width"] = round(self.stroke_width_button.get_value())
        page.save()

        # Reload key on all decks that have this page loaded
        for deck_controller in gl.deck_manager.deck_controller:
            if current_deck_controller.active_page.json_path != deck_controller.active_page.json_path:
                continue
            key_index = deck_controller.coords_to_index(self.active_coords)
            if key_index >= len(deck_controller.keys):
                continue
            controller_key = deck_controller.keys[key_index]

            controller_key.labels[self.key_name].font_weight = round(self.stroke_width_button.get_value())
            controller_key.update()


    def load_defaults(self):
        visible_child = gl.app.main_win.leftArea.deck_stack.get_visible_child()
        if visible_child is None:
            return
        controller = visible_child.deck_controller
        if controller is None:
            return
        page = controller.active_page

        # Update ui
        self.text_entry.set_text(page.dict["keys"][f"{self.active_coords[0]}x{self.active_coords[1]}"]["states"][str(self.state)]["labels"][self.key_name]["text"])
        self.stroke_width_button.set_value(page.dict["keys"][f"{self.active_coords[0]}x{self.active_coords[1]}"]["states"][str(self.state)]["labels"][self.key_name]["stroke-width"])

class TextEntry(Gtk.Box):
    def __init__(self, **kwargs):
        super().__init__(css_classes=["linked"], margin_end=5,  **kwargs)

        self.entry = Gtk.Entry(hexpand=True,placeholder_text=gl.lm.get("label-editor-placeholder-text"))
        self.revert_button = RevertButton()

        self.append(self.entry)
        self.append(self.revert_button)

class ColorChooserButton(Gtk.Box):
    def __init__(self, **kwargs):
        super().__init__(css_classes=["linked"], **kwargs)

        self.button = Gtk.ColorButton()
        self.revert_button = RevertButton()

        self.append(self.button)
        self.append(self.revert_button)

class FontChooserButton(Gtk.Box):
    def __init__(self, **kwargs):
        super().__init__(css_classes=["linked"], **kwargs)

        self.button = Gtk.FontButton()
        self.revert_button = RevertButton()

        self.append(self.button)
        self.append(self.revert_button)
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
from gi.repository import Gtk, Adw, Gdk, Pango

# Import Python modules
from loguru import logger as log

# Import own modules
from src.backend.DeckManagement.HelperMethods import font_path_from_name, font_name_from_path

# Import globals
import globals as gl

class LabelEditor(Gtk.Box):
    def __init__(self, right_area, **kwargs):
        self.right_area = right_area
        super().__init__(**kwargs)
        self.build()

    def build(self):
        self.clamp = Adw.Clamp()
        self.append(self.clamp)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.clamp.set_child(self.main_box)

        self.label_group = LabelGroup(self.right_area)
        self.main_box.append(self.label_group)

    def load_for_coords(self, coords):
        self.label_group.load_for_coords(coords)


class LabelGroup(Adw.PreferencesGroup):
    def __init__(self, right_area, **kwargs):
        super().__init__(**kwargs)
        self.right_area = right_area

        self.build()

    def build(self):
        self.expander = LabelExpanderRow(self)
        self.add(self.expander)

        return

    def load_for_coords(self, coords):
        self.expander.load_for_coords(coords)

class LabelExpanderRow(Adw.ExpanderRow):
    def __init__(self, label_group):
        super().__init__(title=gl.lm.get("label-editor-header"), subtitle=gl.lm.get("label-editor-expander-subtitle"))
        self.label_group = label_group
        self.active_coords = None
        self.build()

    def build(self):
        self.top_row = LabelRow(gl.lm.get("label-editor-top-name"), self.label_group.right_area)
        self.center_row = LabelRow(gl.lm.get("label-editor-center-name"), self.label_group.right_area)
        self.bottom_row = LabelRow(gl.lm.get("label-editor-bottom-name"), self.label_group.right_area)

        self.add_row(self.top_row)
        self.add_row(self.center_row)
        self.add_row(self.bottom_row)

    def load_for_coords(self, coords):
        self.active_coords = coords

        self.top_row.load_for_coords(coords)
        self.center_row.load_for_coords(coords)
        self.bottom_row.load_for_coords(coords)

class LabelRow(Adw.PreferencesRow):
    def __init__(self, label_text, right_area, **kwargs):
        super().__init__(**kwargs)
        self.label_text = label_text
        self.right_area = right_area
        self.active_coords = None
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

        self.entry = Gtk.Entry(hexpand=True, margin_end=5, placeholder_text=gl.lm.get("label-editor-placeholder-text"))
        self.entry.connect("changed", self.on_change_text)
        self.text_box.append(self.entry)

        self.color_chooser_button = Gtk.ColorButton()
        self.color_chooser_button.connect("color-set", self.on_change_color)
        self.text_box.append(self.color_chooser_button)

        self.font_chooser_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True, margin_top=6)
        self.main_box.append(self.font_chooser_box)

        self.font_chooser_label = Gtk.Label(label=gl.lm.get("label-editor-font-chooser-label"), xalign=0, hexpand=True)
        self.font_chooser_box.append(self.font_chooser_label)

        self.font_chooser_button = Gtk.FontButton()
        self.font_chooser_button.connect("font-set", self.on_change_font)
        self.font_chooser_box.append(self.font_chooser_button)

        self.stroke_width_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True, margin_top=6)
        self.main_box.append(self.stroke_width_box)

        self.stroke_width_label = Gtk.Label(label=gl.lm.get("label-editor-font-weight-label"), xalign=0, hexpand=True)
        self.stroke_width_box.append(self.stroke_width_label)

        self.stroke_width_button = Gtk.SpinButton.new_with_range(0, 5, 1)
        self.stroke_width_button.connect("value-changed", self.on_change_stroke_width)
        self.stroke_width_box.append(self.stroke_width_button)

    def load_for_coords(self, coords):
        self.active_coords = coords
        page = self.right_area.main_window.leftArea.deck_stack.get_visible_child().deck_controller.active_page

        x, y = coords

        if page == None:
            #TODO: Show error
            return
        # Set defaults
        page.dict.setdefault("keys", {})
        page.dict["keys"].setdefault(f"{x}x{y}", {})
        page.dict["keys"][f"{x}x{y}"].setdefault("labels", {})
        page.dict["keys"][f"{x}x{y}"]["labels"].setdefault(self.label_text.lower(), {})
        page.dict["keys"][f"{x}x{y}"]["labels"][self.label_text.lower()].setdefault("text", "")
        page.dict["keys"][f"{x}x{y}"]["labels"][self.label_text.lower()].setdefault("color", [255, 255, 255])
        page.dict["keys"][f"{x}x{y}"]["labels"][self.label_text.lower()].setdefault("font-family", "")
        page.dict["keys"][f"{x}x{y}"]["labels"][self.label_text.lower()].setdefault("font-size", 15)
        page.dict["keys"][f"{x}x{y}"]["labels"][self.label_text.lower()].setdefault("stroke-width", 0)

        label = page.dict["keys"][f"{x}x{y}"]["labels"][self.label_text.lower()]
        self.entry.disconnect_by_func(self.on_change_text) # Remove signal to avoid unnecessary updates
        self.entry.set_text(label["text"])
        self.entry.connect("changed", self.on_change_text) # Reconnect signal
        self.set_color(label["color"])
        self.stroke_width_button.set_value(label["stroke-width"])

        self.font_chooser_button.set_font(label["font-family"] + " " + str(label["font-size"]))

        # Hide settings if text is empty
        vis = self.entry.get_text() != ""
        self.font_chooser_box.set_visible(vis)
        self.stroke_width_box.set_visible(vis)

        # Reset appearance
        self.set_sensitive(True)
        self.controlled_by_action_label.set_visible(False)

        # Get all actions for this key - This allows us to see which labels are set by actions and set the sensivity to False
        controller = self.right_area.main_window.leftArea.deck_stack.get_visible_child().deck_controller
        if controller == None:
            return
        action_objects = controller.active_page.get_all_actions_for_key(f"{x}x{y}")
        if action_objects in [None, []]:
            return
        
        action_objects.reverse() # Reverse list, this allows us to easily set the label in the ui to the label set by the last action

        # Set sensitive = False if label is set by an action
        for action in action_objects:
            if isinstance(action, str):
                # No plugin installed for this action
                continue
            for key in action.labels:
                if key == self.label_text.lower():
                    self.set_sensitive(False)
                    self.controlled_by_action_label.set_visible(True)
                    # Update the ui - this is why we reversed the list
                    self.entry.disconnect_by_func(self.on_change_text) # Remove signal to avoid saving to page
                    self.entry.set_text(action.labels[key]["text"])
                    self.entry.connect("changed", self.on_change_text)
                    self.set_color(action.labels[key]["color"])
                    self.stroke_width_button.set_value(action.labels[key]["stroke-width"])
                    self.font_chooser_button.set_font(action.labels[key]["font-family"] + " " + str(action.labels[key]["font-size"]))
                    return

    def set_color(self, color_values: list):
        if len(color_values) == 3:
            color_values.append(255)
        color = Gdk.RGBA()
        color.parse(f"rgba({color_values[0]}, {color_values[1]}, {color_values[2]}, {color_values[3]})")
        self.color_chooser_button.set_rgba(color)

    def on_change_color(self, button):
        color = self.color_chooser_button.get_rgba()
        green = round(color.green * 255)
        blue = round(color.blue * 255)
        red = round(color.red * 255)

        # Get active page
        page = self.right_area.main_window.leftArea.deck_stack.get_visible_child().deck_controller.active_page
        page.dict["keys"][f"{self.active_coords[0]}x{self.active_coords[1]}"]["labels"][self.label_text.lower()]["color"] = [red, green, blue]
        page.save()

        self.update_key()

    def on_change_font(self, button):
        font = self.font_chooser_button.get_font()

        pango_font = Pango.font_description_from_string(font)

        font_path = font_path_from_name(pango_font.get_family())
        font_size = pango_font.get_size()

        # Get active page
        page = self.right_area.main_window.leftArea.deck_stack.get_visible_child().deck_controller.active_page

        page.dict["keys"][f"{self.active_coords[0]}x{self.active_coords[1]}"]["labels"][self.label_text.lower()]["font-family"] = pango_font.get_family()
        page.dict["keys"][f"{self.active_coords[0]}x{self.active_coords[1]}"]["labels"][self.label_text.lower()]["font-size"] = round(font_size/1000)

        page.save()

        self.update_key()

    def on_change_text(self, entry):
        page = self.right_area.main_window.leftArea.deck_stack.get_visible_child().deck_controller.active_page
        page.dict["keys"][f"{self.active_coords[0]}x{self.active_coords[1]}"]["labels"][self.label_text.lower()]["text"] = entry.get_text()
        page.save()

        self.update_key()

        # Hide settings if text is empty
        vis = entry.get_text() != ""
        self.font_chooser_box.set_visible(vis)
        self.stroke_width_box.set_visible(vis)

    def update_key(self):
        controller = self.right_area.main_window.leftArea.deck_stack.get_visible_child().deck_controller
        # controller.reload_keys()
        page = controller.active_page
        page.load()

        # controller.load_key(f"{self.active_coords[0]}x{self.active_coords[1]}", only_labels=True)
        controller.load_key(
            key=controller.coords_to_index(self.active_coords),
            page=controller.active_page,
            load_media=False
        )

    def on_change_stroke_width(self, button):
        page = self.right_area.main_window.leftArea.deck_stack.get_visible_child().deck_controller.active_page
        page.dict["keys"][f"{self.active_coords[0]}x{self.active_coords[1]}"]["labels"][self.label_text.lower()]["stroke-width"] = round(self.stroke_width_button.get_value())
        page.save()

        self.update_key()

    def load_defaults(self):
        page = self.right_area.main_window.leftArea.deck_stack.get_visible_child().deck_controller.active_page

        # Update ui
        self.entry.set_text(page.dict["keys"][f"{self.active_coords[0]}x{self.active_coords[1]}"]["labels"][self.label_text.lower()]["text"])
        self.stroke_width_button.set_value(page.dict["keys"][f"{self.active_coords[0]}x{self.active_coords[1]}"]["labels"][self.label_text.lower()]["stroke-width"])
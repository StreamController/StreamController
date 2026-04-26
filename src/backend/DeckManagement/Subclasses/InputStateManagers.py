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
from copy import copy
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw, ImageOps
from gi.repository import GLib

from src.backend.DeckManagement.HelperMethods import recursive_hasattr
from src.backend.DeckManagement.InputIdentifier import Input
from src.backend.DeckManagement.Subclasses.KeyLabel import KeyLabel
from src.backend.DeckManagement.Subclasses.KeyLayout import ImageLayout

import globals as gl

if TYPE_CHECKING:
    from src.backend.DeckManagement.DeckController import ControllerInput


class LabelManager:
    def __init__(self, controller_input: "ControllerInput"):
        self.controller_input = controller_input
        
        self.page_labels = {}
        self.action_labels = {}
        self.scroll_wait = 25
        self._has_scroll_labels_cache: bool = None

        self.init_labels()
        self.frames: dict[str, dict[str, int]] = {
            "top": {
                "position": 0,
                "wait": self.scroll_wait
            },
            "center": {
                "position": 0,
                "wait": self.scroll_wait
            },
            "bottom": {
                "position": 0,
                "wait": self.scroll_wait
            },
        }

    def init_labels(self):
        for position in ["top", "center", "bottom"]:
            self.page_labels[position] = KeyLabel(self.controller_input)
            self.action_labels[position] = KeyLabel(self.controller_input)
 
    def clear_labels(self):
        self.init_labels()
        self._has_scroll_labels_cache = None

    def set_page_label(self, position: str, label: "KeyLabel", update: bool = True):
        if label is None:
            label = self.page_labels[position]
            label.clear_values()
        else:
            self.page_labels[position] = label

        self._has_scroll_labels_cache = None
        if update:
            self.update_label(position)

    @staticmethod
    def _label_equals(a: "KeyLabel", b: "KeyLabel") -> bool:
        return (a.text == b.text and a.font_size == b.font_size
                and a.font_name == b.font_name and a.color == b.color
                and a.font_weight == b.font_weight and a.style == b.style
                and a.outline_width == b.outline_width
                and a.outline_color == b.outline_color
                and a.alignment == b.alignment)

    def set_action_label(self, position: str, label: "KeyLabel", update: bool = True):
        if label is None:
            label = self.action_labels[position]
            label.clear_values()
        else:
            old = self.action_labels.get(position)
            if old is not None and self._label_equals(old, label):
                return
            self.action_labels[position] = label

        self._has_scroll_labels_cache = None
        GLib.idle_add(self.update_label_editor)
        if update:
            self.update_label(position)

    def update_label_editor(self):
        if not recursive_hasattr(gl, "app.main_win.sidebar.active_identifier"):
            return
        
        if gl.app.main_win.sidebar.active_identifier != self.controller_input.identifier:
            return
        
        controller = gl.app.main_win.get_active_controller()
        if controller is not self.controller_input.deck_controller:
            return

        gl.app.main_win.sidebar.key_editor.label_editor.load_for_identifier(self.controller_input.identifier, self.controller_input.state)
        

    def get_use_page_label_properties(self, position: str) -> dict:
        if self.page_labels.get(position) is None:
            return {
                "text": False,
                "color": False,
                "font-family": False,
                "font-size": False,
                "font-weight": False,
                "font-style": False,
                "outline_width": False,
                "outline_color": False,
                "alignment": False,
            }
        return {
            "text": self.page_labels[position].text is not None,
            "color": self.page_labels[position].color is not None,
            "font-family": self.page_labels[position].font_name is not None,
            "font-size": self.page_labels[position].font_size is not None,
            "font-weight": self.page_labels[position].font_weight is not None,
            "font-style": self.page_labels[position].style is not None,
            "outline_width": self.page_labels[position].outline_width is not None,
            "outline_color": self.page_labels[position].outline_color is not None,
            "alignment": self.page_labels[position].alignment is not None,
        }

    def get_composed_label(self, position: str) -> str:
        use_page_label_properties = self.get_use_page_label_properties(position)
        
        label = copy(self.action_labels.get(position)) or KeyLabel(self.controller_input)

        # Set to page values
        page_label = self.page_labels.get(position)
        if page_label is not None:
            if use_page_label_properties["text"]:
                label.text = page_label.text
            if use_page_label_properties["color"]:
                label.color = page_label.color
            if use_page_label_properties["font-family"]:
                label.font_name = page_label.font_name
            if use_page_label_properties["font-size"]:
                label.font_size = page_label.font_size
            if use_page_label_properties["font-weight"]:
                label.font_weight = page_label.font_weight
            if use_page_label_properties["font-style"]:
                label.style = page_label.style
            if use_page_label_properties["outline_width"]:
                label.outline_width = page_label.outline_width
            if use_page_label_properties["outline_color"]:
                label.outline_color = page_label.outline_color
            if use_page_label_properties["alignment"]:
                label.alignment = page_label.alignment

        injected = self.inject_defaults(label)
        return self.fix_invalid(injected)
    
    def get_composed_labels(self) -> dict[str, "KeyLabel"]:
        composed_labels = {}
        for position in ["top", "center", "bottom"]:
            composed_labels[position] = self.get_composed_label(position)
        return composed_labels

    
    def inject_defaults(self, label: "KeyLabel"):
        if label.text is None:
            label.text = ""
        if label.color is None:
            label.color = gl.settings_manager.font_defaults.get("font-color") or (255, 255, 255, 255)
        if label.font_name is None:
            label.font_name = gl.settings_manager.font_defaults.get("font-family") or gl.fallback_font
        if label.font_size is None:
            label.font_size = round(gl.settings_manager.font_defaults.get("font-size") or 15)
        if label.font_weight is None:
            label.font_weight = round(gl.settings_manager.font_defaults.get("font-weight") or 400)
        if label.style is None:
            label.style = gl.settings_manager.font_defaults.get("font-style") or "normal"
        if label.outline_width is None:
            label.outline_width = round(gl.settings_manager.font_defaults.get("outline-width") or 2)
        if label.outline_color is None:
            label.outline_color = gl.settings_manager.font_defaults.get("outline-color") or (0, 0, 0, 255)
        if label.alignment is None:
            label.alignment = gl.settings_manager.font_defaults.get("alignment") or "center"

        return label
    
    def fix_invalid(self, label: "KeyLabel"):
        if not isinstance(label.text, str):
            label.text = str(label.text)

        return label

    def update_label(self, position: str):
        self.controller_input.update()

    def get_available_width(self) -> int:
        return self.controller_input.get_image_size()[0]

    def get_has_scroll_labels(self) -> bool:
        if self._has_scroll_labels_cache is not None:
            return self._has_scroll_labels_cache

        labels = self.get_composed_labels()
        for label in labels:
            if labels[label].text is not None and labels[label].text != "":
                _, _, w, _ = labels[label].get_font().getbbox(labels[label].text)
                if w > self.get_available_width():
                    self._has_scroll_labels_cache = True
                    return True
        self._has_scroll_labels_cache = False
        return False

    def add_labels_to_image(self, image: Image.Image) -> Image.Image:
        # image = image.rotate(self.deck.get_rotation()*-1)
        draw = ImageDraw.Draw(image)

        labels = self.get_composed_labels()
        for label in labels:
            text = labels[label].text
            if text in [None, ""]:
                continue

            color = tuple(labels[label].color)
            font = labels[label].get_font()
            outline_width = labels[label].outline_width
            outline_color = tuple(labels[label].outline_color)
            alignment = labels[label].alignment

            _, _, w, h = draw.textbbox((0, 0), text, font=font)

            # Calculate x position based on alignment
            padding = 3
            if alignment == "left":
                x_position = padding
                anchor_x = "l"
            elif alignment == "right":
                x_position = image.width - padding
                anchor_x = "r"
            else:  # center (default)
                x_position = image.width / 2
                anchor_x = "m"

            rolling_labels_enabled = gl.settings_manager.get_app_settings().get("general", {}).get("rolling-labels", True)
            if rolling_labels_enabled and image.width < w:
                # Need to scroll - always use center anchor for scrolling
                start = image.width / 2 - (image.width - w) / 2 + 10
                stop = image.width / 2 + (image.width - w) / 2 - 10

                x_position = start - self.frames[label]["position"]
                anchor_x = "m"
                if x_position < stop:
                    if self.frames[label]["wait"] == 0:
                        x_position = start
                        self.frames[label]["position"] = 0
                        self.frames[label]["wait"] = self.scroll_wait
                    else:
                        self.frames[label]["wait"] -= 1
                elif self.controller_input.media_ticks % 2 == 0:
                    if self.frames[label]["wait"] == 0:
                        if x_position == stop:
                            self.frames[label]["wait"] = self.scroll_wait

                        self.frames[label]["position"] += 1
                    else:
                        self.frames[label]["wait"] -= 1


            if label == "top":
                position = (x_position, h/2 + 3)
            elif label == "bottom":
                position = (x_position, image.height - h/2 - 3)
            else:
                position = (x_position, (image.height - 0) / 2)

            # Use appropriate anchor based on alignment (x-anchor + "m" for vertical middle)
            anchor = anchor_x + "m"

            draw.text(position,
                      text=text, font=font, anchor=anchor, align=alignment,
                      fill=color, stroke_width=outline_width,
                      stroke_fill=outline_color)

        del draw

        return image.copy()
        # return image.copy().rotate(self.deck.get_rotation())


class LayoutManager:
    def __init__(self, controller_input: "ControllerInput"):
        self.controller_input = controller_input

        self.action_layout = ImageLayout()
        self.page_layout = ImageLayout()

    def clear(self):
        self.action_layout = ImageLayout()
        self.page_layout = ImageLayout()

    def get_use_page_layout_properties(self) -> dict:
        return {
            "valign": self.page_layout.valign is not None,
            "halign": self.page_layout.halign is not None,
            "fill-mode": self.page_layout.fill_mode is not None,
            "size": self.page_layout.size is not None
        }
    
    def get_composed_layout(self) -> ImageLayout:
        use_page_layout_properties = self.get_use_page_layout_properties()
        
        layout = copy(self.action_layout) or ImageLayout()

        # Set to page values
        page_layout = self.page_layout
        if use_page_layout_properties["valign"]:
            layout.valign = page_layout.valign
        if use_page_layout_properties["halign"]:
            layout.halign = page_layout.halign
        if use_page_layout_properties["fill-mode"]:
            layout.fill_mode = page_layout.fill_mode
        if use_page_layout_properties["size"]:
            layout.size = page_layout.size

        return self.inject_defaults(layout)
    
    def inject_defaults(self, layout: ImageLayout):
        if layout.valign is None:
            layout.valign = 0
        if layout.halign is None:
            layout.halign = 0
        if layout.fill_mode is None:
            if isinstance(self.controller_input.identifier, Input.Key):
                layout.fill_mode = "cover"
            else:
                layout.fill_mode = "contain"
        if layout.size is None:
            layout.size = 1

        return layout
    
    def set_page_layout(self, layout: ImageLayout, update: bool = True):
        self.page_layout = layout

        if update:
            self.update()

    def set_action_layout(self, layout: ImageLayout, update: bool = True):
        self.action_layout = layout

        if update:
            self.update()

    def update(self):
        self.controller_input.update()
        GLib.idle_add(self.update_layout_editor)

    def update_layout_editor(self):
        if not recursive_hasattr(gl, "app.main_win.leftArea.deck_stack"):
            return
        
        if gl.app.main_win.sidebar.active_identifier != self.controller_input.identifier:
            return

        controller = gl.app.main_win.get_active_controller()
        if controller is not self.controller_input.deck_controller:
            return

        gl.app.main_win.sidebar.key_editor.image_editor.load_for_identifier(self.controller_input.identifier, self.controller_input.state)

    def add_image_to_background(self, image: Image.Image, background: Image.Image) -> Image.Image:
        if image is None:
            return background
        layout = self.get_composed_layout()

        width, height = background.size
        image_size = (int(width * layout.size), int(height * layout.size))

        if 0 in image_size:
            return background.copy()

        if layout.fill_mode == "stretch":
            image_resized = image.resize(image_size, Image.Resampling.HAMMING)
        elif layout.fill_mode == "cover":
            image_resized = ImageOps.cover(image, image_size, Image.Resampling.HAMMING)
        else:
            image_resized = ImageOps.contain(image, image_size, Image.Resampling.HAMMING)

        halign = layout.halign
        valign = layout.valign

        left_margin = int((background.width - image_resized.width) * (halign + 1) / 2)
        top_margin = int((background.height - image_resized.height) * (valign + 1) / 2)

        # Create an image copy for the result
        final_image = background.copy()

        # Paste the resized foreground onto the composite image at the calculated position
        if image_resized.has_transparency_data:
            final_image.paste(image_resized, (left_margin, top_margin), image_resized)
        else:
            final_image.paste(image_resized, (left_margin, top_margin))

        return final_image
    

class BackgroundManager:
    def __init__(self, controller_input: "ControllerInput"):
        self.controller_input = controller_input
        
        self.action_color: list[int] = None
        self.page_color: list[int] = None

    def set_action_color(self, color: list[int], update: bool = True) -> None:
        self.action_color = color
        if isinstance(color, list) and len(color) == 3:
            self.action_color.append(255)

        if update:
            self.update()

    def set_page_color(self, color: list[int], update: bool = True, update_ui: bool = True) -> None:
        self.page_color = color
        if isinstance(color, list) and len(color) == 3:
            self.page_color.append(255)

        if update:
            self.update(ui=update_ui)

    def update(self, ui: bool = True):
        self.controller_input.update()
        if ui:
            GLib.idle_add(self.update_background_editor)

    def update_background_editor(self):
        if not recursive_hasattr(gl, "app.main_win.leftArea.deck_stack"):
            return
        
        if gl.app.main_win.sidebar.active_identifier != self.controller_input.identifier:
            return

        controller = gl.app.main_win.get_active_controller()
        if controller is not self.controller_input.deck_controller:
            return

        gl.app.main_win.sidebar.key_editor.background_editor.load_for_identifier(self.controller_input.identifier, self.controller_input.state)

    def get_color_is_set(self, color: list[int]) -> bool:
        return color not in [None, [None]*3, [None]*4]

    def get_use_page_background(self) -> dict:
        return self.get_color_is_set(self.page_color)
    
    def get_composed_color(self) -> list[int]:
        if self.get_use_page_background() and self.get_color_is_set(self.page_color):
            return self.page_color
        elif self.get_color_is_set(self.action_color):
            return self.action_color
        else:
            return [0] * 4

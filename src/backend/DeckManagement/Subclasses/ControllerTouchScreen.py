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
import os
from typing import TYPE_CHECKING

from PIL import Image, ImageOps
from StreamDeck.Devices.StreamDeck import TouchscreenEventType
from StreamDeck.ImageHelpers import PILHelper
from gi.repository import GLib
from loguru import logger as log

from src.backend.DeckManagement.HelperMethods import recursive_hasattr
from src.backend.DeckManagement.InputIdentifier import Input, InputIdentifier
from src.backend.DeckManagement.Subclasses.ControllerInput import (
    ControllerInput,
    ControllerInputState,
)

import globals as gl

if TYPE_CHECKING:
    from src.backend.DeckManagement.DeckController import (
        ControllerDial,
        DeckController,
    )


class ControllerTouchScreen(ControllerInput):
    def __init__(self, deck_controller: "DeckController", ident: InputIdentifier):
        super().__init__(deck_controller, ControllerTouchScreenState, ident)

        self.enable_states = False

    @staticmethod
    def Available_Identifiers(deck):
        if deck.is_touch():
            return ["sd-plus"]
        return []

    def update(self) -> None:
        image = self.get_current_image()
        
        # Touchscreen only supports JPEG, so composite RGBA onto background
        if image.mode == "RGBA":
            # Create a background image (black by default)
            background = Image.new("RGB", image.size, (0, 0, 0))
            # Composite the RGBA image onto the RGB background
            background.paste(image, (0, 0), image)
            image = background
        
        native_image = PILHelper.to_native_touchscreen_format(self.deck_controller.deck, image)
        self.deck_controller.media_player.add_touchscreen_task(native_image)

        self.set_ui_image(self.get_current_image())

    def generate_empty_image(self) -> Image.Image:
        return Image.new("RGBA", self.get_screen_dimensions(), (0, 0, 0, 0))
    
    def get_dial_image_area(self, identifier: Input.Dial) -> tuple[int, int, int, int]:
        width, height = self.get_screen_dimensions()

        n_dials = len(self.deck_controller.inputs[Input.Dial])
        dial_index = identifier.index

        start_x = int((dial_index / n_dials) * width)
        start_y = 0
        end_x = int(((dial_index + 1) / n_dials) * width)
        end_y = height

        return start_x, start_y, end_x, end_y
    
    def get_dial_image_area_size(self) -> tuple[int, int]:
        width, height = self.get_screen_dimensions()

        n_dials = len(self.deck_controller.inputs[Input.Dial])

        return int(width / n_dials), height
    
    def get_empty_dial_image(self) -> Image.Image:
        screen_width, screen_height = self.get_screen_dimensions()

        n_dials = len(self.deck_controller.inputs[Input.Dial])

        return Image.new("RGBA", (screen_width // n_dials, screen_height), (0, 0, 0, 0))

    def set_ui_image(self, image: Image.Image) -> None:
        if recursive_hasattr(self, "deck_controller.own_deck_stack_child.page_settings.deck_config.screenbar.image") and gl.app.main_win.get_mapped():
            screenbar = self.deck_controller.own_deck_stack_child.page_settings.deck_config.screenbar
            GLib.idle_add(screenbar.image.set_image, image)
        else:
            self.deck_controller.ui_image_changes_while_hidden[self.identifier] = image

    def get_current_image(self) -> Image.Image:
        active_state = self.get_active_state()
        return active_state.get_current_image()

    def event_callback(self, event_type, value):
        screensaver_was_showing = self.deck_controller.screen_saver.showing
        if event_type in (TouchscreenEventType.SHORT, TouchscreenEventType.LONG, TouchscreenEventType.DRAG):
            self.deck_controller.screen_saver.on_key_change()
        if screensaver_was_showing:
            return
        
        active_state = self.get_active_state()
        if event_type == TouchscreenEventType.DRAG:
            # Check if from left to right or the other way
            if value['x'] > value['x_out']:
                active_state.own_actions_event_callback_threaded(
                    Input.Touchscreen.Events.DRAG_LEFT
                )
            else:
                active_state.own_actions_event_callback_threaded(
                    Input.Touchscreen.Events.DRAG_RIGHT
                )


        #TODO get matching actions from the dials
        elif event_type in (TouchscreenEventType.SHORT, TouchscreenEventType.LONG):
            dial = self.get_dial_for_touch_x(value['x'])
            if dial is not None:
                dial_active_state = dial.get_active_state()
                if dial_active_state is not None:

                    event = Input.Dial.Events.SHORT_TOUCH_PRESS
                    if event_type == TouchscreenEventType.LONG:
                        event = Input.Dial.Events.LONG_TOUCH_PRESS

                    dial_active_state.own_actions_event_callback_threaded(
                        event,
                        data={"x": value['x'], "y": value['y']},
                        show_notifications=True
                    )

    def get_dial_for_touch_x(self, touch_x: float) -> "ControllerDial":
        screen_width = self.deck_controller.get_touchscreen_image_size()[0]
        n_dials = len(self.deck_controller.inputs[Input.Dial])
        dial_index = int((touch_x / screen_width) * n_dials)

        return self.deck_controller.get_input(Input.Dial(str(dial_index)))
    
    def get_screen_dimensions(self) -> tuple[int, int]:
        return self.deck_controller.get_touchscreen_image_size()


class ControllerTouchScreenState(ControllerInputState):
    def __init__(self, controller_touch: "ControllerTouchScreen", state: int):
        super().__init__(controller_touch, state)

        self.controller_touch = controller_touch

    def set_current_image(self, image: Image.Image):
        self.current_image = image

        self.update()

    def get_current_image(self) -> Image.Image:
        screen_width, screen_height = self.controller_touch.get_screen_dimensions()
        
        # Start with background image if set
        background: Image.Image = None
        active_page = self.controller_touch.deck_controller.active_page
        background_image_path = active_page.get_background_image(
            identifier=self.controller_touch.identifier, 
            state=self.state
        )
        
        if background_image_path and os.path.isfile(background_image_path):
            try:
                with Image.open(background_image_path) as img:
                    # Resize to exact touchscreen dimensions (KISS - exact dimensions)
                    background = ImageOps.fit(img, (screen_width, screen_height), Image.Resampling.LANCZOS).convert("RGBA")
            except Exception as e:
                log.error(f"Error loading background image: {e}")
                background = None
        
        # Get background color from touchscreen state's background_manager
        background_color = self.background_manager.get_composed_color()
        
        # If no background image, start with empty or colored background
        if background is None:
            # If background color has transparency (alpha < 255), start with transparent
            if background_color[-1] < 255:
                background = self.controller_touch.generate_empty_image()
            
            # If background color is set (alpha > 0), create colored background
            if background_color[-1] > 0:
                background_color_img = Image.new("RGBA", (screen_width, screen_height), color=tuple(background_color))
                
                if background is None:
                    # Use the color as the only background - happens if background color alpha is 255
                    background = background_color_img
                else:
                    # Paste color on top of transparent background
                    background.paste(background_color_img, (0, 0), background_color_img)
            
            # If no background color was set, use empty image
            if background is None:
                background = self.controller_touch.generate_empty_image()
        else:
            # Background image exists - apply color overlay if set
            if background_color[-1] > 0:
                background_color_img = Image.new("RGBA", (screen_width, screen_height), color=tuple(background_color))
                # Blend color over image
                background = Image.alpha_composite(background, background_color_img)

        # Paste dial images on top of the background
        for dial in self.controller_touch.deck_controller.inputs[Input.Dial]:
            state = dial.get_active_state()
            image_area = self.controller_touch.get_dial_image_area(dial.identifier)
            dial_image = state.get_rendered_touch_image()

            background.paste(dial_image, image_area, dial_image)

        return background


    def update(self):
        if self.controller_touch.get_active_state() is self:
            self.controller_touch.update()

    

    def set_dial_image(self, identifier: Input.Dial, image: Image.Image, update: bool = True):
        return
        assert isinstance(identifier, Input.Dial)

        area = self.get_dial_image_area(identifier)
        width, height = area[2] - area[0], area[3] - area[1]

        # Clear underground
        empty_dial = self.get_empty_dial_image()
        # Use alpha mask if empty_dial has transparency to prevent edge artifacts
        if empty_dial.has_transparency_data:
            self.current_image.paste(empty_dial, area, empty_dial)
        else:
            self.current_image.paste(empty_dial, area)

        # Contain image into the area
        image = ImageOps.contain(image, (width, height), Image.Resampling.HAMMING)

        # Get x, y for centered position
        x = area[0] + int((width - image.width) / 2)
        y = area[1] + int((height - image.height) / 2)

        self.current_image.paste(image, (x, y), image)

        self.current_image.save("sd.png")

        if update:
            self.update()


    def clear(self):
        self.set_current_image(self.controller_touch.generate_empty_image())

    def close_resources(self) -> None:
        self.current_image.close()
        del self.current_image

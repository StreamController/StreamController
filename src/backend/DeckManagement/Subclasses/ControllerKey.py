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
import time
from copy import copy
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw
from StreamDeck.ImageHelpers import PILHelper
from gi.repository import GLib

from src.backend.DeckManagement.HelperMethods import (
    is_image,
    is_svg,
    is_video,
    svg_to_pil,
)
from src.backend.DeckManagement.InputIdentifier import Input
from src.backend.DeckManagement.Subclasses.ControllerInput import (
    ControllerInput,
    ControllerInputState,
)
from src.backend.DeckManagement.Subclasses.KeyGIF import KeyGIF
from src.backend.DeckManagement.Subclasses.KeyImage import InputImage
from src.backend.DeckManagement.Subclasses.KeyLabel import KeyLabel
from src.backend.DeckManagement.Subclasses.KeyLayout import ImageLayout
from src.backend.DeckManagement.Subclasses.KeyVideo import InputVideo

import globals as gl

if TYPE_CHECKING:
    from src.backend.DeckManagement.DeckController import DeckController
    from src.windows.mainWindow.elements.KeyGrid import KeyButton


class ControllerKey(ControllerInput):
    def __init__(self, deck_controller: "DeckController", ident: Input.Key):
        super().__init__(deck_controller, ControllerKeyState, ident)
        self.index = ident.get_index(deck_controller)
        # Keep track of the current state of the key because self.deck_controller.deck.key_states seams to give inverted values in get_current_deck_image
        self.press_state: bool = self.deck_controller.deck.key_states()[self.index]

        self.down_start_time: float = None
        
        # GIF timing tracking
        self.last_gif_update_time: float = 0

    def on_hold_timer_end(self):
        state = self.get_active_state()
        state.own_actions_event_callback_threaded(
            event=Input.Key.Events.HOLD_START
        )

    @staticmethod
    def Available_Identifiers(deck):
        return map(lambda x: f"{x[0]}x{x[1]}", map(lambda x: ControllerKey.Index_To_Coords(deck, x), range(deck.key_count())))

    @staticmethod
    def Index_To_Coords(deck, index):
        rows, cols = deck.key_layout()    
        y = index // cols
        x = index % cols
        return x, y
    
    @staticmethod
    def Coords_To_Index(deck, coords):
        if type(coords) == str:
            coords = coords.split("x")
        x, y = map(int, coords)
        rows, cols = deck.key_layout()
        return y * cols + x

    def update(self, force: bool = False):
        image = self.get_current_image()

        # Quick hash check - skip expensive conversion if image unchanged
        img_hash = hash(image.tobytes())
        if not force and img_hash == getattr(self, '_last_img_hash', None):
            image.close()
            return
        self._last_img_hash = img_hash

        # Handle transparency properly - composite RGBA onto RGB to preserve smooth edges
        if image.mode == "RGBA":
            rgb_background = Image.new("RGB", image.size, (0, 0, 0))
            rgb_background.paste(image, (0, 0), image)
            rgb_image = rgb_background.rotate(self.deck_controller.deck.get_rotation())
        else:
            rgb_image = image.convert("RGB").rotate(self.deck_controller.deck.get_rotation())

        if self.deck_controller.is_visual():
            native_image = PILHelper.to_native_key_format(self.deck_controller.deck, rgb_image)
            rgb_image.close()
            self.deck_controller.media_player.add_image_task(self.index, native_image)

        del rgb_image
        self.set_ui_key_image(image)

    def get_active_state(self) -> "ControllerKeyState":
        return super().get_active_state()

    def on_media_player_tick(self) -> None:
        self.media_ticks += 1
        current_time = time.time()

        state = self.get_active_state()
        needs_update = False
        
        # Check if we need to update based on content type
        if state.key_video is not None:
            if isinstance(state.key_video, KeyGIF):
                # Use GIF frame delay timing
                if self.last_gif_update_time == 0:
                    self.last_gif_update_time = current_time
                    needs_update = True
                else:
                    frame_delay = state.key_video.get_frame_delay()
                    if current_time - self.last_gif_update_time >= frame_delay:
                        self.last_gif_update_time = current_time
                        needs_update = True
            else:
                # For non-GIF videos, use the original FPS-based logic
                needs_update = True
        elif self.deck_controller.background.video is not None or state.label_manager.get_has_scroll_labels():
            # Other content types
            needs_update = True

        if needs_update:
            self.update()

    def event_callback(self, press_state):
        screensaver_was_showing = self.deck_controller.screen_saver.showing
        if press_state:
            # Only on key down this allows plugins to control screen saver without directly deactivating it
            self.deck_controller.screen_saver.on_key_change()
        if screensaver_was_showing:
            return
        
        self.deck_controller.mark_page_ready_to_clear(False)
        self.press_state = press_state

        self.update()

        active_state = self.get_active_state()
        if press_state: # Key down
            self.down_start_time = time.time()
            self.start_hold_timer()
            active_state.own_actions_event_callback_threaded(
                event=Input.Key.Events.DOWN,
                show_notifications=True
            )

        elif self.down_start_time is not None: # Key up
            if time.time() - self.down_start_time >= self.deck_controller.hold_time:
                active_state.own_actions_event_callback_threaded(
                    event=Input.Key.Events.HOLD_STOP
                )
            else:
                active_state.own_actions_event_callback_threaded(
                    event=Input.Key.Events.SHORT_UP
                )
            self.down_start_time = None
            self.stop_hold_timer()
            active_state.own_actions_event_callback_threaded(
                event=Input.Key.Events.UP,
                show_notifications=False
            )
        self.deck_controller.mark_page_ready_to_clear(True)

    def get_current_image(self) -> Image.Image:
        state = self.get_active_state()

        background_color = self.get_active_state().background_manager.get_composed_color()

        background: Image.Image = None
        # Only load the background image if it's not gonna be hidden by the background color
        if background_color[-1] < 255:
            background = copy(self.deck_controller.background.tiles[self.index])

        if background_color[-1] > 0:
            background_color_img = Image.new("RGBA", self.deck_controller.get_key_image_size(), color=tuple(background_color))
            
            if background is None:
                # Use the color as the only background - happens if background color alpha is 255
                background = background_color_img
            else:
                background.paste(background_color_img, (0, 0), background_color_img)


        if background is None:
            background = self.deck_controller.generate_alpha_key().copy()

        if state._overlay:
            height = round(self.deck_controller.get_key_image_size()[1]*0.75)
            img = state._overlay.resize((height, height))
            background.paste(img, (int((self.deck_controller.get_key_image_size()[0] - height) // 2), int((self.deck_controller.get_key_image_size()[1] - height) // 2)), img)
            return background


        key_image: Image.Image = None
        # rotation = self.deck_controller.get_deck_settings().get("rotation", {}).get("value", 0)
        if state.key_image is not None:
            image = state.key_image.get_raw_image()
            key_image = state.layout_manager.add_image_to_background(
                image=image,
                background=background
            )
        elif state.key_video is not None:
            image = state.key_video.get_raw_image()
            key_image = state.layout_manager.add_image_to_background(
                image=image,
                background=background)
        else:
            key_image = background

        labeled_image = state.label_manager.add_labels_to_image(key_image)

        if self.is_pressed():
            labeled_image = self.shrink_image(labeled_image)

        if self.has_unavailable_action() and not self.deck_controller.screen_saver.showing:
            labeled_image = self.add_warning_point(labeled_image)

        if background is not None:
            background.close()

        key_image.close()

        return labeled_image
    
    def add_warning_point(self, image: Image.Image, margin: int = 10, size: int = 10, color: tuple = (255, 150, 80)) -> Image.Image:
        draw = ImageDraw.Draw(image)

        # Calculate the coordinates of the top right circle
        width, height = image.size
        top_right_x = width - margin - size
        top_right_y = margin

        # Draw the circle
        draw.ellipse((top_right_x, top_right_y, top_right_x + size, top_right_y + size), fill=color, outline=(0, 0, 0), width=2)

        del draw
        return image
    

    def is_pressed(self) -> bool:
        return self.press_state
    
    def add_border(self, image: Image.Image) -> Image.Image:
        image = image.copy()
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((-1, -1, image.width, image.height), fill=None, outline=(255, 105, 0), width=8, radius=8)

        return image

    def shrink_image(self, image: Image.Image, factor: float = 0.7) -> Image.Image:
        image = image.copy()
        width = int(image.width * factor)
        height = int(image.height * factor)
        image = image.resize((width, height))

        background = Image.new("RGBA", self.deck_controller.get_key_image_size(), (0, 0, 0, 0))

        if image.has_transparency_data:
            background.paste(image, (int((self.deck_controller.get_key_image_size()[0] - width) / 2), int((self.deck_controller.get_key_image_size()[1] - height) / 2)), image)
        else:
            background.paste(image, (int((self.deck_controller.get_key_image_size()[0] - width) / 2), int((self.deck_controller.get_key_image_size()[1] - height) / 2)))

        image.close()

        return background
    
    def load_from_input_dict(self, input_dict, update: bool = True, load_labels: bool = True, load_media: bool = True, load_background_color: bool = True):
        """
        Attention: Disabling load_media might result into disabling custom user assets
        """
        n_states = len(input_dict.get("states", {}))
        self.create_n_states(max(1, n_states))

        old_state_index = self.state

        self.state = 0

        #TODO: Reset states
        for state in input_dict.get("states", {}):
            state: ControllerKeyState = self.states.get(int(state))
            if state is None:
                continue

            state_dict = input_dict["states"][str(state.state)]

            ## Load media - why here? so that it doesn't overwrite the images chosen by the actions
            if load_media:
                state.key_image = None
                state.key_video = None
            
            if load_labels:
                state.label_manager.clear_labels()

            # Reset action layout
            layout = ImageLayout()
            state.layout_manager.set_action_layout(layout, update=False)

            state.own_actions_update() # Why not threaded? Because this would mean that some image changing calls might get executed after the next lines which blocks custom assets

            ## Load labels
            if load_labels:
                for label in state_dict.get("labels", []):
                    key_label = KeyLabel(
                        controller_input=self,
                        text=state_dict["labels"][label].get("text"),
                        font_size=state_dict["labels"][label].get("font-size"),
                        font_name=state_dict["labels"][label].get("font-family"),
                        font_weight=state_dict["labels"][label].get("font-weight"),
                        style=state_dict["labels"][label].get("style"),
                        color=state_dict["labels"][label].get("color"),
                        outline_width=state_dict["labels"][label].get("outline_width"),
                        outline_color=state_dict["labels"][label].get("outline_color"),
                        alignment=state_dict["labels"][label].get("alignment")
                    )
                    # self.add_label(key_label, position=label, update=False)
                    state.label_manager.set_page_label(label, key_label, update=False)

            ## Load media
            if load_media:
                path = state_dict.get("media", {}).get("path", None)
                if path not in ["", None]:
                    if is_image(path):
                        with Image.open(path) as image:
                            state.set_image(InputImage(
                                controller_input=self,
                                image=image.copy()
                            ), update=False)
                            
                    elif is_svg(path):
                        img = svg_to_pil(path, 192)
                        state.set_image(InputImage(
                            controller_input=self,
                            image=img
                        ), update=False)

                    elif is_video(path):
                        if os.path.splitext(path)[1].lower() == ".gif":
                            state.set_video(KeyGIF(
                                controller_key=self,
                                gif_path=path,
                                loop=state_dict.get("media", {}).get("loop", True),
                                fps=state_dict.get("media", {}).get("fps", 30)
                            )) # GIFs always update
                        else:
                            state.set_video(InputVideo(
                                controller_input=self,
                                video_path=path,
                                loop = state_dict.get("media", {}).get("loop", True),
                                fps = state_dict.get("media", {}).get("fps", 30),
                            )) # Videos always update

                layout = ImageLayout(
                    fill_mode=state_dict.get("media", {}).get("fill-mode"),
                    size=state_dict.get("media", {}).get("size"),
                    valign=state_dict.get("media", {}).get("valign"),
                    halign=state_dict.get("media", {}).get("halign"),
                )
                state.layout_manager.set_page_layout(layout, update=False)

            elif len(state.get_own_actions()) > 1 and False: # Disabled for now - we might reuse it later
                if state_dict.get("image-control-action") is None:
                    with Image.open(os.path.join("Assets", "images", "multi_action.png")) as image:
                        self.set_key_image(InputImage(
                            controller_input=self,
                            image=image.copy(),
                        ), update=False)
            
            elif len(state.get_own_actions()) == 1:
                if state_dict.get("image-control-action") is None:
                    self.set_key_image(None, update=False)
                # action = self.get_own_actions()[0]
                # if action.has_image_control()

            if load_background_color:
                state.background_manager.set_page_color(state_dict.get("background", {}).get("color"), update=False)

        if update:
            self.set_state(old_state_index)
            self.update()

    def set_state(self, state: int, update_sidebar: bool = True, allow_reload: bool = False) -> None:
        old_state = self.state
        if state == old_state and not allow_reload:
            return
        super().set_state(state, False, allow_reload)
        if update_sidebar:
            self.reload_sidebar()

    def set_ui_key_image(self, image: Image.Image) -> None:
        if image is None:
            return
        
        x, y = ControllerKey.Index_To_Coords(self.deck_controller.deck, self.index)

        if self.deck_controller.get_own_key_grid() is None or not gl.app.main_win.get_mapped():
            # Save to use later
            self.deck_controller.ui_image_changes_while_hidden[self.identifier] = image # The ui key coords are in reverse order
        else:
            try:
                GLib.idle_add(self.deck_controller.get_own_key_grid().buttons[x][y].set_image, image)
            except Exception:
                print(f"Failed to set ui key image for {self.identifier}")
        
    def get_own_ui_key(self) -> "KeyButton":
        x, y = ControllerKey.Index_To_Coords(self.deck_controller.deck, self.index)
        buttons = self.deck_controller.get_own_key_grid().buttons # The ui key coords are in reverse order
        return buttons[x][y]
    
    def get_image_size(self) -> tuple[int, int]:
        return self.deck_controller.get_key_image_size()


class ControllerKeyState(ControllerInputState):
    def __init__(self, controller_key: "ControllerKey", state: int):
        super().__init__(controller_key, state)

        self.key_image: InputImage = None
        self.key_video: InputVideo = None

    def close_resources(self) -> None:
        if self.key_image is not None:
            self.key_image.close()
            self.key_image = None
        if self.key_video is not None:
            self.key_video.close()
            self.key_video = None
            
        # Reset GIF timing
        if isinstance(self.controller_input, ControllerKey):
            self.controller_input.last_gif_update_time = 0
    
    def set_image(self, key_image: "InputImage", update: bool = True) -> None:
        if self.key_image is not None:
            self.key_image.close()

        self.key_image = key_image
        self.key_video = None

        if update:
            self.update()

    def set_video(self, key_video: "InputVideo") -> None:
        self.key_video = key_video
        if self.key_image is not None:
            self.key_image.close()
        self.key_image = None
        
        # Reset GIF timing for new video
        if isinstance(self.controller_input, ControllerKey):
            self.controller_input.last_gif_update_time = 0

    def clear(self):
        self.key_image = None
        self.key_video = None
        self.label_manager.clear_labels()
        self.layout_manager.clear()
        self.background_manager.set_page_color(None)

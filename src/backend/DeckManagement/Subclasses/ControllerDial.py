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
from typing import TYPE_CHECKING

from PIL import Image
from StreamDeck.Devices.StreamDeck import DialEventType

from src.backend.DeckManagement.HelperMethods import (
    is_image,
    is_svg,
    is_video,
    svg_to_pil,
)
from src.backend.DeckManagement.InputIdentifier import Input, InputIdentifier
from src.backend.DeckManagement.Subclasses.ControllerInput import (
    ControllerInput,
    ControllerInputState,
)
from src.backend.DeckManagement.Subclasses.KeyGIF import KeyGIF
from src.backend.DeckManagement.Subclasses.KeyImage import InputImage
from src.backend.DeckManagement.Subclasses.KeyLabel import KeyLabel
from src.backend.DeckManagement.Subclasses.KeyLayout import ImageLayout
from src.backend.DeckManagement.Subclasses.KeyVideo import InputVideo

if TYPE_CHECKING:
    from src.backend.DeckManagement.DeckController import (
        ControllerTouchScreen,
        DeckController,
    )


class ControllerDial(ControllerInput):
    def __init__(self, deck_controller: "DeckController", ident: InputIdentifier):
        super().__init__(deck_controller, ControllerDialState, ident)

        self.down_start_time: float = None

    def on_hold_timer_end(self):
        state = self.get_active_state()
        state.own_actions_event_callback_threaded(
            event=Input.Dial.Events.HOLD_START
        )

    def get_touch_screen(self) -> "ControllerTouchScreen":
        return self.deck_controller.get_input(Input.Touchscreen("sd-plus"))

    @staticmethod
    def Available_Identifiers(deck):
        return map(str, range(deck.dial_count()))

    def event_callback(self, event_type, value):
        screensaver_was_showing = self.deck_controller.screen_saver.showing
        if event_type == DialEventType.TURN:
            self.deck_controller.screen_saver.on_key_change()
        if event_type == DialEventType.PUSH and value:
            # Only on push, not on hold to allow actions to enable the screensaver without directly causing it to wake up again
            self.deck_controller.screen_saver.on_key_change()
        if screensaver_was_showing:
            return
        
        active_state = self.get_active_state()
        if event_type == DialEventType.PUSH:
            if value:
                self.down_start_time = time.time()
                self.start_hold_timer()
                active_state.own_actions_event_callback_threaded(
                    event=Input.Dial.Events.DOWN,
                    show_notifications=True
                )
            elif self.down_start_time is not None:
                self.stop_hold_timer()
                if time.time() >= self.down_start_time + self.deck_controller.hold_time:
                    active_state.own_actions_event_callback_threaded(
                        event=Input.Dial.Events.HOLD_STOP
                    )
                else:
                    active_state.own_actions_event_callback_threaded(
                        event=Input.Dial.Events.SHORT_UP
                    )
                self.down_start_time = None
                active_state.own_actions_event_callback_threaded(
                    event=Input.Dial.Events.UP
                )
        
        elif event_type == DialEventType.TURN:
            if value < 0:
                active_state.own_actions_event_callback_threaded(
                    event=Input.Dial.Events.TURN_CCW
                )
            else:
                active_state.own_actions_event_callback_threaded(
                    event=Input.Dial.Events.TURN_CW
                )

    def load_from_input_dict(self, page_dict, update: bool = True):
        n_states = len(page_dict.get("states", {}))
        self.create_n_states(max(1, n_states))

        old_state_index = self.state

        self.state = 0

        for state in page_dict.get("states", {}):
            state: ControllerDialState = self.states.get(int(state))
            if state is None:
                continue

            state_dict = page_dict["states"][str(state.state)]

            # Reset action layout
            layout = ImageLayout()
            state.layout_manager.set_action_layout(layout, update=False)

            state.own_actions_update() # Why not threaded? Because this would mean that some image changing calls might get executed after the next lines which blocks custom assets

            ## Load labels
            for label in state_dict.get("labels", []):
                key_label = KeyLabel(
                    controller_input=self,
                    text=state_dict["labels"][label].get("text"),
                    font_size=state_dict["labels"][label].get("font-size"),
                    font_name=state_dict["labels"][label].get("font-family"),
                    font_weight=state_dict["labels"][label].get("font-weight"),
                    style=state_dict["labels"][label].get("style"),
                    color=state_dict["labels"][label].get("color"),
                    alignment=state_dict["labels"][label].get("alignment"),
                )
                state.label_manager.set_page_label(label, key_label, update=False)

            ## Load media
            path = state_dict.get("media", {}).get("path")
            if path not in ["", None]:
                if is_image(path):
                    image = InputImage(
                        controller_input=self,
                        image=Image.open(path),
                    )
                    state.set_image(image, update=False)
                elif is_svg(path):
                    img = svg_to_pil(path, 192)
                    state.set_image(InputImage(
                        controller_input=self,
                        image=img
                    ), update=False)

                elif is_video(path):
                    if os.path.splitext(path)[1].lower() == ".gif":
                        raise NotImplementedError("TODO") #TODO
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

            state.background_manager.set_page_color(state_dict.get("background", {}).get("color", [0, 0, 0, 0]), update=False)

        if update:
            self.set_state(old_state_index)
            self.update()

    def update(self):
        if self.deck_controller.deck.is_touch():
            self.get_touch_screen().update()

    def get_active_state(self) -> "ControllerDialState":
        return super().get_active_state()

    def on_media_player_tick(self) -> None:
        self.media_ticks += 1

        state = self.get_active_state()
        if not any([state.video, state.label_manager.get_has_scroll_labels()]):
            return

        self.update()

    def get_image_size(self) -> tuple[int, int]:
        if self.deck_controller.deck.is_touch():
            return self.get_touch_screen().get_dial_image_area_size()
        return (0, 0)
    

class ControllerDialState(ControllerInputState):
    def __init__(self, dial: "ControllerDial", state: int):
        self.dial = dial

        self.image: InputImage = None
        self.video: InputVideo = None

        self.touch_image: Image.Image = None

        super().__init__(dial, state)

    def set_image(self, image: "InputImage", update: bool = True) -> None:
        if self.image is not None:
            self.image.close()

        self.image = image

        if update:
            self.update()

    def set_video(self, video: "InputVideo") -> None:
        if self.video is not None:
            self.video.close()

        self.video = video


    def get_rendered_touch_image(self) -> Image.Image:
        touch_screen = self.dial.get_touch_screen()

        background: Image.Image = None

        background_color = self.background_manager.get_composed_color()

        if background_color[-1] < 255:
            background = touch_screen.get_empty_dial_image()
        if background_color[-1] > 0:
            background_color_img = Image.new("RGBA", self.dial.get_image_size(), color=tuple(background_color))

            if background is None:
                # Use the color as the only background - happens if background color alpha is 255
                background = background_color_img
            else:
                background.paste(background_color_img, (0, 0), background_color_img)
        

        image = None
        if self.video is not None:
            image = self.video.get_next_frame()
        elif self.image is not None:
            image = self.image.image

        # rotation = self.deck_controller.get_deck_settings().get("rotation", {}).get("value", 0)

        image = self.layout_manager.add_image_to_background(image, background)
        image = self.label_manager.add_labels_to_image(image)

        return image

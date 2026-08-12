import math

import gi

from src.backend.DeckManagement.InputIdentifier import Input
from src.windows.mainWindow.DeckNeo.ScreenBar import ScreenBar, KEY_IMAGE_SIZE

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

import globals as gl

from gi.repository import Gtk

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.mainWindow.elements.PageSettingsPage import PageSettingsPage

TOUCH_KEY_HEIGHT = 12
TOUCH_KEY_OFF_COLOR = (0.25, 0.25, 0.25)


class ScreenRow(Gtk.Grid):
    """
    The bottom row of a Stream Deck Neo: the screen with the two touch keys to its left and right
    """
    def __init__(self, page_settings_page: "PageSettingsPage", **kwargs):
        super().__init__(column_homogeneous=True, **kwargs)
        self.page_settings_page = page_settings_page

        deck = page_settings_page.deck_controller.deck
        n_columns = deck.key_layout()[1]

        # The screen is as wide as the key columns between the two touch keys
        self.screenbar = ScreenBar(page_settings_page, Input.Screen("sd-neo"))
        self.attach(self.screenbar, 1, 0, max(1, n_columns - 2), 1)

        # The touch keys are aligned with the outer key columns
        self.touch_keys: list["TouchKeyButton"] = []
        for i in range(deck.touch_key_count()):
            button = TouchKeyButton(page_settings_page, i)
            self.attach(button, 0 if i == 0 else n_columns - 1, 0, 1, 1)
            self.touch_keys.append(button)

    def set_touch_key_color(self, index: int, color: tuple[int, int, int]) -> None:
        if index >= len(self.touch_keys):
            return
        self.touch_keys[index].set_color(color)


class TouchKeyButton(Gtk.Frame):
    """
    Preview of one of the two touch keys - they can only show a color, no image
    """
    def __init__(self, page_settings_page: "PageSettingsPage", index: int, **kwargs):
        super().__init__(valign=Gtk.Align.CENTER, **kwargs)
        self.page_settings_page = page_settings_page
        self.index = index
        self.identifier = Input.TouchKey(str(index))

        self.color: tuple[int, int, int] = None

        self.set_css_classes(["key-button-frame-hidden"])

        self.area = Gtk.DrawingArea(width_request=KEY_IMAGE_SIZE, height_request=TOUCH_KEY_HEIGHT,
                                    focusable=True)
        self.area.set_draw_func(self.on_draw)
        self.set_child(self.area)
        self.set_focus_child(self.area)

        focus_controller = Gtk.EventControllerFocus()
        self.area.add_controller(focus_controller)
        focus_controller.connect("enter", self.on_focus_in)

        self.click_ctrl = Gtk.GestureClick().new()
        self.click_ctrl.connect("pressed", self.on_click)
        self.click_ctrl.set_button(0)
        self.area.add_controller(self.click_ctrl)

        self.connect("map", self.on_map)

    def on_map(self, *args):
        # The color might have been set before this widget existed
        controller_input = self.page_settings_page.deck_controller.get_input(self.identifier)
        if controller_input is None:
            return
        color = controller_input.get_active_state().background_manager.get_composed_color()
        self.set_color(tuple(color[:3]))

    def set_color(self, color: tuple[int, int, int]) -> None:
        self.color = color
        self.area.queue_draw()

    def on_draw(self, area, context, width: int, height: int):
        radius = height / 2

        context.new_sub_path()
        context.arc(width - radius, radius, radius, -math.pi/2, 0)
        context.arc(width - radius, height - radius, radius, 0, math.pi/2)
        context.arc(radius, height - radius, radius, math.pi/2, math.pi)
        context.arc(radius, radius, radius, math.pi, 3*math.pi/2)
        context.close_path()

        if self.color in [None, (0, 0, 0)]:
            # The touch key is off - show a placeholder to keep it visible
            context.set_source_rgb(*TOUCH_KEY_OFF_COLOR)
        else:
            context.set_source_rgb(*[channel / 255 for channel in self.color])
        context.fill()

    def on_click(self, gesture, n_press, x, y):
        if gesture.get_current_button() == 1 and n_press == 1:
            self.area.grab_focus()

            controller_input = self.page_settings_page.deck_controller.get_input(self.identifier)
            if controller_input is None:
                return
            state = controller_input.get_active_state().state
            gl.app.main_win.sidebar.load_for_identifier(self.identifier, state)

    def on_focus_in(self, *args):
        self.set_border_active(True)

    def set_border_active(self, active: bool):
        deck_config = self.page_settings_page.deck_config
        if active:
            if deck_config.active_widget not in [self, None]:
                deck_config.active_widget.set_border_active(False)
            deck_config.active_widget = self
            self.set_css_classes(["key-button-frame"])
        else:
            self.set_css_classes(["key-button-frame-hidden"])
            deck_config.active_widget = None


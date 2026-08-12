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
from gi.repository import Gtk, Adw

# Import own modules
from src.backend.DeckManagement.HelperMethods import recursive_hasattr
from src.windows.mainWindow.elements.DeckSettings.DeckSettingsPage import DeckSettingsPage
from src.windows.mainWindow.elements.PageSettingsPage import PageSettingsPage

# Import globals
import globals as gl

class DeckStackChild(Gtk.Overlay):
    """
    Child of DeckStack
    This stack features one page for the page specific settings and one for the deck settings
    """
    def __init__(self, deck_stack, deck_controller, **kwargs):
        super().__init__(**kwargs)
        self.deck_stack = deck_stack
        self.deck_controller = deck_controller

        self.build()

    def build(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True)
        self.set_child(self.main_box)

        self.stack = Gtk.Stack(hexpand=True, vexpand=True)
        self.main_box.append(self.stack)

        self.page_settings = PageSettingsPage(self, self.deck_controller)
        self.deck_settings = DeckSettingsPage(self, self.deck_controller)

        self.stack.add_titled(self.page_settings, "page-settings", "Page Settings")
        self.stack.add_titled(self.deck_settings, "deck-settings", "Deck Settings")

        # Low-fps banner
        self.low_fps_banner = Adw.Banner(
            title=gl.lm.get("warning.low-fps"),
            button_label=gl.lm.get("warning.dismiss"),
            revealed=False
        )
        self.low_fps_banner.connect("button-clicked", self.on_banner_dismiss)
        self.main_box.prepend(self.low_fps_banner)

        # Sticky actions banner - shown while the sticky actions editor is open
        self.sticky_banner = Adw.Banner(
            title=gl.lm.get("deck.sticky-actions.banner"),
            button_label=gl.lm.get("deck.sticky-actions.banner.button"),
            revealed=False
        )
        self.sticky_banner.connect("button-clicked", self.on_sticky_banner_clicked)
        self.main_box.prepend(self.sticky_banner)

        self.stack.connect("notify::visible-child-name", self.on_visible_child_changed)
        self.connect("unmap", self.on_unmap)

    def on_banner_dismiss(self, banner):
        banner.set_revealed(False)

    # Sticky actions

    def enter_sticky_mode(self):
        """
        Opens the sticky actions editor: the deck shows its sticky page, which the key grid
        mirrors, so the normal page editor edits the sticky config.
        """
        self.deck_controller.enter_sticky_edit()
        self.stack.set_visible_child_name("page-settings")

        if recursive_hasattr(gl, "app.main_win.deck_settings_button"):
            gl.app.main_win.deck_settings_button.update_state()

        self.update_sticky_mode()

    def exit_sticky_mode(self):
        self.deck_controller.exit_sticky_edit()
        self.update_sticky_mode()

    def update_sticky_mode(self):
        """Brings the ui in line with the controller - safe to call at any time"""
        self.sticky_banner.set_revealed(self.deck_controller.is_sticky_editing())
        self.page_settings.deck_config.update_sticky_markers()

    def on_sticky_banner_clicked(self, banner):
        self.exit_sticky_mode()

    def on_visible_child_changed(self, *args):
        # Leaving the key grid (deck settings, ...) closes the editor
        if self.stack.get_visible_child_name() != "page-settings":
            self.exit_sticky_mode()

    def on_unmap(self, widget):
        # Another deck got selected or the window was closed - the deck must not stay on
        # its sticky page
        self.exit_sticky_mode()
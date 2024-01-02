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
from gi.repository import Gtk, Adw, GLib

# Import Python modules
import cv2
import threading
from loguru import logger as log
from math import floor
from time import sleep
from copy import copy

# Import globals
import globals as gl

# Import own modules
from src.backend.DeckManagement.ImageHelpers import image2pixbuf, is_transparent

class BackgroundGroup(Adw.PreferencesGroup):
    def __init__(self, settings_page):
        super().__init__(title=gl.lm.get("background"), description=gl.lm.get("page-settings-only-current-page-hint"), margin_top=15)
        self.media_row = BackgroundMediaRow(settings_page)
        self.add(self.media_row)


class BackgroundMediaRow(Adw.PreferencesRow):
    def __init__(self, settings_page, **kwargs):
        super().__init__()
        self.settings_page = settings_page
        self.build()

    def build(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True,
                                margin_start=15, margin_end=15, margin_top=15, margin_bottom=15)
        self.set_child(self.main_box)

        self.overwrite_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        self.main_box.append(self.overwrite_box)

        self.overwrite_label = Gtk.Label(label=gl.lm.get("page-settings-deck-overwrite-background"), hexpand=True, xalign=0)
        self.overwrite_box.append(self.overwrite_label)

        self.overwrite_switch = Gtk.Switch()
        self.overwrite_box.append(self.overwrite_switch)

        self.config_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, visible=False)
        self.main_box.append(self.config_box)

        self.config_box.append(Gtk.Separator(hexpand=True, margin_top=10, margin_bottom=10))

        self.show_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        self.config_box.append(self.show_box)

        self.show_label = Gtk.Label(label=gl.lm.get("page-settings-deck-show-background"), hexpand=True, xalign=0)
        self.show_box.append(self.show_label)
        self.show_switch = Gtk.Switch()
        self.show_box.append(self.show_switch)

        self.media_selector = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, halign=Gtk.Align.CENTER)
        self.config_box.append(self.media_selector)

        self.media_selector_image = Gtk.Image() # Will be bound to the button by self.set_thumbnail()

        self.media_selector_button = Gtk.Button(label=gl.lm.get("select"), css_classes=["page-settings-media-selector"])
        self.media_selector.append(self.media_selector_button)

        self.progress_bar = Gtk.ProgressBar(hexpand=True, margin_top=10, text="Caching...", fraction=0, show_text=True, visible=False)
        self.config_box.append(self.progress_bar)

        # Signals get directly disconnected by disconnect_signals() but we have to connect them beforehand to prevent errors
        self.connect_signals()

        self.load_defaults_from_page()

    def connect_signals(self):
        self.overwrite_switch.connect("state-set", self.on_toggle_overwrite)
        self.show_switch.connect("state-set", self.on_toggle_enable)
        self.media_selector_button.connect("clicked", self.on_choose_image)

    def disconnect_signals(self):
        try:
            self.overwrite_switch.disconnect_by_func(self.on_toggle_overwrite)
            self.show_switch.disconnect_by_func(self.on_toggle_enable)
            self.media_selector_button.disconnect_by_func(self.on_choose_image)
        except TypeError as e:
            log.error(f"Don't panic, getting this error is normal: {e}")

    def load_defaults_from_page(self):
        self.disconnect_signals()

        if not hasattr(self.settings_page.deck_page.deck_controller, "active_page"):
            self.connect_signals()
            return
        if self.settings_page.deck_page.deck_controller.active_page == None:
            self.connect_signals()
            return
        
        original_values = None
        if "background" in self.settings_page.deck_page.deck_controller.active_page.dict:
            original_values = copy(self.settings_page.deck_page.deck_controller.active_page.dict)

        self.settings_page.deck_page.deck_controller.active_page.dict.setdefault("background", {}) 

        overwrite = self.settings_page.deck_page.deck_controller.active_page.dict["background"].setdefault("overwrite", False)
        show = self.settings_page.deck_page.deck_controller.active_page.dict["background"].setdefault("show", False)
        file_path = self.settings_page.deck_page.deck_controller.active_page.dict["background"].setdefault("path", None)

        # Save if changed
        if original_values != self.settings_page.deck_page.deck_controller.active_page.dict:
            self.settings_page.deck_page.deck_controller.active_page.save()

        self.overwrite_switch.set_active(overwrite)
        self.show_switch.set_active(show)

        # Set config box state
        self.config_box.set_visible(overwrite)


        if self.settings_page.deck_page.deck_controller.active_page.dict["background"]["path"] in [None, ""]:
            self.connect_signals()
            return

        self.set_thumbnail(file_path)

        self.connect_signals()

    def on_toggle_enable(self, toggle_switch, state):
        # Change setting in the active deck page
        self.settings_page.deck_page.deck_controller.active_page.dict["background"]["show"] = state
        self.settings_page.deck_page.deck_controller.active_page.save()
        self.settings_page.deck_page.deck_controller.reload_page(load_background=False, load_keys=False, load_screensaver=False)

    def on_toggle_overwrite(self, toggle_switch, state):
        self.config_box.set_visible(state)
        # Update page
        self.settings_page.deck_page.deck_controller.active_page.dict["background"]["overwrite"] = state
        # Save
        self.settings_page.deck_page.deck_controller.active_page.save()
        self.settings_page.deck_page.deck_controller.reload_page(load_background=False, load_keys=False, load_screensaver=False)

    def on_choose_image(self, button):
        self.settings_page.deck_page.deck_controller.active_page.dict.setdefault("background", {})
        media_path = self.settings_page.deck_page.deck_controller.active_page.dict["background"].setdefault("path", None)

        gl.app.let_user_select_asset(default_path=media_path, callback_func=self.set_deck_background)

    def set_thumbnail(self, file_path):
        if file_path == None:
            return
        # return
        image = gl.media_manager.get_thumbnail(file_path)
        pixbuf = image2pixbuf(image)
        self.media_selector_image.set_from_pixbuf(pixbuf)
        self.media_selector_button.set_child(self.media_selector_image)

    def set_deck_background(self, file_path):
        self.set_thumbnail(file_path)
        # Add background to assets
        asset_id = gl.asset_manager.add(file_path)

        local_path = gl.asset_manager.get_by_id(asset_id)["internal-path"]
        self.set_background_to_page(local_path)

    def set_background_to_page(self, file_path):
        self.settings_page.deck_page.deck_controller.active_page.set_background(file_path)
        self.settings_page.deck_page.deck_controller.set_background(file_path, bypass_task=True)

        # self.update_progress_bar()

    def update_progress_bar(self):
        #TODO: Thread is not the best solution
        def thread(self):
            if self.settings_page.deck_page.deck_controller.set_background_task_id == None:
                return
            # Return if task is directly finished
            progress_dir = self.settings_page.deck_page.deck_controller.media_handler.progress_dir
            if progress_dir[self.settings_page.deck_page.deck_controller.set_background_task_id] >= 1:
                return
            self.progress_bar.set_visible(True)
            while True:
                set_background_task_id = self.settings_page.deck_page.deck_controller.set_background_task_id
                progress_dir = self.settings_page.deck_page.deck_controller.media_handler.progress_dir
                self.progress_bar.set_fraction(floor(progress_dir[set_background_task_id]*10)/ 10) # floor to one decimal
                sleep(0.25)

                if progress_dir[set_background_task_id] >= 1:
                    self.progress_bar.set_fraction(1)
                    # Keep the progress bar visible for 2s
                    sleep(2)
                    self.progress_bar.set_visible(False)
                    break

        # Start thread
        threading.Thread(target=thread, args=(self,)).start()



class ChooseBackgroundDialog(Gtk.FileDialog):
    def __init__(self, background_row: BackgroundMediaRow):
        super().__init__(title="Select Background",
                         accept_label="Select")
        self.background_row = background_row
        self.open(callback=self.callback)

    def callback(self, dialog, result):
        try:
            selected_file = self.open_finish(result)
            file_path = selected_file.get_path()
        except GLib.Error as err:
            log.error(err)
            return
        
        self.background_row.set_thumbnail(file_path)
        self.background_row.set_deck_background(file_path)
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
import threading
from typing import TYPE_CHECKING

import gi

import globals as gl
from src.backend.DeckManagement.HelperMethods import (
    color_values_to_gdk,
    gdk_color_to_values,
    get_pango_font_description,
    get_values_from_pango_font_description,
)

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

if TYPE_CHECKING:
    from src.windows.Settings.Settings import Settings


class GeneralPage(Adw.PreferencesPage):
    def __init__(self, settings: "Settings"):
        self.settings = settings
        super().__init__()
        self.set_title("General")
        self.set_icon_name("open-menu-symbolic")

        self.add(GeneralPageGroup(settings=settings))
        self.add(FontPageGroup(settings=settings))

class GeneralPageGroup(Adw.PreferencesGroup):
    def __init__(self, settings: "Settings"):
        self.settings = settings
        super().__init__(title=gl.lm.get("General app settings"))

        self.hold_time_row = Adw.SpinRow.new_with_range(min=0.1, max=3, step=0.1)
        self.hold_time_row.set_title("Minimum hold duration (s)")
        self.hold_time_row.set_subtitle("Minimum hold duration for keys and dials")
        self.hold_time_row.set_range(0.1, 3)
        self.add(self.hold_time_row)

        self.rolling_labels = Adw.SwitchRow(title="Rolling labels", subtitle="Enable automatic rolling/scrolling of too long labels")
        self.add(self.rolling_labels)

        self.load_defaults()

        # Connect signals
        self.hold_time_row.connect("changed", self.on_n_fake_decks_row_changed)
        self.rolling_labels.connect("notify::active", self.on_rolling_labels_changed)

    def load_defaults(self):
        self.hold_time_row.set_value(self.settings.settings_json.get("general", {}).get("hold-time", 0.5))
        self.rolling_labels.set_active(self.settings.settings_json.get("general", {}).get("rolling-labels", True))

    def on_n_fake_decks_row_changed(self, *args):
        self.settings.settings_json.setdefault("general", {})
        self.settings.settings_json["general"]["hold-time"] = self.hold_time_row.get_value()

        for controller in gl.deck_manager.deck_controller:
            controller.hold_time = self.hold_time_row.get_value()

        # Save
        self.settings.save_json()

        # Reload decks
        gl.deck_manager.load_fake_decks()

    def on_rolling_labels_changed(self, *args):
        self.settings.settings_json.setdefault("general", {})
        self.settings.settings_json["general"]["rolling-labels"] = self.rolling_labels.get_active()

        # Save
        self.settings.save_json()

        # Reload all pages - TODO: might not be necessary
        for controller in gl.deck_manager.deck_controller:
            controller.reload_page()

class FontPageGroup(Adw.PreferencesGroup):
    def __init__(self, settings: "Settings"):
        self.settings = settings
        super().__init__(title=gl.lm.get("settings-font-settings-header"))

        self.font_row = FontRow(self)
        self.add(self.font_row)

        self.font_color_row = FontColorRow(self)
        self.add(self.font_color_row)

        self.font_outline_width_row = FontOutlineWidthRow(self)
        self.add(self.font_outline_width_row.row)

        self.font_outline_color_row = FontOutlineColorRow(self)
        self.add(self.font_outline_color_row)


class FontRow(Adw.ActionRow):
    def __init__(self, font_page_group: FontPageGroup):
        super().__init__(title=gl.lm.get("settings-font-settings-header"),
                         subtitle=gl.lm.get("settings-font-settings-subtitle"))
        
        self.font_page_group = font_page_group
        
        self.font_chooser_button = Gtk.FontButton(valign=Gtk.Align.CENTER)
        self.add_suffix(self.font_chooser_button)

        default_font = self.font_page_group.settings.settings_json.get("general", {}).get("default-font", {})

        font_family = default_font.get("font-family") or gl.fallback_font
        font_size = default_font.get("font-size") or 15
        font_weight = default_font.get("font-weight") or 400
        font_style = default_font.get("font-style") or "normal"

        desc = get_pango_font_description(font_family, font_size, font_weight, font_style)
        self.font_chooser_button.set_font_desc(desc)

        self.font_chooser_button.connect("font-set", self.on_set)

    def on_set(self, widget):
        font_desc = widget.get_font_desc()
        family, size, weight, style = get_values_from_pango_font_description(font_desc)

        gl.settings_manager.font_defaults["font-family"] = family
        gl.settings_manager.font_defaults["font-size"] = size
        gl.settings_manager.font_defaults["font-weight"] = weight
        gl.settings_manager.font_defaults["font-style"] = style

        self.font_page_group.settings.settings_json.setdefault("general", {})
        self.font_page_group.settings.settings_json["general"]["default-font"] = gl.settings_manager.font_defaults
        gl.settings_manager.save_font_defaults()

        self.font_page_group.settings.save_json()

        threading.Thread(target=gl.page_manager.reload_all_pages, daemon=True, name="reload-all-pages").start()

class FontColorRow(Adw.ActionRow):
    def __init__(self, font_page_group: FontPageGroup):
        super().__init__(title=gl.lm.get("settings-font-color-settings-header"),
                         subtitle=gl.lm.get("settings-font-color-settings-subtitle"))
        
        self.font_page_group = font_page_group
        
        self.font_color_chooser_button = Gtk.ColorButton(valign=Gtk.Align.CENTER)
        self.add_suffix(self.font_color_chooser_button)

        default_font = self.font_page_group.settings.settings_json.get("general", {}).get("default-font", {})

        font_color = default_font.get("font-color") or (255, 255, 255, 255)
        self.font_color_chooser_button.set_rgba(color_values_to_gdk(font_color))

        self.font_color_chooser_button.connect("color-set", self.on_set)

    def on_set(self, widget):
        font_color = widget.get_rgba()

        gl.settings_manager.font_defaults["font-color"] = gdk_color_to_values(font_color)
        self.font_page_group.settings.settings_json.setdefault("general", {})
        self.font_page_group.settings.settings_json["general"]["default-font"] = gl.settings_manager.font_defaults
        gl.settings_manager.save_font_defaults()

        threading.Thread(target=gl.page_manager.reload_all_pages, daemon=True, name="reload-all-pages").start()

class FontOutlineColorRow(Adw.ActionRow):
    def __init__(self, font_page_group: FontPageGroup):
        super().__init__(title=gl.lm.get("settings-font-outline-color-settings-header"),
                         subtitle=gl.lm.get("settings-font-outline-color-settings-subtitle"))
        
        self.font_page_group = font_page_group

        self.outline_color_chooser_button = Gtk.ColorButton(valign=Gtk.Align.CENTER)
        self.add_suffix(self.outline_color_chooser_button)

        default_font = self.font_page_group.settings.settings_json.get("general", {}).get("default-font", {})

        outline_color = default_font.get("outline-color") or (0, 0, 0, 1)
        self.outline_color_chooser_button.set_rgba(color_values_to_gdk(outline_color))

        self.outline_color_chooser_button.connect("color-set", self.on_set)

    def on_set(self, widget):
        outline_color = widget.get_rgba()

        gl.settings_manager.font_defaults["outline-color"] = gdk_color_to_values(outline_color)
        self.font_page_group.settings.settings_json.setdefault("general", {})
        self.font_page_group.settings.settings_json["general"]["default-font"] = gl.settings_manager.font_defaults
        gl.settings_manager.save_font_defaults()

        threading.Thread(target=gl.page_manager.reload_all_pages, daemon=True, name="reload-all-pages").start()

class FontOutlineWidthRow:
    """
    Can't inherit from Adw.SpinRow
    """
    def __init__(self, font_page_group: FontPageGroup):
        self.font_page_group = font_page_group

        self.row = Adw.SpinRow.new_with_range(min=0, max=10, step=1)
        self.row.set_title(gl.lm.get("settings-font-outline-width-settings-header"))
        self.row.set_subtitle(gl.lm.get("settings-font-outline-width-settings-subtitle"))

        default_font = self.font_page_group.settings.settings_json.get("general", {}).get("default-font", {})

        outline_width = default_font.get("outline-width") or 2
        self.row.set_value(round(outline_width))

        self.row.connect("changed", self.on_set)

    def on_set(self, widget):
        outline_width = widget.get_value()

        gl.settings_manager.font_defaults["outline-width"] = outline_width
        self.font_page_group.settings.settings_json.setdefault("general", {})
        self.font_page_group.settings.settings_json["general"]["default-font"] = gl.settings_manager.font_defaults
        gl.settings_manager.save_font_defaults()

        threading.Thread(target=gl.page_manager.reload_all_pages, daemon=True, name="reload-all-pages").start()

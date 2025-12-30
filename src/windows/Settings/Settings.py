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
import re
# Import gtk modules
import subprocess
import threading
from abc import abstractmethod, ABC
from urllib.parse import urlparse

import gi

from GtkHelper.ColorButtonRow import ColorButtonRow
from GtkHelper.GtkHelper import BetterPreferencesGroup, better_disconnect, IconTextButton, BetterExpander
from autostart import is_flatpak, setup_autostart
from src.backend.DeckManagement.HelperMethods import color_values_to_gdk, gdk_color_to_values, get_pango_font_description, get_values_from_pango_font_description
from src.backend.PluginManager.PluginBase import PluginBase
from src.windows.Settings.PluginAbout import PluginAboutFactory
from src.windows.Settings.PluginSettingsWindow.PluginSettingsWindow import PluginSettingsWindow

# Import globals first to get IS_MAC
import globals as gl

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, Pango
if not gl.IS_MAC:
    from gi.repository import Xdp

import os

class Settings(Adw.PreferencesWindow):
    def __init__(self):
        super().__init__(title="Settings")
        self.set_default_size(1000, 700)

        # Center settings win over main_win (depends on DE)
        self.set_transient_for(gl.app.main_win)

        # Allow interaction with other windows
        self.set_modal(True)

        self.settings_json: dict = None
        self.load_json()

        self.general_page = GeneralPage(settings=self)
        self.system_page = SystemPage(settings=self)
        self.ui_page = UIPage(settings=self)
        self.plugin_page = PluginPage(settings=self)
        self.store_page = StorePage(settings=self)
        self.performance_page = PerformancePage(settings=self)
        self.dev_page = DevPage(settings=self)

        self.add(self.general_page)
        self.add(self.system_page)
        self.add(self.ui_page)
        self.add(self.plugin_page)
        self.add(self.store_page)
        self.add(self.performance_page)
        self.add(self.dev_page)


    def load_json(self):
        # Load settings from file
        settings = gl.settings_manager.load_settings_from_file(os.path.join(gl.DATA_PATH, "settings", "settings.json"))
        self.settings_json = settings
    
    def save_json(self):
        gl.settings_manager.save_settings_to_file(os.path.join(gl.DATA_PATH, "settings", "settings.json"), self.settings_json)

class SettingsPage(Adw.PreferencesPage):
    def __init__(self, settings: Settings, *args, **kwargs):
        self.settings = settings
        super().__init__(*args, **kwargs)

class SettingsGroup(Adw.PreferencesGroup):
    def __init__(self, settings: Settings, *args, **kwargs):
        self.settings = settings
        super().__init__(*args, **kwargs)

    @abstractmethod
    def build(self):
        pass

    def connect_events(self):
        pass

    def disconnect_events(self):
        pass

    def load_defaults(self):
        pass

class SettingsRow(Adw.ActionRow):
    def __init__(self, settings: Settings, *args, **kwargs):
        self.settings = settings
        super().__init__(*args, **kwargs)#

    @abstractmethod
    def build(self):
        pass

    @abstractmethod
    def connect_events(self):
        pass

    @abstractmethod
    def disconnect_events(self):
        pass

    @abstractmethod
    def load_defaults(self):
        pass

###############
#   General   #
###############

class GeneralPage(SettingsPage):
    def __init__(self, settings, *args, **kwargs):
        super().__init__(settings, *args, **kwargs)
        self.set_title("General")
        self.set_icon_name("open-menu-symbolic")

        self.add(GeneralGroup(self.settings, title="General"))
        self.add(FontGroup(self.settings, title="Font"))
        self.add(BackgroundGroup(self.settings, title="Background"))
        self.add(LayoutGroup(self.settings, title="Layout"))

# General Settings

class GeneralGroup(SettingsGroup):
    def __init__(self, settings: Settings, *args, **kwargs):
        super().__init__(settings, *args, **kwargs)
        self.build()
        self.load_defaults()
        self.connect_events()

    def build(self):
        self.hold_time_spin = Adw.SpinRow.new_with_range(min=0.1, max=5, step=0.1)
        self.hold_time_spin.set_title("Minimum hold duration (s)")
        self.hold_time_spin.set_subtitle("Minimum hold duration for keys and dials")

        self.add(self.hold_time_spin)

    def load_defaults(self):
        hold_time = self.settings.settings_json.get("general", {}).get("hold-time", 0.5)
        self.hold_time_spin.set_value(hold_time)

    def connect_events(self):
        self.hold_time_spin.connect("changed", self.hold_time_changed)

    def disconnect_events(self):
        better_disconnect(self.hold_time_spin, self.hold_time_changed)

    def hold_time_changed(self, *args):
        hold_time = self.hold_time_spin.get_value()

        self.settings.settings_json.setdefault("general", {})
        self.settings.settings_json["general"]["hold-time"] = hold_time

        for controller in gl.deck_manager.deck_controller:
            controller.hold_time = hold_time

        self.settings.save_json()
        # gl.deck_manager.load_fake_decks() WHY?

# Font settings

class FontGroup(SettingsGroup):
    def __init__(self, settings: Settings, *args, **kwargs):
        super().__init__(settings, *args, **kwargs)
        self.build()
        self.load_defaults()
        self.connect_events()

    def build(self):
        self.add(FontRow(self.settings, title="Default Font"))
        self.add(FontOutlineRow(self.settings, title="Default Font Outline"))

class FontRow(SettingsRow):
    def __init__(self, settings: Settings, *args, **kwargs):
        super().__init__(settings, *args, **kwargs)
        self.build()
        self.load_defaults()
        self.connect_events()

    def build(self):
        self.font_chooser_button = Gtk.FontButton(valign=Gtk.Align.CENTER)
        self.add_suffix(self.font_chooser_button)

        self.font_color_button = Gtk.ColorButton(valign=Gtk.Align.CENTER)
        self.add_suffix(self.font_color_button)

    def load_defaults(self):
        font_settings = self.settings.settings_json.get("general", {}).get("default-font", {})

        # Set font
        font_family = font_settings.get("font-family", gl.fallback_font)
        font_size = font_settings.get("font-size", 15)
        font_weight = font_settings.get("font-weight", 400)
        font_style = font_settings.get("font-style", "normal")
        desc = get_pango_font_description(font_family, font_size, font_weight, font_style)

        self.font_chooser_button.set_font_desc(desc)

        # Set font color
        font_color = font_settings.get("font-color", (255,255,255,255))
        self.font_color_button.set_rgba(color_values_to_gdk(font_color))

    def connect_events(self):
        self.font_chooser_button.connect("font-set", self.on_font_changed)
        self.font_color_button.connect("color-set", self.on_font_color_changed)

    def disconnect_events(self):
        better_disconnect(self.font_chooser_button, self.on_font_changed)
        better_disconnect(self.font_color_button, self.on_font_color_changed)

    def on_font_changed(self, widget):
        font_desc = widget.get_font_desc()
        family, size, weight, style = get_values_from_pango_font_description(font_desc)

        gl.settings_manager.font_defaults["font-family"] = family
        gl.settings_manager.font_defaults["font-size"] = size
        gl.settings_manager.font_defaults["font-weight"] = weight
        gl.settings_manager.font_defaults["font-style"] = style

        self.settings.settings_json.setdefault("general", {})
        self.settings.settings_json["general"]["font-family"] = gl.settings_manager.font_defaults
        gl.settings_manager.save_font_defaults()

        self.settings.save_json()

        threading.Thread(target=gl.page_manager.reload_all_pages, daemon=True, name="reload-all-pages").start()

    def on_font_color_changed(self, widget):
        font_color = widget.get_rgba()

        gl.settings_manager.font_defaults["font-color"] = gdk_color_to_values(font_color)
        self.settings.settings_json.setdefault("general", {})
        self.settings.settings_json["general"]["default-font"] = gl.settings_manager.font_defaults
        gl.settings_manager.save_font_defaults()

        threading.Thread(target=gl.page_manager.reload_all_pages, daemon=True, name="reload-all-pages").start()

class FontOutlineRow(SettingsRow):
    def __init__(self, settings: Settings, *args, **kwargs):
        super().__init__(settings, *args, **kwargs)
        self.build()
        self.load_defaults()
        self.connect_events()

    def build(self):
        self.font_outline_width_spin = Gtk.SpinButton.new_with_range(min=0, max=10, step=1)
        self.font_outline_width_spin.set_valign(Gtk.Align.CENTER)
        self.add_suffix(self.font_outline_width_spin)

        self.font_outline_color_button = Gtk.ColorButton(valign=Gtk.Align.CENTER)
        self.add_suffix(self.font_outline_color_button)

    def load_defaults(self):
        font_settings = self.settings.settings_json.get("general", {}).get("default-font", {})

        outline_width = font_settings.get("outline-width", 2)
        self.font_outline_width_spin.set_value(outline_width)

        outline_color = font_settings.get("outline-color", (0, 0, 0, 255))
        self.font_outline_color_button.set_rgba(color_values_to_gdk(outline_color))

    def connect_events(self):
        self.font_outline_width_spin.connect("changed", self.on_font_outline_width_changed)
        self.font_outline_color_button.connect("color-set", self.on_font_outline_color_changed)

    def disconnect_events(self):
        better_disconnect(self.font_outline_width_spin, self.on_font_outline_width_changed)
        better_disconnect(self.font_outline_color_button, self.on_font_outline_color_changed)

    def on_font_outline_width_changed(self, widget):
        outline_width = widget.get_value()

        gl.settings_manager.font_defaults["outline-width"] = outline_width
        self.settings.settings_json.setdefault("general", {})
        self.settings.settings_json["general"]["default-font"] = gl.settings_manager.font_defaults
        gl.settings_manager.save_font_defaults()

        threading.Thread(target=gl.page_manager.reload_all_pages, daemon=True, name="reload-all-pages").start()

    def on_font_outline_color_changed(self, widget):
        outline_color = widget.get_rgba()

        gl.settings_manager.font_defaults["outline-color"] = gdk_color_to_values(outline_color)
        self.settings.settings_json.setdefault("general", {})
        self.settings.settings_json["general"]["default-font"] = gl.settings_manager.font_defaults
        gl.settings_manager.save_font_defaults()

        threading.Thread(target=gl.page_manager.reload_all_pages, daemon=True, name="reload-all-pages").start()

# Background Color Settings

class BackgroundGroup(SettingsGroup):
    def __init__(self, settings: Settings, *args, **kwargs):
        super().__init__(settings, *args, **kwargs)
        self.build()
        self.load_defaults()
        self.connect_events()

    def build(self):
        self.background_color_button = ColorButtonRow(title="Default Background Color", default_color=(0,0,0,0))
        self.add(self.background_color_button)

    def load_defaults(self):
        background_color = self.settings.settings_json.get("general", {}).get("default-background-color", (0, 0, 0, 0))
        self.background_color_button.set_color(background_color)

    def connect_events(self):
        self.background_color_button.color_button.connect("color-set", self.on_background_color_changed)

    def disconnect_events(self):
        better_disconnect(self.background_color_button.color_button, self.on_background_color_changed)

    def on_background_color_changed(self, widget):
        background_color = self.background_color_button.get_color()

        self.settings.settings_json.setdefault("general", {})
        self.settings.settings_json["general"]["default-background-color"] = background_color
        self.settings.save_json()

        threading.Thread(target=gl.page_manager.reload_all_pages, daemon=True, name="reload-all-pages").start()

# Layout Settings

class LayoutGroup(SettingsGroup):
    def __init__(self, settings: Settings, *args, **kwargs):
        super().__init__(settings, *args, **kwargs)
        self.build()
        self.load_defaults()
        self.connect_events()

    def build(self):
        self.size_spin = Adw.SpinRow.new_with_range(min=0, max=200, step=1)
        self.size_spin.set_title("Default Size (%)")
        self.add(self.size_spin)

        self.valign_spin = Adw.SpinRow.new_with_range(min=-1.0, max=1.0, step=0.1)
        self.valign_spin.set_title("VAlign")
        self.add(self.valign_spin)

        self.halign_spin = Adw.SpinRow.new_with_range(min=-1.0, max=1.0, step=0.1)
        self.halign_spin.set_title("HAlign")
        self.add(self.halign_spin)

    def load_defaults(self):
        layout_settings = self.settings.settings_json.get("general", {}).get("default-layout", {})

        size = layout_settings.get("size", 100)
        self.size_spin.set_value(size)

        valign = layout_settings.get("valign", 0.0)
        self.valign_spin.set_value(valign)

        halign = layout_settings.get("halign", 0.0)
        self.halign_spin.set_value(halign)

    def connect_events(self):
        self.size_spin.connect("changed", self.on_size_changed)
        self.valign_spin.connect("changed", self.on_valign_changed)
        self.halign_spin.connect("changed", self.on_halign_changed)

    def disconnect_events(self):
        better_disconnect(self.size_spin, self.on_size_changed)
        better_disconnect(self.valign_spin, self.on_valign_changed)
        better_disconnect(self.halign_spin, self.on_halign_changed)

    def on_size_changed(self, widget):
        size = widget.get_value()

        self.settings.settings_json.setdefault("general", {})
        self.settings.settings_json["general"].setdefault("default-layout", {})
        self.settings.settings_json["general"]["default-layout"]["size"] = size
        self.settings.save_json()

        threading.Thread(target=gl.page_manager.reload_all_pages, daemon=True, name="reload-all-pages").start()

    def on_valign_changed(self, widget):
        valign = widget.get_value()

        self.settings.settings_json.setdefault("general", {})
        self.settings.settings_json["general"].setdefault("default-layout", {})
        self.settings.settings_json["general"]["default-layout"]["valign"] = valign
        self.settings.save_json()

        threading.Thread(target=gl.page_manager.reload_all_pages, daemon=True, name="reload-all-pages").start()

    def on_halign_changed(self, widget):
        halign = widget.get_value()

        self.settings.settings_json.setdefault("general", {})
        self.settings.settings_json["general"].setdefault("default-layout", {})
        self.settings.settings_json["general"]["default-layout"]["halign"] = halign
        self.settings.save_json()

        threading.Thread(target=gl.page_manager.reload_all_pages, daemon=True, name="reload-all-pages").start()

###############
#   System    #
###############

class SystemPage(SettingsPage):
    def __init__(self, settings, *args, **kwargs):
        super().__init__(settings, *args, **kwargs)
        self.set_title("System")
        self.set_icon_name("system-run-symbolic")

        self.add(SystemGroup(self.settings, title="System"))

# System Settings

class SystemGroup(SettingsGroup):
    def __init__(self, settings, *args, **kwargs):
        super().__init__(settings, *args, **kwargs)
        self.build()
        self.load_defaults()
        self.connect_events()

    def build(self):
        self.keep_running_switch = Adw.SwitchRow(title="Keep Running", active=False)
        self.add(self.keep_running_switch)

        self.autostart_switch = Adw.SwitchRow(title="Autostart", active=False)
        self.add(self.autostart_switch)

        self.tray_icon_switch = Adw.SwitchRow(title="Tray Icon", active=False)
        self.add(self.tray_icon_switch)

        self.lock_on_lock_screen_switch = Adw.SwitchRow(title="Lock On Lock Screen", active=False)
        self.add(self.lock_on_lock_screen_switch)

        self.resume_after_suspend_switch = Adw.SwitchRow(title="Resume After Suspend", active=False)
        self.add(self.resume_after_suspend_switch)

    def load_defaults(self):
        system_settings = self.settings.settings_json.get("system", {})

        self.keep_running_switch.set_active(system_settings.get("keep-running", False))
        self.autostart_switch.set_active(system_settings.get("autostart", True))
        self.tray_icon_switch.set_active(system_settings.get("tray-icon", True))
        self.lock_on_lock_screen_switch.set_active(system_settings.get("lock-on-lock-screen", True))
        self.resume_after_suspend_switch.set_active(system_settings.get("beta-resume-mode", True))

    def connect_events(self):
        self.keep_running_switch.connect("notify::active", self.on_keep_running_changed)
        self.autostart_switch.connect("notify::active", self.on_autostart_changed)
        self.tray_icon_switch.connect("notify::active", self.on_tray_icon_changed)
        self.lock_on_lock_screen_switch.connect("notify::active", self.on_lock_on_lock_screen_changed)
        self.resume_after_suspend_switch.connect("notify::active", self.on_resume_after_suspend_changed)

    def disconnect_events(self):
        better_disconnect(self.keep_running_switch, self.on_keep_running_changed)
        better_disconnect(self.autostart_switch, self.on_autostart_changed)
        better_disconnect(self.lock_on_lock_screen_switch, self.on_lock_on_lock_screen_changed)
        better_disconnect(self.resume_after_suspend_switch, self.on_resume_after_suspend_changed)

    def on_keep_running_changed(self, *args):
        self.settings.settings_json.setdefault("system", {})
        self.settings.settings_json["system"]["keep-running"] = self.keep_running_switch.get_active()

        # Save
        self.settings.save_json()

    def on_autostart_changed(self, *args):
        self.settings.settings_json.setdefault("system", {})
        self.settings.settings_json["system"]["autostart"] = self.autostart_switch.get_active()

        setup_autostart(self.autostart_switch.get_active())

        # Save
        self.settings.save_json()

    def on_tray_icon_changed(self, *args):
        self.settings.settings_json.setdefault("system", {})
        self.settings.settings_json["system"]["tray-icon"] = self.tray_icon_switch.get_active()

        # Save
        self.settings.save_json()

        if self.settings.settings_json["system"]["tray-icon"]:
            gl.tray_icon.start()
        else:
            gl.tray_icon.stop()

    def on_lock_on_lock_screen_changed(self, *args):
        self.settings.settings_json.setdefault("system", {})
        self.settings.settings_json["system"]["lock-on-lock-screen"] = self.lock_on_lock_screen_switch.get_active()

        # Save
        self.settings.save_json()

    def on_resume_after_suspend_changed(self, *args):
        self.settings.settings_json.setdefault("system", {})
        self.settings.settings_json["system"]["beta-resume-mode"] = self.resume_after_suspend_switch.get_active()

        # Save
        self.settings.save_json()

###############
#     UI      #
###############

class UIPage(SettingsPage):
    def __init__(self, settings, *args, **kwargs):
        super().__init__(settings)
        self.set_title(gl.lm.get("settings-ui-settings-title"))
        self.set_icon_name("window-new-symbolic")

        self.add(UIGroup(settings=self.settings, title="UI"))

# UI Settings

class UIGroup(SettingsGroup):
    def __init__(self, settings, *args, **kwargs):
        super().__init__(settings, *args, **kwargs)
        self.build()
        self.load_defaults()
        self.connect_events()

    def build(self):
        self.emulate_double_click_switch = Adw.SwitchRow(title="Emulate Double Click", active=False)
        self.add(self.emulate_double_click_switch)

        self.fps_warning_switch = Adw.SwitchRow(title="FPS Warning", active=False)
        self.add(self.fps_warning_switch)

        self.allow_white_mode_switch = Adw.SwitchRow(title="Allow White Mode", active=False)
        self.add(self.allow_white_mode_switch)

        self.show_notifications_switch = Adw.SwitchRow(title="Show Notifications", active=False)
        self.add(self.show_notifications_switch)

        self.auto_open_config_switch = Adw.SwitchRow(title="Auto Open Config", active=False)
        self.add(self.auto_open_config_switch)

    def load_defaults(self):
        ui_settings = self.settings.settings_json.get("ui",{})

        self.emulate_double_click_switch.set_active(ui_settings.get("emulate-at-double-click", True))
        self.fps_warning_switch.set_active(ui_settings.get("enable-fps-warnings", True))
        self.allow_white_mode_switch.set_active(ui_settings.get("allow-white-mode", False))
        self.show_notifications_switch.set_active(ui_settings.get("show-notifications", True))
        self.auto_open_config_switch.set_active(ui_settings.get("auto-open-action-config", True))

    def connect_events(self):
        self.emulate_double_click_switch.connect("notify::active", self.on_emulate_double_click_changed)
        self.fps_warning_switch.connect("notify::active", self.on_fps_warning_changed)
        self.allow_white_mode_switch.connect("notify::active", self.on_allow_white_mode_changed)
        self.show_notifications_switch.connect("notify::active", self.on_show_notifications_changed)
        self.auto_open_config_switch.connect("notify::active", self.on_auto_open_config_changed)

    def disconnect_events(self):
        better_disconnect(self.emulate_double_click_switch, self.on_emulate_double_click_changed)
        better_disconnect(self.fps_warning_switch, self.on_fps_warning_changed)
        better_disconnect(self.allow_white_mode_switch, self.on_allow_white_mode_changed)
        better_disconnect(self.show_notifications_switch, self.on_show_notifications_changed)
        better_disconnect(self.auto_open_config_switch, self.on_auto_open_config_changed)

    def on_emulate_double_click_changed(self, *args):
        self.settings.settings_json.setdefault("ui", {})
        self.settings.settings_json["ui"]["emulate-at-double-click"] = self.emulate_double_click_switch.get_active()

        # Save
        self.settings.save_json()

    def on_fps_warning_changed(self, *args):
        self.settings.settings_json.setdefault("ui", {})
        self.settings.settings_json["ui"]["enable-fps-warnings"] = self.fps_warning_switch.get_active()

        # Save
        self.settings.save_json()

        # Inform all deck controllers
        for controller in gl.deck_manager.deck_controller:
            controller.media_player.set_show_fps_warnings(self.fps_warning_switch.get_active())


    def on_allow_white_mode_changed(self, *args):
        self.settings.settings_json.setdefault("ui", {})
        self.settings.settings_json["ui"]["allow-white-mode"] = self.allow_white_mode_switch.get_active()

        if self.allow_white_mode_switch.get_active():
            gl.app.style_manager.set_color_scheme(Adw.ColorScheme.PREFER_DARK)
        else:
            gl.app.style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)

        # Save
        self.settings.save_json()

    def on_show_notifications_changed(self, *args):
        self.settings.settings_json.setdefault("ui", {})
        self.settings.settings_json["ui"]["show-notifications"] = self.show_notifications_switch.get_active()

        # Save
        self.settings.save_json()

    def on_auto_open_config_changed(self, *args):
        self.settings.settings_json.setdefault("ui", {})
        self.settings.settings_json["ui"]["auto-open-action-config"] = self.auto_open_config_switch.get_active()

        # Save
        self.settings.save_json()

###############
#   Plugins   #
###############

class PluginPage(SettingsPage):
    def __init__(self, settings, *args, **kwargs):
        super().__init__(settings, *args, **kwargs)
        self.set_title("Plugins")
        self.set_icon_name("application-x-addon-symbolic")

        self.add(PluginGroup(settings, title="Plugins"))
        self.add(PluginPrivacyGroup(settings, title="Banned logging terms"))

# Plugin Settings

class PluginGroup(SettingsGroup):
    def __init__(self, settings, *args, **kwargs):
        super().__init__(settings, *args, **kwargs)
        self.build()
        self.load_defaults()
        self.connect_events()

    def build(self):
        for plugin_id in gl.plugin_manager.get_plugin_ids():
            plugin_base = gl.plugin_manager.get_plugin_by_id(plugin_id)
            self.add(PluginRow(self.settings, plugin_base))

class PluginRow(SettingsRow):
    def __init__(self, settings, plugin_base, *args, **kwargs):
        super().__init__(settings, *args, **kwargs)
        self.plugin_base: PluginBase = plugin_base
        self.build()
        self.load_defaults()
        self.connect_events()

    def build(self):
        self.set_title(self.plugin_base.plugin_name)
        self.set_subtitle(self.plugin_base.plugin_id)

        self.settings_window_button = IconTextButton(icon_name="emblem-system-symbolic", text="Settings",
                                                     valign=Gtk.Align.CENTER)
        self.add_suffix(self.settings_window_button)

        self.changelog_window_button = IconTextButton(icon_name="help-about-symbolic", text="About",
                                                      valign=Gtk.Align.CENTER)
        self.add_suffix(self.changelog_window_button)

        self.troubleshoot_button = IconTextButton(icon_name="system-run-symbolic", text="Diagnostics",
                                                  valign=Gtk.Align.CENTER)
        self.add_suffix(self.troubleshoot_button)

    def load_defaults(self):
        pass

    def connect_events(self):
        self.settings_window_button.connect("clicked", self.on_settings_window_button_clicked)
        self.changelog_window_button.connect("clicked", self.on_changelog_window_button_clicked)
        self.troubleshoot_button.connect("clicked", self.on_troubleshoot_button_clicked)

    def disconnect_events(self):
        better_disconnect(self.settings_window_button, self.on_settings_window_button_clicked)
        better_disconnect(self.changelog_window_button, self.on_changelog_window_button_clicked)
        better_disconnect(self.troubleshoot_button, self.on_troubleshoot_button_clicked)

    def on_settings_window_button_clicked(self, *args):
        settings = PluginSettingsWindow(self.plugin_base)
        settings.present(self.settings)

    def on_changelog_window_button_clicked(self, *args):
        factory = PluginAboutFactory(self.plugin_base)
        about = factory.create_new_about()

        about.present(self)

    def on_troubleshoot_button_clicked(self, *args):
        self.plugin_base.troubleshoot()

# Plugin Privacy Settings

class PluginPrivacyGroup(SettingsGroup):
    def __init__(self, settings, *args, **kwargs):
        super().__init__(settings, *args, **kwargs)
        self._banned_words: set[str] = set()
        self.build()
        self.load_defaults()
        self.connect_events()

    def build(self):
        self.word_entry = Adw.EntryRow(title="Add banned term")
        self.word_entry.set_show_apply_button(True)
        self.add(self.word_entry)

        self.search_entry = Adw.EntryRow(title="Search terms")
        self.add(self.search_entry)

        self.word_expander = BetterExpander(title="Current Banned terms")
        self.add(self.word_expander)

    def load_defaults(self):
        self._banned_words = set(self.settings.settings_json.get("banned-terms", []))
        self._populate_expander()

        if self._banned_words:
            self.word_expander.set_expanded(True)

    def connect_events(self):
        self.word_entry.connect("apply", self.on_add_word)
        self.search_entry.connect("changed", self.on_search_changed)

    def disconnect_events(self):
        better_disconnect(self.word_entry, self.on_add_word)
        better_disconnect(self.search_entry, self.on_search_changed)

    def _populate_expander(self, filter_text: str = ""):
        self.word_expander.clear()

        for word in sorted(self._banned_words):  # Sort for stable order
            if filter_text and filter_text not in word.lower():
                continue
            self.word_expander.add_row(self._create_word_row(word))

    def _create_word_row(self, word):
        row = Adw.ActionRow(title=word)
        remove_button = Gtk.Button(icon_name="user-trash-symbolic")
        remove_button.set_valign(Gtk.Align.CENTER)
        remove_button.connect("clicked", self.on_remove_word, word, row)
        row.add_suffix(remove_button)
        row.set_activatable(False)

        return row

    def on_add_word(self, entry_row):
        text = entry_row.get_text().strip()
        self._banned_words.add(text)

        self.settings.settings_json.setdefault("banned-terms", [])
        self.settings.settings_json["banned-terms"] = list(self._banned_words)
        self.settings.save_json()

        self._populate_expander()

    def on_remove_word(self, button, word, row):
        self._banned_words.remove(word)

        self.settings.settings_json.setdefault("banned-terms", [])
        self.settings.settings_json["banned-terms"] = list(self._banned_words)
        self.settings.save_json()

        self._populate_expander()

    def on_search_changed(self, entry):
        query = entry.get_text().strip().lower()
        self._populate_expander(filter_text=query)

###############
#    Store    #
###############

class StorePage(SettingsPage):
    def __init__(self, settings, *args, **kwargs):
        super().__init__(settings, *args, **kwargs)
        self.set_title(gl.lm.get("settings-store-settings-title"))
        self.set_icon_name("go-home-symbolic")

        self.add(StoreGroup(self.settings, title="Store"))

        custom_element_group = Adw.PreferencesGroup(title="Custom Elements")
        self.add(custom_element_group)

        custom_element_group.add(CustomElementGroup(self.settings, key="Stores", margin_bottom=10))
        custom_element_group.add(CustomElementGroup(self.settings, key="Plugins", margin_bottom=10))

class StoreGroup(SettingsGroup):
    def __init__(self, settings, *args, **kwargs):
        super().__init__(settings, *args, **kwargs)
        self.build()
        self.load_defaults()
        self.connect_events()

    def build(self):
        self.auto_update_switch = Adw.SwitchRow(title="Auto update")
        self.add(self.auto_update_switch)

    def load_defaults(self):
        store_settings = self.settings.settings_json.get("store", {})

        self.auto_update_switch.set_active(store_settings.get("auto-update", True))

    def connect_events(self):
        self.auto_update_switch.connect("notify::active", self.on_auto_update_changed)

    def disconnect_events(self):
        better_disconnect(self.auto_update_switch, self.on_auto_update_changed)

    def on_auto_update_changed(self, *args):
        self.settings.settings_json.setdefault("store", {})
        self.settings.settings_json["store"]["auto-update"] = self.auto_update_switch.get_active()

        # Save
        self.settings.save_json()

# Custom Group Settings

class CustomElementGroup(SettingsGroup):
    def __init__(self, settings, key: str, *args, **kwargs):
        super().__init__(settings, *args, **kwargs)

        self.key = key
        self.list_key = f"custom-{key.lower()}"
        self.enable_key = f"enable-custom-{key.lower()}"

        self.build()
        self.load_defaults()
        self.connect_events()

    def build(self):
        self.custom_expander = BetterExpander(title=f"Custom {self.key}")
        self.add(self.custom_expander)

        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        header_box.set_halign(Gtk.Align.END)
        self.custom_expander.add_suffix(header_box)

        self.enable_custom_group_switch = Adw.SwitchRow(activatable=False, valign=Gtk.Align.CENTER)
        header_box.append(self.enable_custom_group_switch)

        self.add_custom_entry_button = Gtk.Button(icon_name="list-add-symbolic", valign=Gtk.Align.CENTER)
        self.add_custom_entry_button.set_tooltip_text("Add new entry")
        header_box.append(self.add_custom_entry_button)

    def load_defaults(self):
        store_settings = self.settings.settings_json.get("store", {})
        self.enable_custom_group_switch.set_active(store_settings.get(self.enable_key, False))

        element_list = store_settings.get(self.list_key, [])

        for i, element in enumerate(element_list):
            self._add_custom_row(i, element.get("url", ""), element.get("branch", ""))#

        if len(element_list) > 0:
            self.custom_expander.set_expanded(True)

    def _add_custom_row(self, index, url, branch):
        row = CustomElementRow(self.settings, self, index, url, branch)
        self.custom_expander.add_row(row)

    def connect_events(self):
        self.enable_custom_group_switch.connect("notify::active", self.on_enable_custom_group_changed)
        self.add_custom_entry_button.connect("clicked", self.on_add_custom_entry_clicked)

    def disconnect_events(self):
        better_disconnect(self.enable_custom_group_switch, self.on_enable_custom_group_changed)
        better_disconnect(self.add_custom_entry_button, self.on_add_custom_entry_clicked)

    def on_enable_custom_group_changed(self, *_):
        self.settings.settings_json.setdefault("store", {})[self.enable_key] = self.enable_custom_group_switch.get_active()
        self.settings.save_json()

    def on_add_custom_entry_clicked(self, *args):
        store = self.settings.settings_json.setdefault("store", {})
        store.setdefault(self.list_key, []).append({"url": "", "branch": ""})
        self.settings.save_json()

        self._add_custom_row(len(store[self.list_key]) - 1, "", "")
        self.custom_expander.set_expanded(True)

    def update_indicies(self):
        for i, row in enumerate(self.custom_expander.get_rows()):
            row.index = i

class CustomElementRow(Adw.PreferencesRow):
    def __init__(self, settings, group: CustomElementGroup, index: int, url: str = "", branch: str = "", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_activatable(False)
        self.settings = settings
        self.group = group
        self.index = index
        self.list_key = self.group.list_key

        self.build(url, branch)
        self.connect_events()

    def build(self, url: str, branch: str):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10,
                                margin_top=6, margin_bottom=6, margin_start=6, margin_end=6)
        self.set_child(self.main_box)

        self.url_entry = Gtk.Entry(text=url, hexpand=True, placeholder_text="Repository URL")
        self.main_box.append(self.url_entry)

        self.branch_entry = Gtk.Entry(text=branch, hexpand=True, placeholder_text="Branch")
        self.main_box.append(self.branch_entry)

        self.remove_button = Gtk.Button(icon_name="user-trash-symbolic", valign=Gtk.Align.CENTER)
        self.remove_button.set_tooltip_text("Remove this entry")
        self.main_box.append(self.remove_button)

        self.validate_url(url)

    def connect_events(self):
        self.url_entry.connect("changed", self.on_url_changed)
        self.branch_entry.connect("changed", self.on_branch_changed)
        self.remove_button.connect("clicked", self.on_remove_clicked)

    def disconnect_events(self):
        better_disconnect(self.url_entry, self.on_url_changed)
        better_disconnect(self.branch_entry, self.on_branch_changed)
        better_disconnect(self.remove_button, self.on_remove_clicked)

    def update_store(self, field, value):
        store = self.settings.settings_json.setdefault("store", {})
        stores = store.setdefault(self.list_key, [])

        while self.index >= len(stores):
            stores.append({"url": "", "branch": ""})

        stores[self.index][field] = value
        self.settings.save_json()

    def validate_url(self, url):
        parsed = urlparse(url)

        valid_url = all([
            parsed.scheme in ("http", "https"),
            parsed.netloc == "github.com",
        ])

        if not valid_url and url != "":
            self.url_entry.get_style_context().add_class("warning-label")
        else:
            self.url_entry.get_style_context().remove_class("warning-label")

    def on_url_changed(self, entry):
        text = entry.get_text()

        self.validate_url(text)
        self.update_store("url", text)

    def on_branch_changed(self, entry):
        self.update_store("branch", entry.get_text())

    def on_remove_clicked(self, *args):
        store = self.settings.settings_json.setdefault("store", {})
        stores = store.get(self.list_key, [])

        if self.index < len(stores):
            stores.pop(self.index)
            self.settings.save_json()

        self.group.custom_expander.remove(self)
        self.group.update_indicies()

###############
# Performance #
###############

class PerformancePage(SettingsPage):
    def __init__(self, settings, *args, **kwargs):
        super().__init__(settings, *args, **kwargs)
        self.set_title(gl.lm.get("settings.performance.title"))
        self.set_icon_name("power-profile-performance-symbolic")

        self.add(PerformanceGroup(settings, title="Performance &amp; Optimizations"))

class PerformanceGroup(SettingsGroup):
    def __init__(self, settings, *args, **kwargs):
        super().__init__(settings, *args, **kwargs)
        self.build()
        self.load_defaults()
        self.connect_events()

    def build(self):
        self.cache_page_spin = Adw.SpinRow().new_with_range(min=0, max=50, step=1)
        self.cache_page_spin.set_title("Number of cached pages")
        self.cache_page_spin.set_subtitle("Number of pages to keep in cache")
        self.add(self.cache_page_spin)

        self.cache_video_switch = Adw.SwitchRow(title="Cache Videos", subtitle="Only applies to new videos or after a restart")
        self.add(self.cache_video_switch)

    def load_defaults(self):
        performance_settings = self.settings.settings_json.get("performance", {})

        self.cache_page_spin.set_value(int(performance_settings.get("n-cached-pages", 3)))
        self.cache_video_switch.set_active(performance_settings.get("cache-videos", True))

    def connect_events(self):
        self.cache_page_spin.connect("changed", self.on_cache_page_changed)
        self.cache_video_switch.connect("notify::active", self.on_cache_video_changed)

    def disconnect_events(self):
        better_disconnect(self.cache_page_spin, self.on_cache_page_changed)
        better_disconnect(self.cache_video_switch, self.on_cache_video_changed)

    def on_cache_page_changed(self, *args):
        self.settings.settings_json.setdefault("performance", {})
        self.settings.settings_json["performance"]["n-cached-pages"] = int(self.cache_page_spin.get_value())

        # Save
        self.settings.save_json()

        # Update value in page manager
        gl.page_manager.set_n_pages_to_cache(int(self.cache_page_spin.get_value()))

    def on_cache_video_changed(self, *args):
        self.settings.settings_json.setdefault("performance", {})
        self.settings.settings_json["performance"]["cache-videos"] = self.cache_video_switch.get_active()

        # Save
        self.settings.save_json()

###############
#  Developer  #
###############

class DevPage(SettingsPage):
    def __init__(self, settings, *args, **kwargs):
        super().__init__(settings, *args, **kwargs)
        self.set_title(gl.lm.get("settings-dev-settings-title"))
        self.set_icon_name("text-editor-symbolic")

        self.add(DevPageGroup(settings))

class DevPageGroup(SettingsGroup):
    def __init__(self, settings, *args, **kwargs):
        super().__init__(settings, *args, **kwargs)
        self.build()
        self.load_defaults()
        self.connect_events()

    def build(self):
        self.fake_deck_spin = Adw.SpinRow().new_with_range(min=0, max=3, step=1)
        self.fake_deck_spin.set_title("Number of fake decks")
        self.fake_deck_spin.set_subtitle("Might require restart of the app")
        self.add(self.fake_deck_spin)

        self.data_path_entry = Adw.EntryRow(title="Data Path (requires restart)")
        self.add(self.data_path_entry)

        self.open_data_path_button = Gtk.Button(icon_name="folder-open-symbolic", valign=Gtk.Align.CENTER)
        self.data_path_entry.add_suffix(self.open_data_path_button)

        self.browse_data_path_button = Gtk.Button(icon_name="system-search-symbolic", valign=Gtk.Align.CENTER)
        self.data_path_entry.add_suffix(self.browse_data_path_button)

    def load_defaults(self):
        developer_settings = self.settings.settings_json.get("dev", {})

        self.fake_deck_spin.set_value(int(developer_settings.get("n-fake-decks", 0)))

        static_settings = gl.settings_manager.get_static_settings()
        self.data_path_entry.set_text(static_settings.get("data-path", gl.DATA_PATH))

    def connect_events(self):
        self.fake_deck_spin.connect("changed", self.on_fake_deck_changed)
        self.data_path_entry.connect("changed", self.on_data_path_changed)
        self.open_data_path_button.connect("clicked", self.on_open_data_path_clicked)
        self.browse_data_path_button.connect("clicked", self.on_browse_data_path_clicked)

    def disconnect_events(self):
        better_disconnect(self.fake_deck_spin, self.on_fake_deck_changed)
        better_disconnect(self.data_path_entry, self.on_data_path_changed)
        better_disconnect(self.open_data_path_button, self.on_open_data_path_clicked)
        better_disconnect(self.browse_data_path_button, self.on_browse_data_path_clicked)

    def on_fake_deck_changed(self, *args):
        self.settings.settings_json.setdefault("dev", {})
        self.settings.settings_json["dev"]["n-fake-decks"] = self.fake_deck_spin.get_value()

        # Save
        self.settings.save_json()

        # Reload decks
        gl.deck_manager.load_fake_decks()

    def on_data_path_changed(self, *args):
        static_settings = gl.settings_manager.get_static_settings()
        static_settings["data-path"] = self.data_path_entry.get_text()
        gl.settings_manager.save_static_settings(static_settings)

    def on_open_data_path_clicked(self, *args):
        path = self.data_path_entry.get_text()

        if is_flatpak():
            command = ["flatpak-spawn", "--host", "xdg-open", path]
        else:
            command = ["xdg-open", path]

        try:
            subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            # fallback to gio if xdg-open missing
            fallback = ["gio", "open", path]
            subprocess.Popen(fallback, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            pass

    def on_browse_data_path_clicked(self, button):
        dialog = Gtk.FileDialog()
        dialog.set_title("Select Data Path")

        # Set initial folder if available
        current_path = self.data_path_entry.get_text()
        if current_path:
            file = Gio.File.new_for_path(current_path)
            dialog.set_initial_folder(file)

        # Show the folder chooser asynchronously
        dialog.select_folder(self.get_root(), None, self.on_browse_response)

    def on_browse_response(self, dialog, result):
        try:
            file = dialog.select_folder_finish(result)
            if file:
                folder_path = file.get_path()
                if folder_path:
                    self.data_path_entry.set_text(folder_path)
                    self.on_data_path_changed()
        except:
            pass
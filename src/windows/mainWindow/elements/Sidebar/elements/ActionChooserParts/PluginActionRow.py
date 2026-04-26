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
import gi
from loguru import logger as log

from src.backend.DeckManagement.InputIdentifier import InputIdentifier
from src.backend.PluginManager.ActionHolder import ActionHolder
from src.backend.PluginManager.ActionInputSupport import ActionInputSupport

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk


class PluginActionRow(Adw.ActionRow):
    def __init__(self, expander, action_holder: ActionHolder, **kwargs):
        super().__init__(**kwargs)
        self.expander = expander
        self.action_holder = action_holder

        self.button = Gtk.Button(hexpand=True, vexpand=True, overflow=Gtk.Overflow.HIDDEN,
                                 css_classes=["no-margin", "invisible"])
        self.button.connect("clicked", self.on_click)
        self.set_child(self.button)
        
        self.main_box = Gtk.Box(hexpand=True, vexpand=True, orientation=Gtk.Orientation.HORIZONTAL,
                                margin_top=10, margin_bottom=10)
        self.button.set_child(self.main_box)

        # self.icon = Gtk.Image(icon_name="insert-image", icon_size=Gtk.IconSize.LARGE, margin_start=5)
        self.icon = action_holder.icon
        if action_holder.icon.get_parent() is not None:
            self.action_holder.icon.get_parent().remove(self.action_holder.icon)
        self.main_box.append(self.icon)

        self.label = Gtk.Label(label=self.action_holder.action_name, margin_start=10, css_classes=["bold", "large-text"])
        self.main_box.append(self.label)

        self.warning_icon = Gtk.Image(icon_name="dialog-warning-symbolic",
                                      hexpand=True, halign=Gtk.Align.END, margin_end=3, visible=False)
        self.main_box.append(self.warning_icon)

    def on_click(self, button):
        if self.action_holder.action_core == None:
            return
        
        # Go back to old page
        self.expander.plugin_group.action_chooser.sidebar.main_stack.set_visible_child(self.expander.plugin_group.action_chooser.current_stack_page)

        # Verify the callback function
        if not callable(self.expander.plugin_group.action_chooser.callback_function):
            log.warning(f"Invalid callback function: {self.expander.plugin_group.action_chooser.callback_function}")
            return
        
        # Call the callback function
        callback = self.expander.plugin_group.action_chooser.callback_function
        args = self.expander.plugin_group.action_chooser.callback_args
        kwargs = self.expander.plugin_group.action_chooser.callback_kwargs

        
        callback(self.action_holder, *args, **kwargs)

    def show_warning(self, show: bool, tooltip: str = None):
        self.warning_icon.set_visible(show)

        if show and tooltip is not None:
            self.warning_icon.set_tooltip_text(tooltip)

    def set_identifier(self, identifier: InputIdentifier):
        action_input_compatibility = self.action_holder.get_input_compatibility(identifier)

        if action_input_compatibility <= ActionInputSupport.UNSUPPORTED:
            self.warning_icon.set_from_icon_name("dialog-error-symbolic")
            self.set_tooltip_text(f"Action is not compatible with {identifier.input_type}")
            self.show_warning(True)
            self.set_sensitive(False)
            
        elif action_input_compatibility == ActionInputSupport.UNTESTED:
            self.warning_icon.set_from_icon_name("dialog-warning-symbolic")
            self.warning_icon.set_tooltip_text(f"Action might not be compatible with {identifier.input_type}")
            self.set_tooltip_text("")
            self.show_warning(True)
            self.set_sensitive(True)

        elif action_input_compatibility >= ActionInputSupport.SUPPORTED:
            self.set_tooltip_text("")
            self.show_warning(False)
            self.set_sensitive(True)

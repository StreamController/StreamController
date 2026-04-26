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
from typing import TYPE_CHECKING

import gi
from loguru import logger as log

import globals as gl
from src.backend.DeckManagement.HelperMethods import add_default_keys
from src.windows.Settings.PluginSettingsWindow.PluginSettingsWindow import (
    PluginSettingsWindow,
)

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw

if TYPE_CHECKING:
    from src.windows.mainWindow.elements.Sidebar.elements.ActionManagerParts.ActionExpanderRow import (
        ActionExpanderRow,
    )


class AddActionButtonRow:
    def __init__(self, expander: "ActionExpanderRow", **kwargs):
        # super().__init__(**kwargs, css_classes=["no-padding"])
        self.expander: "ActionExpanderRow" = expander
        self.button = Adw.ButtonRow(title=gl.lm.get("action-editor-add-new-action"), css_classes=["suggested-action", "add-action-button"])
        # self.button = Gtk.Button(hexpand=True, vexpand=True, overflow=Gtk.Overflow.HIDDEN,
        #                          css_classes=["no-margin", "suggested-action"],
        #                          label=gl.lm.get("action-editor-add-new-action"),
        #                          margin_bottom=5, margin_top=5)
        self.button.connect("activated", self.on_click)
        self.action_name = "Add Action"
        # self.set_child(self.button)

    def on_click(self, button):
        self.expander.action_group.sidebar.let_user_select_action(callback_function=self.add_action, identifier=self.expander.active_identifier)

    def add_action(self, action_class):
        log.trace(f"Adding action: {action_class}")

        # Gather data
        # action_string = gl.plugin_manager.get_action_string_from_action(action_class)
        active_page = gl.app.main_win.get_active_page()
        if active_page is None:
            return
        
        add_default_keys(active_page.dict, [self.expander.active_identifier.input_type, self.expander.active_identifier.json_identifier, "states", str(self.expander.active_state)])
        state_dict = active_page.dict[self.expander.active_identifier.input_type][self.expander.active_identifier.json_identifier]["states"][str(self.expander.active_state)]
        state_dict.setdefault("actions", [])

        # Add action
        state_dict["actions"].append({
            "id": action_class.action_id,
            "settings": {}
        })

        if len(state_dict["actions"]) == 1:
            state_dict.setdefault("image-control-action", 0)
            state_dict.setdefault("label-control-actions", [0, 0, 0])
            state_dict.setdefault("background-control-action", 0)

        # Save page
        active_page.save()
        # Reload page to add an object to the new action
        active_page.load()
        # Reload the key on all decks
        active_page.reload_similar_pages(identifier=self.expander.active_identifier, reload_self=True)

        # Reload ui
        self.expander.load_for_identifier(self.expander.active_identifier, self.expander.active_state)

        rows = self.expander.get_rows()
        if len(rows) < 2:
            return

        last_row = rows[-2]  # -1 is the add button
        action = last_row.action_object

        # Open Action Config Screen
        settings = gl.settings_manager.get_app_settings()
        if settings.get("ui", {}).get("auto-open-action-config", True):
            if action and action.has_configuration:
                gl.app.main_win.sidebar.action_configurator.load_for_action(last_row.action_object, last_row.index)
                gl.app.main_win.sidebar.show_action_configurator()

        # Open Plugin Settings Window
        if action and action.plugin_base.has_plugin_settings and action.plugin_base.first_setup:
            settings_window = PluginSettingsWindow(action.plugin_base)
            settings_window.present(gl.app.get_active_window())

            settings = action.plugin_base.get_settings()
            settings["first-setup"] = False
            action.plugin_base.set_settings(settings)
            action.plugin_base.first_setup = False

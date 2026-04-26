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

import globals as gl

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk


class RemoveButton(Gtk.Button):
    def __init__(self, configurator, **kwargs):
        super().__init__(**kwargs)
        self.set_css_classes(["remove-action-button"])
        self.configurator = configurator
        self.set_label(gl.lm.get("action-configurator-remove-action"))
        self.set_margin_bottom(100)
        self.connect("clicked", self.on_remove_button_click)

        self.action = None
        self.index = None

    def on_remove_button_click(self, button):
        visible_child = gl.app.main_win.leftArea.deck_stack.get_visible_child()
        if visible_child is None:
            return
        controller = visible_child.deck_controller
        if controller is None:
            return
        page = controller.active_page

        # Swtich to main editor page
        self.configurator.sidebar.main_stack.set_visible_child_name("configurator_stack")

        # Remove from action_objects
        try:
            del page.action_objects[self.action.input_ident.input_type][self.action.input_ident.json_identifier][int(self.action.state)][self.index]
        except KeyError:
            #FIXME
            pass
        page.fix_action_objects_order(self.action.input_ident)

        # Remove from page json
        page.dict[self.action.input_ident.input_type][self.action.input_ident.json_identifier]["states"][str(self.action.state)]["actions"].pop(self.index)

        #TODO: Also update if action before this one has the access
        if self.action.input_ident.input_type == "keys" and page.dict[self.action.input_ident.input_type][self.action.input_ident.json_identifier]["states"][str(self.action.state)].get("image-control-action") == self.index:
            if len(page.dict[self.action.input_ident.input_type][self.action.input_ident.json_identifier]["states"][str(self.action.state)]["actions"]) > 0:
                page.dict[self.action.input_ident.input_type][self.action.input_ident.json_identifier]["states"][str(self.action.state)]["image-control-action"] = 0
            else:
                page.dict[self.action.input_ident.input_type][self.action.input_ident.json_identifier]["states"][str(self.action.state)]["image-control-action"] = None

        page.save()

        # Reload configurator
        self.configurator.sidebar.update()

        # Check whether we have to reload the key
        load = not page.has_key_an_image_controlling_action(self.action.input_ident, self.action.state)
        load = True # TODO
        if load:
            page.reload_similar_pages(identifier=self.action.input_ident, reload_self=True)

        # Destroy the actual action
        if hasattr(self.action, "on_remove"):
            self.action.on_remove()
        del self.action


    def load_for_action(self, action, index):
        self.action = action
        self.index = index

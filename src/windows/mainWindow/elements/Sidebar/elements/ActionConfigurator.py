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
from cv2 import exp
import gi

from GtkHelper.GtkHelper import BackButton
from src.backend.DeckManagement.InputIdentifier import Input, InputEvent

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

# Import globals
import globals as gl

# Import own modules
from src.backend.PluginManager.ActionBase import ActionBase


class ActionConfigurator(Gtk.Box):
    def __init__(self, sidebar, **kwargs):
        super().__init__(**kwargs)
        self.sidebar = sidebar
        self.build()

    def build(self):
        self.scrolled_window = Gtk.ScrolledWindow(hexpand=True, vexpand=True, margin_end=4)
        self.append(self.scrolled_window)

        self.clamp = Adw.Clamp()
        self.scrolled_window.set_child(self.clamp)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True, margin_top=4)
        self.clamp.set_child(self.main_box)

        self.nav_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        self.main_box.append(self.nav_box)

        self.back_button = BackButton()
        self.back_button.connect("clicked", self.on_back_button_click)
        self.nav_box.append(self.back_button)

        self.header = Gtk.Label(label=gl.lm.get("action-configurator-header"), xalign=0, css_classes=["page-header"], margin_start=20, margin_top=30)
        self.main_box.append(self.header)

        self.comment_group = CommentGroup(self, margin_top=20)
        self.main_box.append(self.comment_group)

        self.event_assigner = EventAssigner(self, margin_top=20)
        self.main_box.append(self.event_assigner)

        self.main_box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL, margin_top=20, margin_bottom=20))

        self.config_group = ConfigGroup(self)
        self.main_box.append(self.config_group)

        self.custom_configs = CustomConfigs(self, margin_top=6)
        self.main_box.append(self.custom_configs)

        self.remove_button = RemoveButton(self, margin_top=12)
        self.main_box.append(self.remove_button)


    def load_for_action(self, action, index):
        self.config_group.load_for_action(action)
        self.custom_configs.load_for_action(action)
        self.remove_button.load_for_action(action, index)
        self.comment_group.load_for_action(action, index)
        self.event_assigner.load_for_action(action)

    def on_back_button_click(self, button):
        self.sidebar.main_stack.set_visible_child_name("configurator_stack")

class CommentGroup(Adw.PreferencesGroup):
    def __init__(self, parent, **kwargs):
        super().__init__(**kwargs)
        self.parent = parent
        self.action: ActionBase = None
        self.index: int = None
        self.build()

    def build(self):
        self.comment_row = Adw.EntryRow(title="Comment")
        self.connect_signals()
        self.add(self.comment_row)

    def load_for_action(self, action, index):
        self.disconnect_signals()
        self.action = action
        self.index = index

        comment = self.get_comment()
        if comment is None:
            comment = ""
        self.comment_row.set_text(comment)

        self.connect_signals()

    def on_comment_changed(self, entry):
        self.set_comment(entry.get_text())

        # Update ActionManager - A full reload is not efficient but ensures correct behavior if the ActionConfigurator is triggered from a plugin action
        if self.action.input_ident.input_type == "keys":
            gl.app.main_win.sidebar.key_editor.action_editor.load_for_coords(self.action.input_ident.coords, self.action.state)

    def connect_signals(self):
        self.comment_row.connect("changed", self.on_comment_changed)

    def disconnect_signals(self):
        self.comment_row.disconnect_by_func(self.on_comment_changed)
    

    def get_comment(self) -> str:
        visible_child = gl.app.main_win.leftArea.deck_stack.get_visible_child()
        if visible_child is None:
            return
        controller = visible_child.deck_controller
        if controller is None:
            return
        page = controller.active_page
        if page is None:
            return
        return page.get_action_comment(self.index, self.action.state, self.action.input_ident)
    
    def set_comment(self, comment: str) -> None:
        visible_child = gl.app.main_win.leftArea.deck_stack.get_visible_child()
        if visible_child is None:
            return
        controller = visible_child.deck_controller
        if controller is None:
            return
        page = controller.active_page
        page.set_action_comment(self.index, comment, self.action.state, self.action.input_ident)
    


class ConfigGroup(Adw.PreferencesGroup):
    def __init__(self, parent, **kwargs):
        super().__init__(**kwargs)
        self.parent = parent
        self.loaded_rows = []
        self.build()

    def build(self):
        pass

    def load_for_action(self, action: ActionBase):
        if not hasattr(action, "get_config_rows"):
            self.hide()
            return
        
        config_rows = action.get_config_rows()
        if config_rows is None:
            self.hide()
            return
        # Load labels
        self.set_title(action.action_name)
        self.set_description(action.plugin_base.plugin_name)

        # Clear
        self.clear()

        # Load rows
        for row in config_rows:
            self.add(row)
            self.loaded_rows.append(row)
        
        # Show
        self.show()

    def clear(self):
        for row in self.loaded_rows:
            self.remove(row)
        self.loaded_rows = []

class CustomConfigs(Gtk.Box):
    def __init__(self, parent, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, **kwargs)
        self.parent = parent

        self.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL, margin_bottom=6))

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.append(self.main_box)

    def load_for_action(self, action):
        if not hasattr(action, "get_custom_config_area"):
            self.hide()
            return
        
        if action.get_custom_config_area() is None:
            self.hide()
            return
        
        # Clear
        self.clear()

        # Append custom config area
        custom_config_area = action.get_custom_config_area()
        if custom_config_area is not None:
            self.main_box.append(custom_config_area)

        # Show
        self.show()

    def clear(self):
        while self.main_box.get_first_child() is not None:
            self.main_box.remove(self.main_box.get_first_child())

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
            page.reload_similar_pages(identifier=self.action.input_ident)

        # Destroy the actual action
        del self.action


    def load_for_action(self, action, index):
        self.action = action
        self.index = index

class EventAssigner(Adw.PreferencesGroup):
    def __init__(self, action_configurator: ActionConfigurator, **kwargs):
        super().__init__(**kwargs)
        self.action_configurator = action_configurator
        self.action: ActionBase = None
        self.build()

    def build(self):
        self.expander = Adw.ExpanderRow(title="Event Assigner", subtitle="Configure event assignments",
                                        expanded=True)
        self.add(self.expander)

        self.reset_button = Gtk.Button(icon_name="edit-undo-symbolic", tooltip_text="Reset to default",
                                       valign=Gtk.Align.CENTER, css_classes=["flat"])
        self.reset_button.connect("clicked", self.on_reset)
        self.expander.add_suffix(self.reset_button)

        all_events = Input.AllEvents()

        self.rows: list[EventAssignerRow] = []

        for event in all_events:
            row = EventAssignerRow(
                event_assigner=self,
                event=event,
                available_events=all_events
            )

            self.rows.append(row)
            self.expander.add_row(row)

    def load_for_action(self, action: ActionBase):
        self.action = action

        assignments = action.get_event_assignments()

        for row in self.rows:
            new_assignment = assignments.get(row.event)
            row.select_event(new_assignment)

            action_input_type = type(action.input_ident)
            row.set_visible(row.event in action_input_type.Events)

    def change_assignment_for_event(self, event: InputEvent, new_assignment: InputEvent):
        assignments = self.action.get_event_assignments()
        assignments[event] = new_assignment
        self.action.set_event_assignments(assignments)

    def reset_assignments(self):
        self.action.set_event_assignments({})

    def on_reset(self, button):
        self.reset_assignments()
        self.load_for_action(self.action)


class EventAssignerRow(Adw.ComboRow):
    def __init__(self, event_assigner: EventAssigner, event: InputEvent, available_events: list[InputEvent]):
        super().__init__()

        self.event_assigner = event_assigner
        self.event = event
        self.available_events = available_events

        self.build()

    def _connect_signal(self):
        self.connect("notify::selected", self.on_changed)

    def _disconnect_signal(self):
        try:
            self.disconnect_by_func(self.on_changed)
        except TypeError:
            pass

    def build(self):
        self.set_title(self.event.string_name)

        self.str_list = Gtk.StringList()
        for event in self.available_events:
            self.str_list.append(event.string_name)

        self.set_model(self.str_list)

        self.select_event(None)

    def select_event(self, event: InputEvent):
        self._disconnect_signal()
        string_name = None
        if isinstance(event, InputEvent):
            string_name = event.string_name

        for i, e in enumerate(self.str_list):
            if e.get_string() == string_name:
                self.set_selected(i)
                self._connect_signal()
                return
            
        self.set_selected(Gtk.INVALID_LIST_POSITION)
        self._connect_signal()

    def on_changed(self, *args):
        selected = self.get_selected()

        if selected == Gtk.INVALID_LIST_POSITION:
            event = None
        else:
            string_name = self.str_list[selected].get_string()
            event = Input.EventFromStringName(string_name)

        self.event_assigner.change_assignment_for_event(self.event, event)
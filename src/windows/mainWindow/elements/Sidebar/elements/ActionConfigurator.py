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

from GtkHelper.GtkHelper import BackButton, BetterPreferencesGroup
from src.backend.PluginManager.EventAssigner import EventAssigner
from src.backend.DeckManagement.InputIdentifier import Input, InputEvent

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GObject, Gio

# Import globals
import globals as gl

# Import own modules
from src.backend.PluginManager.ActionCore import ActionCore


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

        self.event_assigner = EventAssignerUI(self, margin_top=20)
        self.main_box.append(self.event_assigner)

        self.main_box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL, margin_top=20, margin_bottom=20))

        self.config_group = ConfigGroup(self)
        self.main_box.append(self.config_group)

        self.config_group_and_custom_configs_separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL, margin_top=20, margin_bottom=20)
        self.main_box.append(self.config_group_and_custom_configs_separator)

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

        self.config_group_and_custom_configs_separator.set_visible(self.config_group.is_visible() and self.custom_configs.is_visible())

    def on_back_button_click(self, button):
        self.sidebar.main_stack.set_visible_child_name("configurator_stack")

class CommentGroup(Adw.PreferencesGroup):
    def __init__(self, parent, **kwargs):
        super().__init__(**kwargs)
        self.parent = parent
        self.action: ActionCore = None
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
        gl.app.main_win.sidebar.key_editor.action_editor.load_for_identifier(self.action.input_ident, self.action.state)

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

    def load_for_action(self, action: ActionCore):
        config_rows = action.get_config_rows()

        if not config_rows:
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

        for gen_ui_row in action.get_generative_ui_widgets():
            self.add(gen_ui_row)
            self.loaded_rows.append(gen_ui_row)
        
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

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.append(self.main_box)

    def load_for_action(self, action):
        # Append custom config area
        custom_config_area = action.get_custom_config_area()
        
        if custom_config_area is None:
            self.hide()
            return

        # Clear
        self.clear()

        # Append custom content
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
            page.reload_similar_pages(identifier=self.action.input_ident, reload_self=True)

        # Destroy the actual action
        if hasattr(self.action, "on_remove"):
            self.action.on_remove()
        del self.action


    def load_for_action(self, action, index):
        self.action = action
        self.index = index

class EventAssignerUI(BetterPreferencesGroup):
    def __init__(self, action_configurator: ActionConfigurator, **kwargs):
        super().__init__(**kwargs)
        self.action_configurator = action_configurator
        self.action: ActionCore = None
        self.build()

    def build(self):
        self.expander = Adw.ExpanderRow(title="Event Assigner", subtitle="Configure event assignments")
        self.add(self.expander)

        self.button_box = Gtk.Box(css_classes=["linked"])
        self.expander.add_suffix(self.button_box)

        self.reset_button = Gtk.Button(icon_name="edit-undo-symbolic", tooltip_text="Reset to default",
                                       valign=Gtk.Align.CENTER)
        self.reset_button.connect("clicked", self.on_reset)
        self.button_box.append(self.reset_button)

        self.clear_all_button = Gtk.Button(icon_name="edit-clear-all-symbolic", tooltip_text="Clear all",
                                           valign=Gtk.Align.CENTER)
        self.clear_all_button.connect("clicked", self.on_clear_all)
        self.button_box.append(self.clear_all_button)

        all_events = Input.AllEvents()
        self.rows: list[EventAssignerRow] = []

        for event in all_events:
            row = EventAssignerRow(
                event_assigner=self,
                event=event
            )

            self.rows.append(row)
            self.expander.add_row(row)

    def load_for_action(self, action: ActionCore):
        self.action = action
        
        self.set_sensitive(action.allow_event_configuration)

        # return
        # self.clear()

        all_event_assigners = action.event_manager.get_all_event_assigners()
        event_assigner_map = action.event_manager.get_event_map()

        for row in self.rows:
            row.set_available_events(all_event_assigners)
            row.select_event(event_assigner_map.get(row.event, None))

            action_input_type = type(action.input_ident)
            row.set_visible(row.event in action_input_type.Events)


        return

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
        self.action.set_all_events_to_null()
        # for event, assigner in self.action.event_manager.get_event_map(True).items():
            # self.action.set_event_assignment(event, assigner.default_event)
        
        for assigner in self.action.event_manager.get_all_event_assigners():
            self.action.set_event_assignment(assigner.default_event, assigner)


    def on_reset(self, button):
        self.reset_assignments()
        self.load_for_action(self.action)

    def on_clear_all(self, button):
        assignments: dict[InputEvent, InputEvent] = {}
        for row in self.rows:
            if not row.get_visible():
                continue

            assignments[row.event] = None

        self.action.set_all_events_to_null()
        # self.action.set_event_assignments(assignments)
        self.load_for_action(self.action)



class EventAssignerRowItem(GObject.Object):
    __gtype_name__ = "EventAssignerRowItem"

    ui_label = GObject.Property(type=str)
    id = GObject.Property(type=str)
    # event_assigner = GObject.Property(type=EventAssigner)


    def __init__(self, event_assigner: EventAssigner):
        super().__init__()
        if not event_assigner:
            self.ui_label = "None"
            self.id = None
            return
        
        self.ui_label = event_assigner.ui_label
        self.id = event_assigner.id



class EventAssignerRow(Adw.ComboRow):
    def __init__(self, event_assigner: EventAssignerUI, event: InputEvent):
        super().__init__()

        self.set_title(str(event))
        self.event_assigner = event_assigner
        self.event = event
        self.available_events: list[EventAssigner] = []

        # Create the item list factory
        self.factory = Gtk.SignalListItemFactory()
        self.set_factory(self.factory)

        def f_setup(fact, item):
            label = Gtk.Label(halign=Gtk.Align.START)
            label.set_selectable(False)
            item.set_child(label)
        self.factory.connect("setup", f_setup)

        def f_bind(fact, item):
            item.get_child().set_label(item.get_item().ui_label)
        self.factory.connect("bind", f_bind)

        self.connect("notify::selected", self.on_changed)



    def _connect_signal(self):
        self.connect("notify::selected", self.on_changed)

    def _disconnect_signal(self):
        try:
            self.disconnect_by_func(self.on_changed)
        except TypeError:
            pass

    def set_available_events(self, events: list[EventAssigner]):
        self._disconnect_signal()
        model = Gio.ListStore.new(EventAssignerRowItem)
        self.set_model(model)

        model.append(EventAssignerRowItem(None))

        for event in events:
            model.append(EventAssignerRowItem(event))

        self.set_selected(0)
        self._connect_signal()

    def select_event(self, event_assigner: EventAssigner):
        self._disconnect_signal()

        model = self.get_model()

        for i in range(model.get_n_items()):
            e = model.get_item(i)
            if event_assigner is None:
                if e.id == None:
                    self.set_selected(i)
                    self._connect_signal()
                    return
                
            if e.id == event_assigner.id:
                self.set_selected(i)
                self._connect_signal()
                return
            
        self.set_selected(Gtk.INVALID_LIST_POSITION)
        self._connect_signal()

    def on_changed(self, *args):
        selected = self.get_selected_item()

        event_id = selected.id if selected else None


        event_assigner = self.event_assigner.action.event_manager.get_event_assigner_by_id(event_id)
        self.event_assigner.action.set_event_assignment(self.event, event_assigner)


        return

        if selected == Gtk.INVALID_LIST_POSITION:
            event = None
        else:
            string_name = self.str_list[selected].get_string()
            event = Input.EventFromStringName(string_name)

        self.event_assigner.change_assignment_for_event(self.event, event)
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

from GtkHelper.GtkHelper import BetterPreferencesGroup
from src.backend.DeckManagement.InputIdentifier import Input, InputEvent
from src.backend.PluginManager.ActionCore import ActionCore
from src.backend.PluginManager.EventAssigner import EventAssigner

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GObject, Gtk

if TYPE_CHECKING:
    from src.windows.mainWindow.elements.Sidebar.elements.ActionConfigurator import (
        ActionConfigurator,
    )


class EventAssignerUI(BetterPreferencesGroup):
    def __init__(self, action_configurator: "ActionConfigurator", **kwargs):
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
            for event in assigner.default_events:
                self.action.set_event_assignment(event, assigner)


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
    tooltip = GObject.Property(type=str)
    # event_assigner = GObject.Property(type=EventAssigner)


    def __init__(self, event_assigner: EventAssigner):
        super().__init__()
        if not event_assigner:
            self.ui_label = "None"
            self.id = None
            return
        
        self.ui_label = event_assigner.ui_label
        self.id = event_assigner.id
        self.tooltip = event_assigner.tooltip



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
            item.get_child().set_tooltip_text(item.get_item().tooltip)
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

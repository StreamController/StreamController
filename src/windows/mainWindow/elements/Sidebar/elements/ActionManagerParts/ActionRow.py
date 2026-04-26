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

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gtk, Pango

if TYPE_CHECKING:
    from src.backend.PluginManager.ActionCore import ActionCore
    from src.windows.mainWindow.elements.Sidebar.elements.ActionManagerParts.ActionExpanderRow import (
        ActionExpanderRow,
    )
    from src.windows.mainWindow.elements.Sidebar.Sidebar import Sidebar


class ActionRowLabelToggle(Gtk.Button):
    def __init__(self, action_row: "ActionRow"):
        self.action_row = action_row
        super().__init__(tooltip_text="Control which labels are controlled by this action")

        self.build()

    def build(self):
        self.set_css_classes(["blue-toggle-button"])

        self.main_box = Gtk.Box()
        self.set_child(self.main_box)

        self.main_box.append(Gtk.Image(icon_name="format-text-italic-symbolic"))

        self.indicator_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3, valign=Gtk.Align.CENTER, margin_start=5)
        self.main_box.append(self.indicator_box)


        self.indicators: list[Gtk.Box] = []
        for i in range(3):
            indicator = Gtk.Box(css_classes=["action-row-label-toggle-inactive"])
            self.indicator_box.append(indicator)
            self.indicators.append(indicator)

        self.config_buttons: list[Gtk.CheckButton] = []
        self.config_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        label_names = ["Top", "Center", "Bottom"]
        for i, name in enumerate(label_names):
            check = Gtk.CheckButton(label=name, name=str(i))
            self.config_buttons.append(check)
            if "action-row-label-toggle-active" in self.indicators[i].get_css_classes():
                check.set_active(True)    
            check.connect("toggled", self.on_label_toggled)
            self.config_box.append(check)


        self.popover = Gtk.Popover(child=self.config_box)
        self.main_box.append(self.popover)


        self.connect("clicked", self.on_click)

    def on_click(self, button):
        self.popover.popup()

    def on_label_toggled(self, button: Gtk.CheckButton):
        i = int(button.get_name())

        indicator = self.indicators[i]

        if button.get_active():
            indicator.set_css_classes(["action-row-label-toggle-active"])
        else:
            indicator.set_css_classes(["action-row-label-toggle-inactive"])

        self.action_row.label_toggled(i, button.get_active())

    def connect_signals(self):
        for button in self.config_buttons:
            button.connect("toggled", self.on_label_toggled)

    def disconnect_signals(self):
        for button in self.config_buttons:
            try:
                button.disconnect_by_func(self.on_label_toggled)
            except:
                pass

    def set_active(self, values: list[bool]) -> None:
        self.disconnect_signals()
        for i, value in enumerate(values):
            indicator = self.indicators[i]
            if value:
                indicator.set_css_classes(["action-row-label-toggle-active"])
            else:
                indicator.set_css_classes(["action-row-label-toggle-inactive"])

            self.config_buttons[i].set_active(value)
        self.connect_signals()

    def get_active(self) -> list[bool]:
        return [indicator.get_css_classes() == ["action-row-label-toggle-active"] for indicator in self.indicators]


class ActionRow(Adw.ActionRow):
    def __init__(self, action_name, action_id, action_category, action_object, sidebar: "Sidebar", comment: str, index, controls_image: bool, controls_labels: list[bool], controls_background: bool, total_rows: int, expander: "ActionExpanderRow", **kwargs):
        super().__init__(**kwargs, css_classes=["no-padding"])
        self.action_name = action_name
        self.action_id = action_id
        self.action_category = action_category
        self.sidebar: "Sidebar" = sidebar
        self.action_object: "ActionCore" = action_object
        self.comment = comment
        self.index = index
        self.controls_image = controls_image
        self.controls_labels = controls_labels
        self.controls_background = controls_background
        self.active_type = None
        self.active_identifier = None
        self.total_rows = total_rows
        self.expander = expander
        self.build()
        self.update_allow_box_visibility()
        # self.init_dnd() #FIXME: Add drag and drop

    def build(self):
        # self.overlay = Gtk.Overlay()
        # self.set_child(self.overlay)

        # self.button = Gtk.Button(hexpand=True, vexpand=True, overflow=Gtk.Overflow.HIDDEN, css_classes=["no-margin", "invisible", "action-row-button"])
        # self.button.connect("clicked", self.on_click)
        # self.overlay.set_child(self.button)

        self.connect("activated", self.on_click)

        self.set_activatable(True)


        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True, margin_start=15, margin_end=15, margin_top=15, margin_bottom=15)
        self.set_child(self.main_box)

        self.allow_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, css_classes=["linked"], margin_end=15)
        self.main_box.append(self.allow_box)

        self.allow_image_toggle = Gtk.ToggleButton(css_classes=["blue-toggle-button"], icon_name="image-x-generic-symbolic", active=self.controls_image,
                                                   tooltip_text="Allow action to control the media")
        self.allow_image_toggle.connect("toggled", self.on_allow_image_toggled)
        self.allow_box.append(self.allow_image_toggle)

        self.allow_background_toggle = Gtk.ToggleButton(css_classes=["blue-toggle-button"], icon_name="color-select-symbolic", active=self.controls_background,
                                                        tooltip_text="Allow action to control the background color")
        self.allow_background_toggle.connect("toggled", self.on_allow_background_toggled)
        self.allow_box.append(self.allow_background_toggle)

        self.allow_label_toggle = ActionRowLabelToggle(self)
        self.allow_label_toggle.set_active(self.controls_labels)
        self.allow_box.append(self.allow_label_toggle)
        
        self.left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, valign=Gtk.Align.CENTER)
        self.main_box.append(self.left_box)

        self.left_top_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        self.left_box.append(self.left_top_box)

        self.left_bottom_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        self.left_box.append(self.left_bottom_box)

        self.label = Gtk.Label(label=f"<b>{self.action_name}</b> <span color=\"#979797\">({self.action_category})</span>", use_markup=True, xalign=0, hexpand=False, margin_end=5,
                               wrap_mode=Pango.WrapMode.WORD_CHAR, wrap=True)
        self.left_top_box.append(self.label)

        self.comment_label = Gtk.Label(label=self.comment, xalign=0, sensitive=False, ellipsize=Pango.EllipsizeMode.END, margin_end=60)
        self.left_bottom_box.append(self.comment_label)

        if self.comment in ["", None]:
            self.left_bottom_box.set_visible(False)
            # self.left_top_box.set_

        ## Edit buttons
        self.button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, halign=Gtk.Align.END, valign=Gtk.Align.CENTER, css_classes=["linked"])
        self.main_box.append(self.button_box)
        # self.overlay.add_overlay(self.button_box)

        self.up_button = Gtk.Button(icon_name="go-up-symbolic")
        self.up_button.connect("clicked", self.on_click_up)
        self.button_box.append(self.up_button)

        self.down_button = Gtk.Button(icon_name="go-down-symbolic")
        self.down_button.connect("clicked", self.on_click_down)
        self.button_box.append(self.down_button)

        self.remove_button = Gtk.Button(icon_name="user-trash-symbolic", css_classes=["destructive-action"])
        # self.button_box.append(self.remove_button) #TODO
        # self.remove_button.connect("clicked", self.on_click_remove)

    def update_allow_box_visibility(self):
        self.allow_box.set_visible(True) #TODO
        return
        if self.expander.active_identifier is None:
            self.allow_box.set_visible(False)
            return
        hide = self.controls_image and any(self.controls_labels) and (self.total_rows == 1)
        self.allow_box.set_visible(not hide)

    def on_allow_image_toggled(self, button):
        for child in self.expander.get_rows():
            if child is self:
                continue
            if not isinstance(child, ActionRow):
                continue
            child.set_image_toggled(False)


        controller = gl.app.main_win.get_active_controller()
        if controller is None:
            return
        page = controller.active_page

        input_state = self.action_object.get_input().states.get(self.expander.active_state)
        if input_state is None:
            log.error("Input state not found")
            return
        
        new_value = self.index if button.get_active() else None
        input_state.action_permission_manager.set_image_control_index(new_value, True, True)

        page.reload_similar_pages(identifier=self.action_object.input_ident, reload_self=True)

    def on_allow_background_toggled(self, button):
        for child in self.expander.get_rows():
            if child is self:
                continue
            if not isinstance(child, ActionRow):
                continue
            child.set_background_toggled(False)

        controller = gl.app.main_win.get_active_controller()
        if controller is None:
            return
        page = controller.active_page

        input_state = self.action_object.get_input().states.get(self.expander.active_state)
        if input_state is None:
            log.error("Input state not found")
            return
        
        new_value = self.index if button.get_active() else None
        input_state.action_permission_manager.set_background_control_index(new_value, True, True)

        page.reload_similar_pages(identifier=self.action_object.input_ident, reload_self=True)

    def label_toggled(self, i, value):
        for child in self.expander.get_rows():
            if child is self:
                continue
            if not isinstance(child, ActionRow):
                continue
            # child.set_label_toggled(False)
            active = child.allow_label_toggle.get_active()
            active[i] = False
            child.allow_label_toggle.set_active(active)

        controller = gl.app.main_win.get_active_controller()
        if controller is None:
            return
       
        input_state = self.action_object.get_input().states.get(self.expander.active_state)
        if input_state is None:
            log.error("Input state not found")
            return
        
        value = self.action_object.get_own_action_index() if value else None
        
        input_state.action_permission_manager.set_label_control_index(i, value, True, True)

    def set_image_toggled(self, value: bool):
        try:
            self.allow_image_toggle.disconnect_by_func(self.on_allow_image_toggled)
        except:
            pass

        self.allow_image_toggle.set_active(value)

        self.allow_image_toggle.connect("toggled", self.on_allow_image_toggled)

    def set_background_toggled(self, value: bool):
        try:
            self.allow_background_toggle.disconnect_by_func(self.on_allow_background_toggled)
        except:
            pass

        self.allow_background_toggle.set_active(value)

        self.allow_background_toggle.connect("toggled", self.on_allow_background_toggled)

    def set_label_toggled(self, value: bool):
        try:
            self.allow_label_toggle.disconnect_by_func(self.on_allow_label_toggled)
        except:
            pass

        self.allow_label_toggle.set_active(value)

        self.allow_label_toggle.connect("toggled", self.on_allow_label_toggled)
        
    def get_own_index(self) -> int:
        return self.expander.get_index_of_child(self)

    def on_click_up(self, button):
        from src.windows.mainWindow.elements.Sidebar.elements.ActionManagerParts.AddActionButtonRow import (
            AddActionButtonRow,
        )
        one_up_child = self.expander.get_rows()[self.index - 1]
        if isinstance(one_up_child, AddActionButtonRow.button):
            return
        self.expander.reorder_child_after(self, one_up_child.button)
        self.expander.reorder_actions(self.index - 1, self.index)

        # self.expander.update_indices()


    def on_click_down(self, button):
        from src.windows.mainWindow.elements.Sidebar.elements.ActionManagerParts.AddActionButtonRow import (
            AddActionButtonRow,
        )
        one_down_child = self.expander.get_rows()[self.index + 1]
        if isinstance(one_down_child, AddActionButtonRow.button):
            return
        self.expander.reorder_child_after(self, one_down_child.button)
        self.expander.reorder_actions(self.index, self.index + 1)

        # self.expander.update_indices()
        
    def on_click_remove(self, button):
        visible_child = gl.app.main_win.leftArea.deck_stack.get_visible_child()
        if visible_child is None:
            return
        controller = visible_child.deck_controller
        if controller is None:
            return
        page = controller.active_page

        # Remove from action_objects
        del page.action_objects[self.action_object.type][self.action_object.identifier][self.index]
        page.fix_action_objects_order(self.action_object.type, self.action_object.identifier)

        # Remove from page json
        page.dict[self.action_object.type][self.action_object.identifier]["actions"].pop(self.index)
        page.save()

        page.reload_similar_pages(type=self.action_object.type, identifier=self.action_object.identifier)
        page.reload_similar_pages()

        if hasattr(self.action_object, "on_removed_from_cache"):
            self.action_object.on_removed_from_cache()

        self.action_object = None
        del self.action_object

        self.get_parent().remove(self)
            
        
    def init_dnd(self):
        if self.index == None:
            return
        # DnD Source
        dnd_source = Gtk.DragSource()
        dnd_source.set_actions(Gdk.DragAction.MOVE)
        dnd_source.connect("prepare", self.on_dnd_prepare)
        dnd_source.connect("drag-begin", self.on_dnd_begin)
        dnd_source.connect("drag-end", self.on_dnd_end)

        self.add_controller(dnd_source)

        # DnD Target
        dnd_target = Gtk.DropTarget.new(self, Gdk.DragAction.MOVE)
        dnd_target.set_gtypes([ActionRow])
        dnd_target.connect("drop", self.on_dnd_drop)
        dnd_target.connect("motion", self.on_dnd_motion)

        self.add_controller(dnd_target)

    def on_dnd_begin(self, drag_source, data):
        content = data.get_content()

    def on_dnd_end(self, drag_source, data, flag):
        pass

    def on_dnd_prepare(self, drag_source, x, y):
        drag_source.set_icon(
            Gtk.WidgetPaintable.new(self),
            self.get_width() / 2, self.get_height() / 2
        )
        content = Gdk.ContentProvider.new_for_value(self)
        return content

    def on_dnd_drop(self, drop_target, value, x, y):
        if not isinstance(value, ActionRow):
            return False
        
        self.sidebar.key_editor.action_editor.action_group.expander.reorder_child_after(value, self)
        return True
        # Remove preview
        index = self.sidebar.key_editor.action_editor.action_group.expander.get_index_of_child(self.sidebar.key_editor.action_editor.action_group.expander.preview)
        self.sidebar.key_editor.action_editor.action_group.expander.remove(self.sidebar.key_editor.action_editor.action_group.expander.preview)
        self.sidebar.key_editor.action_editor.action_group.expander.actions.pop(index)
        return True
    
    def on_dnd_motion(self, drop_target, x, y):
        if y > self.get_height() / 2:
            self.sidebar.key_editor.action_editor.action_group.expander.add_drop_preview(self.index-1)
        else:
            self.sidebar.key_editor.action_editor.action_group.expander.add_drop_preview(self.index)
        return Gdk.DragAction.MOVE


        self.sidebar.key_editor.action_editor.action_group.expander.add_drop_preview(self.index)

        return Gdk.DragAction.MOVE

    def on_click(self, button):
        self.sidebar.action_configurator.load_for_action(self.action_object, self.index)
        self.sidebar.show_action_configurator()

    def update_comment(self, comment: str):
        self.comment = comment
        # Update ui
        if comment is None:
            comment = ""
            self.left_bottom_box.set_visible(False)
        else:
            self.left_bottom_box.set_visible(True)

        self.comment_row.set_text(comment)

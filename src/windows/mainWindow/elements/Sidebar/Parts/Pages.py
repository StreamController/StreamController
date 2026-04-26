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
import os

import gi

import globals as gl
from GtkHelper.GtkHelper import BetterPreferencesGroup

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk


class PagesGroup(BetterPreferencesGroup):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.load_pages()

    def load_pages(self):
        pages = gl.page_manager.get_pages()
        for page_path in pages:
            if os.path.dirname(page_path) != os.path.join(gl.DATA_PATH, "pages"):
                continue
            page_row = AdwPageRow(pages_group=self, page_path=page_path)
            self.add(page_row)

        row1 = Adw.EntryRow(title="Title")
        self.add(row1)

        child:Gtk.Box = row1.get_child() # Box
        prefix_box:Gtk.Box = child.get_first_child()
        gizmo = prefix_box.get_next_sibling()
        empty_title = gizmo.get_first_child()
        title = empty_title.get_next_sibling()

        empty_title.set_visible(False)
        title.set_visible(False)

        row1.add_suffix(Gtk.Button(icon_name="view-more-symbolic", css_classes=["flat"], vexpand=False, valign=Gtk.Align.CENTER))


class AdwPageRow(Adw.PreferencesRow):
    def __init__(self, pages_group:PagesGroup, page_path:str = None):
        super().__init__(overflow=Gtk.Overflow.HIDDEN, css_classes=["no-padding"])

        self.pages_group = pages_group
        self.page_path = page_path

        # self.toggle_button = Gtk.ToggleButton(hexpand=True, vexpand=True, css_classes=["no-rounded-corners", "flat"])
        # self.toggle_button.connect("toggled", self.on_toggled)
        # self.set_child(self.toggle_button)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True, margin_bottom=6, margin_top=6,
                                margin_start=10, margin_end=10)
        self.set_child(self.main_box)
        # self.toggle_button.set_child(self.main_box)

        self.label = Gtk.Label(xalign=0, label=os.path.splitext(os.path.basename(page_path))[0], hexpand=False,
                               visible=True, margin_start=2)
        self.main_box.append(self.label)

        self.entry = Gtk.Entry(text=os.path.splitext(os.path.basename(page_path))[0], hexpand=False, xalign=0,
                               css_classes=["flat", "no-border", "no-outline"], has_frame=False,
                               visible=False)
        self.main_box.append(self.entry)

        self.active_icon = Gtk.Image(icon_name="selection-mode-symbolic", css_classes=["flat"], margin_start=3, visible=False)
        self.main_box.append(self.active_icon)

        self.edit_button = Gtk.Button(icon_name="document-edit-symbolic", halign=Gtk.Align.END, css_classes=["flat"], hexpand=True)
        self.edit_button.connect("clicked", self.on_edit_clicked)
        self.main_box.append(self.edit_button)

        # Click ctrl
        self.click_ctrl = Gtk.GestureClick.new()
        self.click_ctrl.set_button(1)
        self.click_ctrl.connect("pressed", self.on_click)
        self.main_box.add_controller(self.click_ctrl)

        # Focus ctrl
        self.focus_ctrl = Gtk.EventControllerFocus()
        self.main_box.add_controller(self.focus_ctrl)
        # self.focus_ctrl.connect("enter", self.on_focus_in)
        self.focus_ctrl.connect("leave", self.on_focus_out)

    def on_toggled(self, button):
        self.active_icon.set_visible(button.get_active())

    def on_loose_focus(self, *args):
        self.set_active(False)
        self.remove_css_class("active-border")
        self.label.set_visible(True)
        self.entry.set_visible(False)
        self.entry.set_hexpand(False)
        self.active_icon.set_visible(False)
        self.active_icon.set_hexpand(True)


    def on_focus_out(self, *args):
        return
        self.on_loose_focus()

    def remove_focus_from_other_pages(self):
        page_rows = self.pages_group.get_rows()
        for row in page_rows:
            if row != self:
                row.on_loose_focus()

    def on_click(self, gesture, n_press, x, y):
        self.remove_focus_from_other_pages()
        if n_press == 1:
            self.set_active(True)
            return

        elif n_press == 2:
            self.on_edit_clicked(self)

    def on_edit_clicked(self, button):
        self.add_css_class("active-border")
        show_label = not self.label.get_visible()
        self.label.set_visible(show_label)
        self.entry.set_visible(not show_label)
        self.entry.grab_focus_without_selecting()
        self.entry.set_position(-1)
        self.active_icon.set_hexpand(False)
        self.entry.set_hexpand(True)

    def set_active(self, active: bool):
        if active:
            self.set_other_rows_inactive()

        self.active_icon.set_visible(active)
        if active:
            self.add_css_class("page-row-active")
        else:
            self.remove_css_class("page-row-active")

    def set_other_rows_inactive(self):
        page_rows = self.pages_group.get_rows()
        for row in page_rows:
            if row != self:
                if hasattr(row, "set_active"):
                    row.set_active(False)
        




class PageRow(Gtk.Overlay):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_halign(Gtk.Align.CENTER)
        self.set_size_request(300, -1)
        self.build()

    def build(self):
        self.toggle_button = Gtk.ToggleButton(hexpand=False, css_classes=["flat"])
        self.set_child(self.toggle_button)

        self.label = Gtk.Label(xalign=0, label="Page Row")
        self.toggle_button.set_child(self.label)

        self.menu_button = Gtk.Button(icon_name="view-more-symbolic", halign=Gtk.Align.END, css_classes=["flat"])
        self.add_overlay(self.menu_button)

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
from typing_extensions import deprecated

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from GtkHelper.widgets.AttributeRow import AttributeRow
from GtkHelper.widgets.BackButton import BackButton
from GtkHelper.widgets.BetterExpander import BetterExpander
from GtkHelper.widgets.BetterPreferencesGroup import BetterPreferencesGroup
from GtkHelper.widgets.EntryDialog import EntryDialog
from GtkHelper.widgets.EntryRowWithoutTitle import EntryRowWithoutTitle
from GtkHelper.widgets.ErrorPage import ErrorPage
from GtkHelper.widgets.LoadingScreen import LoadingScreen
from GtkHelper.widgets.OriginalURL import OriginalURL
from GtkHelper.widgets.RevertButton import RevertButton

__all__ = [
    "AttributeRow",
    "BackButton",
    "BetterExpander",
    "BetterPreferencesGroup",
    "ComboRow",
    "EntryDialog",
    "EntryRowWithoutTitle",
    "ErrorPage",
    "LoadingScreen",
    "OriginalURL",
    "RevertButton",
    "ScaleRow",
    "better_disconnect",
    "better_unparent",
    "get_deepest_focused_widget",
    "get_deepest_focused_widget_with_attr",
    "get_focused_widgets",
]


# Helper Functions
def get_focused_widgets(start: Gtk.Widget) -> list[Gtk.Widget]:
    widgets = []
    while True:
        child = start.get_focus_child()
        if child is None:
            return widgets
        widgets.append(child)
        start = child

def get_deepest_focused_widget(start: Gtk.Widget) -> Gtk.Widget:
    return get_focused_widgets(start)[-1]

def get_deepest_focused_widget_with_attr(start: Gtk.Widget, attr:str) -> Gtk.Widget:
    for widget in reversed(get_focused_widgets(start)):
        if hasattr(widget, attr):
            return widget

def better_disconnect(widget: Gtk.Widget, handler: callable):
    try:
        widget.disconnect_by_func(handler)
    except Exception:
        pass

def better_unparent(widget: Gtk.Widget):
    if widget.get_parent() is not None:
        widget.unparent()


# These two classes collide by name with the standalone GtkHelper/ComboRow.py
# and GtkHelper/ScaleRow.py modules (which expose different APIs and are
# themselves plugin-imported). They stay in GtkHelper.py so that
# `from GtkHelper.GtkHelper import ComboRow, ScaleRow` continues to resolve to
# the same class objects it always has.
@deprecated("This has been deprecated in favor of GtkHelper.ComboRow.ComboRow.")
class ComboRow(Adw.PreferencesRow):
    def __init__(self, title, model: Gtk.ListStore, **kwargs):
        super().__init__(title=title, **kwargs)
        self.model = model

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,
                                margin_start=10, margin_end=10,
                                margin_top=10, margin_bottom=10)
        self.set_child(self.main_box)

        self.label = Gtk.Label(label=title, hexpand=True, xalign=0)
        self.main_box.append(self.label)

        self.combo_box = Gtk.ComboBox.new_with_model(self.model)
        self.main_box.append(self.combo_box)


@deprecated("This has been deprecated in favor of GtkHelper.ScaleRow.ScaleRow.")
class ScaleRow(Adw.PreferencesRow):
    def __init__(self, title, value: float, min: float, max: float, step: float, text_right: str = "", text_left: str = "", **kwargs):
        super().__init__(title=title, **kwargs)
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,
                                margin_start=10, margin_end=10,
                                margin_top=10, margin_bottom=10)
        self.set_child(self.main_box)

        self.label = Gtk.Label(label=title, hexpand=True, xalign=0)
        self.main_box.append(self.label)

        self.adjustment = Gtk.Adjustment.new(value, min, max, step, 1, 0)

        self.scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=self.adjustment)
        self.scale.set_size_request(200, -1)  # Adjust width as needed
        self.scale.set_tooltip_text(str(value))

        def correct_step_amount(adjustment):
            value = adjustment.get_value()
            step = adjustment.get_step_increment()
            rounded_value = round(value / step) * step
            adjustment.set_value(rounded_value)

        self.adjustment.connect("value-changed", correct_step_amount)

        self.label_right = Gtk.Label(label=text_right, hexpand=False, xalign=0)

        self.label_left = Gtk.Label(label=text_left, hexpand=False, xalign=0)

        self.main_box.append(self.label_left)
        self.main_box.append(self.scale)
        self.main_box.append(self.label_right)

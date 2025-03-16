import re

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gdk, GLib

from GtkHelper.GtkHelper import better_disconnect

class ScaleRow(Adw.ActionRow):
    def __init__(self,
                 value: float,
                 min: float,
                 max: float,
                 add_text_entry: bool,
                 title: str = None,
                 subtitle: str = None,
                 step: float = 0.1,
                 digits: int = 2,
                 draw_value: bool = False,
                 round_digits: bool = True,
                 ):
        super().__init__(title=title, subtitle=subtitle)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)

        self._add_text_entry = add_text_entry

        self.left = Gtk.Label(label=str(min), hexpand=False, halign=Gtk.Align.END)
        self.right = Gtk.Label(label=str(max), hexpand=False, halign=Gtk.Align.START)

        self._adjustment = Gtk.Adjustment.new(value, min, max, step, 1, 0)
        self.scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=self._adjustment, hexpand=True)
        self.scale.set_draw_value(draw_value)
        self.scale.set_round_digits(round_digits)
        self.scale.set_digits(digits)

        if self._add_text_entry:
            self.entry_row = Gtk.Entry()
            self.entry_row.set_margin_top(5)
            self.entry_row.set_margin_bottom(5)
            self.entry_row.set_text(str(value))
            self.entry_row.set_max_width_chars(5)
            self.entry_row.set_width_chars(5)

            self.entry_row_controller = Gtk.EventControllerFocus()
            self.entry_row.add_controller(self.entry_row_controller)

        box.append(self.left)
        box.append(self.scale)
        box.append(self.right)

        self._connect_signals()

        self.add_suffix(box)

        if self._add_text_entry:
            self.add_suffix(self.entry_row)

    def _connect_signals(self):
        self._adjustment.connect("value-changed", self._correct_step_amount)

        if self._add_text_entry:
            self.entry_row.connect("changed", self._entry_row_changed)
            self.entry_row.connect("activate", self._reset_entry_row)
            self.entry_row_controller.connect("leave", self._reset_entry_row)

    def _disconnect_signals(self):
        better_disconnect(self._adjustment, self._correct_step_amount)

        if self._add_text_entry:
            better_disconnect(self.entry_row, self._entry_row_changed)
            better_disconnect(self.entry_row, self._reset_entry_row)
            better_disconnect(self.entry_row_controller, self._reset_entry_row)

    def set_min(self, min: float):
        if self._adjustment.get_upper() < min:
            return

        self._adjustment.set_lower(min)
        self.left.set_label(str(min))

    def set_max(self, max: float):
        if max < self._adjustment.get_lower():
            return

        self._adjustment.set_upper(max)
        self.right.set_label(str(max))

    def set_step(self, step: float):
        self._adjustment.set_step_increment(step)

    def _correct_step_amount(self, adjustment):
        value = adjustment.get_value()
        step = adjustment.get_step_increment()
        rounded_value = round(value / step) * step
        adjustment.set_value(rounded_value)

        if not self._add_text_entry:
            return

        self._disconnect_signals()

        self.entry_row.set_text(str(rounded_value))

        self._connect_signals()

    def _text_reset(self, text):
        better_disconnect(self.entry_row, self._entry_row_changed)

        cursor_pos = self.entry_row.get_position()
        self.entry_row.set_text(text)

        self.entry_row.set_position(cursor_pos - 1)

        self.entry_row.connect("changed", self._entry_row_changed)

    def _entry_row_changed(self, entry_row):
        self._disconnect_signals()

        text = entry_row.get_text()

        if not re.fullmatch(r"-?\d*\.?\d*", text):
            text = re.sub(r"[^\d.-]", "", text)  # Remove non-numeric characters except '.' and '-'

            print(text)

            # Ensure only one '-' at the beginning
            if text.count("-") > 1 or (text and text[0] != "-"):
                text = text.lstrip("-")  # Remove all but the first '-'
                text = "-" + text if text else ""

            # Ensure only one decimal point exists
            if text.count(".") > 1:
                parts = text.split(".")
                text = parts[0] + "." + "".join(parts[1:])  # Keep first '.', remove extra

        try:
            value = float(text)
        except ValueError:
            value = self._adjustment.get_value()

        value = min(max(value, self._adjustment.get_lower()), self._adjustment.get_upper())

        self.scale.set_value(value)

        self._connect_signals()

    def _reset_entry_row(self, *args):
        self._disconnect_signals()

        self.entry_row.set_text(str(self._adjustment.get_value()))

        self._connect_signals()
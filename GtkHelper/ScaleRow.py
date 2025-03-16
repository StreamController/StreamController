import re

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gdk, GLib

from GtkHelper.GtkHelper import better_disconnect

class ScaleRow(Adw.ActionRow):
    """
        Initializes a new instance of the ScaleRow widget.

        Parameters:
            value (float): The initial value of the scale.
            min (float): The minimum value of the scale.
            max (float): The maximum value of the scale.
            add_text_entry (bool): Whether to include a text entry field alongside the scale.
            title (str, optional): The title of the row (displayed on the left).
            subtitle (str, optional): The subtitle of the row (displayed below the title).
            step (float, optional): The step increment for the scale (default is 0.1).
            digits (int, optional): The number of decimal places to display for the scale value (default is 2).
            draw_value (bool, optional): Whether to display the current value of the scale on the scale itself (default is False).
            round_digits (bool, optional): Whether to round the value to the nearest step increment (default is True).

        Description:
            This constructor creates a row containing a horizontal scale widget with optional labels for the minimum
            and maximum values. If `add_text_entry` is set to True, a text entry field is included that allows the user
            to enter a value directly. The value entered will be synchronized with the scale. The constructor also sets up
            necessary signal handlers to ensure that changes to the scale or text entry are appropriately handled.
    """
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
                 text_entry_max_length: int = 6
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
            self.entry_row.set_max_length(text_entry_max_length)

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
            self.entry_row.connect("activate", self._reset_entry_row)
            self.entry_row.connect("changed", self._entry_row_changed)
            self.entry_row_controller.connect("leave", self._reset_entry_row)

    def _disconnect_signals(self):
        better_disconnect(self._adjustment, self._correct_step_amount)

        if self._add_text_entry:
            better_disconnect(self.entry_row, self._entry_row_changed)
            better_disconnect(self.entry_row, self._reset_entry_row)
            better_disconnect(self.entry_row_controller, self._reset_entry_row)

    @property
    def min(self):
        return self._adjustment.get_lower()

    @min.setter
    def min(self, value: float):
        if self._adjustment.get_upper() < value:
            return

        self._adjustment.set_lower(value)
        self.left.set_label(str(value))

    @property
    def max(self):
        return self._adjustment.get_upper()

    @max.setter
    def max(self, value: float):
        if value < self._adjustment.get_lower():
            return

        self._adjustment.set_upper(value)
        self.right.set_label(str(value))

    @property
    def step(self):
        return self._adjustment.get_step_increment()

    @step.setter
    def step(self, value: float):
        self._adjustment.set_step_increment(value)

    # Scale Row

    def _correct_step_amount(self, adjustment):
        value = adjustment.get_value()
        step = adjustment.get_step_increment()
        rounded_value = round(value / step) * step

        if rounded_value != value:  # Prevent unnecessary updates
            adjustment.set_value(rounded_value)

        if self._add_text_entry:
            self._disconnect_signals()
            self.entry_row.set_text(str(rounded_value))
            self._connect_signals()

    # Entry Row

    def _entry_row_changed(self, entry_row):
        self._disconnect_signals()

        text = entry_row.get_text()

        text = re.sub(r"[^0-9.-]", "", text)  # Remove invalid characters
        text = re.sub(r"^-?(?!\d)", "", text)  # Remove leading '-' if not followed by a digit
        text = re.sub(r"\.(?=.*\.)", "", text)  # Keep only the first decimal point

        try:
            value = float(text)
        except ValueError:
            value = self._adjustment.get_value()
        value = min(max(value, self._adjustment.get_lower()), self._adjustment.get_upper())

        self.scale.set_value(value)

        self._connect_signals()

    def _reset_entry_row(self, *args):
        self._disconnect_signals()

        current_value = self.entry_row.get_text()
        expected_value = str(self._adjustment.get_value())

        if current_value != expected_value:  # Avoid unnecessary updates
            self.entry_row.set_text(expected_value)

        self._connect_signals()
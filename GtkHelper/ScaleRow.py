import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gdk, GLib

class ScaleRow(Adw.ActionRow):
    def __init__(self,
                 title: str = ...,
                 subtitle: str = ...,
                 value: float = ...,
                 min: float = ...,
                 max: float = ...,
                 step: float = ...,
                 digits: int = ...,
                 draw_value: bool = ...,
                 round_digits: bool = ...,
                 ):
        super().__init__(title=title, subtitle=subtitle)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)

        self.left = Gtk.Label(label=str(min), hexpand=False, halign=Gtk.Align.END)
        self.right = Gtk.Label(label=str(max), hexpand=False, halign=Gtk.Align.START)

        adjustment = Gtk.Adjustment.new(value, min, max, step, 1, 0)
        self.scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=adjustment, hexpand=True)
        self.scale.set_draw_value(draw_value)
        self.scale.set_round_digits(round_digits)
        self.scale.set_digits(digits)

        box.append(self.left)
        box.append(self.scale)
        box.append(self.right)

        adjustment.connect("value-changed", self._correct_step_amount)

        self.add_suffix(box)

    def _correct_step_amount(self, adjustment):
        value = adjustment.get_value()
        step = adjustment.get_step_increment()
        rounded_value = round(value / step) * step
        adjustment.set_value(rounded_value)
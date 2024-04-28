"""
Author: Core447
Year: 2024

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This programm comes with ABSOLUTELY NO WARRANTY!

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

from gi.repository import Gtk

class StateSwitcher(Gtk.ScrolledWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.build()

    def build(self):
        self.stack = Gtk.Stack()

        self.main_box = Gtk.Box(overflow=Gtk.Overflow.HIDDEN, css_classes=["state-switcher-box", "linked"], valign=Gtk.Align.CENTER, halign=Gtk.Align.CENTER)
        self.set_child(self.main_box)

        self.switcher = Gtk.StackSwitcher(stack=self.stack, css_classes=["state-switcher"])
        self.main_box.append(self.switcher)

        self.add_button = Gtk.Button(icon_name="list-add-symbolic")
        self.add_button.connect("clicked", self.on_add_click)
        self.main_box.append(self.add_button)

    def clear_stack(self):
        while self.stack.get_first_child() is not None:
            self.stack.remove(self.stack.get_first_child())

    def get_n_states(self) -> int:
        n = 0
        child = self.stack.get_first_child()
        while child is not None:
            n += 1
            child = child.get_next_sibling()
        return n

    def set_n_states(self, n: int):
        self.clear_stack()

        for i in range(n):
            self.stack.add_titled(Gtk.Box(), f"state{i+1}", f"State {i+1}")

    def on_add_click(self, button):
        n_states = self.get_n_states()
        self.stack.add_titled(Gtk.Box(), f"state{n_states + 1}", f"State {n_states + 1}")
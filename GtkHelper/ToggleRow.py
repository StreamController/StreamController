import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GObject

class ToggleRow(Adw.ActionRow):
    def __init__(self,
                 toggles: list[Adw.Toggle],
                 active_toggle: int,
                 title: str,
                 subtitle: str,
                 can_shrink: bool,
                 homogeneous: bool,
                 active: bool):
        super().__init__(title=title, subtitle=subtitle)

        self.toggle_group = Adw.ToggleGroup()
        self.toggle_group.set_can_shrink(can_shrink)
        self.toggle_group.set_homogeneous(homogeneous)
        self.toggle_group.set_active(active)
        self.toggle_group.set_valign(Gtk.Align.CENTER)

        toggles = toggles or []
        active_index = active_toggle or 0
        self.populate(toggles, active_index)

        self.add_suffix(self.toggle_group)

    def get_toggles(self):
        return self.toggle_group.get_toggles()

    def get_toggle_amount(self):
        return self.toggle_group.get_n_toggles()

    def get_toggle_by_name(self, name: str):
        return self.toggle_group.get_toggle_by_name(name)

    def get_toggle_at(self, index: int):
        return self.toggle_group.get_toggle(index)

    def get_active_toggle(self):
        toggle_index = self.toggle_group.get_active()
        toggle = self.toggle_group.get_toggle(toggle_index)
        return toggle

    def get_active_index(self):
        return self.toggle_group.get_active()

    def get_active_name(self):
        return self.toggle_group.get_active_name()

    def set_active_toggle(self, index: int):
        self.toggle_group.set_active(index)

    def set_active_by_name(self, name: str):
        self.toggle_group.set_active_name(name)

    def add_toggle(self, label = None, tooltip: str = None, icon_name: str = None, name: str = None, enabled: bool = True):
        self.toggle_group.add(
            Adw.Toggle(label=label, tooltip=tooltip, icon_name=icon_name, name=name, enabled=enabled)
        )

    def add_toggles(self, toggles: list[Adw.Toggle]):
        for toggle in toggles:
            self.toggle_group.add(toggle)

    def populate(self, toggles: list[Adw.Toggle], active_index: int):
        self.toggle_group.remove_all()
        self.add_toggles(toggles)
        self.toggle_group.set_active(active_index)

    def add_custom_toggle(self, toggle: Adw.Toggle):
        self.toggle_group.add(toggle)

    def remove_toggle(self, toggle: Adw.Toggle):
        self.toggle_group.remove(toggle)

    def remove_at(self, index: int):
        toggle = self.get_toggle_at(index)
        self.toggle_group.remove(toggle)

    def remove_with_name(self, name: str):
        toggle = self.toggle_group.get_toggle_by_name(name)
        self.toggle_group.remove(toggle)

    def remove_all(self):
        self.toggle_group.remove_all()
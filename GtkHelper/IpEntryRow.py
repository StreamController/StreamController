import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GObject

import re

class IpEntryRow(Adw.PreferencesRow):
    __gtype_name__ = "IpEntryRow"
    __gsignals__ = {
        'ip-changed': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.set_child(self.main_box)

        self.label = Gtk.Label(label="Ip Address:", margin_start=10)
        self.main_box.append(self.label)

        self.ip_boxes: dict[int, Gtk.Entry] = {}

        self.ip_numbers_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10, margin_top=5, margin_bottom=5, margin_end=10)
        self.main_box.append(self.ip_numbers_box)

        for i in range(4):
            entry = Gtk.Entry(max_length=3, input_purpose=Gtk.InputPurpose.NUMBER, name=f"ip-box-{i}")
            self.ip_boxes[i] = entry
            self.ip_numbers_box.append(entry)

            if i < 3:
                self.ip_numbers_box.append(Gtk.Label(label=".", vexpand=True))
        self.connect_entries()

    def generate_settings_dict(self):
        settings = {"ip-address": []}

        for key, value in self.ip_boxes.items():
            settings["ip-address"].append(value.get_text())
        return settings

    def disconnect_entries(self):
        for _, ip_box in self.ip_boxes.items():
            ip_box.disconnect_by_func(self.ip_changed)

    def connect_entries(self):
        for _, ip_box in self.ip_boxes.items():
            ip_box.connect("changed", self.ip_changed)

    def set_ip(self, ip_address: str):
        self.disconnect_entries()

        regex = r'(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})'

        match = re.match(regex, ip_address)

        if match:
            for i in range(1, 5):
                self.ip_boxes[i-1].set_text(match.group(i))
        self.connect_entries()
        self.emit('ip-changed', self.get_ip())

    def get_ip(self) -> str:
        out = ""
        for key, value in self.ip_boxes.items():
            out += value.get_text()

            if key < 3:
                out += "."
        return out

    def ip_changed(self, *args):
        self.emit('ip-changed', self.get_ip())
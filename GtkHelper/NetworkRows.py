import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GObject

import re
import socket

class IpEntryRow(Adw.PreferencesRow):
    __gtype_name__ = "IpEntryRow"
    __gsignals__ = {
        'ip-changed': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ip_boxes: dict[int, Gtk.Entry] = {}

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.set_child(self.main_box)

        self.build()

    def build(self):
        self.label = Gtk.Label(label="Ip Address", margin_start=10)
        self.main_box.append(self.label)

        self.ip_numbers_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10, margin_top=5, margin_bottom=5,
                                      margin_end=10)
        self.main_box.append(self.ip_numbers_box)

        for i in range(4):
            entry = Gtk.Entry(max_length=3, input_purpose=Gtk.InputPurpose.NUMBER, name=f"ip-box-{i}")
            self.ip_boxes[i] = entry
            self.ip_numbers_box.append(entry)

            if i < 3:
                self.ip_numbers_box.append(Gtk.Label(label=".", vexpand=True))

        self.connect_events()

    def connect_events(self):
        for _, ip_box in self.ip_boxes.items():
            ip_box.connect("changed", self.ip_changed)

    def disconnect_events(self):
        try:
            for _, ip_box in self.ip_boxes.items():
                ip_box.disconnect_by_func(self.ip_changed)
        except:
            pass

    def ip_changed(self, *args):
        self.emit('ip-changed', self.get_ip())

    def get_ip(self) -> str:
        out = ""
        for key, value in self.ip_boxes.items():
            out += value.get_text()

            if key < 3:
                out += "."
        return out

    def set_ip(self, ip_address: str):
        self.disconnect_events()

        regex = r'(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})'

        match = re.match(regex, ip_address)

        if match:
            for i in range(1, 5):
                self.ip_boxes[i-1].set_text(match.group(i))
        else:
            for i in range(0, 4):
                self.ip_boxes[i-1].set_text("0")
        self.connect_events()
        self.emit('ip-changed', self.get_ip())

    def set_ip_by_hostname(self, hostname: str):
        try:
            ip_address = socket.gethostbyname(hostname)
            self.set_ip(ip_address)
        except socket.gaierror:
            self.set_ip("")


class HostnameEntryRow(Adw.PreferencesRow):
    __gtype_name__ = "HostnameEntryRow"
    __gsignals__ = {
        'hostname-changed': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.set_child(self.main_box)

        self.build()

    def build(self):
        self.label = Gtk.Label(label="Hostname", margin_start=10)
        self.main_box.append(self.label)

        self.hostname_entry = Gtk.Entry(margin_start=10, margin_end=10, margin_top=5, margin_bottom=5, hexpand=True)
        self.main_box.append(self.hostname_entry)

        self.connect_events()

    def connect_events(self):
        self.hostname_entry.connect("activate", self.hostname_changed)

    def disconnect_events(self):
        try:
            self.hostname_entry.disconnect_by_func(self.hostname_changed)
        except:
            pass

    def hostname_changed(self, *args):
        self.emit('hostname-changed', self.hostname_entry.get_text())

    def get_hostname(self) -> str:
        return self.hostname_entry.get_text()

    def set_hostname(self, hostname: str):
        try:
            socket.gethostbyname(hostname)
            self.hostname_entry.set_text(hostname)
        except socket.gaierror:
            self.hostname_entry.set_text("")

    def set_hostname_by_ip(self, ip_address: str):
        try:
            hostname, _, _ = socket.gethostbyaddr(ip_address)
            self.hostname_entry.set_text(hostname)
        except (socket.herror, socket.gaierror):
            self.hostname_entry.set_text("")


class NetworkEntryRow(Adw.PreferencesRow):
    __gtype_name__ = "NetworkEntryRow"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_child(self.main_box)

        self.ip_box = IpEntryRow()
        self.main_box.append(self.ip_box)

        self.hostname_box = HostnameEntryRow()
        self.main_box.append(self.hostname_box)

    def get_ip(self) -> str:
        return self.ip_box.get_ip()

    def get_hostname(self) -> str:
        return self.hostname_box.get_hostname()

    def set_ip(self, ip_address: str):
        self.ip_box.set_ip(ip_address)

    def set_ip_by_hostname(self, hostname: str):
        self.ip_box.set_ip_by_hostname(hostname)

    def set_hostname(self, hostname: str):
        self.hostname_box.set_hostname(hostname)

    def set_hostname_by_ip(self, ip_address: str):
        self.hostname_box.set_hostname_by_ip(ip_address)
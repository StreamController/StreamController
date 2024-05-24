import threading
from gi.repository import Gtk, Adw, GLib

from GtkHelper.GtkHelper import BetterPreferencesGroup, LoadingScreen

import globals as gl
from src.windows.Store.StoreData import PluginData

class PluginRecommendations(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.defaults = [
            "com_core447_DeckPlugin",
            "com_core447_OSPlugin",
            "com_core447_OBSPlugin",
            "com_core447_MediaPlugin",
            "com_core447_VolumeMixer"
        ]

        self.title = Gtk.Label(label="Plugins", css_classes=["title-1"], margin_top=20)
        self.append(self.title)

        self.main_stack = Gtk.Stack(hexpand=True, vexpand=True)
        self.append(self.main_stack)

        self.loading_box = LoadingScreen()
        self.main_stack.add_named(self.loading_box, "loading")

        self.scrolled_window = Gtk.ScrolledWindow(hexpand=True, vexpand=True, margin_top=10)
        self.main_stack.add_named(self.scrolled_window, "scrolled")

        self.scrolled_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True)
        self.scrolled_window.set_child(self.scrolled_box)

        self.clamp = Adw.Clamp(margin_start=40, margin_end=40)
        self.scrolled_box.append(self.clamp)

        self.scrolled_box.append(Gtk.Label(label="You can always install more plugins from the store", css_classes=["dim-label"], margin_top=5, margin_bottom=5))

        self.group = BetterPreferencesGroup()
        self.group.set_sort_func(self.sort_func)
        self.clamp.set_child(self.group)

        threading.Thread(target=self.load).start()

    def set_loading(self, loading: bool):
        if loading:
            self.loading_box.set_spinning(True)
            GLib.idle_add(self.main_stack.set_visible_child, self.loading_box)
        else:
            self.loading_box.set_spinning(False)
            GLib.idle_add(self.main_stack.set_visible_child, self.scrolled_window)

    def load(self):
        self.set_loading(True)

        plugins = gl.store_backend.get_all_plugins()

        for plugin in plugins:
            if not plugin.is_compatible:
                continue

            row = PluginRow(plugin=plugin)
            if plugin.plugin_id in self.defaults:
                row.check.set_active(True)

            self.group.add(row)

        self.set_loading(False)

    def get_selected_ids(self) -> list[str]:
        return [row.plugin.plugin_id for row in self.group.get_rows() if row.check.get_active()]
    
    def sort_func(self, row1, row2):
        title1 = row1.plugin.plugin_name or ""
        title2 = row2.plugin.plugin_name or ""

        if title1 < title2:
            return -1
        if title1 > title2:
            return 1
        return 0

class PluginRow(Adw.ActionRow):
    def __init__(self, plugin: PluginData, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.plugin = plugin

        self.set_title(self.plugin.plugin_name or "")
        self.set_subtitle(self.plugin.short_description or "")
        self.check = Gtk.CheckButton()
        self.add_prefix(self.check)

        self.set_activatable(True)

        self.connect("activated", self.on_activated)
        self.check.connect("toggled", self.on_toggled)

    def on_activated(self, row):
        self.check.set_active(not self.check.get_active())

    def on_toggled(self, button):
        pass
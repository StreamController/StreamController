# Inspired by code of deltragon/SafeEyes repo.
# Link: https://github.com/deltragon/SafeEyes/blob/f25f554585c79a11621e3a505cc6ce5af08a3d58/safeeyes/plugins/trayicon/plugin.py

from gi.repository import Gio

from src.backend.trayicon.DBusService import StatusNotifierItemService


class DBusTrayIcon:
    def __init__(self, menu = None, path = "", menu_path = "", app_id = "", title = ""):
        session_bus = Gio.bus_get_sync(Gio.BusType.SESSION)

        self.menu = menu

        kwargs = {
            "session_bus": session_bus,
            "menu_items": self.menu.get_items()
        }
        if path != "":
            kwargs["path"] = path

        if menu_path != "":
            kwargs["menu_path"] = menu_path

        self.sni_service = StatusNotifierItemService(**kwargs)
        if app_id != "":
            self.sni_service.Id = app_id

        if title != "":
            self.sni_service.Title = title

    def set_icon(self, icon, path: str = ""):
        self.sni_service.set_icon(icon, path)

    def set_tooltip(self, title, description = ""):
        self.sni_service.set_tooltip(title, description)

    def set_label(self, label):
        self.sni_service.set_xayatanalabel(label)

    def update_menu(self):
        self.sni_service.set_items(self.menu.get_items())

    def register(self):
        self.sni_service.register()

    def unregister(self):
        self.sni_service.unregister()

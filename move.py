import json
from pprint import pprint
from shutil import make_archive
import dbus
import re

# Connect to the session bus
bus = dbus.SessionBus()

class WindowManager:
    def __init__(self, bus):
        self.bus = bus
        self.proxy = bus.get_object("org.gnome.Shell", "/org/gnome/Shell/Extensions/Windows")
        self.interface = dbus.Interface(self.proxy, "org.gnome.Shell.Extensions.Windows")

    def get_all_windows(self) -> dict:
        return json.loads(self.interface.List())
    
    def get_window_details(self, id: int) -> dict:
        return json.loads(self.interface.Details(str(id)))
    
    def move_window_to(self, id: int, x: int, y: int):
        self.interface.Move(str(id), x, y)

    def resize_window_to(self, id: int, width: int, height: int):
        self.interface.Resize(str(id), width, height)

    def maximize_window(self, id: int) -> None:
        self.interface.Maximize(str(id))

    def minimize_window(self, id: int) -> None:
        self.interface.Minimize(str(id))

    def unmaximize_window(self, id: int) -> None:
        self.interface.Unmaximize(str(id))

    def unminimize_window(self, id: int) -> None:
        self.interface.Unminimize(str(id))

    def activate_window(self, id: int) -> None:
        self.interface.Activate(str(id))

    def close_window(self, id: int) -> None:
        self.interface.Close(str(id))

    def get_title(self, id: int) -> str:
        return self.interface.GetTitle(str(id))
    
    def get_all_wm_classes(self) -> list[str]:
        classes: str = []
        for window in self.get_all_windows():
            classes.append(window["wm_class"])
        return classes
    
    def get_all_titles(self) -> list[str]:
        titles: str = []
        for window in self.get_all_windows():
            title = self.get_title(window["id"])
            titles.append(str(title))
        return titles
    
    def find_windows_by_class_and_title(self, wm_class_pattern: str, title_pattern: str) -> list[int]:
        matching_window_ids = []
        all_windows = self.get_all_windows()

        for window in all_windows:
            try:
                wm_class_match = re.search(wm_class_pattern, window.get("wm_class", ""), re.IGNORECASE)
                title_match = re.search(title_pattern, self.get_title(window["id"]), re.IGNORECASE)
            except re.error:
                return []

            if wm_class_match and title_match:
                matching_window_ids.append(window["id"])

        return matching_window_ids


manager = WindowManager(bus)
_id = manager.get_all_windows()[0]["id"]
print(_id)
pprint(manager.get_window_details(_id))
manager.move_window_to(_id, 0, 0)
manager.resize_window_to(_id, 100, 100)
manager.activate_window(_id)

print(manager.get_title(_id))
print(manager.get_all_wm_classes())
print(manager.get_all_titles())

print(manager.find_windows_by_class_and_title(".*", "gimp"))
print(manager.get_window_details(_id))
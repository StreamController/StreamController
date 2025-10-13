import os
from loguru import logger as log
import globals as gl
from src.backend.trayicon import DBusTrayIcon, DBusMenu

class TrayIcon(DBusTrayIcon):
    MenuPath = "/com/core447/StreamController/Menu"
    IndicatorPath = "/org/ayatana/NotificationItem/com_core447_StreamController_TrayIcon"
    AppId = "com.core447.StreamController.TrayIcon"

    def __init__(self):
        self.menu = DBusMenu()
        self.menu.add_menu_item(1, "Show Window", callback=self.on_show)
        self.menu.add_menu_item(2, menu_type="separator")
        self.menu.add_menu_item(3, "Settings", callback=self.on_settings)
        self.menu.add_menu_item(4, "Store", callback=self.on_store)
        self.menu.add_menu_item(5, "About", callback=self.on_about)
        self.menu.add_menu_item(6, menu_type="separator")
        self.menu.add_menu_item(7, "Quit", callback=self.on_quit)
        super().__init__(self.menu, self.MenuPath, self.IndicatorPath, self.AppId, "StreamController")
        self.set_icon("com.core447.StreamController")
        self.set_tooltip("StreamController")
        self.set_label("StreamController")

        self.main_win = None
        self.show_about_action = None
        self.show_store_action = None
        self.show_settings_action = None
        self.quit_app_action = None
        self.activate_id = -1

    @log.catch
    def initialize(self, main_win):
        self.main_win = main_win
        self.show_about_action = main_win.menu_button.open_about_action
        self.show_store_action = main_win.menu_button.open_store_action
        self.show_settings_action = main_win.menu_button.open_settings_action
        self.quit_app_action = main_win.menu_button.quit_action
        app_settings = gl.settings_manager.get_app_settings()
        show_now = app_settings.get("ui",{}).get("tray-icon", True)
        if show_now:
            self.register()

    @log.catch
    def start(self):
        self.register()

    @log.catch
    def stop(self):
        self.unregister()

    @log.catch
    def on_show(self):
        self.main_win.present()

    @log.catch
    def on_settings(self):
        self.show_settings_action.activate()

    @log.catch
    def on_store(self):
        self.show_store_action.activate()

    @log.catch
    def on_about(self):
        self.main_win.present()
        self.show_about_action.activate()

    @log.catch
    def on_quit(self):
        self.quit_app_action.activate()



# import os
# os.environ["PYSTRAY_BACKEND"] = "appindicator"
# # import pystray

# from pystray import _appindicator
# from PIL import Image
# from pystray import Menu, MenuItem

# class TrayIcon(_appindicator.Icon):
#     def __init__(self):
#         icon_image = Image.open("flatpak/icon_256.png")
#         menu = Menu(
#             MenuItem("StreamController", enabled=False, action=None),
#             MenuItem("Open", self.on_open),
#             MenuItem("Quit", self.on_quit)
#         )
#         super().__init__("StreamController", icon_image, menu=menu, title="StreamController")

#     def on_open(self):
#         print("Open")

#     def on_quit(self):
#         print("Quit")
#         self.stop()  # Stop the icon running when "Quit" is clicked

# if __name__ == "__main__":
#     # Usage
#     stream_controller_icon = TrayIcon()
#     stream_controller_icon.run()

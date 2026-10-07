import os
import sys
import glob
import subprocess
from gi.repository import GLib
from loguru import logger as log
import globals as gl
from src.backend.trayicon import DBusTrayIcon, DBusMenu

class TrayIcon(DBusTrayIcon):
    MenuPath = "/com/core447/StreamController/Menu"
    IndicatorPath = "/org/ayatana/NotificationItem/com_core447_StreamController_TrayIcon"
    AppId = "com.core447.StreamController.TrayIcon"
    IconName = "com.core447.StreamController"

    def __init__(self):
        if gl.IS_MAC:
            return
        self.menu = DBusMenu()
        self.menu.add_menu_item(1, "Show Window", callback=self.on_show)
        self.menu.add_menu_item(2, menu_type="separator")
        self.menu.add_menu_item(3, "Settings", callback=self.on_settings)
        self.menu.add_menu_item(4, "Store", callback=self.on_store)
        self.menu.add_menu_item(5, "About", callback=self.on_about)
        self.menu.add_menu_item(6, menu_type="separator")
        self.menu.add_menu_item(7, "Quit", callback=self.on_quit)
        self.menu.add_menu_item(8, "Quit and Restart", callback=self.on_restart)
        super().__init__(self.menu, self.IndicatorPath, self.MenuPath, self.AppId, "StreamController")
        self.set_icon(self.IconName, path=self.get_icon_theme_path())
        self.set_tooltip("StreamController")

    def get_icon_theme_path(self) -> str:
        """
        The tray host resolves the icon on its own side, so IconThemePath is only useful if it
        points somewhere the host can actually read. Inside a Flatpak it never can - and it
        doesn't have to, because Flatpak exports our icon into the host's icon theme. Hosts
        like the GNOME AppIndicator extension show a placeholder instead of falling back to
        the theme once a path is set, so only hand out a path if the icon is missing from the
        installed theme, which is the case when running from source.
        """
        for data_dir in [GLib.get_user_data_dir(), *GLib.get_system_data_dirs()]:
            if glob.glob(os.path.join(data_dir, "icons", "*", "*", "apps", f"{self.IconName}.*")):
                return ""

        log.info(f"{self.IconName} is not in an installed icon theme, pointing the tray at our own assets")
        return os.path.join(gl.MAIN_PATH, "Assets", "icons")

    @log.catch
    def initialize(self):
        app_settings = gl.settings_manager.get_app_settings()
        show_now = app_settings.get("ui",{}).get("tray-icon", True)
        if show_now:
            self.start()

    @log.catch
    def start(self):
        if not gl.IS_MAC:
            self.register()

    @log.catch
    def stop(self):
        if not gl.IS_MAC:
            self.unregister()

    @log.catch
    def on_show(self):
        gl.app.ensure_main_window(present=True)

    @log.catch
    def on_settings(self):
        main_win = gl.app.ensure_main_window(present=True)
        main_win.menu_button.open_settings_action.activate(None)

    @log.catch
    def on_store(self):
        main_win = gl.app.ensure_main_window(present=True)
        main_win.menu_button.open_store_action.activate(None)

    @log.catch
    def on_about(self):
        main_win = gl.app.ensure_main_window(present=True)
        main_win.menu_button.open_about_action.activate(None)

    @log.catch
    def on_quit(self):
        GLib.idle_add(gl.app.on_quit)

    @log.catch
    def on_restart(self):
        pid = str(os.getpid())
        restart_cmd = [sys.executable, *sys.argv]

        restart_script = """
pid="$1"
shift

sleep 0.5

if kill -0 "$pid" 2>/dev/null; then
    kill -TERM "$pid" 2>/dev/null
fi

while kill -0 "$pid" 2>/dev/null; do
    sleep 0.2
done

exec "$@"
"""

        subprocess.Popen(
            ["/bin/sh", "-c", restart_script, "streamcontroller-restart", pid, *restart_cmd],
            cwd=gl.MAIN_PATH,
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        self.on_quit()



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

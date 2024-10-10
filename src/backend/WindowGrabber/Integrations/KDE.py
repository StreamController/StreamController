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
import dbus
from re import sub
import threading
import time
import tempfile
import os.path
from datetime import datetime
from src.backend.WindowGrabber.Integration import Integration
from src.backend.WindowGrabber.Window import Window

import subprocess
import json
from loguru import logger as log

import globals as gl

# Import typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.backend.WindowGrabber.WindowGrabber import WindowGrabber


class KDE(Integration):
    def __init__(self, window_grabber: "WindowGrabber"):
        super().__init__(window_grabber=window_grabber)

        self.bus: dbus.Bus = None
        self.proxy = None
        self.interface = None
        self.tempScriptFile = None

        self.allWindows = []
        self.activeWindow = None
        self.threadLock = threading.Lock()

        self.start_active_window_change_thread()
        self.connect_dbus_script()

    def connect_dbus_script(self) -> None:
        script = """
                function onWindowActivated(win) {
                        print("windowActive:" + win.resourceClass + ":" + win.resourceName);
                }
                function getAllWindows(win=null){
                    const currentWindows = workspace.stackingOrder;
                    var listAll = "";
                    for(var i = 0;i < currentWindows.length; i++){
                        listAll += currentWindows[i].resourceClass + ':' + currentWindows[i].resourceName + ',';
                    }
                    print("allWindows:" + listAll)
                }
                workspace.windowActivated.connect(onWindowActivated);
                getAllWindows();
                workspace.windowAdded.connect(getAllWindows);
                workspace.windowRemoved.connect(getAllWindows);
            """
        tempDir = tempfile.gettempdir()
        self.tempScriptFile = os.path.join(tempDir, 'streamControllerKdeScript.js')
        with open(self.tempScriptFile, 'w') as f:
            f.write(script)

        try:
            self.bus = dbus.SessionBus()
            # temporary proxy for putting the script in KDE
            proxy = self.bus.get_object("org.kde.KWin", "/Scripting")
            interface = dbus.Interface(proxy, "org.kde.kwin.Scripting")
            # first check if the script already is running, if so don't start another one
            if interface.isScriptLoaded(self.tempScriptFile):
                log.debug('KDE script already running')
                return
            scriptId = interface.loadScript(self.tempScriptFile)

            self.proxy = self.bus.get_object("org.kde.KWin", f"/Scripting/Script{scriptId}")
            self.interface = dbus.Interface(self.proxy, "org.kde.kwin.Script")
            self.interface.run()
        except dbus.exceptions.DBusException as e:
            log.error(f"Failed to connect to D-Bus: {e}")
            pass

    @log.catch
    def start_active_window_change_thread(self):
        self.active_window_change_thread = WatchForScriptLogs(self)
        self.active_window_change_thread.start()

    def get_all_windows(self) -> list[Window]:
        with self.threadLock:
            return self.allWindows

    def get_active_window(self) -> Window:
        with self.threadLock:
            return self.activeWindow

    def get_is_connected(self) -> bool:
        return None not in (self.bus, self.proxy, self.interface)

    def close(self) -> None:
        if self.interface:
            self.interface.stop()

    @staticmethod
    def script_name_to_window(s: str) -> Window:
        """converts a name from the KDE script into a Window class"""
        s = s.split(':')
        return Window(wm_class=s[0], title=s[1])


class WatchForScriptLogs(threading.Thread):
    """Thread that reads all windows and the active window from systemd, printed by the script ran"""
    def __init__(self, kde: KDE):
        super().__init__(name="WatchForActiveWindowChange", daemon=True)
        self.kde = kde

        self.last_active_window = kde.get_active_window()
        self.lastCheck = datetime.now()

    @log.catch
    def run(self) -> None:
        while gl.threads_running:
            time.sleep(0.2)

            new_active_window = None

            msg_all = subprocess.run("journalctl QT_CATEGORY=js QT_CATEGORY=kwin_scripting -o cat --since \"" + str(self.lastCheck) + "\"",
                                     capture_output=True, shell=True)
            msg_all = msg_all.stdout.decode().rstrip().split("\n")

            self.lastCheck = datetime.now()

            for msg in msg_all:
                if msg == '':
                    continue
                msg = msg.lstrip("js: ")
                # if we get a allWindows message, then update the current windows
                if msg.startswith("allWindows:"):
                    msg = msg.replace("allWindows:", "")
                    msg = msg.split(',')
                    with self.kde.threadLock:
                        self.kde.allWindows = []
                        for wind in msg:
                            if wind == '':
                                continue
                            wind = self.kde.script_name_to_window(wind)
                            self.kde.allWindows.append(wind)

                # otherwise update the current active window
                elif msg.startswith("windowActive:"):
                    msg = msg.replace("windowActive:", "")
                    new_active_window = msg

            # if we don't have a window to update, continue
            if new_active_window is None:
                continue
            new_active_window = self.kde.script_name_to_window(new_active_window)

            if new_active_window == self.last_active_window:
                continue

            self.last_active_window = new_active_window

            with self.kde.threadLock:
                self.kde.activeWindow = new_active_window
            self.kde.window_grabber.on_active_window_changed(new_active_window)

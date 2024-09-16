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

import os
import shutil

import gi
gi.require_version("Xdp", "1.0")
from gi.repository import Xdp

from loguru import logger as log

def is_flatpak():
    return os.path.isfile('/.flatpak-info')

log.catch
def setup_autostart(enable: bool = True):
    if enable:
        if is_flatpak():
            setup_autostart_flatpak(True)

        else:
            setup_autostart_desktop_entry(True, True)

    else:
        setup_autostart_flatpak(False)
        setup_autostart_desktop_entry(False)
    
    


def setup_autostart_flatpak(enable: bool = True):
    """
    Use portal to autostart for Flatpak
    Documentation:
    https://libportal.org/method.Portal.request_background.html
    https://libportal.org/method.Portal.request_background_finish.html 
    https://docs.flatpak.org/de/latest/portal-api-reference.html#gdbus-org.freedesktop.portal.Background
    """
    def request_background_callback(portal, result, user_data):
        try:
            success = portal.request_background_finish(result)
        except:
            success = False
        log.info(f"request_background success={success}")
        if not success:
            setup_autostart_desktop_entry()

    xdp = Xdp.Portal.new()

    try:
        flag = Xdp.BackgroundFlags.AUTOSTART if enable else Xdp.BackgroundFlags.ACTIVATABLE

        # Request Autostart
        xdp.request_background(
            None,  # parent
            "Autostart StreamController",  # reason
            ["/app/bin/launch.sh", "-b"],  # commandline
            flag,
            None,  # cancellable
            request_background_callback,
            None,  # user_data
        )
    except:
        log.error(f"request_background failed")
        setup_autostart_desktop_entry(enable)

def setup_autostart_desktop_entry(enable: bool = True, native: bool = False):
    log.info("Setting up autostart using desktop entry")


    xdg_config_home = os.path.join(os.environ.get("HOME"), ".config")
    AUTOSTART_DIR = os.path.join(xdg_config_home, "autostart")
    AUTOSTART_DESKTOP_PATH = os.path.join(AUTOSTART_DIR, "StreamController.desktop")

    if enable:
        try:
            os.makedirs(os.path.dirname(AUTOSTART_DESKTOP_PATH), exist_ok=True)
            if native:
                shutil.copyfile(os.path.join("flatpak", "autostart-native.desktop"), AUTOSTART_DESKTOP_PATH)
            else:
                shutil.copyfile(os.path.join("flatpak", "autostart.desktop"), AUTOSTART_DESKTOP_PATH)
            log.info(f"Autostart set up at: {AUTOSTART_DESKTOP_PATH}")
        except Exception as e:
            log.error(f"Failed to set up autostart at: {AUTOSTART_DESKTOP_PATH} with error: {e}")
    else:
        if os.path.exists(AUTOSTART_DESKTOP_PATH):
            try:
                os.remove(AUTOSTART_DESKTOP_PATH)
                log.info(f"Autostart removed from: {AUTOSTART_DESKTOP_PATH}")
            except Exception as e:
                log.error(f"Failed to remove autostart from: {AUTOSTART_DESKTOP_PATH} with error: {e}")

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

import gi
gi.require_version("Xdp", "1.0")
from gi.repository import Xdp

from loguru import logger as log

def is_flatpak():
    return os.path.isfile('/.flatpak-info')

def setup_autostart(autostart):
    if not is_flatpak():
        log.warning("Autostart is only supported on Flatpak")
        return
    
    """
    Use portal to autostart for Flatpak
    Documentation:
    https://libportal.org/method.Portal.request_background.html
    https://libportal.org/method.Portal.request_background_finish.html 
    https://docs.flatpak.org/de/latest/portal-api-reference.html#gdbus-org.freedesktop.portal.Background
    """

    xdp = Xdp.Portal.new()

    # Request Autostart
    xdp.request_background(
        None,  # parent
        "Autostart StreamController",  # reason
        ["/app/bin/launch.sh", "-b"],  # commandline
        Xdp.BackgroundFlags.AUTOSTART if autostart else Xdp.BackgroundFlags.NONE,  # flags
        None,  # cancellable
        lambda portal, result, user_data: log.info(
            f"[Utils] autostart={autostart}, request_background sucess={portal.request_background_finish(result)}"),  # callback
        None,  # user_data
    )
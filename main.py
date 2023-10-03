"""
Author: Core447
Year: 2023

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This programm comes with ABSOLUTELY NO WARRANTY!

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
# Import Python modules
import sys
from loguru import logger as log

# Import own modules
from src.app import App

def config_logger():
    log.remove(0)
    # Create log files
    log.add("logs/logs.log", rotation="3 days", backtrace=True, diagnose=True, level="TRACE")
    # Set min level to print
    log.add(sys.stderr, level="INFO")

class Main:
    def __init__(self, application_id):
        # Launch gtk application
        app = App(application_id=application_id)
        app.run(sys.argv)


if __name__ == "__main__":
    config_logger()
    log.info("Loading app")
    Main(application_id="com.core447.StreamController")

log.trace("Reached end of main.py")
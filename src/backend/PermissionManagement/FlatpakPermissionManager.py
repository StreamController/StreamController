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

import gi
gi.require_version("Xdp", "1.0")
from gi.repository import Xdp

import subprocess
import shlex
from loguru import logger as log

import globals as gl

from src.windows.Permissions.FlatpakPermissionRequest import FlatpakPermissionRequestWindow


class FlatpakPermissionManager:
    def __init__(self):
        self.portal = Xdp.Portal.new()
        self.app_id = "com.core447.StreamController"

    def get_is_flatpak(self):
        return self.portal.running_under_flatpak()
    
    def add_spawn_prefix_if_needed(self, command: str) -> str:
        if self.get_is_flatpak() and not command.startswith("flatpak-spawn"):
            command = "flatpak-spawn --host " + command
        return command
    
    def get_flatpak_permissions(self) -> dict:
        command = self.add_spawn_prefix_if_needed(f"flatpak info --show-permissions {self.app_id}")
        # Execute the command, capturing stdout and stderr
        process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd="/")
        stdout, stderr = process.communicate()

        # If there is an error (captured in stderr), raise an exception
        if stderr:
            log.error(f"Error running command: {stderr.decode()}")
            return {}
        
        # Decode the stdout to get the permissions output as a string
        permissions_output = stdout.decode()
        # Initialize an empty dictionary to hold the parsed permissions
        permissions_dict = {}
        
        # Split the output into sections based on double newline characters
        sections = permissions_output.split('\n\n')
        for section in sections:
            # Split the section into lines and extract the header
            lines = section.strip().split('\n')
            header = lines.pop(0).strip('[]').lower().replace(' ', '-')
            # Parse the 'Context' section differently from the policy sections
            if header == 'context':
                context_dict = {}
                for line in lines:
                    # Split each line on '=' and construct a list of values, ignoring the last empty string
                    if '=' in line:
                        key, value = line.split('=')
                        context_dict[key] = value.split(';')[:-1]
                # Add the context dictionary to the permissions dictionary
                permissions_dict[header] = context_dict
            else: # For 'Session Bus Policy' and 'System Bus Policy' sections
                policy_list = []
                for line in lines:
                    # For each policy, remove the '=talk' part and add the policy to the list
                    if '=' in line:
                        policy = line.split('=')[0]
                        policy_list.append(policy)
                # Add the policy list to the permissions dictionary
                permissions_dict[header] = policy_list

        # Return the complete permissions dictionary
        return permissions_dict
    
    def has_dbus_permission(self, name: str, bus: str="session") -> bool:
        if bus not in ["session", "system"]:
            raise ValueError("Invalid bus type. Must be 'session' or 'system'.")
        permissions = self.get_flatpak_permissions()
        policy_permissions = permissions.get(f"{bus}-bus-policy", [])
        return name in policy_permissions
    
    def get_dbus_permission_add_command(self, name: str, bus: str="session") -> str:
        if bus not in ["session", "system"]:
            raise ValueError("Invalid bus type. Must be 'session' or 'system'.")
        
        command = "flatpak override --user"
        if bus == "session":
            command += " --talk-name="
        else:
            command += " --system-talk-name="
        command += name

        command =+ f" {self.app_id}"

        return command
    
    def show_dbus_permission_request_dialog(self, name: str, bus: str="session", description: str="None"):
        if not self.get_is_flatpak():
            return
        if self.has_dbus_permission(name, bus):
            return
        if bus not in ["session", "system"]:
            raise ValueError("Invalid bus type. Must be 'session' or 'system'.")
        
        if description is None:
            description = gl.lm.get("permissions.request.default-description")

        command = self.get_dbus_permission_add_command(name, bus)
        window = None
        # Checks are required because the request might come before the mainwin has been created
        if hasattr(gl.app, "main_win"):
            if gl.app.main_win is not None:
                window = gl.app.main_win

        window = FlatpakPermissionRequestWindow(gl.app, window, command=command, description=description)
        window.present()
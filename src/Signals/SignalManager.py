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

from src.Signals.Signals import AppQuit, Signal

from gi.repository import GLib

class SignalManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.connected_signals: dict = {}

    def connect_signal(self, signal: Signal, callback: callable) -> None:
        # Verify signal
        if not issubclass(signal, Signal):
            raise TypeError("signal_name must be of type Signal")
        
        # Verify callback
        if not callable(callback):
            raise TypeError("callback must be callable")
        
        self.connected_signals.setdefault(signal, [])
        self.connected_signals[signal].append(callback)

    def trigger_signal(self, signal: Signal, *args, **kwargs) -> None:
        # Verify signal
        if not issubclass(signal, Signal):
            raise TypeError("signal must be of type Signal")
        
        for callback in self.connected_signals.get(signal, []):
            if signal == AppQuit:
                callback(*args, **kwargs)
            else:
                GLib.idle_add(callback, *args, **kwargs)
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
import gi

import globals as gl
from src.backend.PluginManager.ActionCore import ActionCore

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw


class CommentGroup(Adw.PreferencesGroup):
    def __init__(self, parent, **kwargs):
        super().__init__(**kwargs)
        self.parent = parent
        self.action: ActionCore = None
        self.index: int = None
        self.build()

    def build(self):
        self.comment_row = Adw.EntryRow(title="Comment")
        self.connect_signals()
        self.add(self.comment_row)

    def load_for_action(self, action, index):
        self.disconnect_signals()
        self.action = action
        self.index = index

        comment = self.get_comment()
        if comment is None:
            comment = ""
        self.comment_row.set_text(comment)

        self.connect_signals()

    def on_comment_changed(self, entry):
        self.set_comment(entry.get_text())

        # Update ActionManager - A full reload is not efficient but ensures correct behavior if the ActionConfigurator is triggered from a plugin action
        gl.app.main_win.sidebar.key_editor.action_editor.load_for_identifier(self.action.input_ident, self.action.state)

    def connect_signals(self):
        self.comment_row.connect("changed", self.on_comment_changed)

    def disconnect_signals(self):
        self.comment_row.disconnect_by_func(self.on_comment_changed)
    

    def get_comment(self) -> str:
        visible_child = gl.app.main_win.leftArea.deck_stack.get_visible_child()
        if visible_child is None:
            return
        controller = visible_child.deck_controller
        if controller is None:
            return
        page = controller.active_page
        if page is None:
            return
        return page.get_action_comment(self.index, self.action.state, self.action.input_ident)
    
    def set_comment(self, comment: str) -> None:
        visible_child = gl.app.main_win.leftArea.deck_stack.get_visible_child()
        if visible_child is None:
            return
        controller = visible_child.deck_controller
        if controller is None:
            return
        page = controller.active_page
        page.set_action_comment(self.index, comment, self.action.state, self.action.input_ident)

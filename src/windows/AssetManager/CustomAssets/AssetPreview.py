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
# Import gtk modules
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GdkPixbuf

# Import own modules
from src.windows.AssetManager.Preview import Preview

import globals as gl
import os

# Import typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.AssetManager.CustomAssets.FlowBox import CustomAssetChooserFlowBox

class AssetPreview(Preview):
    def __init__(self, flow:"CustomAssetChooserFlowBox", asset:dict, *args, **kwargs):
        super().__init__(
            image_path=asset["thumbnail"],
            text=asset["name"],
            can_be_deleted=True
        )
        self.asset = asset
        self.flow = flow


    def on_click_info(self, button):
        self.flow.asset_chooser.asset_manager.show_info(
            internal_path = self.asset["internal-path"],
            licence_name = self.asset["license"].get("name"),
            license_url = self.asset["license"].get("url"),
            author = self.asset["license"].get("author"),
            license_comment = self.asset["license"].get("comment")
        )

    def on_click_remove(self, *args):
        dial = DeleteConfirmationDialog(self)
        dial.present()

    def on_remove_confirmed(self):
        gl.asset_manager_backend.remove_asset_by_id(self.asset["id"])
        
        parent: Gtk.FlowBox = self.get_parent()
        parent.unselect_all()
        parent.remove(self)


class DeleteConfirmationDialog(Adw.MessageDialog):
    def __init__(self, asset_preview: AssetPreview, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.asset_preview = asset_preview

        self.set_transient_for(gl.asset_manager)
        self.set_modal(True)
        self.set_title(gl.lm.get("asset-manager.custom-assets.remove-confirmation-dialog.tite"))
        self.add_response("cancel", gl.lm.get("asset-manager.custom-assets.remove-confirmation-dialog.cancel"))
        self.add_response("remove", gl.lm.get("asset-manager.custom-assets.remove-confirmation-dialog.remove"))
        self.set_default_response("cancel")
        self.set_close_response("cancel")
        self.set_response_appearance("remove", Adw.ResponseAppearance.DESTRUCTIVE)

        asset_name = os.path.splitext(os.path.basename(self.asset_preview.asset["internal-path"]))[0]
        self.set_body(f'{gl.lm.get("asset-manager.custom-assets.remove-confirmation-dialog.body")}"{asset_name}"?')

        self.connect("response", self.on_response)

    def on_response(self, dialog: Adw.MessageDialog, response: int) -> None:
        if response == "remove":
            self.asset_preview.on_remove_confirmed()
        self.destroy()
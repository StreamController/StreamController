"""
Author: Core447
Year: 2025

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
from gi.repository import Gtk, Adw

# Import own modules
from src.windows.AssetManager.Preview import Preview
from src.backend.IconPackManagement import CustomIconPack
from src.backend.IconPackManagement.IconPack import IconPack

# Import globals
import globals as gl

# Import typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.AssetManager.CustomIconPacks.PackChooser import CustomIconPackChooser


class CustomIconPackPreview(Preview):
    def __init__(self, pack_chooser: "CustomIconPackChooser", pack: IconPack):
        super().__init__(
            image_path=pack.get_thumbnail_path(),
            text=pack.name,
            can_be_deleted=True
        )
        self.pack = pack
        self.pack_chooser = pack_chooser

        # The pack belongs to the user, so there is nothing to attribute - it can be edited instead
        self.info_button.set_icon_name("document-edit-symbolic")
        self.info_button.set_tooltip_text("Edit pack")

    def on_click_info(self, *args):
        from src.windows.AssetManager.CustomIconPacks.PackDialog import CustomIconPackDialog
        CustomIconPackDialog(self.pack_chooser, pack=self.pack).present(gl.asset_manager)

    def on_click_remove(self, *args):
        DeleteConfirmationDialog(self).present()

    def on_remove_confirmed(self):
        CustomIconPack.delete_custom_icon_pack(self.pack.path)
        self.pack_chooser.reload()


class DeleteConfirmationDialog(Adw.MessageDialog):
    def __init__(self, preview: CustomIconPackPreview, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.preview = preview

        self.set_transient_for(gl.asset_manager)
        self.set_modal(True)
        self.set_heading("Remove Asset Pack")
        self.set_body(f'Do you want to remove "{preview.pack.name}" and all of its icons?')
        self.add_response("cancel", "Cancel")
        self.add_response("remove", "Remove")
        self.set_default_response("cancel")
        self.set_close_response("cancel")
        self.set_response_appearance("remove", Adw.ResponseAppearance.DESTRUCTIVE)

        self.connect("response", self.on_response)

    def on_response(self, dialog: Adw.MessageDialog, response: str) -> None:
        if response == "remove":
            self.preview.on_remove_confirmed()
        self.destroy()

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

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .AssetManager import AssetManager

# Import python modules
from PIL import Image
from videoprops import get_video_properties

# Import own modules
from src.GtkHelper import AttributeRow
from src.backend.DeckManagement.HelperMethods import is_video, get_image_aspect_ratio

class InfoPage(Gtk.Box):
    def __init__(self, asset_manager:"AssetManager"):
        super().__init__(orientation=Gtk.Orientation.VERTICAL,
                         margin_top=15)
        self.asset_manager = asset_manager
        self.build()

    def build(self):
        self.clamp = Adw.Clamp(hexpand=True)
        self.append(self.clamp)

        self.clamp_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.clamp.set_child(self.clamp_box)

        # Image
        self.image_group = Adw.PreferencesGroup(title="Image")
        self.clamp_box.append(self.image_group)

        self.img_resolution_row = AttributeRow(title="Resolution:", attr="Error")
        self.image_group.add(self.img_resolution_row)

        self.img_aspect_ratio_row = AttributeRow(title="Aspect Ratio:", attr="Error")
        self.image_group.add(self.img_aspect_ratio_row)

        # Video
        self.video_group = Adw.PreferencesGroup(title="Video")
        self.clamp_box.append(self.video_group)

        self.video_resolution_row = AttributeRow(title="Resolution:", attr="Error")
        self.video_group.add(self.video_resolution_row)

        self.aspect_ratio_row = AttributeRow(title="Aspect Ratio:", attr="Error")
        self.video_group.add(self.aspect_ratio_row)

        self.video_framerate_row = AttributeRow(title="Framerate:", attr="Error")
        self.video_group.add(self.video_framerate_row)

        # License
        self.license_group = Adw.PreferencesGroup(title="License")
        self.clamp_box.append(self.license_group)

        self.license_type_row = AttributeRow(title="License:", attr="Error")
        self.license_group.add(self.license_type_row)

        self.license_author_row = AttributeRow(title="Author:", attr="Error")
        self.license_group.add(self.license_author_row)

        self.license_url_row = AttributeRow(title="URL:", attr="Error")
        self.license_group.add(self.license_url_row)

        self.license_comment_row = AttributeRow(title="Comment:", attr="Error")
        self.license_group.add(self.license_comment_row)

    def show_info(self, internal_path:str = None, licence_name: str = None, license_url: str = None, author: str = None, license_comment: str = None):
        if internal_path is None:
            self.image_group.set_visible(False)
            self.video_group.set_visible(False)
        elif is_video(internal_path):
            self.show_for_vid(internal_path)
        else:
            self.show_for_img(internal_path)

        self.license_type_row.set_url(licence_name)
        self.license_author_row.set_url(author)
        self.license_url_row.set_url(license_url)
        self.license_comment_row.set_url(license_comment)


    def show_for_asset(self, asset:dict):
        if is_video(asset["internal-path"]):
            self.show_for_vid(asset["internal-path"])
        else:
            self.show_for_img(asset["internal-path"])

        self.license_type_row.set_url(asset["license"].get("name"))
        self.license_author_row.set_url(asset["license"].get("author"))
        self.license_url_row.set_url(asset["license"].get("url"))
        self.license_comment_row.set_url(asset["license"].get("comment"))

        

    def show_for_img(self, path:str):
        # Update ui vis
        self.image_group.set_visible(True)
        self.video_group.set_visible(False)

        # Update ui content
        with Image.open(path) as img:
            self.img_resolution_row.set_url(f"{img.width}x{img.height}")
            self.img_aspect_ratio_row.set_url(f"{get_image_aspect_ratio(img)}")

    def show_for_vid(self, path:str):
        props = get_video_properties(path)

        # Update ui vis
        self.image_group.set_visible(False)
        self.video_group.set_visible(True)

        # Update ui content
        self.video_resolution_row.set_url(f"{props['width']}x{props['height']}")
        self.aspect_ratio_row.set_url(f"{props['display_aspect_ratio']}")
        self.video_framerate_row.set_url(f"{eval(props['avg_frame_rate']):.2f} fps")
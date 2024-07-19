"""
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
from gi.repository import Gtk, Adw, Pango

# Import python modules
from typing import TYPE_CHECKING
import webbrowser as web

# Import own modules
if TYPE_CHECKING:
    from src.windows.Store.StorePage import StorePage

from GtkHelper.GtkHelper import AttributeRow, OriginalURL

# Import globals
import globals as gl

class InfoPage(Gtk.Box):
    def __init__(self, store_page:"StorePage"):
        super().__init__(orientation=Gtk.Orientation.VERTICAL,
                       margin_top=15)
        
        self.store_page = store_page
        self.build()

    def build(self):
        self.clamp = Adw.Clamp(hexpand=True)
        self.append(self.clamp)

        self.clamp_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.clamp.set_child(self.clamp_box)

        self.about_group = Adw.PreferencesGroup(title="About")
        self.clamp_box.append(self.about_group)

        self.name_row = AttributeRow(title="Name:", attr="Error")
        self.about_group.add(self.name_row)

        self.author_row = AttributeRow(title="Author:", attr="Error")
        self.about_group.add(self.author_row)

        self.version_row = AttributeRow(title="Version:", attr="Error")
        self.about_group.add(self.version_row)

        self.description_row = DescriptionRow(title="Description:", desc="N/A")
        self.about_group.add(self.description_row)

        self.legal_group = Adw.PreferencesGroup(title="Legal")
        self.clamp_box.append(self.legal_group)

        self.license_row = AttributeRow(title="License:", attr="Error")
        self.legal_group.add(self.license_row)

        self.copyright_row = AttributeRow(title="Copyright:", attr="Error")
        self.legal_group.add(self.copyright_row)

        self.original_url = OriginalURL()
        self.legal_group.add(self.original_url)

        self.license_description = DescriptionRow(title="License Description:", desc="N/A")
        self.legal_group.add(self.license_description)

    def set_name(self, name:str):
        self.name_row.set_url(name)

    def set_description(self, description:str):
        self.description_row.set_description(description)

    def set_author(self, author:str):
        self.author_row.set_url(author)

    def set_version(self, version:str):
        self.version_row.set_url(version)

    def set_license(self, license:str):
        self.license_row.set_url(license)

    def set_copyright(self, copyright:str):
        self.copyright_row.set_url(copyright)

    def set_license_description(self, description:str):
        self.license_description.set_description(description)

    def set_original_url(self, url:str):
        self.original_url.set_url(url)


class DescriptionRow(Adw.PreferencesRow):
    def __init__(self, title:str, desc:str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = title
        self.desc = desc

        self.build()

    def build(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True,
                                margin_top=15, margin_bottom=15)
        self.set_child(self.main_box)

        self.title_label = Gtk.Label(label=self.title, xalign=0, hexpand=True, margin_start=15)
        self.main_box.append(self.title_label)

        self.description_label = Gtk.Label(label=self.desc, xalign=0, wrap=True, wrap_mode=Pango.WrapMode.WORD,
                                           margin_start=15, margin_top=15, margin_end=15)
        self.main_box.append(self.description_label)

    def set_description(self, description:str):
        if description in [None, ""]:
            description = "N/A"
        self.description_label.set_text(description)

    def set_title(self, title:str):
        if title in [None, ""]:
            title = "N/A"
        self.title_label.set_text(title)

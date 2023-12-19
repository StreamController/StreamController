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
from gi.repository import Gtk, Adw, GLib, Gio, Gdk, GObject, GdkPixbuf

# Import Python modules
from loguru import logger as log
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.mainWindow.mainWindow import MainWindow

# Import globals
import globals as gl

# Import own modules
from src.windows.AssetManager.InfoPage import InfoPage
from src.windows.AssetManager.CustomAssets.Chooser import CustomAssetChooser

class AssetManager(Gtk.ApplicationWindow):
    def __init__(self, main_window: "MainWindow", *args, **kwargs):
        super().__init__(
            title="Asset Manager",
            default_width=1050,
            default_height=750,
            transient_for=main_window,
            *args, **kwargs
            )
        self.main_window = main_window
        self.build()

    def build(self):
        self.main_stack = Gtk.Stack(transition_duration=200, transition_type=Gtk.StackTransitionType.SLIDE_LEFT_RIGHT, hexpand=True, vexpand=True)
        self.set_child(self.main_stack)
        self.asset_chooser = AssetChooser(self)
        self.main_stack.add_titled(self.asset_chooser, "Asset Chooser", "Asset Chooser")

        self.asset_info = InfoPage(self)
        self.main_stack.add_titled(self.asset_info, "Asset Info", "Asset Info")

        # Header bar
        self.header_bar = Gtk.HeaderBar()
        self.set_titlebar(self.header_bar)

        self.stack_switcher = Gtk.StackSwitcher(stack=self.asset_chooser)
        self.header_bar.set_title_widget(self.stack_switcher)

        self.back_button = Gtk.Button(icon_name="go-previous", visible=False)
        self.back_button.connect("clicked", self.on_back_button_click)
        self.header_bar.pack_start(self.back_button)

    def show_for_path(self, path, callback_func=None, *callback_args, **callback_kwargs):
        self.asset_chooser.show_for_path(path, callback_func, *callback_args, **callback_kwargs)
        self.main_stack.set_visible_child(self.asset_chooser)
        self.back_button.set_visible(False)
        self.present()

    def show_info_for_asset(self, asset:dict):
        self.asset_info.show_for_asset(asset)
        self.main_stack.set_visible_child(self.asset_info)
        self.back_button.set_visible(True)
        self.present()

    def on_back_button_click(self, button):
        self.main_stack.set_visible_child(self.asset_chooser)


class AssetChooser(Gtk.Stack):
    def __init__(self, asset_manager: AssetManager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.asset_manager = asset_manager

        self.build()

    def build(self):
        self.custom_asset_chooser = CustomAssetChooser(self.asset_manager)
        self.add_titled(self.custom_asset_chooser, "custom-assets", "Custom Assets")

    def show_for_path(self, *args, **kwargs):
        self.custom_asset_chooser.show_for_path(*args, **kwargs)
    def __init__(self, asset_manager: AssetManager):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=False,
                            margin_start=15, margin_end=15, margin_top=15, margin_bottom=15)
        self.asset_manager = asset_manager

        self.build()
        self.load_defaults()

        self.init_dnd()

    def build(self):
        self.nav_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True, vexpand=False, margin_bottom=15)
        self.append(self.nav_box)

        self.search_entry = Gtk.SearchEntry(placeholder_text="Search", hexpand=True)
        self.search_entry.connect("search-changed", self.on_search_changed)
        self.nav_box.append(self.search_entry)

        self.type_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, css_classes=["linked"], margin_start=15)
        self.nav_box.append(self.type_box)

        self.video_button = Gtk.ToggleButton(icon_name="view-list-video-symbolic", css_classes=["blue-toggle-button"])
        self.video_button.connect("toggled", self.on_video_toggled)
        self.type_box.append(self.video_button)

        self.image_button = Gtk.ToggleButton(icon_name="view-list-images-symbolic", css_classes=["blue-toggle-button"])
        self.image_button.connect("toggled", self.on_image_toggled)
        self.type_box.append(self.image_button)

        self.scrolled_window = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        self.append(self.scrolled_window)

        self.scrolled_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=False,
                                margin_top=5, margin_bottom=5)
        self.scrolled_window.set_child(self.scrolled_box)

        self.inside_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=False)
        self.scrolled_box.append(self.inside_box)

        self.asset_chooser = AssetChooserFlowBox(self, orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        self.scrolled_box.append(self.asset_chooser)

        # Add vexpand box to the bottom to avoid unwanted stretching of the children
        self.scrolled_box.append(Gtk.Box(vexpand=True, hexpand=True))

    def init_dnd(self):
        self.dnd_target = Gtk.DropTarget.new(Gdk.FileList, Gdk.DragAction.COPY)
        self.dnd_target.connect("drop", self.on_dnd_drop)
        self.dnd_target.connect("accept", self.on_dnd_accept)

        self.add_controller(self.dnd_target)

    def on_dnd_accept(self, drop, user_data):
        return True
    
    def on_dnd_drop(self, drop_target, value, x, y):
        paths = value.get_files()
        for path in paths:
            path = path.get_path()
            if path == None:
                continue
            if not os.path.exists(path):
                continue
            if not os.path.splitext(path)[1] not in ["png", "jpg", "jpeg", "gif", "GIF", "MP4", "mp4", "mov", "MOV"]:
                continue
            asset_id = gl.asset_manager.add(asset_path=path)
            if asset_id == None:
                continue
            asset = gl.asset_manager.get_by_id(asset_id)
            self.asset_chooser.flow_box.append(AssetPreview(flow=self, asset=asset, width_request=100, height_request=100))
        return True

    def show_for_path(self, path, callback_func=None, *callback_args, **callback_kwargs):
        if not callable(callback_func):
            log.error("callback_func is not callable")
        self.asset_chooser.show_for_path(path, callback_func, *callback_args, **callback_kwargs)

    def on_video_toggled(self, button):
        settings = gl.settings_manager.load_settings_from_file("settings/ui/AssetManager.json")
        settings["video-toggle"] = button.get_active()
        gl.settings_manager.save_settings_to_file("settings/ui/AssetManager.json", settings)

        # Update ui
        self.asset_chooser.flow_box.invalidate_filter()

    def on_image_toggled(self, button):
        settings = gl.settings_manager.load_settings_from_file("settings/ui/AssetManager.json")
        settings["image-toggle"] = button.get_active()
        gl.settings_manager.save_settings_to_file("settings/ui/AssetManager.json", settings)

        # Update ui
        self.asset_chooser.flow_box.invalidate_filter()

    def load_defaults(self):
        settings = gl.settings_manager.load_settings_from_file("settings/ui/AssetManager.json")
        self.video_button.set_active(settings.get("video-toggle", True))
        self.image_button.set_active(settings.get("image-toggle", True))

    def on_search_changed(self, entry):
        self.asset_chooser.flow_box.invalidate_sort()



class AssetChooserFlowBox(Gtk.Box):
    def __init__(self, asset_chooser, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_orientation(Gtk.Orientation.HORIZONTAL)
        self.set_hexpand(True)

        self.callback_func = None
        self.callback_args = ()
        self.callback_kwargs = {}

        self.asset_chooser:AssetChooser = asset_chooser

        self.all_assets:list[AssetPreview] = []

        self.build()

        self.flow_box.set_filter_func(self.filter_func)
        self.flow_box.set_sort_func(self.sort_func)


    def build(self):
        self.flow_box = Gtk.FlowBox(hexpand=True, orientation=Gtk.Orientation.HORIZONTAL)
        self.flow_box.connect("child-activated", self.on_child_activated)
        self.append(self.flow_box)

        for asset in gl.asset_manager.get_all():
            asset = AssetPreview(flow=self, asset=asset, width_request=100, height_request=100)
            self.flow_box.append(asset)

    def show_for_path(self, path, callback_func=None, *callback_args, **callback_kwargs):
        self.callback_func = callback_func
        self.callback_args = callback_args
        self.callback_kwargs = callback_kwargs

        for i in range(1, 100):
            child = self.flow_box.get_child_at_index(i)
            if child == None:
                return
            if child.asset["internal-path"] == path:
                self.flow_box.select_child(child)
                return
            
    def filter_func(self, child):
        search_string = self.asset_chooser.search_entry.get_text()
        show_image = self.asset_chooser.image_button.get_active()
        show_video = self.asset_chooser.video_button.get_active()

        child_is_video = is_video(child.asset["internal-path"])

        if child_is_video and not show_video:
            return False
        if not child_is_video and not show_image:
            return False
        
        if search_string == "":
            return True
        
        fuzz_score = fuzz.partial_ratio(search_string.lower(), child.name.lower())
        if fuzz_score < 40:
            return False
        
        return True
    
    def sort_func(self, a, b):
        search_string = self.asset_chooser.search_entry.get_text()

        if search_string == "":
            # Sort alphabetically
            if a.asset["name"] < b.asset["name"]:
                return -1
            if a.asset["name"] > b.asset["name"]:
                return 1
            return 0
        
        a_fuzz = fuzz.partial_ratio(search_string.lower(), a.asset["name"].lower())
        b_fuzz = fuzz.partial_ratio(search_string.lower(), b.asset["name"].lower())

        if a_fuzz > b_fuzz:
            return -1
        elif a_fuzz < b_fuzz:
            return 1
        
        return 0
    
    def on_child_activated(self, flow_box, child):
        if callable(self.callback_func):
            self.callback_func(child.asset["internal-path"], *self.callback_args, **self.callback_kwargs)
        self.asset_chooser.asset_manager.close()


class AssetPreview(Gtk.FlowBoxChild):
    def __init__(self, flow:AssetChooserFlowBox, asset:dict, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_css_classes(["asset-preview"])
        self.set_margin_start(5)
        self.set_margin_end(5)
        self.set_margin_top(5)
        self.set_margin_bottom(5)

        self.asset = asset
        self.flow = flow

        self.build()

    def build(self):
        self.overlay = Gtk.Overlay()
        self.set_child(self.overlay)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, width_request=250, height_request=180)
        self.overlay.set_child(self.main_box)

        self.picture = Gtk.Picture(width_request=250, height_request=180, overflow=Gtk.Overflow.HIDDEN, content_fit=Gtk.ContentFit.COVER,
                                   hexpand=False, vexpand=False, keep_aspect_ratio=True)
        self.pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(self.asset["thumbnail"],
                                                              width=250,
                                                              height=180,
                                                              preserve_aspect_ratio=True)
        
        self.picture.set_pixbuf(self.pixbuf)
        self.main_box.append(self.picture)

        self.label = Gtk.Label(label=self.asset["name"], xalign=Gtk.Align.CENTER)
        self.main_box.append(self.label)

        self.info_button = Gtk.Button(icon_name="help-info-symbolic", halign=Gtk.Align.END, valign=Gtk.Align.END, margin_end=5, margin_bottom=5)
        self.info_button.connect("clicked", self.on_click_info)
        self.overlay.add_overlay(self.info_button)

    def on_click_info(self, button):
        self.flow.asset_chooser.asset_manager.show_info_for_asset(self.asset)

class AssetInfo(Gtk.Box):
    def __init__(self, asset_manager:AssetManager):
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
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
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, GObject, Pango

# Import python modules
import threading
from collections import OrderedDict

from loguru import logger as log

# Import typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.backend.IconPackManagement.Icon import Icon
    from src.windows.AssetManager.IconPacks.Icons.IconChooser import IconChooserPage

# Icons are always loaded at this size and scaled down by the picture, so the
# size slider does not have to touch the disk again
RENDER_SIZE = 160


class IconTextureLoader:
    """
    Loads the icon files in the background and keeps the last textures around.

    The grid only binds the visible icons, but scrolling through a few thousand
    of them would still block the main loop on every file - especially for svgs,
    which have to be rendered before they can be shown.

    The queue is a stack, and a tile only ever waits for the icon it shows right
    now: jumping to the end of a pack binds far more icons than the user gets to
    see, and without both of those the icons on screen end up behind thousands
    of files nobody is waiting for anymore.
    """
    def __init__(self, cache_size: int = 250, workers: int = 2):
        self.cache_size = cache_size

        self.cache: OrderedDict[str, Gdk.Texture] = OrderedDict()
        # The queue is only used as an ordered set, the values are unused
        self.queue: OrderedDict[str, None] = OrderedDict()
        self.waiting: dict[str, set["IconTile"]] = {}
        self.waiting_for: dict["IconTile", str] = {}
        self.condition = threading.Condition()

        for i in range(workers):
            threading.Thread(target=self._work, name=f"icon-loader-{i}", daemon=True).start()

    def get_cached(self, path: str) -> Gdk.Texture:
        with self.condition:
            texture = self.cache.get(path)
            if texture is not None:
                self.cache.move_to_end(path)
            return texture

    def request(self, path: str, tile: "IconTile") -> None:
        """
        Loads the icon and hands it to tile.apply_texture() on the main thread,
        immediately if it is already loaded.
        """
        texture = self.get_cached(path)
        if texture is not None:
            tile.apply_texture(path, texture)
            return

        with self.condition:
            self._forget(tile)

            self.waiting_for[tile] = path
            self.waiting.setdefault(path, set()).add(tile)

            self.queue[path] = None
            self.queue.move_to_end(path)

            self.condition.notify()

    def cancel(self, tile: "IconTile") -> None:
        with self.condition:
            self._forget(tile)

    def _forget(self, tile: "IconTile") -> None:
        """
        Drops the request of a tile that has been recycled for another icon.
        Has to be called with the condition held.
        """
        path = self.waiting_for.pop(tile, None)
        if path is None:
            return

        tiles = self.waiting.get(path)
        if tiles is None:
            return

        tiles.discard(tile)
        if not tiles:
            self.waiting.pop(path, None)
            self.queue.pop(path, None)

    def _work(self) -> None:
        while True:
            with self.condition:
                while not self.queue:
                    self.condition.wait()
                path = self.queue.popitem()[0]

            pixbuf = None
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(str(path), RENDER_SIZE, RENDER_SIZE)
            except GLib.Error as e:
                log.warning(f"Failed to load icon {path}: {e}")

            GLib.idle_add(self._finish, path, pixbuf)

    def _finish(self, path: str, pixbuf: GdkPixbuf.Pixbuf) -> bool:
        # The texture is created on the main thread, the tiles only get to show it
        texture = Gdk.Texture.new_for_pixbuf(pixbuf) if pixbuf is not None else None

        with self.condition:
            if texture is not None:
                self.cache[path] = texture
                while len(self.cache) > self.cache_size:
                    self.cache.popitem(last=False)

            tiles = self.waiting.pop(path, set())
            for tile in tiles:
                self.waiting_for.pop(tile, None)

        if texture is not None:
            for tile in tiles:
                tile.apply_texture(path, texture)

        return False


texture_loader = IconTextureLoader()


class IconObject(GObject.Object):
    """
    Wrapper because the list model can only hold GObjects
    """
    __gtype_name__ = "StreamControllerIconObject"

    def __init__(self, icon: "Icon"):
        super().__init__()
        self.icon = icon


class IconTile(Gtk.Box):
    """
    One icon in the grid. The tiles are recycled by the grid view, set_icon()
    and clear() are called while the user scrolls.
    """
    def __init__(self, chooser: "IconChooserPage"):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=2,
                         halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER,
                         css_classes=["icon-tile"])
        self.chooser = chooser
        self.icon: "Icon" = None

        self.build()

    def build(self):
        self.overlay = Gtk.Overlay()
        self.append(self.overlay)

        self.picture = Gtk.Picture(content_fit=Gtk.ContentFit.CONTAIN, can_shrink=True,
                                   hexpand=False, vexpand=False)
        self.overlay.set_child(self.picture)

        self.info_button = Gtk.Button(icon_name="help-about-symbolic", visible=False,
                                      halign=Gtk.Align.END, valign=Gtk.Align.START,
                                      tooltip_text="Show icon info",
                                      css_classes=["circular", "osd", "icon-tile-info-button"])
        self.info_button.connect("clicked", self.on_info_clicked)
        self.overlay.add_overlay(self.info_button)

        self.label = Gtk.Label(visible=False, ellipsize=Pango.EllipsizeMode.END, max_width_chars=1,
                               css_classes=["caption", "dim-label"])
        self.append(self.label)

        self.motion_controller = Gtk.EventControllerMotion()
        self.motion_controller.connect("enter", self.on_enter)
        self.motion_controller.connect("leave", self.on_leave)
        self.add_controller(self.motion_controller)

    def set_icon_size(self, size: int) -> None:
        self.picture.set_size_request(size, size)
        self.label.set_size_request(size, -1)

    def set_backdrop(self, backdrop: bool) -> None:
        """
        Packs ship black and white icons, one of them always disappears in the
        background of the window. The neutral backdrop keeps both visible.
        """
        if backdrop:
            self.picture.add_css_class("icon-tile-backdrop")
        else:
            self.picture.remove_css_class("icon-tile-backdrop")

    def set_show_name(self, show: bool) -> None:
        self.label.set_visible(show)
        if show and self.icon is not None:
            self.label.set_text(self.icon.name)

    def set_icon(self, icon: "Icon") -> None:
        self.icon = icon

        self.set_tooltip_text(self.get_tooltip_for_icon(icon))
        if self.label.get_visible():
            self.label.set_text(icon.name)

        # Keep the tile empty until the icon has been loaded instead of showing
        # the icon of the tile this one has been recycled from
        self.picture.set_paintable(None)
        texture_loader.request(icon.path, self)

    def clear(self) -> None:
        texture_loader.cancel(self)

        self.icon = None
        self.picture.set_paintable(None)
        self.label.set_text("")
        self.set_tooltip_text(None)

    def apply_texture(self, path: str, texture: Gdk.Texture) -> None:
        # The tile may have been recycled for another icon in the meantime
        if self.icon is None or self.icon.path != path:
            return
        self.picture.set_paintable(texture)

    def get_tooltip_for_icon(self, icon: "Icon") -> str:
        parts = [icon.name]
        if icon.category and icon.category != "Base":
            parts.append(icon.category)
        parts.append(icon.icon_pack.name)
        return " · ".join(parts)

    def on_enter(self, *args):
        self.info_button.set_visible(True)

    def on_leave(self, *args):
        self.info_button.set_visible(False)

    def on_info_clicked(self, *args):
        if self.icon is not None:
            self.chooser.show_info_for_icon(self.icon)

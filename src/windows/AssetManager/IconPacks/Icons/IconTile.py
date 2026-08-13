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

# Icons are loaded at one of these sizes so that the size slider only has to
# touch the disk again when it leaves the size it is currently rendering at
RENDER_SIZES = (64, 96, 128, 160)

# The tiles are allocated a bit more than the requested icon size, and a texture
# that is a little larger than the tile keeps the icons from looking soft
RENDER_HEADROOM = 1.5

# Textures are kept in memory until this is reached. Scrolling through a pack
# loads far more icons than fit into the cache, so the limit decides how much of
# a pack survives a jump to another place in it (~1300 icons at 96px).
CACHE_BUDGET_BYTES = 48 * 1024 * 1024

# Textures are handed to the tiles in batches, so that a burst of loaded icons
# cannot block the main loop for longer than a frame
MAX_TEXTURES_PER_BATCH = 24


def get_render_size(display_size: int, scale_factor: int = 1) -> int:
    """The size the icon has to be loaded at to be shown at display_size."""
    wanted = display_size * max(scale_factor, 1) * RENDER_HEADROOM
    for size in RENDER_SIZES:
        if size >= wanted:
            return size
    return RENDER_SIZES[-1]


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
    def __init__(self, budget_bytes: int = CACHE_BUDGET_BYTES, workers: int = 3):
        self.budget_bytes = budget_bytes
        self.cache_bytes = 0

        self.cache: OrderedDict[tuple[str, int], Gdk.Texture] = OrderedDict()
        # The queue is only used as an ordered set, the values are unused
        self.queue: OrderedDict[tuple[str, int], None] = OrderedDict()
        self.waiting: dict[tuple[str, int], set["IconTile"]] = {}
        self.waiting_for: dict["IconTile", tuple[str, int]] = {}
        # Loaded pixbufs that still have to be turned into textures
        self.loaded: list[tuple[tuple[str, int], GdkPixbuf.Pixbuf]] = []
        self.batch_pending = False
        self.condition = threading.Condition()

        for i in range(workers):
            threading.Thread(target=self._work, name=f"icon-loader-{i}", daemon=True).start()

    def request(self, path: str, render_size: int, tile: "IconTile") -> None:
        """
        Loads the icon and hands it to tile.apply_texture() on the main thread,
        immediately if it is already loaded.
        """
        key = (path, render_size)

        with self.condition:
            # Also for a cached icon: the tile may be waiting for the same icon
            # in another size because the size slider has been moved
            self._forget(tile)

            texture = self.cache.get(key)
            if texture is not None:
                self.cache.move_to_end(key)
            else:
                self.waiting_for[tile] = key
                self.waiting.setdefault(key, set()).add(tile)

                self.queue[key] = None
                self.queue.move_to_end(key)

                self.condition.notify()

        if texture is not None:
            tile.apply_texture(path, texture)

    def cancel(self, tile: "IconTile") -> None:
        with self.condition:
            self._forget(tile)

    def _forget(self, tile: "IconTile") -> None:
        """
        Drops the request of a tile that has been recycled for another icon.
        Has to be called with the condition held.
        """
        key = self.waiting_for.pop(tile, None)
        if key is None:
            return

        tiles = self.waiting.get(key)
        if tiles is None:
            return

        tiles.discard(tile)
        if not tiles:
            self.waiting.pop(key, None)
            self.queue.pop(key, None)

    def _work(self) -> None:
        while True:
            with self.condition:
                while not self.queue:
                    self.condition.wait()
                key = self.queue.popitem()[0]

                if key not in self.waiting:
                    # Nobody is interested in it anymore
                    continue

            path, render_size = key
            pixbuf = None
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(str(path), render_size, render_size)
            except GLib.Error as e:
                log.warning(f"Failed to load icon {path}: {e}")

            if pixbuf is None:
                with self.condition:
                    for tile in self.waiting.pop(key, ()):
                        self.waiting_for.pop(tile, None)
                continue

            with self.condition:
                self.loaded.append((key, pixbuf))
                if self.batch_pending:
                    continue
                self.batch_pending = True

            GLib.idle_add(self._apply_batch)

    def _apply_batch(self) -> bool:
        """
        Turns the loaded pixbufs into textures and hands them to their tiles.
        Only a couple of them per run, the rest waits for the next idle slot so
        that a pack that loads faster than it is scrolled cannot stall the
        rendering of the icons that are already there.
        """
        with self.condition:
            batch = self.loaded[:MAX_TEXTURES_PER_BATCH]
            del self.loaded[:MAX_TEXTURES_PER_BATCH]
            self.batch_pending = len(self.loaded) > 0

        updates: list[tuple[str, Gdk.Texture, set["IconTile"]]] = []

        for key, pixbuf in batch:
            texture = Gdk.Texture.new_for_pixbuf(pixbuf)

            with self.condition:
                self._cache(key, texture)

                tiles = self.waiting.pop(key, set())
                for tile in tiles:
                    self.waiting_for.pop(tile, None)

            updates.append((key[0], texture, tiles))

        for path, texture, tiles in updates:
            for tile in tiles:
                tile.apply_texture(path, texture)

        if self.batch_pending:
            GLib.idle_add(self._apply_batch)

        return False

    def _cache(self, key: tuple[str, int], texture: Gdk.Texture) -> None:
        """Has to be called with the condition held."""
        if key in self.cache:
            self.cache.move_to_end(key)
            return

        self.cache[key] = texture
        self.cache_bytes += texture.get_width() * texture.get_height() * 4

        while self.cache_bytes > self.budget_bytes and len(self.cache) > 1:
            dropped = self.cache.popitem(last=False)[1]
            self.cache_bytes -= dropped.get_width() * dropped.get_height() * 4


texture_loader = IconTextureLoader()


class IconObject(GObject.Object):
    """
    Wrapper because the list model can only hold GObjects
    """
    __gtype_name__ = "StreamControllerIconObject"

    def __init__(self, icon: "Icon"):
        super().__init__()
        self.icon = icon
        self.tooltip: str = None

    def get_tooltip(self) -> str:
        # Built once per icon instead of on every bind while scrolling
        if self.tooltip is None:
            icon = self.icon
            parts = [icon.name]
            if icon.category and icon.category != "Base":
                parts.append(icon.category)
            parts.append(icon.icon_pack.name)
            self.tooltip = " · ".join(parts)
        return self.tooltip


class IconTile(Gtk.Box):
    """
    One icon in the grid. The tiles are recycled by the grid view, set_icon()
    and clear() are called while the user scrolls.

    Everything that is not needed to show an icon (the name, the info button) is
    only built when it is used - a pack switch throws away and rebuilds every
    tile of the grid, so the cost of building one is paid a few hundred times.
    """
    def __init__(self, chooser: "IconChooserPage"):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=2,
                         halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER,
                         css_classes=["icon-tile"])
        self.chooser = chooser
        self.icon: "Icon" = None
        self.icon_object: "IconObject" = None
        self.icon_size: int = 0
        self.render_size: int = RENDER_SIZES[0]
        self.show_name: bool = False

        self.label: Gtk.Label = None
        self.info_button: Gtk.Button = None

        self.build()

    def build(self):
        self.overlay = Gtk.Overlay()
        self.append(self.overlay)

        # A Gtk.Image keeps its size no matter what it shows, a Gtk.Picture takes
        # the size of its texture - which would make the grid measure itself
        # again for every one of the hundreds of icons that arrive while scrolling
        self.image = Gtk.Image(hexpand=False, vexpand=False)
        self.overlay.set_child(self.image)

        self.motion_controller = Gtk.EventControllerMotion()
        self.motion_controller.connect("enter", self.on_enter)
        self.motion_controller.connect("leave", self.on_leave)
        self.add_controller(self.motion_controller)

        # set_tooltip_text() makes gtk re-evaluate the tooltip of the window and
        # costs up to a millisecond on a tile that is on screen - which is far
        # too much for something that runs for every icon that is scrolled by
        self.set_has_tooltip(True)
        self.connect("query-tooltip", self.on_query_tooltip)

    def build_label(self) -> Gtk.Label:
        self.label = Gtk.Label(ellipsize=Pango.EllipsizeMode.END, max_width_chars=1,
                               css_classes=["caption", "dim-label"])
        self.label.set_size_request(self.icon_size, -1)
        self.append(self.label)
        return self.label

    def build_info_button(self) -> Gtk.Button:
        self.info_button = Gtk.Button(icon_name="help-about-symbolic", visible=False,
                                      halign=Gtk.Align.END, valign=Gtk.Align.START,
                                      tooltip_text="Show icon info",
                                      css_classes=["circular", "osd", "icon-tile-info-button"])
        self.info_button.connect("clicked", self.on_info_clicked)
        self.overlay.add_overlay(self.info_button)
        return self.info_button

    def set_icon_size(self, size: int, render_size: int) -> None:
        if size != self.icon_size:
            self.icon_size = size
            self.image.set_pixel_size(size)
            if self.label is not None:
                self.label.set_size_request(size, -1)

        if render_size == self.render_size:
            return
        self.render_size = render_size

        # The icon is on screen in the wrong resolution, load it again
        if self.icon is not None:
            texture_loader.request(self.icon.path, self.render_size, self)

    def set_backdrop(self, backdrop: bool) -> None:
        """
        Packs ship black and white icons, one of them always disappears in the
        background of the window. The neutral backdrop keeps both visible.
        """
        if backdrop:
            self.image.add_css_class("icon-tile-backdrop")
        else:
            self.image.remove_css_class("icon-tile-backdrop")

    def set_show_name(self, show: bool) -> None:
        self.show_name = show

        if not show:
            if self.label is not None:
                self.label.set_visible(False)
            return

        label = self.label or self.build_label()
        label.set_visible(True)
        label.set_text(self.icon.name if self.icon is not None else "")

    def set_icon(self, icon_object: "IconObject") -> None:
        """
        Called for every icon that is scrolled into the grid, so it does as
        little as it can get away with - clear() has already emptied the tile.
        """
        icon = icon_object.icon
        self.icon = icon
        self.icon_object = icon_object

        if self.show_name:
            (self.label or self.build_label()).set_text(icon.name)

        texture_loader.request(icon.path, self.render_size, self)

    def clear(self) -> None:
        texture_loader.cancel(self)

        self.icon = None
        self.icon_object = None
        # Keep the tile empty until the next icon has been loaded instead of
        # showing the icon of the tile this one has been recycled from. The
        # name and the tooltip are overwritten before the tile is shown again.
        self.image.set_from_paintable(None)

    def apply_texture(self, path: str, texture: Gdk.Texture) -> None:
        # The tile may have been recycled for another icon in the meantime
        if self.icon is None or self.icon.path != path:
            return
        self.image.set_from_paintable(texture)

    def on_query_tooltip(self, widget, x: int, y: int, keyboard: bool, tooltip: Gtk.Tooltip) -> bool:
        if self.icon_object is None:
            return False
        tooltip.set_text(self.icon_object.get_tooltip())
        return True

    def on_enter(self, *args):
        (self.info_button or self.build_info_button()).set_visible(True)

    def on_leave(self, *args):
        if self.info_button is not None:
            self.info_button.set_visible(False)

    def on_info_clicked(self, *args):
        if self.icon is not None:
            self.chooser.show_info_for_icon(self.icon)

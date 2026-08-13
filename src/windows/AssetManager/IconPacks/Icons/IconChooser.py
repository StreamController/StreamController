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
from gi.repository import Gtk, Adw, Gio, GLib

# Import own modules
from src.windows.AssetManager.ChooserPage import ChooserPage
from src.windows.AssetManager.IconPacks.Icons.IconTile import IconObject, IconTile
from src.backend.IconPackManagement import IconSearch

# Import python modules
import threading

from loguru import logger as log

# Import globals
import globals as gl

# Import typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.AssetManager.AssetManager import AssetManager
    from src.backend.IconPackManagement.Icon import Icon
    from src.backend.IconPackManagement.IconPack import IconPack
    from src.windows.AssetManager.IconPacks.Stack import IconPackChooserStack

MIN_ICON_SIZE = 32
MAX_ICON_SIZE = 128
DEFAULT_ICON_SIZE = 64

SEARCH_DEBOUNCE_MS = 150
SETTINGS_DEBOUNCE_MS = 500


class IconChooserPage(ChooserPage):
    """
    Browses the icons of one pack or - in all packs mode - of every pack the
    user has installed.

    All icons live in a list model behind a Gtk.GridView, so even packs with a
    couple of thousand icons are scrolled instead of paginated and the search
    always runs over the whole pack.
    """
    def __init__(self, stack: "IconPackChooserStack", asset_manager: "AssetManager"):
        super().__init__()
        self.asset_manager = asset_manager
        self.stack = stack

        self.selected_icon: str = None
        self.scroll_to_selected: bool = False
        self.pack: "IconPack" = None
        self.icons: list["Icon"] = []
        self.icon_objects: dict[str, IconObject] = {}
        self.all_packs: bool = False

        # The recycled tiles of the grid, kept to apply the view settings to them
        self.tiles: list[IconTile] = []

        self.search_timeout_id: int = None
        self.settings_timeout_id: int = None
        self.load_id: int = 0
        self.updating_all_packs_button: bool = False

        self.icon_size, self.show_names, self.backdrop = self.load_view_settings()

        self.build_finished = False
        self.build()

    @log.catch
    def build(self):
        self.type_box.set_visible(False)
        self.search_entry.set_placeholder_text("Search icons")

        self.all_packs_button = Gtk.ToggleButton(margin_start=15, tooltip_text="Search in all icon packs")
        self.all_packs_button.set_child(Adw.ButtonContent(icon_name="view-grid-symbolic", label="All Packs"))
        self.all_packs_button.connect("toggled", self.on_all_packs_toggled)
        self.nav_box.append(self.all_packs_button)

        self.view_button = Gtk.MenuButton(icon_name="view-more-symbolic", margin_start=5,
                                          tooltip_text="View options", popover=self.build_view_popover())
        self.nav_box.append(self.view_button)

        # The default scrolled window of the chooser page holds a box, the grid brings its own
        self.main_box.remove(self.scrolled_window)

        self.overlay = Gtk.Overlay(hexpand=True, vexpand=True)
        self.main_box.append(self.overlay)

        self.grid_scroller = Gtk.ScrolledWindow(hexpand=True, vexpand=True,
                                                hscrollbar_policy=Gtk.PolicyType.NEVER)
        self.overlay.set_child(self.grid_scroller)

        self.status_page = Adw.StatusPage(icon_name="system-search-symbolic", title="No Icons Found",
                                          description="Try a different search term",
                                          visible=False, can_target=False)
        self.overlay.add_overlay(self.status_page)

        self.list_store = Gio.ListStore(item_type=IconObject)
        self.selection_model = Gtk.SingleSelection(model=self.list_store, autoselect=False, can_unselect=True)

        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self.on_factory_setup)
        factory.connect("bind", self.on_factory_bind)
        factory.connect("unbind", self.on_factory_unbind)
        factory.connect("teardown", self.on_factory_teardown)

        self.grid_view = Gtk.GridView(model=self.selection_model, factory=factory, max_columns=64,
                                      single_click_activate=True, vexpand=True, hexpand=True,
                                      css_classes=["icon-grid"])
        self.grid_view.connect("activate", self.on_activate)
        self.grid_scroller.set_child(self.grid_view)

        self.set_loading(False)

        self.build_finished = True
        self.stack.on_load_finished()

    def build_view_popover(self) -> Gtk.Popover:
        popover = Gtk.Popover()

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10,
                      margin_start=10, margin_end=10, margin_top=10, margin_bottom=10)
        popover.set_child(box)

        box.append(Gtk.Label(label="Icon Size", xalign=0, css_classes=["heading"]))

        self.size_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, MIN_ICON_SIZE, MAX_ICON_SIZE, 8)
        self.size_scale.set_draw_value(False)
        self.size_scale.set_size_request(200, -1)
        self.size_scale.set_value(self.icon_size)
        self.size_scale.connect("value-changed", self.on_size_changed)
        box.append(self.size_scale)

        self.names_button = Gtk.CheckButton(label="Show names", active=self.show_names)
        self.names_button.connect("toggled", self.on_show_names_toggled)
        box.append(self.names_button)

        self.backdrop_button = Gtk.CheckButton(label="Icon background", active=self.backdrop,
                                               tooltip_text="Show a neutral background behind every icon so that dark icons stay visible")
        self.backdrop_button.connect("toggled", self.on_backdrop_toggled)
        box.append(self.backdrop_button)

        return popover

    ## View settings

    def load_view_settings(self) -> tuple[int, bool, bool]:
        settings = gl.settings_manager.get_app_settings().get("icon-browser", {})
        size = settings.get("icon-size", DEFAULT_ICON_SIZE)
        size = min(max(int(size), MIN_ICON_SIZE), MAX_ICON_SIZE)
        return size, bool(settings.get("show-names", False)), bool(settings.get("backdrop", True))

    def save_view_settings(self) -> bool:
        self.settings_timeout_id = None

        settings = gl.settings_manager.get_app_settings()
        settings.setdefault("icon-browser", {})
        settings["icon-browser"]["icon-size"] = self.icon_size
        settings["icon-browser"]["show-names"] = self.show_names
        settings["icon-browser"]["backdrop"] = self.backdrop
        gl.settings_manager.save_app_settings(settings)

        return False

    def save_view_settings_delayed(self) -> None:
        # The slider fires for every step while it is dragged
        if self.settings_timeout_id is not None:
            GLib.source_remove(self.settings_timeout_id)
        self.settings_timeout_id = GLib.timeout_add(SETTINGS_DEBOUNCE_MS, self.save_view_settings)

    def on_size_changed(self, scale: Gtk.Scale):
        size = int(scale.get_value())
        if size == self.icon_size:
            return
        self.icon_size = size

        for tile in self.tiles:
            tile.set_icon_size(size)

        self.save_view_settings_delayed()

    def on_show_names_toggled(self, button: Gtk.CheckButton):
        self.show_names = button.get_active()

        for tile in self.tiles:
            tile.set_show_name(self.show_names)

        self.save_view_settings_delayed()

    def on_backdrop_toggled(self, button: Gtk.CheckButton):
        self.backdrop = button.get_active()

        for tile in self.tiles:
            tile.set_backdrop(self.backdrop)

        self.save_view_settings_delayed()

    ## Loading

    def load_for_pack(self, pack: "IconPack") -> None:
        # Called from the build thread of the pack chooser
        GLib.idle_add(self.do_load_for_pack, pack)

    def do_load_for_pack(self, pack: "IconPack") -> bool:
        if pack is not self.pack:
            # The search of the pack the user just left does not mean anything here
            self.search_entry.set_text("")

        self.pack = pack
        self.all_packs = False
        self.load_id += 1

        self.set_all_packs_button_state(active=False, sensitive=True)
        self.apply_icons(pack.get_icons())

        return False

    def load_all_packs(self) -> None:
        GLib.idle_add(self.do_load_all_packs)

    def do_load_all_packs(self) -> bool:
        self.all_packs = True
        self.set_all_packs_button_state(active=True, sensitive=self.pack is not None)
        self.set_loading(True)

        self.load_id += 1
        threading.Thread(target=self.load_all_packs_thread, args=(self.load_id,),
                         name="load-all-icons", daemon=True).start()

        return False

    @log.catch
    def load_all_packs_thread(self, load_id: int) -> None:
        icons = gl.icon_pack_manager.get_all_icons()
        # Creating the wrappers takes a moment for a few thousand icons
        icon_objects = {icon.path: IconObject(icon) for icon in icons}

        GLib.idle_add(self.finish_load_all_packs, load_id, icons, icon_objects)

    def finish_load_all_packs(self, load_id: int, icons: list["Icon"], icon_objects: dict) -> bool:
        if load_id != self.load_id:
            # The user has already switched to something else
            return False

        self.apply_icons(icons, icon_objects=icon_objects)
        self.set_loading(False)

        return False

    def apply_icons(self, icons: list["Icon"], icon_objects: dict = None) -> None:
        self.icons = icons
        self.icon_objects = icon_objects or {icon.path: IconObject(icon) for icon in icons}

        if self.all_packs:
            self.search_entry.set_placeholder_text(f"Search {len(icons):,} icons in all packs")
        elif self.pack is not None:
            self.search_entry.set_placeholder_text(f"Search {len(icons):,} icons in {self.pack.name}")

        self.update_results()

        # The user opened the pack to look for something
        GLib.idle_add(self.search_entry.grab_focus)

    ## Search

    def on_search_changed(self, entry):
        if self.search_timeout_id is not None:
            GLib.source_remove(self.search_timeout_id)
        self.search_timeout_id = GLib.timeout_add(SEARCH_DEBOUNCE_MS, self.on_search_timeout)

    def on_search_timeout(self) -> bool:
        self.search_timeout_id = None
        self.update_results()
        return False

    def update_results(self) -> None:
        query = self.search_entry.get_text()
        icons = IconSearch.search_icons(self.icons, query, match_pack_name=self.all_packs)

        self.list_store.splice(0, self.list_store.get_n_items(),
                               [self.icon_objects[icon.path] for icon in icons])

        self.status_page.set_visible(len(icons) == 0 and len(self.icons) > 0)
        self.grid_scroller.get_vadjustment().set_value(0)

        self.apply_selection()

    ## Selection

    def select_icon(self, path) -> None:
        self.selected_icon = path
        self.scroll_to_selected = True
        GLib.idle_add(self.apply_selection, priority=GLib.PRIORITY_LOW)

    def apply_selection(self) -> bool:
        if self.selected_icon is None:
            return False

        for i in range(self.list_store.get_n_items()):
            if self.list_store.get_item(i).icon.path != self.selected_icon:
                continue

            self.selection_model.set_selected(i)
            if self.scroll_to_selected:
                # Only when the browser was opened for the icon, not on every search
                self.scroll_to_selected = False
                self.scroll_to_index(i)
            break

        return False

    def scroll_to_index(self, index: int, attempts: int = 20) -> bool:
        """
        Scrolling before the grid has laid out its rows leaves it anchored to an
        item it does not know yet and it ends up showing nothing at all, so this
        waits until the scroll area knows how tall the grid is.
        """
        adjustment = self.grid_scroller.get_vadjustment()
        if adjustment.get_upper() <= adjustment.get_page_size() and attempts > 0:
            GLib.timeout_add(50, self.scroll_to_index, index, attempts - 1)
            return False

        self.grid_view.scroll_to(index, Gtk.ListScrollFlags.FOCUS, None)
        return False

    def on_activate(self, grid_view, position: int):
        item = self.selection_model.get_item(position)
        if item is None:
            return

        if callable(self.asset_manager.callback_func):
            self.asset_manager.callback_func(item.icon.path, *self.asset_manager.callback_args,
                                             **self.asset_manager.callback_kwargs)
        self.asset_manager.close()
        self.asset_manager.destroy()

    ## All packs

    def set_all_packs_button_state(self, active: bool, sensitive: bool) -> None:
        self.updating_all_packs_button = True
        self.all_packs_button.set_active(active)
        self.updating_all_packs_button = False

        self.all_packs_button.set_sensitive(sensitive)

    def on_all_packs_toggled(self, button: Gtk.ToggleButton):
        if self.updating_all_packs_button:
            return

        if button.get_active():
            self.do_load_all_packs()
        elif self.pack is not None:
            self.do_load_for_pack(self.pack)

    ## Tiles

    def on_factory_setup(self, factory, list_item: Gtk.ListItem):
        tile = IconTile(self)
        tile.set_icon_size(self.icon_size)
        tile.set_show_name(self.show_names)
        tile.set_backdrop(self.backdrop)

        self.tiles.append(tile)
        list_item.set_child(tile)

    def on_factory_bind(self, factory, list_item: Gtk.ListItem):
        list_item.get_child().set_icon(list_item.get_item().icon)

    def on_factory_unbind(self, factory, list_item: Gtk.ListItem):
        list_item.get_child().clear()

    def on_factory_teardown(self, factory, list_item: Gtk.ListItem):
        tile = list_item.get_child()
        if tile in self.tiles:
            self.tiles.remove(tile)

    def show_info_for_icon(self, icon: "Icon") -> None:
        attribution = icon.get_attribution() or {}
        self.asset_manager.show_info(
            internal_path = icon.path,
            licence_name = attribution.get("license"),
            license_url = attribution.get("license-url"),
            author = attribution.get("copyright"),
            license_comment = attribution.get("comment")
        )

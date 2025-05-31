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
import gc

# Import gi
import gi

from GtkHelper.ScaleRow import ScaleRow
from GtkHelper.ToggleRow import ToggleRow
from src.backend.DeckManagement.ImageHelpers import image2pixbuf
from src.windows.MultiDeckSelector.MultiDeckSelectorRow import MultiDeckSelectorRow
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio

# Import typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.PageManager.PageManager import PageManager

# Import globals
import globals as gl

# Import python modules
import os

# Import own modules
from GtkHelper.GtkHelper import BetterExpander, better_disconnect
from src.backend.WindowGrabber.Window import Window
from src.windows.PageManager.elements.MenuButton import MenuButton

class PageEditor(Adw.NavigationPage):
    def __init__(self, page_manager: "PageManager"):
        super().__init__(title=gl.lm.get("page-manager.page-editor.title"))
        self.page_manager = page_manager
        self.active_page_path: str = None
        self.build()

    def build(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.set_child(self.main_box)

        # Header
        self.header = Adw.HeaderBar(show_back_button=False, css_classes=["flat"], show_end_title_buttons=True)
        self.main_box.append(self.header)

        # Menu button
        self.menu_button = MenuButton(self)
        self.header.pack_end(self.menu_button)

        # Main stack - one page for the normal editor and one for the no page info screen
        self.main_stack = Gtk.Stack(hexpand=True, vexpand=True)
        self.main_box.append(self.main_stack)

        # The box for the normal editor
        self.editor_main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.main_stack.add_titled(self.editor_main_box, "editor", "Editor")

        # Scrolled window for  the normal editor
        self.scrolled_window = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        self.editor_main_box.append(self.scrolled_window)

        # Clamp for the scrolled window
        self.clamp = Adw.Clamp(margin_top=40)
        self.scrolled_window.set_child(self.clamp)

        # Box for all widgets in the editor
        self.editor_main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.clamp.set_child(self.editor_main_box)

        # Name group - Used to rename the page
        self.name_group = NameGroup(page_editor=self)
        self.editor_main_box.append(self.name_group)

        # Default page group - Used to configure default page for decks
        self.default_page_group = DefaultPageGroup(page_editor=self)
        self.editor_main_box.append(self.default_page_group)

        # Auto change group - Used to configure automatic page switching
        self.auto_change_group = AutoChangeGroup(page_editor=self)
        self.editor_main_box.append(self.auto_change_group)

        # Brightness Group
        self.brightness_group = BrightnessGroup(page_editor=self)
        self.editor_main_box.append(self.brightness_group)

        # Background Group
        self.background_group = BackgroundGroup(page_editor=self)
        self.editor_main_box.append(self.background_group)

        # Delete button
        self.delete_button = DeleteButton(page_editor=self, margin_top=40)
        self.editor_main_box.append(self.delete_button)

        # No page page
        self.no_page_box = Gtk.Box(hexpand=True, vexpand=True)
        self.main_stack.add_titled(self.no_page_box, "no-page", "No Page")

        self.no_page_box.append(Gtk.Label(label=gl.lm.get("page-manager.page-editor.no-page-selected"), halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER, hexpand=True))

        # Default to the no page info screen
        self.main_stack.set_visible_child_name("no-page")

    def load_for_page(self, page_path: str) -> None:
        self.active_page_path = page_path
        self.name_group.load_for_page(page_path=page_path)
        self.default_page_group.load_for_page(page_path=page_path)
        self.auto_change_group.load_for_page(page_path=page_path)
        self.brightness_group.load_for_page(page_path=page_path)
        self.background_group.load_for_page(page_path=page_path)

    def delete_active_page(self) -> None:
        if self.active_page_path is None:
            return
        
        self.page_manager.remove_page_by_path(self.active_page_path)


class PageEditorGroup(Adw.PreferencesGroup):
    def __init__(self, page_editor: PageEditor, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.page_editor = page_editor
        self.build()

    def build(self):
        pass

    def connect_events(self):
        pass

    def disconnect_events(self):
        pass

    def load_config_settings(self, page_path: str):
        pass

    def load_for_page(self, page_path: str) -> None:
        self.disconnect_events()
        self.load_config_settings(page_path)
        self.connect_events()

class NameGroup(PageEditorGroup):
    def __init__(self, page_editor: PageEditor):
        super().__init__(page_editor)

    def build(self):
        self.name_entry = Adw.EntryRow(title=gl.lm.get("page-manager.page-editor.name-group.name"), show_apply_button=True)
        self.add(self.name_entry)

    def connect_events(self):
        self.name_entry.connect("changed", self.on_name_changed)
        self.name_entry.connect("apply", self.on_name_change_applied)

    def disconnect_events(self):
        better_disconnect(self.name_entry, self.on_name_changed)
        better_disconnect(self.name_entry, self.on_name_change_applied)

    def load_config_settings(self, page_path: str):
        if page_path is None:
            return

        page_name = os.path.basename(page_path).split(".")[0]
        self.name_entry.set_text(page_name)

        base_path = os.path.dirname(page_path)
        is_user_page = base_path == os.path.join(gl.DATA_PATH, "pages")

        self.set_sensitive(is_user_page)

    def on_name_changed(self, entry: Adw.EntryRow, *args):
        original_name = os.path.basename(self.page_editor.active_page_path).split(".")[0]
        new_name = entry.get_text()

        all_page_names = gl.page_manager.get_page_names()
        all_page_names.remove(original_name)
        all_page_names.append("")

        if new_name in all_page_names:
            entry.add_css_class("error")
            entry.set_show_apply_button(False)
        else:
            entry.remove_css_class("error")
            entry.set_show_apply_button(True)

    def on_name_change_applied(self, entry: Adw.EntryRow, *args):
        original_path = self.page_editor.active_page_path
        new_path = os.path.join(os.path.dirname(original_path), f"{entry.get_text()}.json")

        if original_path == new_path:
            return

        self.page_editor.page_manager.rename_page_by_path(original_path, new_path)

class DefaultPageGroup(PageEditorGroup):
    def __init__(self, page_editor: PageEditor):
        super().__init__(page_editor, title=gl.lm.get("page-manager.page-editor.default-page.title"))

    def build(self):
        self.deck_selector = MultiDeckSelectorRow(
            source_window=self.page_editor.page_manager,
            title=gl.lm.get("page-manager.page-editor.default-page.row.title"),
            subtitle=gl.lm.get("page-manager.page-editor.default-page.row.subtitle"),
            callback=self.on_deck_changed,
            selected_deck_serials=gl.page_manager.get_serial_numbers_from_page(self.page_editor.active_page_path)
        )
        self.add(self.deck_selector)

    def load_config_settings(self, page_path: str):
        serial_numbers = gl.page_manager.get_serial_numbers_from_page(page_path)

        self.deck_selector.set_label(len(serial_numbers))
        self.deck_selector.set_selected_deck_serials(serial_numbers)

    def on_deck_changed(self, serial_number: str, state: bool):
        path = self.page_editor.active_page_path

        if not state:
            path = None

        gl.page_manager.set_default_page(serial_number, path)

class AutoChangeGroup(PageEditorGroup):
    def __init__(self, page_editor: PageEditor):
        super().__init__(page_editor, title=gl.lm.get("page-manager.page-editor.change-group.title"))

    def build(self):
        self.enable_toggle = Adw.SwitchRow(title=gl.lm.get("page-manager.page-editor.change-group.enable"))
        self.add(self.enable_toggle)

        self.stay_on_page_toggle = Adw.SwitchRow(title="Stay on page", subtitle="Stay on the page until another page matches")
        self.add(self.stay_on_page_toggle)

        self.deck_selector = MultiDeckSelectorRow(
            source_window=self.page_editor.page_manager,
            title="Decks",
            subtitle="Decks on which the page should be loaded",
            callback=self.on_deck_changed,
            selected_deck_serials=gl.page_manager.get_serial_numbers_from_page(self.page_editor.active_page_path)
        )
        self.add(self.deck_selector)

        self.title_entry = Adw.EntryRow(title=gl.lm.get("page-manager.page-editor.change-group.title-regex"), text="", show_apply_button=True)
        self.add(self.title_entry)

        self.wm_class_entry = Adw.EntryRow(title=gl.lm.get("page-manager.page-editor.change-group.wm-class-regex"), text="", show_apply_button=True)
        self.add(self.wm_class_entry)

        self.matching_window_expander = MatchingWindowExpander(auto_change_group=self)
        self.add(self.matching_window_expander)

    def connect_events(self):
        self.enable_toggle.connect("notify::active", self.on_enable_changed)
        self.stay_on_page_toggle.connect("notify::active", self.on_stay_on_page_changed)
        self.title_entry.connect("apply", self.on_title_entry_applied)
        self.wm_class_entry.connect("apply", self.on_wm_class_entry_applied)

    def disconnect_events(self):
        better_disconnect(self.enable_toggle, self.on_enable_changed)
        better_disconnect(self.stay_on_page_toggle, self.on_stay_on_page_changed)
        better_disconnect(self.title_entry, self.on_title_entry_applied)
        better_disconnect(self.wm_class_entry, self.on_wm_class_entry_applied)

    def load_config_settings(self, page_path: str):
        auto_change = gl.page_manager.get_auto_change_settings(self.page_editor.active_page_path)

        self.enable_toggle.set_active(auto_change.get("enable", False))
        self.stay_on_page_toggle.set_active(auto_change.get("stay-on-page", True))
        self.wm_class_entry.set_text(auto_change.get("wm-class", ""))
        self.title_entry.set_text(auto_change.get("title", ""))
        self.deck_selector.set_selected_deck_serials(auto_change.get("decks", []).copy())

    def on_enable_changed(self, *args):
        gl.page_manager.overwrite_auto_change_settings(
            path=self.page_editor.active_page_path,
            enable=self.enable_toggle.get_active()
        )

    def on_stay_on_page_changed(self, *args):
        gl.page_manager.overwrite_auto_change_settings(
            path=self.page_editor.active_page_path,
            stay_on_page=self.stay_on_page_toggle.get_active()
        )

    def on_title_entry_applied(self, *args):
        self.matching_window_expander.update_matching_windows()

        gl.page_manager.overwrite_auto_change_settings(
            path=self.page_editor.active_page_path,
            regex_title=self.title_entry.get_text()
        )

    def on_wm_class_entry_applied(self, *args):
        self.matching_window_expander.update_matching_windows()

        gl.page_manager.overwrite_auto_change_settings(
            path=self.page_editor.active_page_path,
            wm_class=self.wm_class_entry.get_text()
        )

    def on_deck_changed(self, serial_number: str, state: bool):
        path = self.page_editor.active_page_path
        info = gl.page_manager.get_auto_change_settings(path)
        decks = info.get("decks", [])

        if state and serial_number not in decks:
            decks.append(serial_number)
        elif not state and serial_number in decks:
            decks.remove(serial_number)
        else:
            return

        gl.page_manager.overwrite_auto_change_settings(path, decks=decks)

class BrightnessGroup(PageEditorGroup):
    def __init__(self, page_editor: PageEditor):
        super().__init__(page_editor, title="Brightness Override")

    def build(self):
        self.enable_toggle = Adw.SwitchRow(title="Enable Brightness Override", subtitle="Overrides the Deck Brighness")
        self.add(self.enable_toggle)

        self.brightness_scale = ScaleRow(0, 0, 100, digits=0, draw_value=True, draw_side_values=False, title="Brightness")
        self.add(self.brightness_scale)

    def connect_events(self):
        self.enable_toggle.connect("notify::active", self.on_enable_changed)
        self.brightness_scale.scale.connect("value-changed", self.on_brightness_changed)

    def disconnect_events(self):
        better_disconnect(self.enable_toggle, self.on_enable_changed)
        better_disconnect(self.brightness_scale.scale, self.on_brightness_changed)

    def load_config_settings(self, page_path: str):
        settings = gl.page_manager.get_brightness_settings(page_path)

        self.enable_toggle.set_active(settings.get("overwrite", False))
        self.brightness_scale.set_value(settings.get("brightness", 75))

    def on_enable_changed(self, *args):
        gl.page_manager.overwrite_brightness_settings(
            path=self.page_editor.active_page_path,
            overwrite=self.enable_toggle.get_active()
        )

    def on_brightness_changed(self, *args):
        gl.page_manager.overwrite_brightness_settings(
            path=self.page_editor.active_page_path,
            brightness=self.brightness_scale.get_value()
        )

class BackgroundGroup(PageEditorGroup):
    def __init__(self, page_editor: PageEditor):
        super().__init__(page_editor, title="Background Override")

    def build(self):
        self.enable_expander = BetterExpander(
            title="Overwrite Background",
            subtitle="Overrides the Deck Background",
            expanded=False,
            show_enable_switch=True
        )
        self.add(self.enable_expander)

        self.media_main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.enable_expander.add_row(self.media_main_box)

        self.media_settings_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, valign=Gtk.Align.CENTER)
        self.media_main_box.append(self.media_settings_box)

        self.show_background_toggle = Adw.SwitchRow(title="Show Background")
        self.media_settings_box.append(self.show_background_toggle)

        self.loop_toggle = Adw.SwitchRow(title="Loop")
        self.media_settings_box.append(self.loop_toggle)

        self.fps_spin = Adw.SpinRow.new_with_range(0, 30, 1)
        self.fps_spin.set_title("FPS")
        self.media_settings_box.append(self.fps_spin)

        self.button_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, valign=Gtk.Align.CENTER)
        self.media_main_box.append(self.button_box)

        self.media_selector_button = Gtk.Button(
            label="Select",
            css_classes=["page-settings-media-selector"],
            halign=Gtk.Align.CENTER,
        )
        self.button_box.append(self.media_selector_button)

        self.media_selector_image = Gtk.Image()

    def connect_events(self):
        self.enable_expander.connect("notify::enable-expansion", self.on_enable_changed)
        self.show_background_toggle.connect("notify::active", self.on_show_background_changed)
        self.loop_toggle.connect("notify::active", self.on_loop_changed)
        self.fps_spin.connect("changed", self.on_fps_changed)
        self.media_selector_button.connect("clicked", self.on_media_selector_click)

    def disconnect_events(self):
        better_disconnect(self.enable_expander, self.on_enable_changed)
        better_disconnect(self.show_background_toggle, self.on_show_background_changed)
        better_disconnect(self.loop_toggle, self.on_loop_changed)
        better_disconnect(self.fps_spin, self.on_fps_changed)
        better_disconnect(self.media_selector_button, self.on_media_selector_click)

    def load_config_settings(self, page_path: str):
        background_settings = gl.page_manager.get_background_settings(page_path)

        self.enable_expander.set_enable_expansion(background_settings.get("overwrite", False))
        self.enable_expander.set_expanded(background_settings.get("overwrite", False))

        self.show_background_toggle.set_active(background_settings.get("show", False))
        self.loop_toggle.set_active(background_settings.get("loop", False))
        self.fps_spin.set_value(background_settings.get("fps", 0))
        self.set_thumbnail(background_settings.get("media-path", None))

    def on_enable_changed(self, *args):
        gl.page_manager.overwrite_background_settings(
            path=self.page_editor.active_page_path,
            overwrite=self.enable_expander.get_enable_expansion()
        )
        self.update_background()

    def on_show_background_changed(self, *args):
        gl.page_manager.overwrite_background_settings(
            path=self.page_editor.active_page_path,
            show=self.show_background_toggle.get_active()
        )
        self.update_background()

    def on_loop_changed(self, *args):
        gl.page_manager.overwrite_background_settings(
            path=self.page_editor.active_page_path,
            loop=self.loop_toggle.get_active()
        )
        self.update_background()

    def on_fps_changed(self, *args):
        gl.page_manager.overwrite_background_settings(
            path=self.page_editor.active_page_path,
            fps=int(self.fps_spin.get_value())
        )
        self.update_background()

    def on_media_selector_click(self, *args):
        background_settings = gl.page_manager.get_background_settings(self.page_editor.active_page_path)

        gl.app.let_user_select_asset(default_path=background_settings.get("media-path", ""), callback_func=self.update_image)

    def set_thumbnail(self, file_path):
        if not file_path:
            self.media_selector_image.set_from_pixbuf(None)
            self.media_selector_image.pixbuf = None
            return

        image = gl.media_manager.get_thumbnail(file_path)
        pixbuf = image2pixbuf(image)

        self.media_selector_image.set_from_pixbuf(pixbuf)
        self.media_selector_button.set_child(self.media_selector_image)

        image.close()

    def update_image(self, file_path):
        self.set_thumbnail(file_path)

        gl.page_manager.overwrite_background_settings(
            path=self.page_editor.active_page_path,
            media_path=file_path
        )

        self.update_background()


    def update_background(self):
        for controller in gl.deck_manager.deck_controller:
            if controller.active_page.json_path == self.page_editor.active_page_path:
                controller.load_background(controller.active_page)


class MatchingWindowExpander(BetterExpander):
    def __init__(self, auto_change_group: AutoChangeGroup):
        super().__init__(
            title=gl.lm.get("page-manager.page-editor.matching-windows.title"),
            subtitle=gl.lm.get("page-manager.page-editor.matching-windows.subtitle"),
            expanded=False
        )

        self.auto_change_group = auto_change_group

        self.update_button = Gtk.Button(icon_name="view-refresh-symbolic", valign=Gtk.Align.CENTER,
                                        css_classes=["flat"])
        self.update_button.connect("clicked", self.update_matching_windows)
        self.add_suffix(self.update_button)

    def load_windows(self, windows: list[Window]):
        self.clear()
        for window in windows:
            self.add_row(Adw.ActionRow(title=window.title, subtitle=window.wm_class, use_markup=False))

    def update_matching_windows(self, *args):
        class_regex = self.auto_change_group.wm_class_entry.get_text()
        title_regex = self.auto_change_group.title_entry.get_text()

        matching_windows = gl.window_grabber.get_all_matching_windows(class_regex=class_regex, title_regex=title_regex)
        self.load_windows(windows=matching_windows)

class DeleteButton(Gtk.Button):
    def __init__(self, page_editor: PageEditor, *args, **kwargs):
        super().__init__(css_classes=["destructive-action", "tall-button"], hexpand=True, *args, **kwargs)
        self.page_editor = page_editor
        self.set_label(gl.lm.get("page-manager.page-editor.delete-page"))
        self.connect("clicked", self.on_delete_clicked)

    def on_delete_clicked(self, button: Gtk.Button) -> None:
        dialog = DeletePageConfirmationDialog(page_editor=self.page_editor)
        dialog.present()

class DeletePageConfirmationDialog(Adw.MessageDialog):
    def __init__(self, page_editor: PageEditor, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.page_editor = page_editor

        self.set_transient_for(page_editor.page_manager)
        self.set_modal(True)
        self.set_title(gl.lm.get("page-manager.page-editor.delete-page-confirm.title"))
        self.add_response("cancel", gl.lm.get("page-manager.page-editor.delete-page-confirm.cancel"))
        self.add_response("delete", gl.lm.get("page-manager.page-editor.delete-page-confirm.delete"))
        self.set_default_response("cancel")
        self.set_close_response("cancel")
        self.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)

        page_name = os.path.splitext(os.path.basename(self.page_editor.active_page_path))[0]
        self.set_body(f'{gl.lm.get("page-manager.page-editor.delete-page-confirm.body")}"{page_name}"?')

        self.connect("response", self.on_response)

    def on_response(self, dialog: Adw.MessageDialog, response: int) -> None:
        if response == "delete":
            page_path = self.page_editor.active_page_path
            self.page_editor.page_manager.remove_page_by_path(page_path)
        self.destroy()

class ScreensaverGroup(Adw.PreferencesRow):
    def __init__(self, page_editor: PageEditor):
        super().__init__()

        self.page_editor = page_editor
        self.build()
        self.load_config_settings()

    def build(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.set_child(self.main_box)

        self.overwrite_toggle = Adw.SwitchRow(title="Overwrite")
        self.main_box.append(self.overwrite_toggle)

        self.media_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.main_box.append(self.media_box)

        self.enable_toggle = Adw.SwitchRow(title="Enable")
        self.media_box.append(self.enable_toggle)

        self.delay_spin = Adw.SpinRow(title="Delay")
        self.media_box.append(self.delay_spin)

        self.media_select_button = Gtk.Button(label="Select", css_classes=["page-settings-media-selector"], halign=Gtk.Align.CENTER)
        self.media_box.append(self.media_select_button)

        self.loop_toggle = Adw.SwitchRow(title="Loop")
        self.media_box.append(self.loop_toggle)

        self.fps_spin = Adw.SpinRow(title="FPS")
        self.media_box.append(self.fps_spin)

        self.brightness_scale = ScaleRow(0, 0, 100, title="Brightness", digits=0, draw_side_values=False, draw_value=True)
        self.media_box.append(self.brightness_scale)

    def load_config_settings(self):
        if self.page_editor.active_page_path is None:
            return

        self.disconnect_signals()

        settings = gl.page_manager.get_screensaver_settings(self.page_editor.active_page_path)

        self.overwrite_toggle.set_active(settings.get("overwrite", False))
        self.enable_toggle.set_active(settings.get("enable", False))
        self.delay_spin.set_value(settings.get("time-delay", 5))
        # Media Select
        self.fps_spin.set_value(settings.get("fps", 30))
        self.brightness_scale.value = settings.get("brightness", 75)

        self.connect_signals()

    def load_for_page(self, page_path: str) -> None:
        self.load_config_settings()

    def connect_signals(self):
        self.overwrite_toggle.connect("notify::active", self.overwrite_changed)
        self.enable_toggle.connect("notify::active", self.enable_changed)
        self.delay_spin.connect("changed", self.delay_changed)
        self.media_select_button.connect("clicked", self.media_select_clicked)
        self.loop_toggle.connect("notify::active", self.loop_changed)
        self.fps_spin.connect("changed", self.fps_changed)
        self.brightness_scale.scale.connect("value-changed", self.brightness_changed)

    def disconnect_signals(self):
        better_disconnect(self.overwrite_toggle, self.overwrite_changed)
        better_disconnect(self.enable_toggle, self.enable_changed)
        better_disconnect(self.delay_spin, self.delay_changed)
        better_disconnect(self.media_select_button, self.media_select_clicked)
        better_disconnect(self.loop_toggle, self.loop_changed)
        better_disconnect(self.fps_spin, self.fps_changed)
        better_disconnect(self.brightness_scale, self.brightness_changed)

    def overwrite_changed(self, *args):
        gl.page_manager.overwrite_screensaver_settings(
            path=self.page_editor.active_page_path,
            overwrite=self.overwrite_toggle.get_active()
        )

    def enable_changed(self, *args):
        gl.page_manager.overwrite_screensaver_settings(
            path=self.page_editor.active_page_path,
            enable=self.enable_toggle.get_active()
        )

    def delay_changed(self, *args):
        gl.page_manager.overwrite_screensaver_settings(
            path=self.page_editor.active_page_path,
            time_delay=int(self.delay_spin.get_value())
        )

    def media_select_clicked(self, *args):
        pass

    def loop_changed(self, *args):
        gl.page_manager.overwrite_screensaver_settings(
            path=self.page_editor.active_page_path,
            loop=self.loop_toggle.get_active()
        )

    def fps_changed(self, *args):
        gl.page_manager.overwrite_screensaver_settings(
            path=self.page_editor.active_page_path,
            fps=int(self.fps_spin.get_value())
        )

    def brightness_changed(self, *args):
        gl.page_manager.overwrite_screensaver_settings(
            path=self.page_editor.active_page_path,
            brightness=int(self.brightness_scale.value)
        )
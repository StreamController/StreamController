from gi.repository import Gtk, Adw, Gdk

from typing import TYPE_CHECKING

from src.backend.DeckManagement.InputIdentifier import Input, InputIdentifier
from src.windows.mainWindow.elements.Sidebar.elements.ActionManager import ActionManager
from src.windows.mainWindow.elements.Sidebar.elements.BackgroundEditor import BackgroundEditor
from src.windows.mainWindow.elements.Sidebar.elements.IconSelector import IconSelector
from src.windows.mainWindow.elements.Sidebar.elements.ImageEditor import ImageEditor
from src.windows.mainWindow.elements.Sidebar.elements.StateSwitcher import StateSwitcher
from src.windows.mainWindow.DeckPlus.ScreenBar import ScreenBarImage

from PIL import Image

if TYPE_CHECKING:
    from src.windows.mainWindow.elements.Sidebar.Sidebar import Sidebar

import globals as gl


class ClockEditor(Gtk.Box):
    def __init__(self, sidebar: "Sidebar", **kwargs):
        self.sidebar = sidebar
        super().__init__(**kwargs)
        self.active_identifier: InputIdentifier = None
        self.active_state: int = None
        self._signals_connected = False
        self.build()

    def build(self):
        self.clamp = Adw.Clamp()
        self.append(self.clamp)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.clamp.set_child(self.main_box)

        self.group = Adw.PreferencesGroup(title="Clock")
        self.main_box.append(self.group)

        self.expander = Adw.ExpanderRow(title="Clock &amp; Date", subtitle="Show time and date on screen")
        self.group.add(self.expander)

        # Enable switch
        self.enable_row = Adw.SwitchRow(title="Enable Clock")
        self.expander.add_row(self.enable_row)

        # 24h toggle
        self.format_24h_row = Adw.SwitchRow(title="24-hour format")
        self.expander.add_row(self.format_24h_row)

        # Show seconds
        self.show_seconds_row = Adw.SwitchRow(title="Show seconds")
        self.expander.add_row(self.show_seconds_row)

        # Show date
        self.show_date_row = Adw.SwitchRow(title="Show date")
        self.expander.add_row(self.show_date_row)

        # Date format dropdown
        self.date_format_row = Adw.PreferencesRow()
        date_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True,
                           margin_start=15, margin_end=15, margin_top=10, margin_bottom=10)
        self.date_format_row.set_child(date_box)

        date_label = Gtk.Label(label="Date format", xalign=0, hexpand=True)
        date_box.append(date_label)

        self.date_format_strings = Gtk.StringList.new(["MM/DD/YY", "DD/MM/YY", "YYYY-MM-DD"])
        self.date_format_dropdown = Gtk.DropDown(model=self.date_format_strings)
        date_box.append(self.date_format_dropdown)
        self.expander.add_row(self.date_format_row)

        # Color picker
        self.color_row = Adw.PreferencesRow()
        color_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True,
                            margin_start=15, margin_end=15, margin_top=10, margin_bottom=10)
        self.color_row.set_child(color_box)

        color_label = Gtk.Label(label="Text color", xalign=0, hexpand=True)
        color_box.append(color_label)

        self.color_dialog = Gtk.ColorDialog(title="Clock text color")
        self.color_button = Gtk.ColorDialogButton(dialog=self.color_dialog)
        color_box.append(self.color_button)
        self.expander.add_row(self.color_row)

    def connect_signals(self):
        if self._signals_connected:
            return
        self._signals_connected = True
        self.enable_row.connect("notify::active", self._on_change)
        self.format_24h_row.connect("notify::active", self._on_change)
        self.show_seconds_row.connect("notify::active", self._on_change)
        self.show_date_row.connect("notify::active", self._on_change)
        self.date_format_dropdown.connect("notify::selected", self._on_change)
        self.color_button.connect("notify::rgba", self._on_change)

    def disconnect_signals(self):
        if not self._signals_connected:
            return
        self._signals_connected = False
        try:
            self.enable_row.disconnect_by_func(self._on_change)
            self.format_24h_row.disconnect_by_func(self._on_change)
            self.show_seconds_row.disconnect_by_func(self._on_change)
            self.show_date_row.disconnect_by_func(self._on_change)
            self.date_format_dropdown.disconnect_by_func(self._on_change)
            self.color_button.disconnect_by_func(self._on_change)
        except Exception:
            pass

    def _get_config_from_ui(self) -> dict:
        rgba = self.color_button.get_rgba()
        color = [round(rgba.red * 255), round(rgba.green * 255),
                 round(rgba.blue * 255), round(rgba.alpha * 255)]

        date_formats = ["MM/DD/YY", "DD/MM/YY", "YYYY-MM-DD"]
        idx = self.date_format_dropdown.get_selected()
        date_fmt = date_formats[idx] if idx < len(date_formats) else "MM/DD/YY"

        return {
            "enabled": self.enable_row.get_active(),
            "use-24h": self.format_24h_row.get_active(),
            "show-seconds": self.show_seconds_row.get_active(),
            "show-date": self.show_date_row.get_active(),
            "date-format": date_fmt,
            "color": color,
        }

    def _on_change(self, *args):
        controller = gl.app.main_win.get_active_controller()
        if controller is None:
            return
        identifier = self.active_identifier
        c_input = controller.get_input(identifier)
        if c_input is None:
            return

        active_state = c_input.get_active_state()
        cfg = self._get_config_from_ui()
        active_state.clock_config = cfg

        page = controller.active_page
        if page is not None:
            page.dict.setdefault(identifier.input_type, {})
            page.dict[identifier.input_type].setdefault(identifier.json_identifier, {})
            page.dict[identifier.input_type][identifier.json_identifier].setdefault("states", {})
            state_key = str(active_state.state)
            page.dict[identifier.input_type][identifier.json_identifier]["states"].setdefault(state_key, {})
            page.dict[identifier.input_type][identifier.json_identifier]["states"][state_key]["screen-clock"] = cfg
            page.save()

        c_input.restart_clock_timer()
        c_input.update()

    def load_for_identifier(self, identifier: InputIdentifier, state: int):
        self.disconnect_signals()

        self.active_identifier = identifier
        self.active_state = state

        controller = gl.app.main_win.get_active_controller()
        if controller is None:
            self.connect_signals()
            return

        c_input = controller.get_input(identifier)
        if c_input is None:
            self.connect_signals()
            return

        active_state = c_input.get_active_state()
        cfg = getattr(active_state, 'clock_config', {})

        self.enable_row.set_active(cfg.get("enabled", False))
        self.format_24h_row.set_active(cfg.get("use-24h", False))
        self.show_seconds_row.set_active(cfg.get("show-seconds", False))
        self.show_date_row.set_active(cfg.get("show-date", True))

        date_formats = ["MM/DD/YY", "DD/MM/YY", "YYYY-MM-DD"]
        fmt = cfg.get("date-format", "MM/DD/YY")
        self.date_format_dropdown.set_selected(date_formats.index(fmt) if fmt in date_formats else 0)

        color_vals = cfg.get("color", [255, 255, 255, 255])
        while len(color_vals) < 4:
            color_vals.append(255)
        rgba = Gdk.RGBA()
        rgba.parse(f"rgba({color_vals[0]},{color_vals[1]},{color_vals[2]},{color_vals[3]/255})")
        self.color_button.set_rgba(rgba)

        self.connect_signals()


class ScreenEditor(Gtk.ScrolledWindow):
    def __init__(self, sidebar: "Sidebar"):
        self.sidebar = sidebar
        super().__init__(hexpand=True, vexpand=True)

        self.build()

    def build(self):
        self.clamp = Adw.Clamp(hexpand=True, vexpand=True)
        self.set_child(self.clamp)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.clamp.set_child(self.main_box)

        self.header = Gtk.Label(css_classes=["large-title", "bold"], margin_top=15, margin_bottom=30)
        self.main_box.append(self.header)

        self.state_switcher = StateSwitcher("touchscreens", margin_start=20, margin_end=20, margin_top=10, margin_bottom=10, hexpand=True)
        self.state_switcher.add_switch_callback(self.on_state_switch)
        self.state_switcher.add_add_new_callback(self.on_add_new_state)
        self.state_switcher.set_n_states(0)
        self.main_box.append(self.state_switcher)

        self.icon_selector = IconSelector(self.sidebar, halign=Gtk.Align.CENTER, margin_top=30)
        self.main_box.append(self.icon_selector)

        self.image_editor = ImageEditor(self.sidebar, margin_top=25)
        self.main_box.append(self.image_editor)

        self.scale_group = Adw.PreferencesGroup(title="Display")
        self.main_box.append(self.scale_group)

        self.scale_spin = Adw.SpinRow.new_with_range(1.0, 4.0, 0.5)
        self.scale_spin.set_title("Screen Scale")
        self.scale_spin.set_value(1.0)
        self.scale_spin.connect("changed", self.on_scale_changed)
        self.scale_group.add(self.scale_spin)

        self.clock_editor = ClockEditor(self.sidebar, margin_top=25)
        self.main_box.append(self.clock_editor)

        self.background_editor = BackgroundEditor(self.sidebar, margin_top=25)
        self.main_box.append(self.background_editor)

        self.action_manager_group = Adw.PreferencesGroup(title="Actions")
        self.main_box.append(self.action_manager_group)

        self.action_manager = ActionManager(self.sidebar)
        self.action_manager_group.add(self.action_manager)

        self.remove_state_button = Gtk.Button(label="Remove State", css_classes=["destructive-action"], margin_top=15, margin_bottom=15, margin_start=15, margin_end=15)
        self.remove_state_button.connect("clicked", self.on_remove_state)
        self.main_box.append(self.remove_state_button)


    def on_state_switch(self, *args):
        state = self.state_switcher.get_selected_state()

        visible_child = gl.app.main_win.leftArea.deck_stack.get_visible_child()
        if visible_child is None:
            return
        controller = visible_child.deck_controller
        if controller is None:
            return

        c_input = controller.get_input(self.sidebar.active_identifier)
        if c_input is not None:
            c_input.set_state(state, update_sidebar=True)

    def on_add_new_state(self, state):
        controller = gl.app.main_win.get_active_controller()
        if controller is None:
            return

        c_input = controller.get_input(self.sidebar.active_identifier)
        if c_input is not None:
            c_input.add_new_state()
            self.remove_state_button.set_visible(self.state_switcher.get_n_states() > 1)

    def on_remove_state(self, button):
        if self.state_switcher.get_n_states() <= 1:
            return

        controller = gl.app.main_win.get_active_controller()
        if controller is None:
            return

        active_state = self.state_switcher.get_selected_state()

        c_input = controller.get_input(self.sidebar.active_identifier)
        if c_input is not None:
            c_input.remove_state(active_state)

        self.remove_state_button.set_visible(self.state_switcher.get_n_states() > 1)


    def on_scale_changed(self, spin, *args):
        controller = gl.app.main_win.get_active_controller()
        if controller is None:
            return
        identifier = self.sidebar.active_identifier
        c_input = controller.get_input(identifier)
        if c_input is None:
            return

        active_state = c_input.get_active_state()
        active_state.scale_factor = round(spin.get_value(), 1)

        page = controller.active_page
        if page is not None:
            page.dict.setdefault(identifier.input_type, {})
            page.dict[identifier.input_type].setdefault(identifier.json_identifier, {})
            page.dict[identifier.input_type][identifier.json_identifier].setdefault("states", {})
            state_key = str(active_state.state)
            page.dict[identifier.input_type][identifier.json_identifier]["states"].setdefault(state_key, {})
            page.dict[identifier.input_type][identifier.json_identifier]["states"][state_key]["screen-scale"] = active_state.scale_factor
            page.save()

        c_input.update()

    def load_for_identifier(self, identifier, state):
        self.sidebar.active_identifier = identifier

        controller = gl.app.main_win.get_active_controller()
        if controller is None:
            return

        controller_input = controller.get_input(identifier)
        self.state_switcher.load_for_identifier(identifier, state)
        controller_input.set_state(state, update_sidebar=False)

        self.remove_state_button.set_visible(self.state_switcher.get_n_states() > 1)

        active_state = controller_input.get_active_state()
        self.scale_spin.disconnect_by_func(self.on_scale_changed)
        self.scale_spin.set_value(getattr(active_state, 'scale_factor', 1.0))
        self.scale_spin.connect("changed", self.on_scale_changed)

        is_screen = isinstance(identifier, Input.Screen)
        self.header.set_label("Infobar" if is_screen else "Touch Bar")
        self.scale_group.set_visible(is_screen)
        self.clock_editor.set_visible(is_screen)

        if is_screen:
            self.clock_editor.load_for_identifier(identifier, state)

        self.icon_selector.load_for_identifier(identifier, state)
        self.image_editor.load_for_identifier(identifier, state)
        self.background_editor.load_for_identifier(identifier, state)
        self.action_manager.load_for_identifier(identifier, state)

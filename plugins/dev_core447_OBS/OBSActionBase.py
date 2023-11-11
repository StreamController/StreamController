from src.backend.PluginManager.ActionBase import ActionBase
from src.backend.PluginManager.PluginBase import PluginBase

# Import gtk modules
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

class OBSActionBase(ActionBase):
    def __init__(self, deck_controller, page, coords):
        super().__init__(deck_controller=deck_controller, page=page, coords=coords)

        self.status_label = Gtk.Label(label="Couldn't connect to OBS", css_classes=["bold", "red"])

    def get_config_rows(self) -> list:
        self.ip_entry = Adw.EntryRow(title="IP Address")
        self.port_spinner = Adw.SpinRow.new_with_range(0, 65535, 1)
        self.port_spinner.set_title("Port:")
        self.password_entry = Adw.PasswordEntryRow(title="Password")

        self.load_config_defaults()

        # Connect signals
        self.ip_entry.connect("notify::text", self.on_change_ip)
        self.port_spinner.connect("notify::value", self.on_change_port)
        self.password_entry.connect("notify::text", self.on_change_password)

        return [self.ip_entry, self.port_spinner, self.password_entry]
    
    def load_config_defaults(self):
        settings = self.PLUGIN_BASE.get_settings()
        ip = settings.setdefault("ip", "localhost")
        port = settings.setdefault("port", 4455)
        password = settings.setdefault("password", "")

        # Update ui
        self.ip_entry.set_text(ip)
        self.port_spinner.set_value(port)
        self.password_entry.set_text(password)

        self.PLUGIN_BASE.set_settings(settings)

    def on_change_ip(self, entry, *args):
        settings = self.PLUGIN_BASE.get_settings()
        settings["ip"] = entry.get_text()
        self.PLUGIN_BASE.set_settings(settings)

        self.reconnect_obs()

    def on_change_port(self, spinner, *args):
        settings = self.PLUGIN_BASE.get_settings()
        settings["port"] = int(spinner.get_value())
        self.PLUGIN_BASE.set_settings(settings)

        self.reconnect_obs()

    def on_change_password(self, entry, *args):
        settings = self.PLUGIN_BASE.get_settings()
        settings["password"] = entry.get_text()
        self.PLUGIN_BASE.set_settings(settings)

        self.reconnect_obs()

    def reconnect_obs(self):
        print("reconnecing obs")
        self.PLUGIN_BASE.obs.connect_to(host=self.PLUGIN_BASE.get_settings()["ip"], port=self.PLUGIN_BASE.get_settings()["port"], password=self.PLUGIN_BASE.get_settings()["password"], timeout=3, legacy=False)

        if self.PLUGIN_BASE.obs.connected:
            self.status_label.set_label("Successfully connected to OBS")
            self.status_label.remove_css_class("red")
            self.status_label.add_css_class("green")
        else:
            self.status_label.set_label("Couldn't connect to OBS")
            self.status_label.remove_css_class("green")
            self.status_label.add_css_class("red")

    def get_custom_config_area(self):
        return self.status_label
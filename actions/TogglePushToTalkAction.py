import os

from gi.repository import Gtk, Adw

from ..DiscordActionBase import DiscordActionBase
from ..discordrpc.commands import VOICE_SETTINGS_UPDATE

from loguru import logger as log


class TogglePushToTalkAction(DiscordActionBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mode: str = 'Toggle'
        self.ptt: bool = False
        self.label_location: str = 'Bottom'
        self.ptt_lookup = {
            "PUSH_TO_TALK": True,
            "VOICE_ACTIVITY": False
        }

    def on_ready(self):
        self.load_config()
        self.plugin_base.add_callback(
            VOICE_SETTINGS_UPDATE, self.update_display)
        self.plugin_base.backend.register_callback(
            VOICE_SETTINGS_UPDATE, self.update_display)


# To be used when there's icons for push to talk toggle
    def update_display(self, value: dict):
        self.ptt = self.ptt_lookup.get(value["mode"]["type"])
        image = "voice_act.png"
        if self.ptt:
            image = "ptt.png"
        self.set_media(media_path=os.path.join(
            self.plugin_base.PATH, "assets", image), size=0.85)

    def on_tick(self):
        if self.ptt:
            self.set_label("Push to\ntalk", position=self.label_location.lower())
        else:
            self.set_label(
                "Voice\nActivity", position=self.label_location.lower())

    def load_config(self):
        super().load_config()
        settings = self.get_settings()
        self.mode = settings.get('mode')
        if not self.mode:
            self.mode = 'Toggle'
        self.label_location = settings.get('label_location')
        if not self.label_location:
            self.label_location = 'Bottom'

    def get_config_rows(self):
        super_rows = super().get_config_rows()
        self.action_model = Gtk.StringList()
        self.mode_row = Adw.ComboRow(
            model=self.action_model, title=self.plugin_base.lm.get("actions.deafen.choice.title"))

        index = 0
        found = 0
        for k in ['Enable', 'Disable', 'Toggle']:
            self.action_model.append(k)
            if self.mode == k:
                found = index
            index += 1
        self.mode_row.set_selected(found)
        self.mode_row.connect("notify::selected", self.on_change_mode)

        index = 0
        found = 0
        self.label_model = Gtk.StringList()
        self.label_row = Adw.ComboRow(
            model=self.label_model, title=self.plugin_base.lm.get("actions.deafen.label_choice.title"))
        for k in ['Top', 'Center', 'Bottom', 'None']:
            self.label_model.append(k)
            if self.label_location == k:
                found = index
            index += 1
        self.label_row.set_selected(found)
        self.label_row.connect("notify::selected", self.on_change_label_row)

        super_rows.append(self.mode_row)
        super_rows.append(self.label_row)
        return super_rows

    def on_change_mode(self, *_):
        settings = self.get_settings()
        selected_index = self.mode_row.get_selected()
        settings['mode'] = self.action_model[selected_index].get_string()
        self.mode = settings['mode']
        self.set_settings(settings)

    def on_change_label_row(self, *_):
        self.set_label('', position=self.label_location.lower())
        settings = self.get_settings()
        selected_index = self.label_row.get_selected()
        settings['label_location'] = self.label_model[selected_index].get_string()
        self.label_location = settings['label_location']
        self.set_settings(settings)

    def on_key_down(self):
        match self.mode:
            case "Emable":
                if not self.plugin_base.backend.set_push_to_talk("PUSH_TO_TALK"):
                    self.show_error(5)
            case "Disable":
                if not self.plugin_base.backend.set_push_to_talk("VOICE_ACTIVITY"):
                    self.show_error(5)
            case "Toggle":
                if not self.plugin_base.backend.set_push_to_talk("VOICE_ACTIVITY" if self.ptt == True else "PUSH_TO_TALK"):
                    self.show_error(5)
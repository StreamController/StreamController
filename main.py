import os

# Import StreamController modules
from src.backend.PluginManager.PluginBase import PluginBase
from src.backend.PluginManager.ActionHolder import ActionHolder

# Import actions
from .actions.MuteAction import MuteAction
from .actions.DeafenAction import DeafenAction
from .actions.ChangeVoiceChannelAction import ChangeVoiceChannelAction
from .actions.ChangeTextChannel import ChangeTextChannel
from .actions.TogglePushToTalkAction import TogglePushToTalkAction

from loguru import logger as log


class PluginTemplate(PluginBase):
    def __init__(self):
        super().__init__()

        self.callbacks = {}

        self.auth_callback_fn: callable = None

        self.lm = self.locale_manager
        self.lm.set_to_os_default()

        settings = self.get_settings()
        client_id = settings.get('client_id', '')
        client_secret = settings.get('client_secret', '')
        access_token = settings.get('access_token', '')

        backend_path = os.path.join(self.PATH, 'backend.py')
        self.launch_backend(backend_path=backend_path,
                            open_in_terminal=False, venv_path=os.path.join(self.PATH, '.venv'))

        self.backend.update_client_credentials(
            client_id, client_secret, access_token)

        self.message_mute_action_holder = ActionHolder(
            plugin_base=self,
            action_base=MuteAction,
            action_id="com_imdevinc_StreamControllerDiscordPlugin::Mute",
            action_name="Mute"
        )
        self.add_action_holder(self.message_mute_action_holder)

        self.message_deafen_action_holder = ActionHolder(
            plugin_base=self,
            action_base=DeafenAction,
            action_id="com_imdevinc_StreamControllerDiscordPlugin::Deafen",
            action_name="Deafen"
        )
        self.add_action_holder(self.message_deafen_action_holder)

        self.message_ptt_action_holder = ActionHolder(
            plugin_base=self,
            action_base=TogglePushToTalkAction,
            action_id="com_imdevinc_StreamControllerDiscordPlugin::push_to_talk",
            action_name="Toggle push to talk"
        )
        self.add_action_holder(self.message_ptt_action_holder)


        self.change_voice_channel_action = ActionHolder(
            plugin_base=self,
            action_base=ChangeVoiceChannelAction,
            action_id="com_imdevinc_StreamControllerDiscordPlugin::ChangeVoiceChannel",
            action_name="Change Voice Channel"
        )
        self.add_action_holder(self.change_voice_channel_action)

        self.change_text_channel_action = ActionHolder(
            plugin_base=self,
            action_base=ChangeTextChannel,
            action_id="com_imdevinc_StreamControllerDiscordPlugin::ChangeTextChannel",
            action_name="Change Text Channel"
        )
        self.add_action_holder(self.change_text_channel_action)

        self.register(
            plugin_name="Discord",
            github_repo="https://github.com/imdevinc/StreamControllerDiscordPlugin",
            plugin_version="1.0.0",
            app_version="1.5.0"
        )

        self.add_css_stylesheet(os.path.join(self.PATH, "style.css"))

    def save_access_token(self, access_token: str):
        settings = self.get_settings()
        settings['access_token'] = access_token
        self.set_settings(settings)

    def add_callback(self, key: str, callback: callable):
        callbacks = self.callbacks.get(key, [])
        callbacks.append(callback)
        self.callbacks[key] = callbacks

    def handle_callback(self, key: str, data: any):
        for callback in self.callbacks.get(key):
            callback(data)

    def on_auth_callback(self, success: bool, message: str = None):
        if self.auth_callback_fn:
            self.auth_callback_fn(success, message)

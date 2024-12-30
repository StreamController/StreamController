import json

from streamcontroller_plugin_tools import BackendBase

from loguru import logger as log

from discordrpc import AsyncDiscord, commands


class Backend(BackendBase):
    def __init__(self):
        super().__init__()
        self.client_id: str = None
        self.client_secret: str = None
        self.access_token: str = None
        self.discord_client: AsyncDiscord = None
        self.callbacks: dict = {}
        self._is_authed: bool = False

    def discord_callback(self, code, event):
        if code == 0:
            return
        try:
            event = json.loads(event)
        except Exception as ex:
            log.error(f"failed to parse discord event: {ex}")
            return
        match event.get('cmd'):
            case commands.AUTHORIZE:
                auth_code = event.get('data').get('code')
                self.access_token = self.discord_client.get_access_token(
                    auth_code)
                self.discord_client.authenticate(self.access_token)
                self.frontend.save_access_token(self.access_token)
            case commands.AUTHENTICATE:
                self.frontend.on_auth_callback(True)
                self._is_authed = True
                for k in self.callbacks:
                    self.discord_client.subscribe(k)
            case commands.DISPATCH:
                evt = event.get('evt')
                self.frontend.handle_callback(evt, event.get('data'))

    def setup_client(self):
        try:
            self.discord_client = AsyncDiscord(
                self.client_id, self.client_secret)
            self.discord_client.connect(self.discord_callback)
            if not self.access_token:
                self.discord_client.authorize()
            else:
                self.discord_client.authenticate(self.access_token)
        except Exception as ex:
            self.frontend.on_auth_callback(False, str(ex))
            log.error("failed to setup discord client: {0}", ex)

    def update_client_credentials(self, client_id: str, client_secret: str, access_token: str = ""):
        if None in (client_id, client_secret) or "" in (client_id, client_secret):
            self.frontend.on_auth_callback(
                False, "actions.base.credentials.missing_client_info")
            return
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = access_token
        self.setup_client()

    def is_authed(self) -> bool:
        return self._is_authed

    def register_callback(self, key: str, callback: callable):
        callbacks = self.callbacks.get(key, [])
        callbacks.append(callback)
        self.callbacks[key] = callbacks
        if self._is_authed:
            self.discord_client.subscribe(key)

    def set_mute(self, muted: bool) -> bool:
        if self.discord_client is None or not self.discord_client.is_connected():
            self.setup_client()
        try:
            self.discord_client.set_voice_settings({'mute': muted})
        except Exception as ex:
            log.error("failed to set mute {0}", ex)
            return False
        return True

    def set_deafen(self, muted: bool) -> bool:
        if self.discord_client is None or not self.discord_client.is_connected():
            self.setup_client()
        try:
            self.discord_client.set_voice_settings({'deaf': muted})
        except Exception as ex:
            log.error("failed to set deaf {0}", ex)
            return False
        return True

    def change_voice_channel(self, channel_id: str = None) -> bool:
        if self.discord_client is None or not self.discord_client.is_connected():
            self.setup_client()
        try:
            self.discord_client.select_voice_channel(channel_id, True)
        except Exception as ex:
            log.error(
                "failed to change voice channel {0}. {1}", channel_id, ex)
            return False
        return True

    def change_text_channel(self, channel_id: str) -> bool:
        if self.discord_client is None or not self.discord_client.is_connected():
            self.setup_client()
        try:
            self.discord_client.select_text_channel(channel_id)
        except Exception as ex:
            log.error(
                "failed to change text channel {0}. {1}", channel_id, ex)
            return False
        return True

    def set_push_to_talk(self, ptt: str) -> bool:
        if self.discord_client is None or not self.discord_client.is_connected():
            self.setup_client()
        try:
            self.discord_client.set_voice_settings({'mode': {"type": ptt}})
        except Exception as ex:
            log.error("failed to set push to talk {0}", ex)
            return False
        return True

backend = Backend()

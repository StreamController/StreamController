"""
App wide AI configuration.

One provider + model is configured for the whole app (Settings -> AI) and shared by
everything that talks to a model: the sidebar assistant and the AI Button plugin.

The settings live under the "ai" key of the app settings, so a plugin only has to reach
for `gl.ai_manager` instead of asking the user for another API key.
"""

import globals as gl
from src.backend.AI.Providers import PROVIDERS, LLMProvider, ProviderError, get_provider_class


class AIManager:
    SETTINGS_KEY = "ai"

    def get_settings(self) -> dict:
        return gl.settings_manager.get_app_settings().get(self.SETTINGS_KEY, {})

    def set_settings(self, ai_settings: dict) -> None:
        settings = gl.settings_manager.get_app_settings()
        settings[self.SETTINGS_KEY] = ai_settings
        gl.settings_manager.save_app_settings(settings)

    def _set(self, key: str, provider_id: str, value) -> None:
        ai_settings = self.get_settings()
        ai_settings.setdefault(key, {})[provider_id] = value
        self.set_settings(ai_settings)

    # ---------------------------------------------------------------- getters

    def get_assistant_enabled(self) -> bool:
        """Off until the user turns it on in Settings -> AI - nothing talks to a model uninvited."""
        return self.get_settings().get("assistant_enabled", False)

    def get_provider_id(self) -> str:
        return self.get_settings().get("provider", "chatgpt")

    def get_api_key(self, provider_id: str = None) -> str:
        provider_id = provider_id or self.get_provider_id()
        return self.get_settings().get("api_keys", {}).get(provider_id, "")

    def get_base_url(self, provider_id: str = None) -> str:
        provider_id = provider_id or self.get_provider_id()
        return self.get_settings().get("base_urls", {}).get(provider_id, "")

    def get_model(self, provider_id: str = None) -> str:
        provider_id = provider_id or self.get_provider_id()
        return self.get_settings().get("models", {}).get(provider_id, "")

    def get_cached_models(self, provider_id: str = None) -> list[str]:
        provider_id = provider_id or self.get_provider_id()
        return self.get_settings().get("model_cache", {}).get(provider_id, [])

    # ---------------------------------------------------------------- setters

    def set_assistant_enabled(self, enabled: bool) -> None:
        ai_settings = self.get_settings()
        ai_settings["assistant_enabled"] = enabled
        self.set_settings(ai_settings)

    def set_provider_id(self, provider_id: str) -> None:
        ai_settings = self.get_settings()
        ai_settings["provider"] = provider_id
        self.set_settings(ai_settings)

    def set_api_key(self, provider_id: str, api_key: str) -> None:
        self._set("api_keys", provider_id, api_key)

    def set_base_url(self, provider_id: str, base_url: str) -> None:
        self._set("base_urls", provider_id, base_url)

    def set_model(self, provider_id: str, model: str) -> None:
        self._set("models", provider_id, model)

    def set_cached_models(self, provider_id: str, models: list[str]) -> None:
        self._set("model_cache", provider_id, models)

    # ------------------------------------------------------------- providers

    def build_provider(self, provider_id: str = None) -> LLMProvider:
        provider_id = provider_id or self.get_provider_id()
        return get_provider_class(provider_id)(
            api_key=self.get_api_key(provider_id),
            base_url=self.get_base_url(provider_id),
        )

    def get_configured_provider(self) -> tuple[LLMProvider, str]:
        """
        Returns (provider, model), or raises ProviderError with a message that can be shown
        to the user as is.
        """
        provider = self.build_provider()
        provider.check_configured()

        model = self.get_model()
        if not model:
            raise ProviderError(f"No {provider.name} model selected. Pick one in Settings -> AI.")

        return provider, model

    def is_configured(self) -> bool:
        try:
            self.get_configured_provider()
            return True
        except ProviderError:
            return False

    def ask(self, system_prompt: str, user_prompt: str) -> str:
        """Blocking one shot completion - call this from a worker thread, never the main one."""
        provider, model = self.get_configured_provider()
        return provider.generate(system_prompt, user_prompt, model=model)


__all__ = ["AIManager", "PROVIDERS", "ProviderError", "get_provider_class"]

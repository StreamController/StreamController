"""
Settings -> AI: the one place the AI provider is configured for the whole app.

Used by the sidebar assistant and by any plugin that asks `gl.ai_manager` for a provider.
"""

import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib

from loguru import logger as log

from GtkHelper.ComboRow import ComboRow, SimpleComboRowItem
from src.backend.AI.Providers import PROVIDERS, ProviderError, get_provider_class
from src.backend.DeckManagement.HelperMethods import recursive_hasattr

import globals as gl


class AIPage(Adw.PreferencesPage):
    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.set_title("AI")
        self.set_icon_name("starred-symbolic")

        self.add(AIAssistantGroup())
        self.add(AIProviderGroup())


class AIAssistantGroup(Adw.PreferencesGroup):
    """The assistant is opt in - without this switch nothing in the ui offers to ask a model."""

    def __init__(self):
        super().__init__(title="Assistant")

        self.enable_row = Adw.SwitchRow(
            title="AI assistant",
            subtitle="Adds a button to the sidebar that configures the selected key from a "
                     "description. Sends that description, your installed actions and the "
                     "key's current configuration to the provider below.",
            active=gl.ai_manager.get_assistant_enabled(),
        )
        self.enable_row.connect("notify::active", self.on_enabled_changed)
        self.add(self.enable_row)

    def on_enabled_changed(self, *_args) -> None:
        gl.ai_manager.set_assistant_enabled(self.enable_row.get_active())

        if recursive_hasattr(gl, "app.main_win.sidebar.ai_assistant_button"):
            gl.app.main_win.sidebar.ai_assistant_button.update_visibility()


class AIProviderGroup(Adw.PreferencesGroup):
    def __init__(self):
        super().__init__(
            title="AI provider",
            description="Powers the assistant in the sidebar and any plugin that asks for a model.",
        )

        provider_id = gl.ai_manager.get_provider_id()

        self.provider_row = ComboRow(
            title="Provider",
            items=[SimpleComboRowItem(pid, cls.name) for pid, cls in PROVIDERS.items()],
            enable_search=False,
            default_selection=provider_id,
        )
        self.provider_row.connect("notify::selected", self.on_provider_changed)
        self.add(self.provider_row)

        self.api_key_row = Adw.PasswordEntryRow(title="API key", text=gl.ai_manager.get_api_key(provider_id))
        self.api_key_row.connect("changed", self.on_api_key_changed)
        self.add(self.api_key_row)

        self.base_url_row = Adw.EntryRow(title="Server address")
        self.base_url_row.set_text(gl.ai_manager.get_base_url(provider_id)
                                   or get_provider_class(provider_id).default_base_url)
        self.base_url_row.connect("changed", self.on_base_url_changed)
        self.add(self.base_url_row)

        self.model_row = ComboRow(
            title="Model",
            items=self.get_model_items(provider_id),
            enable_search=True,
            default_selection=gl.ai_manager.get_model(provider_id),
        )
        self.model_row.connect("notify::selected", self.on_model_changed)

        refresh_button = Gtk.Button(icon_name="view-refresh-symbolic", valign=Gtk.Align.CENTER,
                                    tooltip_text="Fetch the available models")
        refresh_button.connect("clicked", lambda _: self.refresh_models())
        self.model_row.add_suffix(refresh_button)
        self.add(self.model_row)

        self.status_label = Gtk.Label(label="", wrap=True, xalign=0, margin_top=6,
                                      css_classes=["dim-label", "caption"])
        self.add(self.status_label)

        self.update_row_visibility(provider_id)

    def get_model_items(self, provider_id: str) -> list[str]:
        models = list(gl.ai_manager.get_cached_models(provider_id))
        if not models:
            models = list(get_provider_class(provider_id).fallback_models)

        selected = gl.ai_manager.get_model(provider_id)
        if selected and selected not in models:
            models.insert(0, selected)

        return models

    def update_row_visibility(self, provider_id: str) -> None:
        provider_class = get_provider_class(provider_id)
        self.api_key_row.set_visible(provider_class.needs_api_key)
        self.base_url_row.set_visible(provider_class.needs_base_url)
        self.status_label.set_label(provider_class.settings_hint)

    # ------------------------------------------------------------------ #
    # Signals                                                            #
    # ------------------------------------------------------------------ #

    def on_provider_changed(self, combo_row: ComboRow, _param) -> None:
        item = combo_row.get_selected_item()
        if item is None:
            return

        provider_id = item.get_value()
        gl.ai_manager.set_provider_id(provider_id)

        # Every other row belongs to the provider that was selected before
        self.api_key_row.set_text(gl.ai_manager.get_api_key(provider_id))
        self.base_url_row.set_text(gl.ai_manager.get_base_url(provider_id)
                                   or get_provider_class(provider_id).default_base_url)
        self.model_row.populate(self.model_row.convert_item_list(self.get_model_items(provider_id)),
                                gl.ai_manager.get_model(provider_id))

        self.update_row_visibility(provider_id)

    def on_api_key_changed(self, entry_row: Adw.PasswordEntryRow) -> None:
        gl.ai_manager.set_api_key(gl.ai_manager.get_provider_id(), entry_row.get_text())

    def on_base_url_changed(self, entry_row: Adw.EntryRow) -> None:
        gl.ai_manager.set_base_url(gl.ai_manager.get_provider_id(), entry_row.get_text())

    def on_model_changed(self, combo_row: ComboRow, _param) -> None:
        item = combo_row.get_selected_item()
        if item is None:
            return
        gl.ai_manager.set_model(gl.ai_manager.get_provider_id(), item.get_value())

    # ------------------------------------------------------------------ #
    # Model list                                                         #
    # ------------------------------------------------------------------ #

    def refresh_models(self) -> None:
        provider_id = gl.ai_manager.get_provider_id()

        try:
            provider = gl.ai_manager.build_provider(provider_id)
            provider.check_configured()
        except ProviderError as e:
            self.set_status(str(e), error=True)
            return

        self.set_status(f"Loading models from {provider.name}...")
        threading.Thread(target=self.fetch_models, args=(provider, provider_id),
                         name="ai_settings_models", daemon=True).start()

    def fetch_models(self, provider, provider_id: str) -> None:
        try:
            models = provider.list_models()
        except ProviderError as e:
            GLib.idle_add(self.set_status, str(e), True)
            return
        except Exception as e:
            log.error(f"AI: could not list models: {e}")
            GLib.idle_add(self.set_status, f"Could not list models: {e}", True)
            return

        GLib.idle_add(self.on_models_fetched, provider_id, models)

    def on_models_fetched(self, provider_id: str, models: list[str]) -> None:
        gl.ai_manager.set_cached_models(provider_id, models)

        if not models:
            self.set_status("The provider returned no models.", error=True)
            return False

        # The user may have switched provider while the request was in flight
        if gl.ai_manager.get_provider_id() == provider_id:
            selected = gl.ai_manager.get_model(provider_id)
            self.model_row.populate(self.model_row.convert_item_list(models),
                                    selected if selected in models else models[0])
            gl.ai_manager.set_model(provider_id, self.model_row.get_selected_item().get_value())

        self.set_status(f"{len(models)} models available.")
        return False

    def set_status(self, message: str, error: bool = False) -> None:
        self.status_label.set_label(message)
        self.status_label.set_css_classes(["error", "caption"] if error else ["dim-label", "caption"])
        return False

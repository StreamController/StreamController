"""
The floating assistant button in the sidebar and the little chat behind it.

The user describes what the selected key should do; the model answers with a
configuration spec (see src/backend/AI/InputConfigurator.py) which is applied to the
page. Aimed at people who have not learned yet that "press once to arm, press again to
fire" means two states, a Change State action and a rebound event.
"""

import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, Pango

from loguru import logger as log

from src.backend.AI.InputConfigurator import apply_spec, configure_input, get_required_plugins
from src.backend.AI.PluginInstaller import InstallError, describe as describe_plugin, install as install_plugin
from src.backend.AI.Providers import ProviderError

import globals as gl

_store_docs_thread: threading.Thread | None = None


def fetch_store_docs_once() -> None:
    """
    Pull every plugin's actions.json off GitHub the first time the assistant is opened
    in this session, so it also knows what the user has *not* installed.

    Runs on a worker thread and is cached in memory for the session, so this is a no-op
    after the first open. A failure is not worth bothering the user with - the assistant
    just falls back to the installed actions.
    """
    global _store_docs_thread

    if gl.action_doc_registry is None:
        return
    if gl.action_doc_registry.store_loaded:
        return
    if _store_docs_thread is not None and _store_docs_thread.is_alive():
        return

    def load():
        try:
            gl.action_doc_registry.load_store_docs()
        except Exception as e:
            log.warning(f"Could not load the store's action documentation: {e}")

    _store_docs_thread = threading.Thread(target=load, name="ai_store_docs", daemon=True)
    _store_docs_thread.start()


EXAMPLES = [
    "Mute my microphone while I hold it",
    "Press once to arm it, press again to open Firefox",
    "Show a confirm step before it shuts down my PC",
]


class AIAssistantButton(Gtk.Button):
    """The accent coloured circle floating over the bottom right of the sidebar."""

    def __init__(self, sidebar, **kwargs):
        super().__init__(
            icon_name="starred-symbolic",
            tooltip_text="Configure this button with AI",
            halign=Gtk.Align.END,
            valign=Gtk.Align.END,
            margin_end=18,
            margin_bottom=18,
            css_classes=["suggested-action", "circular", "ai-assistant-fab"],
            **kwargs,
        )
        self.sidebar = sidebar
        self.connect("clicked", self.on_click)

    def on_click(self, _button):
        identifier = self.sidebar.active_identifier
        if identifier is None:
            return

        fetch_store_docs_once()

        dialog = AIAssistantDialog(self.sidebar)
        dialog.present(gl.app.main_win)


class AIAssistantDialog(Adw.Dialog):
    def __init__(self, sidebar):
        super().__init__(title="AI Assistant", content_width=520, content_height=620)
        self.sidebar = sidebar
        self.history: list[dict] = []
        self.busy = False
        self.pending_spec: dict | None = None

        self.build()
        self.show_intro()

    # ------------------------------------------------------------------ #
    # Layout                                                             #
    # ------------------------------------------------------------------ #

    def build(self):
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)

        header = Adw.HeaderBar(show_end_title_buttons=True)
        toolbar_view.add_top_bar(header)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        toolbar_view.set_content(main_box)

        self.scroller = Gtk.ScrolledWindow(vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER)
        main_box.append(self.scroller)

        self.messages_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                                    margin_top=12, margin_bottom=12, margin_start=12, margin_end=12)
        self.scroller.set_child(self.messages_box)

        entry_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8,
                            margin_top=8, margin_bottom=12, margin_start=12, margin_end=12)
        main_box.append(entry_box)

        self.entry = Gtk.Entry(hexpand=True, placeholder_text="What should this button do?")
        self.entry.connect("activate", self.on_send)
        entry_box.append(self.entry)

        self.spinner = Gtk.Spinner(valign=Gtk.Align.CENTER)
        entry_box.append(self.spinner)

        self.send_button = Gtk.Button(icon_name="go-next-symbolic", css_classes=["suggested-action"],
                                      valign=Gtk.Align.CENTER, tooltip_text="Send")
        self.send_button.connect("clicked", self.on_send)
        entry_box.append(self.send_button)

    # ------------------------------------------------------------------ #
    # Messages                                                           #
    # ------------------------------------------------------------------ #

    def add_bubble(self, text: str, from_user: bool = False, error: bool = False) -> Gtk.Widget:
        label = Gtk.Label(label=text, wrap=True, wrap_mode=Pango.WrapMode.WORD_CHAR, xalign=0,
                          selectable=True, margin_top=8, margin_bottom=8, margin_start=12, margin_end=12)

        frame = Gtk.Frame(halign=Gtk.Align.END if from_user else Gtk.Align.START)
        frame.set_child(label)
        frame.add_css_class("ai-bubble-user" if from_user else "ai-bubble-assistant")
        if error:
            frame.add_css_class("error")

        self.messages_box.append(frame)
        self.scroll_to_bottom()
        return frame

    def scroll_to_bottom(self):
        def scroll():
            adjustment = self.scroller.get_vadjustment()
            adjustment.set_value(adjustment.get_upper())
            return False

        GLib.idle_add(scroll)

    def show_intro(self):
        identifier = self.sidebar.active_identifier
        where = "this dial" if identifier is not None and "dial" in str(identifier) else "this button"

        if not gl.ai_manager.is_configured():
            self.add_bubble(
                "No AI provider is set up yet. Open Settings -> AI, pick a provider and a model, "
                "then come back.", error=True)
            self.entry.set_sensitive(False)
            self.send_button.set_sensitive(False)
            return

        self.add_bubble(
            f"Tell me what {where} should do and I will set it up - states, actions and which "
            "press or release triggers what.")

        examples_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, halign=Gtk.Align.START)
        for example in EXAMPLES:
            button = Gtk.Button(label=example, css_classes=["flat", "ai-example"], halign=Gtk.Align.START)
            button.connect("clicked", self.on_example_clicked, example)
            examples_box.append(button)
        self.messages_box.append(examples_box)

    def on_example_clicked(self, _button, example: str):
        self.entry.set_text(example)
        self.on_send(None)

    # ------------------------------------------------------------------ #
    # Asking                                                             #
    # ------------------------------------------------------------------ #

    def on_send(self, _widget):
        if self.busy:
            return

        message = self.entry.get_text().strip()
        if not message:
            return

        identifier = self.sidebar.active_identifier
        page = gl.app.main_win.get_page_for_identifier(identifier) if identifier is not None else None
        if identifier is None or page is None:
            self.add_bubble("Select a key on your deck first, then tell me what it should do.", error=True)
            return

        self.entry.set_text("")
        self.add_bubble(message, from_user=True)
        self.set_busy(True)

        threading.Thread(target=self.ask, args=(message, identifier, page),
                         name="ai_assistant", daemon=True).start()

    def ask(self, message: str, identifier, page):
        try:
            spec = configure_input(message, identifier, page, history=list(self.history))
        except ProviderError as e:
            GLib.idle_add(self.on_failed, str(e))
            return
        except ValueError as e:
            GLib.idle_add(self.on_failed, str(e))
            return
        except Exception as e:
            log.error(f"AI assistant failed: {e}")
            GLib.idle_add(self.on_failed, f"Something went wrong: {e}")
            return

        self.history.append({"role": "user", "content": message})
        GLib.idle_add(self.on_spec_ready, spec, identifier, page)

    def on_spec_ready(self, spec: dict, identifier, page):
        self.set_busy(False)

        summary = spec.get("summary") or "Here is what I came up with."
        self.add_bubble(summary)
        self.history.append({"role": "assistant", "content": summary})

        preview = describe_spec(spec)
        if preview:
            self.add_bubble(preview)

        if not spec.get("states"):
            return False

        self.pending_spec = spec

        required = get_required_plugins(spec)
        if required:
            # Installing means downloading and running third party code, so say exactly
            # which plugin and from where before the user agrees to it
            names = "\n".join(f"  • {describe_plugin(plugin_id)}" for plugin_id in required)
            self.add_bubble(f"This needs a plugin you do not have yet:\n{names}")

        apply_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8, halign=Gtk.Align.START)

        label = "Install and apply" if required else "Apply to this button"
        apply_button = Gtk.Button(label=label, css_classes=["suggested-action"])
        apply_button.connect("clicked", self.on_apply, spec, identifier, page, apply_box, required)
        apply_box.append(apply_button)

        self.messages_box.append(apply_box)
        self.scroll_to_bottom()
        return False

    def on_apply(self, _button, spec: dict, identifier, page, apply_box: Gtk.Widget, required: list):
        apply_box.set_visible(False)

        if not required:
            self.finish_apply(spec, identifier, page)
            return

        self.set_busy(True)
        self.add_bubble(f"Installing {', '.join(required)}...")

        threading.Thread(target=self.install_then_apply, args=(spec, identifier, page, required),
                         name="ai_install", daemon=True).start()

    def install_then_apply(self, spec: dict, identifier, page, required: list):
        for plugin_id in required:
            try:
                install_plugin(plugin_id)
            except InstallError as e:
                GLib.idle_add(self.on_failed, str(e))
                return
            except Exception as e:
                log.error(f"AI assistant: unexpected error installing {plugin_id}: {e}")
                GLib.idle_add(self.on_failed, f"Installing {plugin_id} failed: {e}")
                return

        GLib.idle_add(self.on_installed, spec, identifier, page, required)

    def on_installed(self, spec: dict, identifier, page, required: list):
        self.set_busy(False)
        self.add_bubble(f"Installed {', '.join(required)}.")
        self.finish_apply(spec, identifier, page)
        return False

    def finish_apply(self, spec: dict, identifier, page):
        try:
            apply_spec(spec, identifier, page)
        except Exception as e:
            log.error(f"Could not apply the AI configuration: {e}")
            self.add_bubble(f"Could not apply that: {e}", error=True)
            return

        self.add_bubble("Applied. Try it on your deck - tell me what to change if it is not right.")

        # Rebuild the sidebar so the new states and actions show up
        self.sidebar.load_for_identifier(identifier, 0)

    def on_failed(self, message: str):
        self.set_busy(False)
        self.add_bubble(message, error=True)
        return False

    def set_busy(self, busy: bool):
        self.busy = busy
        self.entry.set_sensitive(not busy)
        self.send_button.set_sensitive(not busy)
        if busy:
            self.spinner.start()
        else:
            self.spinner.stop()


def describe_spec(spec: dict) -> str:
    """A plain reading of the spec, so the user can check it before applying."""
    lines = []

    for index, state in enumerate(spec.get("states", [])):
        label = (state.get("labels") or {}).get("center", "")
        heading = f"State {index}" + (f' - "{label}"' if label else "")
        lines.append(heading)

        actions = state.get("actions", [])
        if not actions:
            lines.append("    does nothing")

        for action in actions:
            trigger = action.get("trigger", "key_down").replace("_", " ")
            name = action.get("id", "").split("::")[-1]
            settings = action.get("settings") or {}
            detail = ", ".join(f"{k}={v}" for k, v in settings.items())
            lines.append(f"    on {trigger}: {name}" + (f" ({detail})" if detail else ""))

    return "\n".join(lines)

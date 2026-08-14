"""
Turns a plain language wish ("press once to arm it, press again to launch Firefox")
into a configured key or dial.

The model never touches the app directly. It answers with a small JSON spec describing
the states, the actions in each state and which event triggers each action; `apply_spec`
is the only thing that writes to the page, going through the same calls the sidebar UI
uses so live objects, json and ui stay in sync.
"""

import json
import re

from loguru import logger as log

import globals as gl
from src.backend.DeckManagement.HelperMethods import add_default_keys
from src.backend.DeckManagement.InputIdentifier import Input, InputIdentifier

# Trigger names the model may use -> the real InputEvent per input type.
# Keeping the names generic means the model does not have to know that a dial press is
# "Dial Down" while a key press is "Key Down".
TRIGGERS: dict[str, dict[type, object]] = {
    "key_down": {Input.Key: Input.Key.Events.DOWN, Input.Dial: Input.Dial.Events.DOWN},
    "key_up": {Input.Key: Input.Key.Events.UP, Input.Dial: Input.Dial.Events.UP},
    "short_up": {Input.Key: Input.Key.Events.SHORT_UP, Input.Dial: Input.Dial.Events.SHORT_UP},
    "hold_start": {Input.Key: Input.Key.Events.HOLD_START, Input.Dial: Input.Dial.Events.HOLD_START},
    "hold_stop": {Input.Key: Input.Key.Events.HOLD_STOP, Input.Dial: Input.Dial.Events.HOLD_STOP},
    "dial_cw": {Input.Dial: Input.Dial.Events.TURN_CW},
    "dial_ccw": {Input.Dial: Input.Dial.Events.TURN_CCW},
    "touch_short": {Input.Dial: Input.Dial.Events.SHORT_TOUCH_PRESS},
    "touch_long": {Input.Dial: Input.Dial.Events.LONG_TOUCH_PRESS},
}

KEY_TRIGGERS = ["key_down", "key_up", "short_up", "hold_start", "hold_stop"]
DIAL_TRIGGERS = KEY_TRIGGERS + ["dial_cw", "dial_ccw", "touch_short", "touch_long"]

LABEL_POSITIONS = ("top", "center", "bottom")

# Only these plugins are offered for now. An action can only be configured well when its
# settings are documented, and that is being rolled out plugin by plugin.
ALLOWED_PLUGIN_PREFIXES = ("com_core447_",)

# Colors the model may name instead of spelling out rgba
NAMED_COLORS: dict[str, list[int]] = {
    "red": [200, 40, 40, 255],
    "green": [40, 160, 60, 255],
    "blue": [40, 90, 200, 255],
    "yellow": [220, 190, 40, 255],
    "orange": [220, 130, 40, 255],
    "purple": [140, 70, 190, 255],
    "pink": [220, 100, 170, 255],
    "cyan": [40, 180, 200, 255],
    "white": [255, 255, 255, 255],
    "black": [0, 0, 0, 255],
    "grey": [120, 120, 120, 255],
    "gray": [120, 120, 120, 255],
    "none": [0, 0, 0, 0],
    "transparent": [0, 0, 0, 0],
}

# Fallback documentation for actions that have not been given a settings_schema yet.
# Anything an action documents itself (ActionHolder(description=..., settings_schema=...))
# wins over this.
KNOWN_SETTINGS: dict[str, str] = {
    "com_core447_DeckPlugin::ChangeState":
        '{"state": <0 based state index>, "return_timeout": 0} '
        '- switches this input to another state. This is how a button changes what it does.',
    "com_core447_DeckPlugin::ChangePage":
        '{"selected_page": "<page name>"} - switches the deck to another page.',
    "com_core447_OSPlugin::EasyCommand":
        '{"command": "<shell command>"} - the way to start an app: {"command": "firefox"}.',
    "com_core447_OSPlugin::RunCommand":
        '{"command": "<shell command>", "detached": true} '
        '- only when you need output on the key or a repeat timer.',
    "com_core447_OSPlugin::OpenInBrowser":
        '{"url": "https://example.com", "new_window": false}',
    "com_core447_OSPlugin::EasyHotkey":
        '{"hotkey": "ctrl+shift+m", "delay": 0.02} - presses a key combination.',
    "com_core447_OSPlugin::Delay":
        '{"delay": 1.0} - waits before the next action on the same event runs.',
    "com_core447_OSPlugin::WriteText":
        '{"text": "<text to type>"}',
}


SYSTEM_PROMPT = r'''
You configure a single button (or dial) on an Elgato Stream Deck for a user of
StreamController, a Linux app for driving those decks.

The user tells you in plain language what the button should do. You answer with a JSON
spec describing the finished button. The app applies your spec - you never write code.

Many of these users have never configured a deck before. Read their wish generously and
produce a button that works end to end, including the parts they did not spell out
(a way back out of a state, a label so they can see what the button is doing).

A button is more than its actions. Its background colour, its labels and its icon are
part of the configuration and need no action at all - "make it red" is a complete,
valid request that you fulfil with a background and no actions whatsoever.

================================================================================
OUTPUT FORMAT
================================================================================

Answer with ONE JSON object and nothing else. No markdown fences, no prose.

{
  "summary": "One short sentence, addressed to the user, describing what you built.",
  "states": [
    {
      "background": "red",
      "labels": {"center": "Safety"},
      "media": {"path": "/path/to/icon.png", "size": 0.8},
      "actions": [
        {
          "id": "<action id from the catalog below>",
          "settings": { ... },
          "trigger": "key_down"
        }
      ]
    }
  ]
}

Every field of a state is optional. Send only what the user asked you to change - a
state you send with just a "background" keeps its existing labels, icon and actions.

* "states" is the full, final list of states, in order. State 0 is the resting state the
  button shows by default. Two entries means the button gets two states. Send exactly
  one entry when the user did not ask for a multi step button.
* "background" is the key's colour behind everything else. Either a colour name
  (red, green, blue, yellow, orange, purple, pink, cyan, white, black, grey, none),
  a hex string ("#c82828"), or [r, g, b, a] with 0-255 components. "none" clears it.
* "labels" holds up to three rows: "top", "center", "bottom". Give a plain string for
  just text, or an object for more control:
      {"center": "Safety"}
      {"center": {"text": "Safety", "color": "white", "font-size": 18}}
  "" clears a row. Most buttons only need "center".
* "media" is the icon: {"path": "<absolute file path>"} plus optional "size" (0.0-1.0),
  "valign" and "halign" (-1.0 to 1.0). Only ever use a path the user gave you - you
  cannot browse their files. Leave "media" out if they did not mention an icon.
  {"path": ""} removes the current icon.
* "actions" is the full list of actions for that state, in the order they should run.
  Send [] to explicitly remove every action from a state.
* "settings" may be omitted or {} if the action needs no configuration.
* "trigger" says which physical event runs the action. If you leave it out the action
  runs on key_down.

If the request needs an action that is not in the catalog, still answer with valid JSON:
do whatever part you can (colours and labels always work) and use the "summary" to say
plainly what you could not do and what the user would have to install.

================================================================================
STATES - the key idea
================================================================================

A button has one or more states. Only one state is shown at a time: its own label, its
own icon, its own actions. The "Change State" action is what moves between them, and it
is how you build a button that does something different the second time it is pressed.

The user's classic example, spelled out:

  "By default it says Safety. Pressed once it becomes Ready. Pressed again it opens
   Firefox, and when I let go it opens Nautilus."

  State 0, label "Safety"  -> Change State to 1 on key_down
  State 1, label "Ready"   -> Easy Run Command "firefox" on key_down
                              Easy Run Command "nautilus" on key_up
                              Change State to 0 on key_up

  Note the last one: without a way back the button would be stuck in "Ready" forever.
  Always give a multi state button a way home unless the user says otherwise.

State indexes are 0 based, and "Change State" takes the target index in its "state"
setting. Do not create a state you never switch to.

================================================================================
TRIGGERS
================================================================================

key_down is the normal answer. Nearly every action is written to do its work when the
key goes down, so unless the user asked for something to happen on release or on hold,
use key_down and do not think about it further.

Whatever you pick becomes the action's only trigger: the app clears every other event for
that action, so exactly one event fires it.

key_down    the moment the key is pressed. The default, and what "when I press it" means.
key_up      the moment it is released. This is "when I let go" / "when released".
short_up    released without having been held. Fires in addition to key_up.
hold_start  the key has been held down for about a second. "when I hold it".
hold_stop   a held key was released.
dial_cw     dial turned clockwise (Stream Deck + only).
dial_ccw    dial turned counter clockwise.
touch_short a tap on the touch strip above a dial.
touch_long  a long press on the touch strip.

Several actions may share a trigger - they run top to bottom, in list order.

================================================================================
RULES
================================================================================

1. Not everything needs an action. Background colour, labels and the icon are set
   directly on the state. "Make it red" is one state with a background and no actions -
   never answer that something is impossible because there is no action for it.
2. Only use action ids from the catalog below, exactly as written. Never invent one.
3. Only use settings keys documented for that action. If an action is in the catalog
   without documented settings, give it {} and mention in the summary that the user
   still has to configure it.
4. To start an app or run a command, use "Easy Run Command" with a plain command name
   ("firefox", "nautilus", "code"). It needs no path and nothing else configured. Only
   reach for "Run Command" when the user wants one of its extras - showing the output on
   the key, re-running it on a timer, or an interactive shell.
5. Give every state a label unless the user asked for icons only. The label is what makes
   a multi state button understandable at a glance.
6. Keep it minimal. Do not add actions the user did not ask for - except the way back out
   of a state, which is part of making the request work.
7. The summary is read by a beginner. Say what the button now does, not which json you
   produced. One sentence.
'''.strip()


def _input_type_name(identifier: InputIdentifier) -> str:
    if isinstance(identifier, Input.Dial):
        return "dial"
    if isinstance(identifier, Input.Touchscreen):
        return "touchscreen"
    if isinstance(identifier, Input.Screen):
        return "screen"
    return "key"


def build_action_catalog(identifier: InputIdentifier) -> str:
    """
    The list of actions actually installed on this machine, so the model can only pick
    something the user really has.

    Documentation for an action comes from, in order:
      1. the plugin's actions.json  (see src/backend/AI/ActionDocs.py)
      2. description/requirements/settings_schema passed to its ActionHolder
      3. the curated KNOWN_SETTINGS fallback in this file
    An action with none of those is still listed - the model can place it, it just has to
    leave the settings empty and say so.
    """
    from src.backend.PluginManager.ActionInputSupport import ActionInputSupport

    lines: list[str] = []
    for action_id, holder in sorted(gl.plugin_manager.action_index.items()):
        if not hasattr(holder, "action_name"):
            continue
        if not action_id.startswith(ALLOWED_PLUGIN_PREFIXES):
            continue
        if holder.get_input_compatibility(identifier) == ActionInputSupport.UNSUPPORTED:
            continue

        plugin_name = getattr(holder.plugin_base, "plugin_name", "") or ""
        line = f'  {action_id}  ("{holder.action_name}"'
        if plugin_name:
            line += f", from {plugin_name}"
        line += ")"

        documentation = _get_action_documentation(action_id, holder)
        if documentation:
            line += "\n" + documentation

        lines.append(line)

    return "\n".join(lines)


def build_uninstalled_catalog() -> str:
    """
    Actions from the store the user does not have, so the assistant can say "that needs
    the OBS plugin" instead of "there is no action for that".
    """
    registry = gl.action_doc_registry
    if registry is None or not registry.store_loaded:
        return ""

    installed = set(gl.plugin_manager.get_plugins().keys()) if gl.plugin_manager else set()

    lines: list[str] = []
    for plugin_id, docs in sorted(registry.get_uninstalled(installed).items()):
        if not plugin_id.startswith(ALLOWED_PLUGIN_PREFIXES):
            continue

        plugin_doc = registry.store_plugins.get(plugin_id, {})
        heading = f"  {plugin_id}"
        if plugin_doc.get("description"):
            heading += f" - {plugin_doc['description']}"
        lines.append(heading)

        for doc in sorted(docs, key=lambda d: d.action_id):
            summary = doc.description or ""
            lines.append(f"      {doc.action_id}: {summary}")

    return "\n".join(lines)


def _get_action_documentation(action_id: str, holder) -> str:
    doc = gl.action_doc_registry.get(action_id) if gl.action_doc_registry else None
    if doc:
        rendered = doc.render()
        if rendered:
            return rendered

    if hasattr(holder, "get_ai_documentation"):
        rendered = holder.get_ai_documentation()
        if rendered:
            return rendered

    if action_id in KNOWN_SETTINGS:
        return f"      settings: {KNOWN_SETTINGS[action_id]}"

    return ""


def describe_current_config(identifier: InputIdentifier, page) -> str:
    """What the button looks like right now, so follow up messages can refine it."""
    input_dict = identifier.get_config(page) or {}
    states = input_dict.get("states", {})

    if not states:
        return "The button is currently empty."

    lines = []
    for state_key in sorted(states, key=lambda k: int(k)):
        state_dict = states[state_key]
        labels = {pos: cfg.get("text", "") for pos, cfg in state_dict.get("labels", {}).items()}
        lines.append(f"  State {state_key}: labels={labels or '{}'}")

        for action in state_dict.get("actions", []):
            events = action.get("event-assignments", {})
            lines.append(f"    - {action.get('id')} settings={action.get('settings', {})} events={events}")

    return "\n".join(lines)


def build_user_prompt(message: str, identifier: InputIdentifier, page, history: list[dict] = None) -> str:
    input_type = _input_type_name(identifier)
    triggers = DIAL_TRIGGERS if input_type == "dial" else KEY_TRIGGERS

    parts = [
        "AVAILABLE ACTIONS ON THIS MACHINE:",
        build_action_catalog(identifier),
    ]

    not_installed = build_uninstalled_catalog()
    if not_installed:
        parts += [
            "",
            "NOT INSTALLED - available in the store:",
            not_installed,
            "",
            "You may use these. If one of them is the right answer, use it exactly as you "
            "would an installed action - the user is offered a button that installs the "
            "plugin and then applies your configuration. Say in your summary which plugin "
            "gets installed. Do not use one of these when an installed action does the job.",
        ]

    parts += [
        "",
        f"THIS INPUT IS A {input_type.upper()}.",
        f"Usable triggers: {', '.join(triggers)}",
        "",
        "CURRENT CONFIGURATION:",
        describe_current_config(identifier, page),
    ]

    if history:
        parts += ["", "EARLIER IN THIS CONVERSATION:"]
        for entry in history:
            parts.append(f"  {entry['role']}: {entry['content']}")
        parts.append("")
        parts.append("The user is refining what you already built - keep what still fits.")

    parts += [
        "",
        "WHAT THE USER WANTS:",
        message.strip(),
        "",
        "Answer with the JSON spec only.",
    ]

    return "\n".join(parts)


_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def parse_spec(answer: str) -> dict:
    """Pulls the JSON object out of the answer and checks it is shaped like a spec."""
    text = (answer or "").strip()

    match = _FENCE_RE.search(text)
    if match:
        text = match.group(1).strip()
    elif not text.startswith("{"):
        # Some models still wrap the object in a sentence
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise ValueError("The model did not answer with a configuration.")
        text = text[start:end + 1]

    try:
        spec = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"The model's answer was not valid JSON: {e}") from e

    if not isinstance(spec, dict):
        raise ValueError("The model's answer was not a configuration object.")

    states = spec.get("states")
    if states is None or not isinstance(states, list):
        raise ValueError("The model's answer had no states.")

    for state in states:
        if not isinstance(state, dict):
            raise ValueError("A state in the model's answer was not an object.")
        for action in state.get("actions", []):
            if not isinstance(action, dict) or not action.get("id"):
                raise ValueError("An action in the model's answer had no id.")

    return spec


def get_required_plugins(spec: dict) -> list[str]:
    """
    Plugins the spec needs but the user does not have.

    Taken from the action ids themselves rather than trusting the model's own
    "install_plugins" list, so we can only ever offer to install something an action in
    this spec actually needs.
    """
    installed = set(gl.plugin_manager.get_plugins().keys()) if gl.plugin_manager else set()
    registry = gl.action_doc_registry

    required: list[str] = []
    for state in spec.get("states", []):
        for action in state.get("actions", []):
            action_id = action.get("id") or ""
            if action_id in gl.plugin_manager.action_index:
                continue

            plugin_id = action_id.split("::")[0]
            if not plugin_id or plugin_id in installed or plugin_id in required:
                continue

            # Only offer plugins we actually know from the store
            if registry is not None and plugin_id in registry.store_plugins:
                required.append(plugin_id)

    return required


def validate_against_catalog(spec: dict, identifier: InputIdentifier) -> list[str]:
    """
    Returns a list of problems - unknown action ids and triggers this input cannot fire.

    An action from a plugin that can be installed from the store is not a problem: the
    assistant offers the install and applies afterwards.
    """
    problems = []
    allowed_triggers = DIAL_TRIGGERS if isinstance(identifier, Input.Dial) else KEY_TRIGGERS
    installable = set(get_required_plugins(spec))

    for index, state in enumerate(spec.get("states", [])):
        for action in state.get("actions", []):
            action_id = action.get("id") or ""
            if action_id not in gl.plugin_manager.action_index:
                if action_id.split("::")[0] not in installable:
                    problems.append(f"State {index}: '{action_id}' is not installed.")

            trigger = action.get("trigger", "key_down")
            if trigger not in allowed_triggers:
                problems.append(f"State {index}: '{trigger}' is not available on this input.")

    return problems


def apply_spec(spec: dict, identifier: InputIdentifier, page) -> str:
    """
    Writes the spec into the page and reloads everything that has to notice.

    Must run on the main thread - it reloads pages and touches the ui.
    Returns the summary to show the user.
    """
    states_spec = spec.get("states", [])
    if not states_spec:
        return spec.get("summary", "Nothing to change.")

    # Bring the live input to the right number of states first, the way the state switcher
    # does it. Creating the action objects before the states exist leaves them without a
    # state to draw on.
    _match_state_count(identifier, page, len(states_spec))

    add_default_keys(page.dict, [identifier.input_type, identifier.json_identifier, "states"])
    input_dict = page.dict[identifier.input_type][identifier.json_identifier]
    states_dict = input_dict.setdefault("states", {})

    # Write the states, keeping anything we were not told about
    for index, state_spec in enumerate(states_spec):
        state_dict = states_dict.setdefault(str(index), {})

        # "actions" missing means "leave them alone"; [] means "remove them all"
        if state_spec.get("actions") is not None:
            state_dict["actions"] = [
                {"id": action["id"], "settings": action.get("settings", {}) or {}}
                for action in state_spec["actions"]
            ]

        state_dict.setdefault("actions", [])
        state_dict.setdefault("image-control-action", 0)
        state_dict.setdefault("label-control-actions", [0, 0, 0])
        state_dict.setdefault("background-control-action", 0)

        _apply_labels(state_dict, state_spec.get("labels"))
        _apply_background(state_dict, state_spec.get("background"))
        _apply_media(state_dict, state_spec.get("media"))

    # Drop states the spec does not have any more
    for state_key in list(states_dict.keys()):
        if int(state_key) >= len(states_spec):
            del states_dict[state_key]

    page.save()
    page.load()
    page.reload_similar_pages(identifier=identifier, reload_self=True)

    _apply_triggers(spec, identifier, page)

    page.save()
    page.reload_similar_pages(identifier=identifier, reload_self=True)

    return spec.get("summary", "Done.")


def parse_color(value) -> list[int] | None:
    """Accepts "red", "#c82828", "#c82828ff" or [r, g, b(, a)]."""
    if value is None:
        return None

    if isinstance(value, dict):
        return parse_color(value.get("color"))

    if isinstance(value, (list, tuple)):
        components = [int(max(0, min(255, c))) for c in value[:4]]
        while len(components) < 4:
            components.append(255)
        return components

    if isinstance(value, str):
        text = value.strip().lower()
        if text in NAMED_COLORS:
            return list(NAMED_COLORS[text])

        hex_text = text.lstrip("#")
        if len(hex_text) in (6, 8) and all(c in "0123456789abcdef" for c in hex_text):
            components = [int(hex_text[i:i + 2], 16) for i in range(0, len(hex_text), 2)]
            if len(components) == 3:
                components.append(255)
            return components

    return None


def _apply_labels(state_dict: dict, labels) -> None:
    if not labels or not isinstance(labels, dict):
        return

    label_dict = state_dict.setdefault("labels", {})

    for position, value in labels.items():
        if position not in LABEL_POSITIONS:
            continue

        entry = label_dict.setdefault(position, {})

        if isinstance(value, dict):
            if "text" in value:
                entry["text"] = str(value["text"])
            if "color" in value:
                color = parse_color(value["color"])
                if color:
                    entry["color"] = color
            for key in ("font-size", "font-family", "font-weight", "style", "alignment"):
                if key in value:
                    entry[key] = value[key]
        else:
            entry["text"] = str(value)


def _apply_background(state_dict: dict, background) -> None:
    if background is None:
        return

    color = parse_color(background)
    if color is None:
        return

    state_dict.setdefault("background", {})["color"] = color


def _apply_media(state_dict: dict, media) -> None:
    if media is None:
        return

    if isinstance(media, str):
        media = {"path": media}
    if not isinstance(media, dict):
        return

    media_dict = state_dict.setdefault("media", {})

    if "path" in media:
        path = media["path"]
        # An empty path is how the model removes the icon again
        media_dict["path"] = str(path) if path else None

    for key in ("size", "valign", "halign", "fill-mode", "loop", "fps"):
        if key in media:
            media_dict[key] = media[key]


def _match_state_count(identifier: InputIdentifier, page, wanted: int) -> None:
    controller_input = page.deck_controller.get_input(identifier)
    if controller_input is None or not controller_input.enable_states:
        return

    while len(controller_input.states) < wanted:
        controller_input.add_new_state(switch=False)

    while len(controller_input.states) > wanted:
        controller_input.remove_state(max(controller_input.states.keys()))


def _apply_triggers(spec: dict, identifier: InputIdentifier, page) -> None:
    """
    Binds each action to the event the spec asked for.

    The model names triggers generically ("key_up"); an action names its callbacks with
    its own event assigner ids. We pick the assigner that would normally handle this kind
    of interaction and move it onto the requested event.
    """
    for state_index, state_spec in enumerate(spec.get("states", [])):
        actions = page.get_all_actions_for_input(identifier, state_index, only_action_cores=True)

        for action_index, action_spec in enumerate(state_spec.get("actions", [])):
            if action_index >= len(actions):
                break

            action = actions[action_index]
            trigger = action_spec.get("trigger", "key_down")
            event = TRIGGERS.get(trigger, {}).get(type(identifier))
            if event is None:
                continue

            assigner = _pick_assigner(action, identifier, event)
            if assigner is None:
                continue

            # Null every event first, then bind the one we want. An action left on its
            # defaults would also fire on those, and the page json is far easier to read
            # when exactly one event is assigned and the rest say null.
            action.set_all_events_to_null()
            action.set_event_assignment(event, assigner)


# The event that carries an action's actual behaviour
PRESS_EVENTS = {
    Input.Key: Input.Key.Events.DOWN,
    Input.TouchKey: Input.TouchKey.Events.DOWN,
    Input.Dial: Input.Dial.Events.DOWN,
}


def _pick_assigner(action, identifier, event):
    """
    Which of the action's callbacks should run on the requested event.

    Actions written against the old ActionBase register one assigner per event, but only
    the press one actually does anything - `on_key_down` is where a Run Command action
    runs its command, and it has an empty `on_key_up`. So "open Nautilus when I let go"
    means moving the *press* assigner onto Key Up, not binding the release assigner that
    does nothing.
    """
    assigners = action.event_manager.get_all_event_assigners()
    if not assigners:
        return None
    if len(assigners) == 1:
        return assigners[0]

    press_event = PRESS_EVENTS.get(type(identifier))
    for assigner in assigners:
        if press_event is not None and press_event in assigner.default_events:
            return assigner

    # Nothing press-like (a turn-only action, say) - take whatever handles the target event
    for assigner in assigners:
        if event in assigner.default_events:
            return assigner

    return assigners[0]


def configure_input(message: str, identifier: InputIdentifier, page, history: list[dict] = None) -> dict:
    """
    Asks the model and returns the parsed spec. Blocking - call from a worker thread.
    """
    user_prompt = build_user_prompt(message, identifier, page, history)
    answer = gl.ai_manager.ask(SYSTEM_PROMPT, user_prompt)

    log.debug(f"AI assistant answer: {answer[:2000]}")

    spec = parse_spec(answer)

    problems = validate_against_catalog(spec, identifier)
    if problems:
        raise ValueError("The suggested configuration cannot be applied:\n" + "\n".join(problems))

    return spec

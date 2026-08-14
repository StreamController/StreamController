# `actions.json` - telling the AI assistant what your plugin can do

The AI assistant in the sidebar configures a key from a plain language description. To do
that it needs to know which actions exist and, crucially, **how their settings json is
shaped** - something it cannot work out from the code, because `get_config_rows()` builds
arbitrary widgets and writes whatever keys it likes.

So a plugin describes itself in one file at the root of its repo, next to `manifest.json`:

```
my-plugin/
├── manifest.json
├── actions.json      <- this file
└── main.py
```

It is optional. A plugin without it still works, and its actions are still offered - the
assistant just has to place them with empty settings and tell the user to configure them
by hand.

## Format

```json
{
    "plugin": {
        "description": "Control OBS Studio from your deck.",
        "requirements": "OBS with obs-websocket 5 enabled."
    },
    "actions": {
        "StartRecording": {
            "description": "Starts recording in OBS. Shows whether it is recording on the key.",
            "requirements": "OBS has to be running and the plugin connected.",
            "settings": {
                "confirm": {
                    "type": "boolean",
                    "default": false,
                    "description": "Ask before starting."
                }
            }
        }
    }
}
```

### `plugin`

| Field | Meaning |
| --- | --- |
| `description` | One or two sentences: what the plugin is for. |
| `requirements` | What the user needs for it to work at all - a running program, a daemon, a permission. Inherited by every action that does not state its own. |

### `actions`

Keyed by the action's id. Either the bare suffix (`"StartRecording"`) or the full id
(`"com_core447_OBSPlugin::StartRecording"`) - the bare form gets your plugin id prefixed
automatically.

| Field | Meaning |
| --- | --- |
| `description` | What the action does, in the terms a user would describe it. Mention when it draws on the key by itself, or when it is meant to pair with another action. |
| `requirements` | Anything beyond the plugin's own requirements. |
| `settings` | The keys this action reads out of its settings json. |

### `settings`

Each key maps to a description string, or to an object with whichever of these you can
usefully fill in:

| Field | Meaning |
| --- | --- |
| `type` | `string`, `integer`, `number`, `boolean`, `object`, `array` |
| `description` | What it controls. |
| `required` | `true` if the action does nothing without it. |
| `default` | What the action assumes when the key is absent. |
| `values` | The allowed values, if it is a fixed set. |
| `example` | A realistic value. This is the single most useful field - the assistant copies the shape of your example. |

The keys and defaults must match what the action actually reads. If your action does
`settings.get("command")`, the schema key is `command`.

## What good documentation looks like

Write for someone who has never seen your plugin. Two things pay off most:

- **An `example` on every setting that takes free text.** `"example": "firefox"` teaches
  more than three sentences of prose.
- **Saying how actions combine.** "Put this on state 0 pointing at state 1, and one on
  state 1 pointing back" is what turns a list of actions into a working button.

## The Python alternative

If you would rather keep it next to the code, `ActionHolder` takes the same information:

```python
ActionHolder(
    plugin_base=self,
    action_core=RunCommand,
    action_id_suffix="RunCommand",
    action_name="Run Command",
    description="Runs a shell command.",
    requirements="The command has to exist on the host.",
    settings_schema={
        "command": {"type": "string", "required": True, "example": "firefox"},
    },
)
```

`actions.json` wins when both are present, because it can also be read without importing
the plugin - which is what lets the assistant know about actions the user has not
installed yet.

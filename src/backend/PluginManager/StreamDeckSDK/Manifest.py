"""
Author: Core447
Year: 2025

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This programm comes with ABSOLUTELY NO WARRANTY!

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
import json
import os

from dataclasses import dataclass, field

from loguru import logger as log


def _get(d: dict, *names, default=None):
    """
    Elgato manifests use PascalCase keys, some third party tooling emits camelCase.
    Look the key up in a case insensitive way so both work.
    """
    for name in names:
        if name in d:
            return d[name]
    lowered = {str(k).lower(): v for k, v in d.items()}
    for name in names:
        if name.lower() in lowered:
            return lowered[name.lower()]
    return default


def resolve_icon_path(path_without_extension: str) -> str | None:
    """
    Icons are referenced without their file extension in the manifest. Resolve to the
    file that actually exists, preferring vector over the high dpi raster variant.
    """
    if not path_without_extension:
        return None

    if os.path.isfile(path_without_extension):
        return path_without_extension

    for suffix in (".svg", "@2x.png", ".png", "@2x.jpg", ".jpg", ".gif"):
        candidate = path_without_extension + suffix
        if os.path.isfile(candidate):
            return candidate

    return None


@dataclass
class SDActionState:
    """A single state of an action as declared in the manifest."""
    image: str = ""
    multi_action_image: str = ""
    name: str = ""
    title: str = ""
    show_title: bool = True
    title_color: str = "#FFFFFF"
    title_alignment: str = "middle"
    font_family: str = ""
    font_style: str = ""
    font_size: int = 16
    font_underline: bool = False

    @classmethod
    def from_dict(cls, d: dict) -> "SDActionState":
        font_size = _get(d, "FontSize", default=16)
        try:
            font_size = int(font_size)
        except (TypeError, ValueError):
            font_size = 16

        return cls(
            image=_get(d, "Image", default="") or "",
            multi_action_image=_get(d, "MultiActionImage", default="") or "",
            name=_get(d, "Name", default="") or "",
            title=_get(d, "Title", default="") or "",
            show_title=bool(_get(d, "ShowTitle", default=True)),
            title_color=_get(d, "TitleColor", default="#FFFFFF") or "#FFFFFF",
            title_alignment=(_get(d, "TitleAlignment", default="middle") or "middle").lower(),
            font_family=_get(d, "FontFamily", default="") or "",
            font_style=_get(d, "FontStyle", default="") or "",
            font_size=font_size,
            font_underline=bool(_get(d, "FontUnderline", default=False)),
        )


@dataclass
class SDEncoder:
    """The encoder (dial) section of an action."""
    icon: str = ""
    background: str = ""
    stack_color: str = ""
    layout: str = "$X1"
    trigger_description: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict) -> "SDEncoder":
        return cls(
            icon=_get(d, "Icon", default="") or "",
            background=_get(d, "background", "Background", default="") or "",
            stack_color=_get(d, "StackColor", default="") or "",
            layout=_get(d, "layout", "Layout", default="$X1") or "$X1",
            trigger_description=_get(d, "TriggerDescription", default={}) or {},
        )


@dataclass
class SDAction:
    """An action as declared in the manifest."""
    uuid: str
    name: str
    icon: str = ""
    tooltip: str = ""
    property_inspector_path: str = ""
    states: list[SDActionState] = field(default_factory=list)
    controllers: list[str] = field(default_factory=lambda: ["Keypad"])
    encoder: SDEncoder | None = None
    supported_in_multi_actions: bool = True
    visible_in_action_list: bool = True
    disable_automatic_states: bool = False
    user_title_enabled: bool = True

    # Filled in by the plugin once the manifest has been read
    plugin_uuid: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "SDAction | None":
        uuid = _get(d, "UUID", default=None)
        if not uuid:
            return None

        states = [SDActionState.from_dict(s) for s in _get(d, "States", default=[]) or []]
        if not states:
            states = [SDActionState()]

        encoder_dict = _get(d, "Encoder", default=None)

        return cls(
            uuid=uuid,
            name=_get(d, "Name", default=uuid) or uuid,
            icon=_get(d, "Icon", default="") or "",
            tooltip=_get(d, "Tooltip", default="") or "",
            property_inspector_path=_get(d, "PropertyInspectorPath", default="") or "",
            states=states,
            controllers=_get(d, "Controllers", default=None) or ["Keypad"],
            encoder=SDEncoder.from_dict(encoder_dict) if isinstance(encoder_dict, dict) else None,
            supported_in_multi_actions=bool(_get(d, "SupportedInMultiActions", default=True)),
            visible_in_action_list=bool(_get(d, "VisibleInActionsList", default=True)),
            disable_automatic_states=bool(_get(d, "DisableAutomaticStates", default=False)),
            user_title_enabled=bool(_get(d, "UserTitleEnabled", default=True)),
        )

    def supports_keypad(self) -> bool:
        return any(c.lower() == "keypad" for c in self.controllers)

    def supports_encoder(self) -> bool:
        return any(c.lower() == "encoder" for c in self.controllers)


@dataclass
class SDManifest:
    """A parsed Stream Deck SDK plugin manifest."""
    path: str
    uuid: str
    name: str
    author: str = ""
    version: str = "0.0.0"
    description: str = ""
    url: str = ""
    icon: str = ""
    category: str = ""
    category_icon: str = ""
    sdk_version: int = 2
    software_minimum_version: str = ""
    os: list[dict] = field(default_factory=list)
    code_path: str = ""
    code_path_win: str = ""
    code_path_mac: str = ""
    code_path_lin: str = ""
    code_paths: dict = field(default_factory=dict)
    property_inspector_path: str = ""
    applications_to_monitor: dict = field(default_factory=dict)
    actions: list[SDAction] = field(default_factory=list)
    nodejs: dict = field(default_factory=dict)

    def get_icon_path(self) -> str | None:
        return resolve_icon_path(os.path.join(self.path, self.icon)) if self.icon else None

    def get_platforms(self) -> list[str]:
        platforms = []
        for entry in self.os:
            if isinstance(entry, dict):
                platform = _get(entry, "Platform", default=None)
            else:
                platform = entry
            if platform:
                platforms.append(str(platform).lower())
        return platforms


# Plugins sold through the Elgato Marketplace can ship an encrypted manifest, which
# starts with this magic. Only Elgato's own software can read those.
ENCRYPTED_MAGIC = b"ELGATO"


class EncryptedManifestError(ValueError):
    """Raised for manifests in Elgato's encrypted package format."""


def _load_manifest_json(manifest_path: str) -> dict:
    with open(manifest_path, "rb") as f:
        raw = f.read()

    if raw.startswith(ENCRYPTED_MAGIC):
        raise EncryptedManifestError(
            "this plugin is distributed in Elgato's encrypted package format, which "
            "only Elgato's own software can read"
        )

    text = None
    for encoding in ("utf-8-sig", "utf-16", "cp1252"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue

    if text is None:
        raise ValueError(f"{manifest_path} is not text in any encoding we understand")

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"failed to parse {os.path.basename(manifest_path)}: {e}") from e


def read_manifest(plugin_path: str) -> SDManifest:
    """
    Read and parse the manifest of the .sdPlugin directory at ``plugin_path``.

    Raises:
        FileNotFoundError: If the directory has no manifest.
        EncryptedManifestError: If the manifest is in Elgato's encrypted format.
        ValueError: If the manifest cannot be parsed.
    """
    manifest_path = os.path.join(plugin_path, "manifest.json")
    if not os.path.isfile(manifest_path):
        raise FileNotFoundError(f"No manifest.json in {plugin_path}")

    d = _load_manifest_json(manifest_path)

    if not isinstance(d, dict):
        raise ValueError(f"{manifest_path} does not contain an object")

    # Linux specific overrides, following the convention used by OpenDeck
    overrides_path = os.path.join(plugin_path, "manifest.linux.json")
    if os.path.isfile(overrides_path):
        try:
            d.update(_load_manifest_json(overrides_path))
        except (OSError, ValueError) as e:
            log.warning(f"Failed to apply {overrides_path}: {e}")

    # Newer manifests carry the UUID; older ones only encode it in the directory name
    folder_name = os.path.basename(os.path.normpath(plugin_path))
    uuid = _get(d, "UUID", default=None)
    if not uuid:
        uuid = folder_name[:-len(".sdPlugin")] if folder_name.endswith(".sdPlugin") else folder_name

    actions = []
    for action_dict in _get(d, "Actions", default=[]) or []:
        if not isinstance(action_dict, dict):
            continue
        action = SDAction.from_dict(action_dict)
        if action is None:
            log.warning(f"Skipping action without UUID in {manifest_path}")
            continue
        action.plugin_uuid = uuid
        actions.append(action)

    software = _get(d, "Software", default={}) or {}

    return SDManifest(
        path=plugin_path,
        uuid=uuid,
        name=_get(d, "Name", default=uuid) or uuid,
        author=_get(d, "Author", default="") or "",
        version=str(_get(d, "Version", default="0.0.0") or "0.0.0"),
        description=_get(d, "Description", default="") or "",
        url=_get(d, "URL", default="") or "",
        icon=_get(d, "Icon", default="") or "",
        category=_get(d, "Category", default="") or "",
        category_icon=_get(d, "CategoryIcon", default="") or "",
        sdk_version=int(_get(d, "SDKVersion", default=2) or 2),
        software_minimum_version=str(_get(software, "MinimumVersion", default="") or ""),
        os=_get(d, "OS", default=[]) or [],
        code_path=_get(d, "CodePath", default="") or "",
        code_path_win=_get(d, "CodePathWin", default="") or "",
        code_path_mac=_get(d, "CodePathMac", default="") or "",
        code_path_lin=_get(d, "CodePathLin", default="") or "",
        code_paths=_get(d, "CodePaths", default={}) or {},
        property_inspector_path=_get(d, "PropertyInspectorPath", default="") or "",
        applications_to_monitor=_get(d, "ApplicationsToMonitor", default={}) or {},
        actions=actions,
        nodejs=_get(d, "Nodejs", "NodeJS", default={}) or {},
    )

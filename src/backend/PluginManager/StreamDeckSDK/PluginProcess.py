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
import ctypes
import functools
import json
import os
import platform
import shutil
import signal
import stat
import subprocess

from enum import Enum

from loguru import logger as log

from autostart import is_flatpak
from src.backend.PluginManager.StreamDeckSDK.Manifest import SDManifest

try:
    _libc = ctypes.CDLL("libc.so.6", use_errno=True)
except OSError:
    _libc = None

PR_SET_PDEATHSIG = 1


class RunMode(Enum):
    NATIVE = "native"
    NODE = "node"
    WINE = "wine"
    WEBVIEW = "webview"


class UnsupportedPluginError(Exception):
    pass


def _host_command(command: str) -> list[str]:
    """
    Return the argv prefix needed to run ``command``. Inside the Flatpak sandbox
    interpreters like node and wine live on the host, so they are run through
    flatpak-spawn.
    """
    if is_flatpak():
        return ["flatpak-spawn", "--host", command]
    return [command]


def _host_command_version(command: str) -> str | None:
    """Return the ``--version`` output of ``command``, or None if it is not runnable."""
    try:
        result = subprocess.run(
            _host_command(command) + ["--version"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return (result.stdout or result.stderr).strip()


def _host_command_available(command: str) -> bool:
    return _host_command_version(command) is not None


MINIMUM_NODE_VERSION = 20

# Distributions do not agree on what the Node.js binary is called. Fedora, for
# instance, only ships the unversioned "node" symlink in a separate package.
NODE_COMMANDS = ("node", "node-24", "node-22", "node-20", "node24", "node22", "node20", "nodejs")


def _major_version(command: str) -> int | None:
    version = _host_command_version(command)
    if version is None:
        return None
    try:
        return int(version.strip().lstrip("vV").split(".")[0])
    except (ValueError, IndexError):
        return None


@functools.lru_cache(maxsize=1)
def find_node() -> tuple[str | None, int | None]:
    """
    Locate a Node.js that is new enough to run Stream Deck plugins.

    Returns:
        tuple: The command to use, or None if there is none, together with the newest
        major version that was found at all so the caller can explain why.
    """
    newest = None
    for command in NODE_COMMANDS:
        major = _major_version(command)
        if major is None:
            continue
        if major >= MINIMUM_NODE_VERSION:
            return command, major
        newest = major if newest is None else max(newest, major)

    return None, newest


def _set_parent_death_signal():
    """Make the kernel kill the plugin if StreamController goes away."""
    if _libc is None:
        return
    try:
        _libc.prctl(PR_SET_PDEATHSIG, signal.SIGTERM, 0, 0, 0)
    except Exception:
        pass


@functools.lru_cache(maxsize=1)
def get_target_triples() -> tuple[str, ...]:
    """
    The Rust target triples this machine can run, most specific first.

    Plugins built against the OpenAction API list their binaries under ``CodePaths``
    keyed by triple rather than by platform.
    """
    machine = platform.machine()
    aliases = {"x86_64": ("x86_64", "amd64"), "aarch64": ("aarch64", "arm64")}.get(machine, (machine,))

    triples = []
    for name in aliases:
        triples.append(f"{name}-unknown-linux-gnu")
        triples.append(f"{name}-unknown-linux-musl")
    return tuple(triples)


def _code_path_for_target(manifest: SDManifest) -> str | None:
    for triple in get_target_triples():
        path = manifest.code_paths.get(triple)
        if path:
            return path
    return None


def determine_run_mode(manifest: SDManifest) -> tuple[RunMode, str]:
    """
    Work out how the plugin described by ``manifest`` has to be started.

    Returns:
        tuple[RunMode, str]: The mode and the code path relative to the plugin dir.

    Raises:
        UnsupportedPluginError: If the plugin cannot run on this system.
    """
    platforms = manifest.get_platforms()

    # A binary built for this exact architecture always wins
    for_target = _code_path_for_target(manifest)
    if for_target:
        return RunMode.NATIVE, for_target

    # Interpreted plugins run anywhere their interpreter does. Elgato's own plugins
    # ship JavaScript but only list mac and windows in their manifest, so the declared
    # platforms are deliberately not consulted here.
    for candidate in (manifest.code_path_lin, manifest.code_path, manifest.code_path_win, manifest.code_path_mac):
        if not candidate:
            continue
        if _is_node_path(candidate):
            return RunMode.NODE, candidate
        if _is_html_path(candidate):
            return RunMode.WEBVIEW, candidate
        break

    if "linux" in platforms or not platforms:
        code_path = manifest.code_path_lin or manifest.code_path
        if code_path:
            return RunMode.NATIVE, code_path
        if not platforms:
            raise UnsupportedPluginError("the manifest does not declare a code path")

    # Compiled Windows plugins can still be run through Wine
    if "windows" in platforms:
        code_path = manifest.code_path_win or manifest.code_path
        if not code_path:
            raise UnsupportedPluginError("the manifest does not declare a code path")
        return RunMode.WINE, code_path

    raise UnsupportedPluginError(
        f"it is only built for {', '.join(platforms) or 'no platform at all'}"
    )


def _is_html_path(code_path: str) -> bool:
    return code_path.lower().endswith((".html", ".htm", ".xhtml"))


def _is_node_path(code_path: str) -> bool:
    return code_path.lower().endswith((".js", ".mjs", ".cjs"))


class PluginProcess:
    """A running Stream Deck SDK plugin process."""

    def __init__(self, manifest: SDManifest, mode: RunMode, code_path: str, log_path: str):
        self.manifest = manifest
        self.mode = mode
        self.code_path = code_path
        self.log_path = log_path

        self.process: subprocess.Popen = None
        self._log_file = None

    def start(self, port: int, info: dict, separate_wine_prefix: bool = False) -> None:
        """
        Launch the plugin, telling it to register itself with the WebSocket server on
        ``port``.

        Raises:
            UnsupportedPluginError: If the required interpreter is missing.
        """
        plugin_dir = self.manifest.path
        absolute_code_path = os.path.join(plugin_dir, self.code_path)

        env = dict(os.environ)

        if self.mode is RunMode.NODE:
            command, found = find_node()
            where = " on your host system" if is_flatpak() else ""
            if command is None:
                if found is None:
                    raise UnsupportedPluginError(
                        f"it needs Node.js, which was not found. Install Node.js {MINIMUM_NODE_VERSION} or newer{where}"
                    )
                raise UnsupportedPluginError(
                    f"it needs Node.js {MINIMUM_NODE_VERSION} or newer, but only version {found} was found{where}"
                )
            argv = _host_command(command) + [absolute_code_path]

        elif self.mode is RunMode.WINE:
            if not _host_command_available("wine"):
                raise UnsupportedPluginError(
                    "it is only built for Windows and Wine was not found. Install Wine"
                    + (" on your host system" if is_flatpak() else "")
                )
            argv = _host_command("wine") + [absolute_code_path]
            if separate_wine_prefix:
                env["WINEPREFIX"] = os.path.join(plugin_dir, "wineprefix")

        elif self.mode is RunMode.NATIVE:
            if not os.path.isfile(absolute_code_path):
                raise UnsupportedPluginError(f"its code path {self.code_path} does not exist")
            self._make_executable(absolute_code_path)
            argv = [absolute_code_path]

        else:
            raise UnsupportedPluginError(f"the run mode {self.mode} is not a process")

        argv += [
            "-port", str(port),
            "-pluginUUID", self.manifest.uuid,
            "-registerEvent", "registerPlugin",
            "-info", json.dumps(info),
        ]

        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        self._log_file = open(self.log_path, "w")

        log.info(f"Launching Stream Deck SDK plugin {self.manifest.uuid} ({self.mode.value})")

        self.process = subprocess.Popen(
            argv,
            cwd=plugin_dir,
            stdout=self._log_file,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            env=env,
            start_new_session=False,
            preexec_fn=_set_parent_death_signal if not is_flatpak() else None,
        )

    @staticmethod
    def _make_executable(path: str) -> None:
        try:
            mode = os.stat(path).st_mode
            os.chmod(path, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        except OSError as e:
            log.warning(f"Failed to mark {path} as executable: {e}")

    def is_alive(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def stop(self, timeout: float = 5) -> None:
        if self.process is not None:
            try:
                self.process.terminate()
                try:
                    self.process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=timeout)
            except OSError as e:
                log.warning(f"Failed to stop plugin {self.manifest.uuid}: {e}")
            self.process = None

        if self._log_file is not None:
            try:
                self._log_file.close()
            except OSError:
                pass
            self._log_file = None


def remove_wine_prefix(plugin_path: str) -> None:
    shutil.rmtree(os.path.join(plugin_path, "wineprefix"), ignore_errors=True)

"""
Author: Core447
Year: 2026

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This programm comes with ABSOLUTELY NO WARRANTY!

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.

Strips personally identifying information out of log messages.

Users paste logs.log and the About dialog's debug info into bug reports, and
those contain their username (in every path below the data dir), their
hostname and whatever hosts plugins happen to log - a Home Assistant instance,
a printer, an MQTT broker. None of that helps anyone debug, so it is replaced
before the record reaches any sink.

Hooked up as loguru's global patcher in main.py's config_logger(), which
covers every sink at once: logs.log, stderr, gl.logs (the About dialog) and
plugins.log. Not covered: exception tracebacks (rendered by the sink, not by
the patcher), print() and plugin backends, which are separate processes.
"""
import getpass
import ipaddress
import os
import re
import socket

# Hosts of our own infrastructure, plus loopback. Redacting these would only
# make store and update problems harder to debug without hiding anything
# about the user.
ALLOWED_HOSTS = {
    "github.com",
    "raw.githubusercontent.com",
    "api.github.com",
    "objects.githubusercontent.com",
    "core447.com",
    "localhost",
    "127.0.0.1",
    "::1",
}

# Names that identify nobody, and that appear in normal log text often enough
# that redacting them would just make logs unreadable.
GENERIC_NAMES = {
    "root", "user", "users", "admin", "guest", "test", "default", "nobody",
    "ubuntu", "debian", "fedora", "arch", "steamos", "deck", "localhost",
}

# A name has to be at least this long before we redact it on its own. Short
# names ("pi", "sc") show up inside unrelated words all the time.
MIN_NAME_LENGTH = 4

# Both patterns match loosely and leave the decision to _replace_ip(), which
# runs the candidate through the ipaddress module. That is both more accurate
# and a lot cheaper than a precise IPv6 regex, which backtracks heavily on
# every line that merely contains a colon.
IPV4 = r"(?:\d{1,3}\.){3}\d{1,3}"
IPV6 = r"(?=[0-9a-f]{0,4}:)[0-9a-f:]{2,45}(?::" + IPV4 + r")?"


def _is_redactable_name(name: str | None) -> bool:
    return bool(name) and len(name) >= MIN_NAME_LENGTH and name.lower() not in GENERIC_NAMES


def _get_username() -> str | None:
    try:
        return getpass.getuser()
    except Exception:
        # No pwd entry and no matching env var - nothing to redact then
        return None


def _get_hostname() -> str | None:
    try:
        return socket.gethostname()
    except Exception:
        return None


def _is_allowed_host(host: str) -> bool:
    host = host.strip("[]").rstrip(".").lower()
    if host in ALLOWED_HOSTS:
        return True
    return any(host.endswith(f".{allowed}") for allowed in ALLOWED_HOSTS)


def _replace_url(match: re.Match) -> str:
    """
    Keeps the scheme, port and path, drops the host and any embedded
    credentials: wss://user:pw@hass.example.com:443/api -> wss://<host>:443/api
    """
    host = match.group("url_host")
    port = match.group("url_port") or ""
    return f"{match.group('url_scheme')}://{host if _is_allowed_host(host) else '<host>'}{port}"


def _replace_ip(match: re.Match) -> str:
    text = match.group()
    try:
        address = ipaddress.ip_address(text.strip("[]"))
    except ValueError:
        # The patterns match loosely on purpose, so anything that only looks
        # like an address (a version number, a timestamp) stays as it is
        return text
    if address.is_loopback or address.is_unspecified:
        return text
    return "<ip>"


def build_rules(username: str | None = None, hostname: str | None = None,
                home: str | None = None) -> list[tuple[str, str, object]]:
    """
    (name, pattern, replacement) in the order they are tried. All patterns go
    into one alternation, so at a given position the first one that matches
    wins - URLs come before bare IPs so a URL with an IP host stays a URL.

    The arguments default to this machine's values and only exist so the tests
    don't depend on who runs them.
    """
    username = username if username is not None else _get_username()
    hostname = hostname if hostname is not None else _get_hostname()
    home = home if home is not None else os.path.expanduser("~")

    rules: list[tuple[str, str, object]] = [
        (
            "url",
            r"(?P<url_scheme>[a-z][a-z0-9+.\-]*)://(?:[^/?#\s@]*@)?"
            r"(?P<url_host>\[[^\]\s]+\]|[^/?#\s:]+)(?P<url_port>:\d+)?",
            _replace_url,
        ),
    ]

    if home not in ("", "/", "~"):
        rules.append(("home", re.escape(home) + r"(?!\w)", "~"))
    # Other users' homes, and our own if HOME is not where it usually lives
    rules.append(("home_generic", r"(?:/var)?/home/[\w.\-]+", "/home/<user>"))

    # Hostname first: it often contains the username ("jonathan-laptop"), and
    # the first branch that matches at a position wins
    if _is_redactable_name(hostname) and hostname != username:
        rules.append(("hostname", r"\b" + re.escape(hostname) + r"\b", "<host>"))

    if _is_redactable_name(username):
        rules.append(("username", r"\b" + re.escape(username) + r"\b", "<user>"))

    rules.append(("ipv6", r"(?<![\w:.])(?:\[" + IPV6 + r"\]|" + IPV6 + r")(?![\w:.])", _replace_ip))
    rules.append(("ipv4", r"(?<![\w.])" + IPV4 + r"(?![\w.])", _replace_ip))

    return rules


class Redactor:
    def __init__(self, rules: list[tuple[str, str, object]]):
        self.pattern = re.compile(
            "|".join(f"(?P<{name}>{pattern})" for name, pattern, _ in rules),
            re.IGNORECASE,
        )
        self.replacements = {name: replacement for name, _, replacement in rules}

    def _substitute(self, match: re.Match) -> str:
        for name, replacement in self.replacements.items():
            if match.group(name) is None:
                continue
            return replacement(match) if callable(replacement) else replacement
        return match.group()

    def redact(self, text: str) -> str:
        """
        Replaces the personally identifying parts of `text`. Idempotent - none
        of the replacements match a rule themselves, so redacting an already
        redacted string changes nothing.
        """
        if not text:
            return text
        return self.pattern.sub(self._substitute, text)


_redactor = Redactor(build_rules())


def redact(text: str) -> str:
    return _redactor.redact(text)


def patch_record(record: dict) -> None:
    """
    loguru patcher. Runs after the message has been formatted and before any
    handler sees the record, so redacting here covers every sink.
    """
    record["message"] = redact(record["message"])

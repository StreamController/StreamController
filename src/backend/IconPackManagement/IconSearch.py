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
"""
Matching and ordering for the icon browser.

Icon names are long and machine generated ("battery-level-90-charged-symbolic"),
so a plain fuzz.ratio() over the whole name scores the interesting matches far
too low - searching "battery" used to drop every battery icon. Instead a match
is scored by where the query appears in the name, and fuzzy matching is only
used as a fallback for typos.

Every icon has to be matched on every key press, so the hot path stays free of
regexes and of anything that builds new strings per icon (Icon pre computes its
lowercase name and category).
"""

# Import python modules
from dataclasses import dataclass, field

from fuzzywuzzy import fuzz

# Import typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.backend.IconPackManagement.Icon import Icon

# Characters that separate the words of an icon name
SEPARATORS = "-_. /"

# Below this a fuzzy match is considered a different icon
FUZZY_THRESHOLD = 72

# Matches in these fields are worth less than a match in the name itself
CATEGORY_WEIGHT = 0.6
PACK_WEIGHT = 0.4
# Keeps every fuzzy match below every substring match (max score 100 * 0.5 < 70)
FUZZY_WEIGHT = 0.5


@dataclass
class Token:
    text: str
    chars: frozenset = field(default_factory=frozenset)


def prepare_query(query: str) -> list[Token]:
    tokens: list[Token] = []
    for word in query.lower().split():
        tokens.append(Token(text=word, chars=frozenset(word)))
    return tokens


def _substring_score(text: str, token: Token) -> float:
    """
    100: the text is the query, 90: it starts with it, 80: a word of it starts
    with it, 70: it contains it somewhere, 0: no match
    """
    if not text:
        return 0
    if text == token.text:
        return 100
    if text.startswith(token.text):
        return 90

    index = text.find(token.text)
    if index == -1:
        return 0
    if text[index - 1] in SEPARATORS:
        return 80
    return 70


def _fuzzy_score(text: str, token: Token) -> float:
    """
    Fallback for typos. The cheap character test in front of it keeps the
    expensive matcher away from the icons that cannot match anyway.
    """
    if len(token.text) < 3:
        return 0
    for char in token.chars:
        if char not in text:
            return 0

    ratio = fuzz.partial_ratio(text, token.text)
    if ratio < FUZZY_THRESHOLD:
        return 0
    return ratio * FUZZY_WEIGHT


def score_icon(icon: "Icon", tokens: list[Token], match_pack_name: bool = False) -> float:
    """
    The score of the icon for the given query, 0 if it does not match. Every
    token has to match, the score is their average.
    """
    if not tokens:
        return 0

    total = 0.0
    for token in tokens:
        score = _substring_score(icon.search_name, token)

        if not score:
            score = _substring_score(icon.search_category, token) * CATEGORY_WEIGHT

        if not score and match_pack_name:
            score = _substring_score(icon.icon_pack.name.lower(), token) * PACK_WEIGHT

        if not score:
            score = _fuzzy_score(icon.search_name, token)

        if not score:
            return 0

        total += score

    return total / len(tokens)


def sort_icons(icons: list["Icon"], group_by_pack: bool = False) -> list["Icon"]:
    """
    The order used when nothing is searched: icons of the same category stay
    together, packs stay together if their icons are mixed.
    """
    if group_by_pack:
        return sorted(icons, key=lambda icon: (icon.icon_pack.name.lower(), icon.search_category, icon.search_name))
    return sorted(icons, key=lambda icon: (icon.search_category, icon.search_name))


def search_icons(icons: list["Icon"], query: str, match_pack_name: bool = False) -> list["Icon"]:
    """
    The icons matching the query, best match first. Returns all icons in their
    browse order if the query is empty.
    """
    tokens = prepare_query(query)
    if not tokens:
        return sort_icons(icons, group_by_pack=match_pack_name)

    matches = []
    for icon in icons:
        score = score_icon(icon, tokens, match_pack_name=match_pack_name)
        if score:
            # Shorter names are the more exact match: "battery" before "battery-low"
            matches.append((-score, len(icon.search_name), icon.search_name, icon))

    matches.sort(key=lambda match: match[:3])
    return [match[3] for match in matches]

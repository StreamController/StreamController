import datetime
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GLOBALS_PATH = REPO_ROOT / "globals.py"
METAINFO_PATH = REPO_ROOT / "flatpak" / "com.core447.StreamController.metainfo.xml"


def read_globals() -> tuple[str, str]:
    text = GLOBALS_PATH.read_text()

    version_match = re.search(r'app_version:\s*str\s*=\s*"([^"]+)"', text)
    if not version_match:
        sys.exit(f"Could not find app_version in {GLOBALS_PATH}")

    notes_match = re.search(r'release_notes:\s*str\s*=\s*"""(.*?)"""', text, re.DOTALL)
    if not notes_match:
        sys.exit(f"Could not find release_notes in {GLOBALS_PATH}")

    return version_match.group(1), notes_match.group(1)


def format_description(release_notes: str) -> str:
    """Reindent the release notes HTML to match the metainfo file's style."""
    lines = []
    for raw_line in release_notes.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("<li>"):
            indent = 10
        elif line.startswith("</ul>") or line.startswith("<ul>") or line.startswith("<p>"):
            indent = 8
        else:
            indent = 8
        lines.append(" " * indent + line)
    return "\n".join(lines)


def build_release_block(version: str, date: str, description: str) -> str:
    return (
        f'    <release version="{version}" date="{date}">\n'
        f'      <description translatable="no">\n'
        f'{description}\n'
        f'      </description>\n'
        f'    </release>\n'
    )


def main() -> None:
    version, release_notes = read_globals()
    description = format_description(release_notes)
    today = datetime.date.today().isoformat()

    metainfo_text = METAINFO_PATH.read_text()

    existing_release_re = re.compile(
        r'(    <release version="' + re.escape(version) + r'" date=")([^"]*)("\s*>\n'
        r'      <description translatable="no">\n)(.*?)(\n      </description>\n    </release>\n)',
        re.DOTALL,
    )
    existing_match = existing_release_re.search(metainfo_text)

    if existing_match:
        print(f"Version {version} already exists in {METAINFO_PATH.name} (date: {existing_match.group(2)}).")
        answer = input("Update that entry with the current globals.py content? [y/N] ").strip().lower()
        if answer not in ("y", "yes"):
            print("Not modifying metainfo file.")
            return

        new_block = existing_match.group(1) + today + existing_match.group(3) + description + existing_match.group(5)
        metainfo_text = metainfo_text[:existing_match.start()] + new_block + metainfo_text[existing_match.end():]
        METAINFO_PATH.write_text(metainfo_text)
        print(f"Updated release {version} in {METAINFO_PATH.name} (date set to {today}).")
        return

    new_block = build_release_block(version, today, description)
    marker = "  <releases>\n"
    if marker not in metainfo_text:
        sys.exit(f"Could not find '<releases>' tag in {METAINFO_PATH}")

    metainfo_text = metainfo_text.replace(marker, marker + new_block, 1)
    METAINFO_PATH.write_text(metainfo_text)
    print(f"Added release {version} (date: {today}) to {METAINFO_PATH.name}.")


if __name__ == "__main__":
    main()

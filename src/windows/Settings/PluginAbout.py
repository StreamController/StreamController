import os.path
from idlelib.pyparse import trans

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from src.backend.PluginManager.PluginBase import PluginBase
import globals as gl

class PluginAboutFactory:
    def __init__(self, plugin_base: PluginBase):
        self.plugin_base = plugin_base

        self.about = (plugin_base.get_manifest() or {}).get("about", {})

    def create_new_about(self):
        about = Adw.AboutWindow()

        about.set_application_name(self.plugin_base.plugin_name)
        about.set_version(self.plugin_base.plugin_version)
        about.set_website(self.plugin_base.github_repo)
        about.set_issue_url(f"{self.plugin_base.github_repo}/issues")

        about.set_modal(True)

        return about

    def add_release_notes(self, about: Adw.AboutWindow):
        release_notes = self.about.get("release-notes", {})

        path = release_notes.get("path", "")
        version = release_notes.get("version", "")

        full_path = f"{self.plugin_base.PATH}/{path}"

        if not os.path.isfile(full_path):
            return

        with open(full_path, "r") as f:
            about.set_release_notes(f.read())

        about.set_release_notes_version(version or self.plugin_base.plugin_version)

    def add_credits(self, about: Adw.AboutWindow):
        credits = self.about.get("credits", {})

        for section, people in credits.items():
            about.add_credit_section(section, people)

    def add_comments(self, about: Adw.AboutWindow):
        manifest = self.plugin_base.get_manifest()

        translation = gl.lm.get_custom_translation(manifest.get("descriptions", {}))

        if translation:
            about.set_comments(translation)

    def add_author(self, about: Adw.AboutWindow):
        manifest = self.plugin_base.get_manifest()

        author = manifest.get("author", "")

        if author:
            about.set_developer_name(author)
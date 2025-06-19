import os.path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from src.backend.PluginManager.PluginBase import PluginBase
import globals as gl

class PluginAboutFactory:
    def __init__(self, plugin_base: PluginBase):
        self.plugin_base = plugin_base

        self.about = self.plugin_base.get_about()
        self.manifest = self.plugin_base.get_manifest()

    def create_new_about(self):
        about = Adw.AboutDialog()

        about.set_application_name(self.plugin_base.plugin_name)
        about.set_version(self.plugin_base.plugin_version)
        about.set_website(self.plugin_base.github_repo)
        about.set_issue_url(f"{self.plugin_base.github_repo}/issues")

        if os.path.exists(self.plugin_base.LOG_FILE_PATH):
            log_path = self.plugin_base.LOG_FILE_PATH

            with open(log_path, "r") as log:
                about.set_debug_info(log.read())
            about.set_debug_info_filename(log_path)

        self._full_setup(about)

        return about

    def _full_setup(self, about: Adw.AboutDialog):
        self.add_release_notes(about)
        self.add_copyright(about)
        self.add_support(about)
        self.add_credits(about)
        self.add_acknowledgements(about)
        self.add_author(about)
        self.add_comments(about)

    def add_release_notes(self, about: Adw.AboutDialog):
        release_notes = self.about.get("release-notes", {})

        path = release_notes.get("path", "")
        version = release_notes.get("version", "")

        full_path = f"{self.plugin_base.PATH}/{path}"

        if not os.path.isfile(full_path):
            return

        with open(full_path, "r") as f:
            about.set_release_notes(f.read())

        about.set_release_notes_version(version or self.plugin_base.plugin_version)

    def add_credits(self, about: Adw.AboutDialog):
        credits = self.about.get("credits", {})

        for section, people in credits.items():
            about.add_credit_section(section, people)

    def add_comments(self, about: Adw.AboutDialog):
        comment = self.about.get("comments", None)

        if not comment:
            manifest = self.plugin_base.get_manifest()
            comment = manifest.get("descriptions", {})

        translation = gl.lm.get_custom_translation(comment)

        if translation:
            about.set_comments(translation)

    def add_support(self, about: Adw.AboutDialog):
        support = self.about.get("support", "")

        if support:
            about.set_support_url(support)

    def add_author(self, about: Adw.AboutDialog):
        author = self.about.get("author", "")

        if author:
            about.set_developer_name(author)

    def add_copyright(self, about: Adw.AboutDialog):
        copyright = self.about.get("copyright", "")

        if copyright:
            about.set_copyright(copyright)

    def add_acknowledgements(self, about: Adw.AboutDialog):
        acknowledgements = self.about.get("acknowledgements", {})

        for section, people in acknowledgements.items():
            about.add_acknowledgement_section(section, people)
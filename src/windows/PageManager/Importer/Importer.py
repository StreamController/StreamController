"""
Author: Core447
Year: 2024

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This programm comes with ABSOLUTELY NO WARRANTY!

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
# Import gi
import json
import os
import threading
import gi

from src.backend.PageManagement import PageBundle
from src.windows.PageManager.Importer.StreamDeckUI.StreamDeckUI import StreamDeckUIImporter
from src.windows.PageManager.Importer.StreamController.StreamController import StreamControllerImporter

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GLib

from loguru import logger as log

class Importer(Adw.ApplicationWindow):
    def __init__(self, app, window):
        super().__init__(application=app,
                         transient_for=window,
                         modal=True,
                         default_width=400,
                         default_height=120,
                         title="Importing")

        self.build()

    def build(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(self.main_box)

        self.header = Adw.HeaderBar(css_classes=["flat"])
        self.main_box.append(self.header)

        self.status_label = Gtk.Label(label="Importing", css_classes=["title-4"], margin_start=20, margin_end=20)
        self.main_box.append(self.status_label)

        self.progess_bar = Gtk.ProgressBar(margin_start=20, margin_end=20, margin_top=20, margin_bottom=20, show_text=True)
        self.main_box.append(self.progess_bar)

    def set_status(self, status: str, detail: str = None, fraction: float = None):
        """Thread safe update of the progress ui."""
        GLib.idle_add(self.status_label.set_label, status)
        if detail is not None:
            GLib.idle_add(self.progess_bar.set_text, detail)
        if fraction is not None:
            GLib.idle_add(self.progess_bar.set_fraction, fraction)

    def show_error(self, message: str = "Import failed"):
        GLib.idle_add(self.status_label.set_label, message)
        GLib.idle_add(self.progess_bar.set_text, "")
        GLib.idle_add(self.progess_bar.set_fraction, 0)
        GLib.timeout_add(3000, self.close)

    def import_pages(self, path: str, app: str, on_finished: callable = None, rename_to: str = None) -> None:
        self.progess_bar.set_text("Importing...")
        self.progess_bar.set_fraction(0)

        if app == "streamdeck-ui":
            thread = threading.Thread(target=self.import_from_streamdeck_ui, args=(path, on_finished), name="import_from_streamdeck_ui")
            thread.start()

        if app == "streamcontroller":
            thread = threading.Thread(target=self.import_from_streamcontroller, args=(path, on_finished, rename_to), name="import_from_streamcontroller")
            thread.start()

    def ask_to_install(self, requirements: list[PageBundle.Requirement]) -> str:
        """
        Asks the user whether the missing plugins and packs should be downloaded
        from the store. Blocks the calling (import) thread until answered.
        """
        answer: dict[str, str] = {}
        answered = threading.Event()

        def finish(response: str):
            answer.setdefault("response", response)
            answered.set()

        def on_window_closed(*args):
            # Never leave the import thread waiting for a dialog that is gone
            finish("cancel")
            return False

        def show():
            names = "\n".join(f"• {requirement.label} ({requirement.type_label})" for requirement in requirements)
            dialog = Adw.MessageDialog(
                transient_for=self,
                modal=True,
                heading="Missing plugins and packs",
                body=f"The imported pages need the following, which will be downloaded from the store:\n\n{names}"
            )
            dialog.add_response("cancel", "Cancel")
            dialog.add_response("skip", "Import Without")
            dialog.add_response("install", "Download and Import")
            dialog.set_default_response("install")
            dialog.set_close_response("cancel")
            dialog.set_response_appearance("install", Adw.ResponseAppearance.SUGGESTED)

            def on_response(dialog, response):
                finish(response)
                dialog.destroy()

            dialog.connect("response", on_response)
            self.connect("close-request", on_window_closed)
            dialog.present()

        self.set_status("Waiting for confirmation", "", 0)
        GLib.idle_add(show)
        answered.wait()

        return answer.get("response", "cancel")


    @log.catch
    def import_from_streamdeck_ui(self, path: str, on_finished: callable) -> None:
        if not os.path.exists(path):
            self.show_error("File not found")
            return
        try:
            with open(path) as f:
                json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.show_error("File is not valid JSON")
            return

        ui_importer = StreamDeckUIImporter(path)
        ui_importer.perform_import()

        GLib.idle_add(self.progess_bar.set_text, "Imported!")
        GLib.idle_add(self.progess_bar.set_fraction, 1)

        if on_finished:
            on_finished()

        GLib.timeout_add(1500, self.close)

    @log.catch
    def import_from_streamcontroller(self, path: str, on_finished: callable, rename_to: str = None) -> None:
        if not os.path.exists(path):
            self.show_error("File not found")
            return

        manifest = None
        if PageBundle.is_bundle(path):
            manifest = PageBundle.read_manifest(path)
            if manifest is None:
                self.show_error("File is not a StreamController export")
                return
        else:
            try:
                with open(path) as f:
                    json.load(f)
            except (json.JSONDecodeError, UnicodeDecodeError):
                self.show_error("File is not valid JSON")
                return

        if manifest is not None and not self.install_missing_requirements(manifest):
            return

        self.set_status("Importing pages", "", 0)

        ui_importer = StreamControllerImporter(path, rename_to=rename_to)
        try:
            ui_importer.perform_import()
        except Exception as e:
            log.error(f"Failed to import {path}: {e}")
            self.show_error("Import failed")
            return

        self.set_status("Imported!", "", 1)

        if on_finished:
            on_finished()

        GLib.timeout_add(1500, self.close)

    def install_missing_requirements(self, manifest: dict) -> bool:
        """
        Installs everything the pages need but that is not installed yet.
        Returns False if the user cancelled the import.
        """
        requirements = PageBundle.get_missing_requirements(manifest)
        if not requirements:
            return True

        response = self.ask_to_install(requirements)
        if response == "cancel":
            GLib.idle_add(self.close)
            return False
        if response != "install":
            return True

        def on_progress(index: int, total: int, requirement):
            self.set_status(
                "Downloading from the store",
                f"{requirement.label} ({index + 1}/{total})" if requirement is not None else "",
                index / total
            )

        failed = PageBundle.install_requirements(requirements, progress_callback=on_progress)
        if failed:
            log.warning(f"Could not install {len(failed)} requirement(s) for the import")

        return True
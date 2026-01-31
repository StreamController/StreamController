"""
Year: 2023

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This programm comes with ABSOLUTELY NO WARRANTY!

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
# Import gtk modules
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Pango, GLib

# Import python modules
from typing import TYPE_CHECKING
import webbrowser as web
import threading
import asyncio
from loguru import logger as log

# Import own modules
if TYPE_CHECKING:
    from src.windows.Store.StorePage import StorePage
    from src.windows.Store.StoreData import PluginData

from GtkHelper.GtkHelper import AttributeRow, OriginalURL

# Import globals
import globals as gl

class InfoPage(Gtk.Box):
    def __init__(self, store_page:"StorePage"):
        super().__init__(orientation=Gtk.Orientation.VERTICAL,
                       margin_top=15)
        
        self.store_page = store_page
        self.current_plugin_data: "PluginData" = None
        self.build()

    def build(self):
        self.clamp = Adw.Clamp(hexpand=True)
        self.append(self.clamp)

        self.clamp_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.clamp.set_child(self.clamp_box)

        self.about_group = Adw.PreferencesGroup(title="About")
        self.clamp_box.append(self.about_group)

        self.name_row = AttributeRow(title="Name:", attr="Error")
        self.about_group.add(self.name_row)

        self.author_row = AttributeRow(title="Author:", attr="Error")
        self.about_group.add(self.author_row)

        self.version_row = AttributeRow(title="Version:", attr="Error")
        self.about_group.add(self.version_row)

        # TODO: Enable in the future
        #self.stargazer_row = AttributeRow(title="Stargazers:", attr="0")
        #self.about_group.add(self.stargazer_row)

        self.description_row = DescriptionRow(title="Description:", desc="N/A")
        self.about_group.add(self.description_row)

        # Source group for git branch selection
        self.source_group = SourceGroup(info_page=self)
        self.clamp_box.append(self.source_group)

        self.legal_group = Adw.PreferencesGroup(title="Legal")
        self.clamp_box.append(self.legal_group)

        self.license_row = AttributeRow(title="License:", attr="Error")
        self.legal_group.add(self.license_row)

        self.copyright_row = AttributeRow(title="Copyright:", attr="Error")
        self.legal_group.add(self.copyright_row)

        self.original_url = OriginalURL()
        self.legal_group.add(self.original_url)

        self.license_description = DescriptionRow(title="License Description:", desc="N/A")
        self.legal_group.add(self.license_description)
    
    def set_plugin_data(self, plugin_data: "PluginData"):
        """Set the current plugin data and update the source group."""
        self.current_plugin_data = plugin_data
        self.source_group.update_for_plugin(plugin_data)
    
    def clear_plugin_data(self):
        """Clear plugin data (used when showing non-plugin content like icons)."""
        self.current_plugin_data = None
        self.source_group.set_visible(False)

    def set_name(self, name:str):
        self.name_row.set_url(name)

    def set_description(self, description:str):
        self.description_row.set_description(description)

    def set_author(self, author:str):
        self.author_row.set_url(author)

    def set_version(self, version:str):
        self.version_row.set_url(version)

    def set_license(self, license:str):
        self.license_row.set_url(license)

    def set_stargazer(self, stargazer: int):
        self.stargazer_row.set_url(str(stargazer))

    def set_copyright(self, copyright:str):
        self.copyright_row.set_url(copyright)

    def set_license_description(self, description:str):
        self.license_description.set_description(description)

    def set_original_url(self, url:str):
        self.original_url.set_url(url)


class DescriptionRow(Adw.PreferencesRow):
    def __init__(self, title:str, desc:str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = title
        self.desc = desc

        self.build()

    def build(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True,
                                margin_top=15, margin_bottom=15)
        self.set_child(self.main_box)

        self.title_label = Gtk.Label(label=self.title, xalign=0, hexpand=True, margin_start=15)
        self.main_box.append(self.title_label)

        self.description_label = Gtk.Label(label=self.desc, xalign=0, wrap=True, wrap_mode=Pango.WrapMode.WORD,
                                           margin_start=15, margin_top=15, margin_end=15)
        self.main_box.append(self.description_label)

    def set_description(self, description:str):
        if description in [None, ""]:
            description = "N/A"
        self.description_label.set_text(description)

    def set_title(self, title:str):
        if title in [None, ""]:
            title = "N/A"
        self.title_label.set_text(title)


class SourceGroup(Adw.PreferencesGroup):
    """Group for selecting plugin source - store version, git branch, or git tag."""
    
    STORE_VERSION_ID = "__store_version__"
    
    def __init__(self, info_page: InfoPage):
        super().__init__(title=gl.lm.get("store.info.source.title") or "Source")
        self.info_page = info_page
        self.current_plugin_data: "PluginData" = None
        self.branches_cache: dict[str, list[str]] = {}
        self.tags_cache: dict[str, list[str]] = {}
        self.is_loading_refs = False
        
        self.set_margin_top(12)
        
        self.build()
    
    def build(self):
        self.set_description(gl.lm.get("store.info.source.description") or 
                           "Choose to use the store version, a git branch, or a git tag")
        
        self.branch_row = Adw.ComboRow(
            title=gl.lm.get("store.info.source.branch-row.title") or "Source",
            subtitle=gl.lm.get("store.info.source.branch-row.subtitle") or "Select store version, branch, or tag"
        )
        
        self.refresh_button = Gtk.Button(
            icon_name="view-refresh-symbolic",
            valign=Gtk.Align.CENTER,
            css_classes=["flat"],
            tooltip_text=gl.lm.get("store.info.source.refresh.tooltip") or "Refresh branches and tags from GitHub"
        )
        self.refresh_button.connect("clicked", self.on_refresh_clicked)
        self.refresh_spinner = Gtk.Spinner(spinning=False, visible=False)
        
        self.branch_row.add_suffix(self.refresh_spinner)
        self.branch_row.add_suffix(self.refresh_button)
        self.add(self.branch_row)
        
        self.branch_model = Gtk.StringList()
        self.branch_row.set_model(self.branch_model)
        
        self.branch_row.connect("notify::selected", self.on_branch_selected)
        
        self.status_row = Adw.ActionRow(
            title=gl.lm.get("store.info.source.status.title") or "Current Status",
            subtitle=""
        )
        self.add(self.status_row)
        
        self.apply_row = Adw.ActionRow(
            title=gl.lm.get("store.info.source.apply.title") or "Apply Now",
            subtitle=gl.lm.get("store.info.source.apply.subtitle") or "Reinstall plugin with the selected source",
            activatable=True
        )
        self.apply_row.connect("activated", self.on_apply_clicked)
        
        self.apply_spinner = Gtk.Spinner(spinning=False)
        self.apply_icon = Gtk.Image(icon_name="emblem-synchronizing-symbolic")
        self.apply_row.add_suffix(self.apply_icon)
        self.apply_row.add_suffix(self.apply_spinner)
        self.add(self.apply_row)
        
        self.is_applying = False
    
    def update_for_plugin(self, plugin_data: "PluginData"):
        """Update the source group for a specific plugin."""
        self.current_plugin_data = plugin_data
        
        if plugin_data is None:
            self.set_visible(False)
            return
        
        self.set_visible(True)
        
        self.branch_row.handler_block_by_func(self.on_branch_selected)
        
        try:
            override = gl.store_backend.get_plugin_git_override(plugin_data.plugin_id)
            
            self.branch_model.splice(0, self.branch_model.get_n_items(), [])
            
            store_label = gl.lm.get("store.info.source.store-version") or "Store Version (Recommended)"
            self.branch_model.append(store_label)
            
            cached_branches = self.branches_cache.get(plugin_data.plugin_id, [])
            cached_tags = self.tags_cache.get(plugin_data.plugin_id, [])
            for branch in cached_branches:
                self.branch_model.append(branch)
            for tag in cached_tags:
                self.branch_model.append(tag)
            
            if override and override.get("branch"):
                override_ref = override["branch"]
                
                found_index = -1
                for i in range(self.branch_model.get_n_items()):
                    if self.branch_model.get_string(i) == override_ref:
                        found_index = i
                        break
                
                if found_index == -1:
                    self.branch_model.append(override_ref)
                    found_index = self.branch_model.get_n_items() - 1
                
                self.branch_row.set_selected(found_index)
                self.update_status(using_override=True, ref=override_ref)
            else:
                self.branch_row.set_selected(0)
                self.update_status(using_override=False)
        finally:
            self.branch_row.handler_unblock_by_func(self.on_branch_selected)
        
        self.fetch_refs_async()
    
    def update_status(self, using_override: bool, ref: str = None):
        """Update the status row to reflect current state."""
        if using_override and ref:
            status = (gl.lm.get("store.info.source.status.using-ref") or 
                     "Using git ref: {ref}").format(ref=ref)
            self.status_row.add_css_class("warning")
        else:
            status = gl.lm.get("store.info.source.status.using-store") or "Using store version"
            self.status_row.remove_css_class("warning")
        
        self.status_row.set_subtitle(status)
    
    def on_branch_selected(self, combo_row, param):
        """Handle branch selection change."""
        if self.current_plugin_data is None:
            return
        
        plugin_id = self.current_plugin_data.plugin_id
        if plugin_id is None:
            return
        
        selected_index = combo_row.get_selected()
        if selected_index == Gtk.INVALID_LIST_POSITION:
            return
        
        selected_text = self.branch_model.get_string(selected_index)
        store_label = gl.lm.get("store.info.source.store-version") or "Store Version (Recommended)"
        
        if selected_index == 0 or selected_text == store_label:
            gl.store_backend.remove_plugin_git_override(plugin_id)
            self.update_status(using_override=False)
        else:
            ref = selected_text
            gl.store_backend.set_plugin_git_override(plugin_id, ref)
            self.update_status(using_override=True, ref=ref)
    
    def on_refresh_clicked(self, *args):
        """Handle refresh button click."""
        self.fetch_refs_async()
    
    def fetch_refs_async(self):
        """Fetch branches and tags from GitHub in a background thread."""
        if self.is_loading_refs or self.current_plugin_data is None:
            return
        
        self.is_loading_refs = True
        GLib.idle_add(self.show_loading, True)
        
        threading.Thread(
            target=self._fetch_refs_thread,
            daemon=True,
            name="fetch_refs"
        ).start()
    
    def _fetch_refs_thread(self):
        """Background thread to fetch branches and tags."""
        try:
            plugin_id = self.current_plugin_data.plugin_id
            branches = asyncio.run(
                gl.store_backend.get_repo_branches(self.current_plugin_data.github)
            )
            tags = asyncio.run(
                gl.store_backend.get_repo_tags(self.current_plugin_data.github)
            )
            
            if branches is not None:
                self.branches_cache[plugin_id] = branches
            if tags is not None:
                self.tags_cache[plugin_id] = tags
            
            GLib.idle_add(self._update_refs_ui, branches or [], tags or [])
        except Exception as e:
            log.error(f"Error fetching branches and tags: {e}")
        finally:
            self.is_loading_refs = False
            GLib.idle_add(self.show_loading, False)
    
    def _update_refs_ui(self, branches: list[str], tags: list[str]):
        """Update the UI with fetched branches and tags (must be called from main thread)."""
        if self.current_plugin_data is None:
            return
        
        self.branch_row.handler_block_by_func(self.on_branch_selected)
        
        try:
            current_selected = self.branch_row.get_selected()
            current_text = None
            if current_selected != Gtk.INVALID_LIST_POSITION:
                current_text = self.branch_model.get_string(current_selected)
            
            store_label = gl.lm.get("store.info.source.store-version") or "Store Version (Recommended)"
            
            self.branch_model.splice(0, self.branch_model.get_n_items(), [])
            self.branch_model.append(store_label)
            
            for branch in branches:
                self.branch_model.append(branch)
            for tag in tags:
                self.branch_model.append(tag)
            
            new_index = 0
            if current_text and current_text != store_label:
                for i in range(self.branch_model.get_n_items()):
                    if self.branch_model.get_string(i) == current_text:
                        new_index = i
                        break
            
            self.branch_row.set_selected(new_index)
        finally:
            self.branch_row.handler_unblock_by_func(self.on_branch_selected)
    
    def show_loading(self, loading: bool):
        """Show or hide the loading spinner."""
        self.refresh_spinner.set_spinning(loading)
        self.refresh_spinner.set_visible(loading)
        self.refresh_button.set_visible(not loading)
        self.refresh_button.set_sensitive(not loading)
    
    def on_apply_clicked(self, *args):
        """Handle apply button click - reinstall plugin with selected source."""
        if self.is_applying or self.current_plugin_data is None:
            return
        
        if self.current_plugin_data.local_sha is None:
            return
        
        self.is_applying = True
        GLib.idle_add(self.show_applying, True)
        
        threading.Thread(
            target=self._apply_source_thread,
            daemon=True,
            name="apply_source"
        ).start()
    
    def _apply_source_thread(self):
        """Background thread to reinstall plugin with selected source."""
        try:
            plugin_id = self.current_plugin_data.plugin_id
            
            gl.store_backend.uninstall_plugin(
                plugin_id=plugin_id,
                remove_from_pages=False,
                remove_files=False
            )
            
            plugin_data = asyncio.run(
                gl.store_backend.get_plugin_for_id(plugin_id)
            )
            
            if plugin_data is None:
                log.error(f"Failed to get plugin data for {plugin_id}")
                return
            
            asyncio.run(gl.store_backend.install_plugin(plugin_data))
            
            self.current_plugin_data = plugin_data
            
        except Exception as e:
            log.error(f"Error applying source change: {e}")
        finally:
            self.is_applying = False
            GLib.idle_add(self.show_applying, False)
    
    def show_applying(self, applying: bool):
        """Show or hide the applying spinner."""
        self.apply_spinner.set_spinning(applying)
        self.apply_spinner.set_visible(applying)
        self.apply_icon.set_visible(not applying)
        self.apply_row.set_sensitive(not applying)
        self.branch_row.set_sensitive(not applying)
        self.refresh_button.set_sensitive(not applying)

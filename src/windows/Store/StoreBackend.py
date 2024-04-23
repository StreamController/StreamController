"""
Author: Core447
Year: 2023

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This programm comes with ABSOLUTELY NO WARRANTY!

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
 
import sys
from git import Repo
import requests
from async_lru import alru_cache
import json
import asyncio
from PIL import Image
from io import BytesIO
from loguru import logger as log
from datetime import datetime
import subprocess
import time
import os
import uuid
import shutil
from install import install
from packaging import version

# Import GLib
import gi
from gi.repository import GLib

# Import own modules
from src.backend.PluginManager.PluginBase import PluginBase
from src.backend.DeckManagement.HelperMethods import recursive_hasattr

# Import signals
from src.Signals import Signals

# Import globals
import globals as gl

class NoConnectionError:
    pass

class StoreBackend:
    def __init__(self):
        # API cache file
        os.makedirs(os.path.join(gl.DATA_PATH, "Store/cache"), exist_ok=True)
        if not os.path.exists(os.path.join(gl.DATA_PATH, "Store/cache/api.json")):
            with open(os.path.join(gl.DATA_PATH, "Store/cache/api.json"), "w") as f:
                json.dump({}, f, indent=4)
        with open(os.path.join(gl.DATA_PATH, "Store/cache/api.json"), "r") as f:
            self.api_cache = json.load(f)
        
        # Image cache file
        os.makedirs(os.path.join(gl.DATA_PATH, "Store/cache/images"), exist_ok=True)
        if not os.path.exists(os.path.join(gl.DATA_PATH, "Store/cache/images.json")):
            with open(os.path.join(gl.DATA_PATH, "Store/cache/images.json"), "w") as f:
                json.dump({}, f, indent=4)
        with open(os.path.join(gl.DATA_PATH, "Store/cache/images.json"), "r") as f:
            self.image_cache = json.load(f)

        # Manifest cache file
        os.makedirs(os.path.join(gl.DATA_PATH, "Store/cache/manifests"), exist_ok=True)
        if not os.path.exists(os.path.join(gl.DATA_PATH, "Store/cache/manifests.json")):
            with open(os.path.join(gl.DATA_PATH, "Store/cache/manifests.json"), "w") as f:
                json.dump({}, f, indent=4)
        with open(os.path.join(gl.DATA_PATH, "Store/cache/manifests.json"), "r") as f:
            self.manifest_cache = json.load(f)

        # Attribution cache file
        os.makedirs(os.path.join(gl.DATA_PATH, "Store/cache/attribution"), exist_ok=True)
        if not os.path.exists(os.path.join(gl.DATA_PATH, "Store/cache/attribution.json")):
            with open(os.path.join(gl.DATA_PATH, "Store/cache/attribution.json"), "w") as f:
                json.dump({}, f, indent=4)
        with open(os.path.join(gl.DATA_PATH, "Store/cache/attribution.json"), "r") as f:
            self.attribution_cache = json.load(f)

        self.official_authors = asyncio.run(self.get_official_authors())

    async def request_from_url(self, url: str) -> requests.Response:
        try:
            req = requests.get(url, stream=True)
            if req.status_code == 200:
                return req
        except requests.exceptions.ConnectionError as e:
            log.error(e)
            return NoConnectionError()
    
    def build_url(self, repo_url: str, file_path: str, branch_name: str = "main") -> str:
        """
        Replaces the domain in the given repository URL with "raw.githubusercontent.com" and constructs the URL for the specified file path in the repository's branch.

        Parameters:
            repo_url (str): The URL of the repository.
            file_path (str): The path of the file in the repository.
            branch_name (str, optional): The name of the branch or commit sha in the repository. Defaults to "main".

        Returns:
            str: The constructed URL for the specified file path in the repository's branch.
        """
        repo_url = repo_url.replace("github.com", "raw.githubusercontent.com")
        return f"{repo_url}/{branch_name}/{file_path}"

    async def get_remote_file(self, repo_url: str, file_path: str, branch_name: str = "main") -> requests.Response:
        """
        This function retrieves the content of a remote file from a GitHub repository.

        Parameters:
            repo_url (str): The URL of the GitHub repository.
            file_path (str): The path to the file within the repository.
            branch_name (str, optional): The name of the branch to retrieve the file from. Defaults to "main".
                                         Alternatively, you can specify a specific commit hash.

        Returns:
            str: The content of the remote file.

        Note:
            - The function uses an LRU cache to improve performance by caching previously retrieved files.
            - If the file is located in a different domain than github.com, the function will replace the domain
              with raw.githubusercontent.com.
        """
        url = self.build_url(repo_url, file_path, branch_name)

        answer = await self.request_from_url(url)

        return answer
    
    async def get_official_authors(self) -> list:
        result = await self.get_remote_file("https://github.com/StreamController/StreamController-Store", "OfficialAuthors.json")
        if isinstance(result, NoConnectionError):
            return result
        authors_json = result.text
        authors_json = json.loads(authors_json)
        return authors_json
    
    async def get_all_plugins_async(self) -> int:
        """
        returns the number of assets that are new old for the current app version
        """
        n_too_new_assets = 0
        result = await self.get_remote_file("https://github.com/StreamController/StreamController-Store", "Plugins.json")
        if isinstance(result, NoConnectionError):
            return result
        plugins_json = result.text
        try:
            plugins_json = json.loads(plugins_json)
        except json.decoder.JSONDecodeError as e:
            log.error(e)
            return NoConnectionError()

        plugins = []

        for plugin in plugins_json:
            plugin = await self.prepare_plugin(plugin)

            if plugin == NoConnectionError:
                continue

            if isinstance(plugin, dict):
                plugins.append(plugin)

        return plugins
    
    async def get_all_icons(self) -> int:
        """
        returns the number of assets that are too new for the current app version
        """
        n_to_new_assets = 0
        result = await self.get_remote_file("https://github.com/StreamController/StreamController-Store", "Icons.json")
        if isinstance(result, NoConnectionError):
            return result
        icons_json = result.text
        try:
            icons_json = json.loads(icons_json)
        except json.decoder.JSONDecodeError as e:
            log.error(e)
            return NoConnectionError()

        icons = []
        for icon in icons_json:
            icon = await self.prepare_icon(icon)

            if icon == NoConnectionError:
                continue

            if isinstance(icon, dict):
                icons.append(icon)

        return icons
    
    async def get_all_wallpapers(self) -> int:
        """
        returns the number of assets that are too new for the current app version
        """
        n_to_new_assets = 0
        result = await self.get_remote_file("https://github.com/StreamController/StreamController-Store", "Wallpapers.json")
        if isinstance(result, NoConnectionError):
            return result
        wallpapers_json = result.text
        try:
            wallpapers_json = json.loads(wallpapers_json)
        except json.decoder.JSONDecodeError as e:
            log.error(e)
            return NoConnectionError()

        wallpapers = []
        for wallpaper in wallpapers_json:
            wallpaper = await self.prepare_wallpaper(wallpaper)

            if wallpaper == NoConnectionError:
                continue

            if isinstance(wallpaper, dict):
                wallpapers.append(wallpaper)
        
        return wallpapers
    
    async def get_manifest(self, url:str, commit:str) -> dict:
        url = self.build_url(url, "manifest.json", commit)
        # Look for cached manifest - if we have a file for the same commit we can safely assume it's the same
        if url in self.manifest_cache:
            if os.path.isfile(self.manifest_cache[url]):
                with open(self.manifest_cache[url], "r") as f:
                    return json.load(f)

        # Not in cache, get it
        manifest = await self.request_from_url(url)
        if isinstance(manifest, NoConnectionError):
            return manifest
        manifest = json.loads(manifest.text)

        # Save to cache
        cache_file_name = f"{self.get_repo_name(url)}::{commit}"
        path = os.path.join(gl.DATA_PATH, "Store/cache/manifests", f"{cache_file_name}.json")
        with open(path, "w") as f:
            json.dump(manifest, f, indent=4)

        self.remove_old_manifest_cache(url, commit)

        self.manifest_cache[url] = os.path.join(gl.DATA_PATH, "Store/cache/manifests", f"{cache_file_name}.json")
        # Save cache file
        with open(os.path.join(gl.DATA_PATH, "Store/cache/manifests.json"), "w") as f:
            json.dump(self.manifest_cache, f, indent=4)

        return manifest
    
    def remove_old_manifest_cache(self, url:str, commit_sha:str):
        for cached_url in list(self.manifest_cache.keys()):
            if self.get_repo_name(cached_url) == self.get_repo_name(url) and not commit_sha in cached_url:
                if os.path.isfile(self.manifest_cache[cached_url]):
                    os.remove(self.manifest_cache[cached_url])
                del self.manifest_cache[cached_url]

    async def get_attribution(self, url:str, commit:str) -> dict:
        url = self.build_url(url, "attribution.json", commit)
        # Look for cached manifest - if we have a file for the same commit we can safely assume it's the same
        if url in self.attribution_cache:
            if os.path.isfile(self.attribution_cache[url]):
                with open(self.attribution_cache[url], "r") as f:
                    return json.load(f)

        # Not in cache, get it
        attribution = await self.request_from_url(url)
        if isinstance(attribution, NoConnectionError):
            return attribution
        
        if attribution is None:
            return {}

        attribution = json.loads(attribution.text)

        cache_file_name = f"{self.get_repo_name(url)}::{commit}"
        path = os.path.join(gl.DATA_PATH, "Store/cache/attribution", f"{cache_file_name}.json")
        with open(path, "w") as f:
            json.dump(attribution, f, indent=4)

        self.remove_old_attribution_cache(url, commit)

        self.attribution_cache[url] = os.path.join(gl.DATA_PATH, "Store", "cache", "attribution", f"{cache_file_name}.json")
        # Save cache file
        with open(os.path.join(gl.DATA_PATH, "Store/cache/attribution.json"), "w") as f:
            json.dump(self.attribution_cache, f, indent=4)

        return attribution
    
    def remove_old_attribution_cache(self, url:str, commit_sha:str):
        for cached_url in list(self.attribution_cache.keys()):
            if self.get_repo_name(cached_url) == self.get_repo_name(url) and not commit_sha in cached_url:
                if os.path.isfile(self.attribution_cache[cached_url]):
                    os.remove(self.attribution_cache[cached_url])
                del self.attribution_cache[cached_url]

    async def prepare_plugin(self, plugin):
        url = plugin["url"]

        # Check if suitable version is available
        version = self.get_newest_compatible_version(plugin["commits"])
        if version is None:
            return NoCompatibleVersion
        commit = plugin["commits"][version]

        manifest = await self.get_manifest(url, commit)
        if isinstance(manifest, NoConnectionError):
            return manifest

        image = await self.image_from_url(self.build_url(url, manifest.get("thumbnail"), commit))
        if isinstance(manifest, NoConnectionError):
            return image
        
        attribution = await self.get_attribution(url, commit)
        if isinstance(attribution, NoConnectionError):
            return attribution
        attribution = attribution.get("generic", {}) #TODO: Choose correct attribution

        user_name = self.get_user_name(url)
        repo_name = self.get_repo_name(url)

        stargazers = await self.get_stargazers(url)

        return {
            "name": manifest.get("name"),
            "short_description": manifest.get("short-description"),
            "description": manifest.get("description"),
            "url": url,
            "user_name": user_name,
            "repo_name": repo_name,
            "version": manifest.get("version"),
            "image": image,
            "stargazers": stargazers,
            "official": user_name in self.official_authors,
            "commit_sha": commit,
            "id": manifest.get("id"),
            "local-sha": await self.get_local_sha(os.path.join(gl.DATA_PATH, "plugins", manifest.get("id"))),
            "license": attribution.get("license"),
            "copyright": attribution.get("copyright"),
            "license_description": attribution.get("license-description", attribution.get("description")),
            "original_url": attribution.get("original-url"),
        }
    
    async def get_local_sha(self, git_dir: str):
        if not os.path.exists(git_dir):
            return
        try:
            sha = subprocess.check_output(f'cd "{git_dir}" && git rev-parse HEAD', shell=True).decode("utf-8").strip()
        except subprocess.CalledProcessError as e:
            log.error(e)
            return
        return sha
    
    async def prepare_icon(self, icon):
        url = icon["url"]

        # Check if suitable version is available
        version = self.get_newest_compatible_version(icon["commits"])
        if version is None:
            return NoCompatibleVersion
        commit = icon["commits"][version]

        manifest = await self.get_manifest(url, commit)
        if isinstance(manifest, NoConnectionError):
            return manifest
        attribution = await self.get_attribution(url, commit)
        if isinstance(attribution, NoConnectionError):
            return attribution
        attribution = attribution.get("generic", {}) #TODO: Choose correct attribution

        image = await self.image_from_url(self.build_url(url, manifest.get("thumbnail"), commit))
        if isinstance(image, NoConnectionError):
            return image

        description = manifest.get("description")

        user_name = self.get_user_name(url)
        repo_name = self.get_repo_name(url)

        stargazers = await self.get_stargazers(url)
        if isinstance(stargazers, NoConnectionError):
            return stargazers

        return {
            "name": manifest.get("name"),
            "description": description,
            "short_description": manifest.get("short-description"),
            "version": manifest.get("version"),
            "url": url,
            "user_name": user_name,
            "repo_name": repo_name,
            "image": image,
            "stargazers": stargazers,
            "license": attribution.get("license"),
            "copyright": attribution.get("copyright"),
            "original_url": attribution.get("original-url"),
            "license_description": attribution.get("description"),
            "commit_sha": commit,
            "local_sha": await self.get_local_sha(os.path.join(gl.DATA_PATH, "icons", f"{user_name}::{manifest.get('name')}")),
            "official": user_name in self.official_authors
        }
    
    async def prepare_wallpaper(self, wallpaper):
        url = wallpaper["url"]

        # Check if suitable version is available
        version = self.get_newest_compatible_version(wallpaper["commits"])
        if version is None:
            return NoCompatibleVersion
        commit = wallpaper["commits"][version]

        manifest = await self.get_manifest(url, commit)
        if isinstance(manifest, NoConnectionError):
            return manifest
        image = await self.image_from_url(self.build_url(url, manifest.get("thumbnail"), commit))
        if isinstance(image, NoConnectionError):
            return image
        attribution = await self.get_attribution(url, commit)
        if isinstance(attribution, NoConnectionError):
            return attribution
        attribution = attribution.get("generic", {}) #TODO: Choose correct attribution
        
        user_name = self.get_user_name(url)

        return {
            "name": manifest.get("name"),
            "description": manifest.get("description"),
            "short_description": manifest.get("short-description"),
            "version": manifest.get("version"),
            "url": url,
            "user_name": user_name,
            "repo_name": self.get_repo_name(url),
            "image": image,
            "stargazers": await self.get_stargazers(url),
            "license": manifest.get("license"),
            "copyright": manifest.get("copyright"),
            "commit_sha": commit,
            "original_url": attribution.get("original-url"),
            "license_description": attribution.get("description"),
            "local_sha": await self.get_local_sha(os.path.join(gl.DATA_PATH, "wallpapers", f"{user_name}::{manifest.get('name')}")),
            "official": self.get_user_name(url) in self.official_authors
        }

    async def image_from_url(self, url):
        # Search in cache
        if url in self.image_cache:
            if os.path.isfile(self.image_cache[url]):
                return Image.open(self.image_cache[url])
        
        result = await self.request_from_url(url)
        if isinstance(result, NoConnectionError):
            return result
        img = Image.open(BytesIO(result.content))
        
        ## Save to cache
        image_uuid = str(uuid.uuid4())
        save_path = f"Store/cache/images/{self.get_repo_name(url)}::{image_uuid}.png"
        save_path = os.path.join(gl.DATA_PATH, save_path)
        if url in self.image_cache:
            # Remove the old file
            if os.path.isfile(self.image_cache[url]):
                os.remove(self.image_cache[url])
        self.image_cache[url] = save_path
        # Update image cache json file
        with open(os.path.join(gl.DATA_PATH, "Store/cache/images.json"), "w") as f:
            json.dump(self.image_cache, f, indent=4)

        return img
    
    async def get_stargazers(self, repo_url:str) -> int:
        "Deactivated for now because of rate limits"
        return 0
        user_name = self.get_user_name(repo_url)
        repo_name = self.get_repo_name(repo_url)

        url = f"https://api.github.com/repos/{user_name}/{repo_name}"
        api_answer = await self.make_api_call(url)
        return api_answer["stargazers_count"]
    
    async def make_api_call(self, api_call_url:str) -> dict:
        async def call():
            log.trace(f"Making API call: {api_call_url}")
            resp = await self.request_from_url(api_call_url)
            if isinstance(resp, NoConnectionError):
                return resp
            self.api_cache[api_call_url] = {}
            self.api_cache[api_call_url]["answer"] = resp.json()
            self.api_cache[api_call_url]["time-code"] = datetime.now().strftime("%d-%m-%y-%H-%M")
            with open(os.path.join(gl.DATA_PATH, "Store/cache/api.json"), "w") as f:
                json.dump(self.api_cache, f, indent=4)
            return resp.json()

        if api_call_url not in self.api_cache:
            return await call()

        # get time from cached result
        t = self.api_cache[api_call_url]["time-code"]
        t_int = datetime.strptime(t, "%d-%m-%y-%H-%M").timestamp()
        t_delta = time.time()-t_int

        if t_delta > 3600:
            return await call()
        
        # Cached
        return self.api_cache[api_call_url]["answer"]

    def get_user_name(self, repo_url:str) -> str:
        splitted =  repo_url.split("/")
        return splitted[splitted.index("github.com")+1]
    
    def get_repo_name(self, repo_url:str) -> str:
        github_split = repo_url.split("github")
        if len(github_split) < 2:
            return
        split = github_split[1].split("/")
        if len(split) < 3:
            return
        return split[2]
    
    def get_all_plugins(self):
        return asyncio.run(self.get_all_plugins_async())
    
    def get_newest_compatible_version(self, available_versions: list[str]) -> str:
        if gl.exact_app_version_check:
            if gl.app_version in available_versions:
                return gl.app_version
            else:
                return None
            
        current_major = version.parse(gl.app_version).major

        compatible_versions = [v for v in available_versions if version.parse(v).major == current_major]
        if compatible_versions:
            return max(compatible_versions)
        else:
            return None

    ## Install
    async def subp_call(self, args):
        return subprocess.call(args)
    
    async def os_sys(self, args):
        return os.system(args)
    
    async def clone_repo(self, repo_url:str, local_path:str, commit_sha:str = None, branch_name:str = None):
        # if branch_name == None and commit_sha == None:
            # Set branch_name to main branch's name
            # api_answer = await self.make_api_call(f"https://api.github.com/repos/{self.get_user_name(repo_url)}/{self.get_repo_name(repo_url)}")
            # branch_name = api_answer["default_branch"]

        if commit_sha is not None:
            # Use the main branch for the initial clone
            branch_name = None

        # Check if git is installed on the system - should be the case for most linux systems
        if shutil.which("git") is None:
            log.error("Git is not installed on this system. Please install it.")
            return 404
        
        # Remove folder if it already exists
        shutil.rmtree(local_path, ignore_errors=True)

        # Clone the repository at the newest stage on the default branch
        await self.subp_call(["git", "clone", repo_url, local_path])

        # Add repository to the safe directory list to avoid dubious ownership warnings
        # FIXME: Check if not already added
        await self.subp_call(["git", "config", "--global", "--add", "safe.directory", os.path.abspath(local_path)])

        # Set repository to the given commit_sha
        if commit_sha is not None:
            await self.os_sys(f"cd '{local_path}' && git reset --hard {commit_sha}")
            return
        
        if branch_name is not None:
            await self.os_sys(f"cd '{local_path}' && git switch {branch_name}")
            return
        
    async def install_plugin(self, plugin_dict:dict, auto_update: bool = False):
        url = plugin_dict["url"]

        PLUGINS_FOLDER = "plugins"
        local_path = os.path.join(gl.DATA_PATH, PLUGINS_FOLDER, plugin_dict["id"])

        response = await self.clone_repo(repo_url=url, local_path=local_path, commit_sha=plugin_dict["commit_sha"])

        # Run install script if present
        if os.path.isfile(os.path.join(local_path, "__install__.py")):
            subprocess.run(f"python3 {os.path.join(local_path, '__install__.py')}", shell=True, start_new_session=True)

        # Install requirements from requirements.txt
        if os.path.isfile(os.path.join(local_path, "requirements.txt")):
            subprocess.run(f"pip install -r {os.path.join(local_path, 'requirements.txt')}", shell=True, start_new_session=True)
            
        if response == 404:
            return 404
        
        # Update plugin manager
        gl.plugin_manager.load_plugins()
        gl.plugin_manager.init_plugins()
        gl.plugin_manager.generate_action_index()
        plugins = gl.plugin_manager.get_plugins()

        # Update ui
        if recursive_hasattr(gl, "app.main_win.sidebar.action_chooser"):
            GLib.idle_add(gl.app.main_win.sidebar.action_chooser.plugin_group.update)

        ## Update page
        for controller in gl.deck_manager.deck_controller:
            ## Checks required to prevent errors after auto-update
            if hasattr(controller, "active_page"):
                if controller.active_page is not None:
                    # Load action objects
                    controller.active_page.action_objects = {}
                    controller.active_page.load_action_objects()
                    # Reload page to send new on_ready events
                    controller.load_page(controller.active_page)

        # Notify plugin actions
        gl.signal_manager.trigger_signal(Signals.PluginInstall, plugin_dict["id"])

        log.success(f"Plugin {plugin_dict['id']} installed successfully under: {local_path} with sha: {plugin_dict['commit_sha']}")
    def uninstall_plugin(self, plugin_id:str, remove_from_pages:bool = False, remove_files:bool = True) -> bool:
        ## 1. Remove all action objects in all pages
        for deck_controller in gl.deck_manager.deck_controller:
            # Track all keys controlled by this plugin
            if deck_controller.active_page is None:
                continue
            keys = deck_controller.active_page.get_keys_with_plugin(plugin_id=plugin_id)

            deck_controller.active_page.remove_plugin_action_objects(plugin_id=plugin_id)
            if remove_from_pages:
                deck_controller.active_page.remove_plugin_actions_from_json(plugin_id=plugin_id)

            # Clear all keys in this page which were controlled by this plugin
            for key in keys:
                key_index = deck_controller.coords_to_index(key.split("x"))
                deck_controller.load_key(key_index, deck_controller.active_page)

        ## 2. Inform plugin base
        plugins = gl.plugin_manager.get_plugins()
        plugin = gl.plugin_manager.get_plugin_by_id(plugin_id)
        if plugin is None:
            return
        if remove_files:
            plugin.on_uninstall()
            
            ## 3. Remove plugin folder
            shutil.rmtree(plugin.PATH)

        ## 4. Delete plugin base object
        # plugin_obj = gl.plugin_manager.get_plugin_by_id(plugin_id)
        gl.plugin_manager.remove_plugin_from_list(plugin)

        del plugin

        GLib.idle_add(gl.app.main_win.sidebar.action_chooser.plugin_group.update)

        GLib.idle_add(gl.app.main_win.sidebar.page_selector.update)

        # Remove from sys.modules
        module_name = f"plugins.{plugin_id}.main"
        if module_name in sys.modules:
            del sys.modules[module_name]

    async def install_icon(self, icon_dict:dict):
        folder_name = f"{icon_dict['user_name']}::{icon_dict['name']}"
        icon_path = os.path.join(gl.DATA_PATH, "icons", folder_name)
        os.makedirs(icon_path, exist_ok=True)

        await self.uninstall_icon(icon_dict)

        await self.clone_repo(
            repo_url=icon_dict["url"],
            local_path=icon_path,
            commit_sha=icon_dict["commit_sha"]
        )

    async def uninstall_icon(self, icon_dict:dict):
        folder_name = f"{icon_dict['user_name']}::{icon_dict['name']}"
        if os.path.exists(os.path.join(gl.DATA_PATH, "icons", folder_name)):
            shutil.rmtree(os.path.join(gl.DATA_PATH, "icons", folder_name))

    async def install_wallpaper(self, wallpaper_dict:dict):
        folder_name = f"{wallpaper_dict['user_name']}::{wallpaper_dict['name']}"
        wallpaper_path = os.path.join(gl.DATA_PATH, "wallpapers", folder_name)
        os.makedirs(wallpaper_path, exist_ok=True)

        await self.uninstall_wallpaper(wallpaper_dict)

        await self.clone_repo(
            repo_url=wallpaper_dict["url"],
            local_path=wallpaper_path,
            commit_sha=wallpaper_dict["commit_sha"]
        )

    async def uninstall_wallpaper(self, wallpaper_dict:dict):
        folder_name = f"{wallpaper_dict['user_name']}::{wallpaper_dict['name']}"
        if os.path.exists(os.path.join(gl.DATA_PATH, "wallpapers", folder_name)):
            shutil.rmtree(os.path.join(gl.DATA_PATH, "wallpapers", folder_name))

    async def get_plugin_for_id(self, plugin_id):
        plugins = await self.get_all_plugins_async()
        for plugin in plugins:
            if plugin["id"] == plugin_id:
                return plugin
            
    ## Updates
    async def get_plugins_to_update(self):
        plugins = await self.get_all_plugins_async()
        if isinstance(plugins, NoConnectionError):
            return plugins

        plugins_to_update: list[dict] = []

        for plugin in plugins:
            if plugin["local-sha"] is None:
                # Plugin is not installed
                continue
            if plugin["local-sha"] != plugin["commit_sha"]:
                plugins_to_update.append(plugin)

        return plugins_to_update
    
    async def update_all_plugins(self) -> int:
        """
        Returns number of updated plugins
        """
        plugins_to_update = await self.get_plugins_to_update()
        if isinstance(plugins_to_update, NoConnectionError):
            return plugins_to_update
        for plugin in plugins_to_update:
            try:
                await self.uninstall_plugin(plugin["id"], remove_from_pages=False, remove_files=False)
            except Exception as e:
                log.error(e)
            await self.install_plugin(plugin)
        
        return len(plugins_to_update)

    async def get_icons_to_update(self):
        icons = await self.get_all_icons()
        if isinstance(icons, NoConnectionError):
            return icons

        icons_to_update: list[dict] = []

        for icon in icons:
            if icon["local_sha"] is None:
                # Plugin is not installed
                continue
            if icon["local_sha"] != icon["commit_sha"]:
                icons_to_update.append(icon)
                
        return icons_to_update
    
    async def update_all_icons(self) -> int:
        """
        Returns number of updated icons
        """
        icons_to_update = await self.get_icons_to_update()
        if isinstance(icons_to_update, NoConnectionError):
            return icons_to_update
        for icon in icons_to_update:
            await self.install_icon(icon)

        return len(icons_to_update)
    
    async def get_wallpapers_to_update(self):
        wallpapers = await self.get_all_wallpapers()
        if isinstance(wallpapers, NoConnectionError):
            return wallpapers

        wallpapers_to_update: list[dict] = []

        for wallpaper in wallpapers:
            if wallpaper["local_sha"] is None:
                # Plugin is not installed
                continue
            if wallpaper["local_sha"] != wallpaper["commit_sha"]:
                wallpapers_to_update.append(wallpaper)

        return wallpapers_to_update
    
    async def update_all_wallpapers(self) -> int:
        """
        Returns number of updated wallpapers
        """
        wallpapers_to_update = await self.get_wallpapers_to_update()
        if isinstance(wallpapers_to_update, NoConnectionError):
            return wallpapers_to_update
        for wallpaper in wallpapers_to_update:
            await self.install_wallpaper(wallpaper)

        return len(wallpapers_to_update)

    async def update_everything(self) -> int:
        """
        Returns number of updated assets
        """
        n_plugins = await self.update_all_plugins()
        n_icons = await self.update_all_icons()
        n_wallpapers = await self.update_all_wallpapers()

        if isinstance(n_plugins, NoConnectionError) or isinstance(n_icons, NoConnectionError):
            return NoConnectionError()

        return n_plugins + n_icons + n_wallpapers

class NoCompatibleVersion:
    pass
            

        
b = StoreBackend()
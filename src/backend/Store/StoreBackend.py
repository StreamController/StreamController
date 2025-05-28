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
import zipfile
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
from packaging import version
import urllib.request

# Import GLib
import gi
from gi.repository import GLib

# Import own modules
from autostart import is_flatpak
from src.backend.Store.StoreCache import StoreCache
from src.backend.PluginManager.PluginBase import PluginBase
from src.backend.DeckManagement.HelperMethods import recursive_hasattr

# Import signals
from src.Signals import Signals

# Import globals
import globals as gl
from src.windows.Store.StoreData import PluginData, IconData, WallpaperData


class NoConnectionError:
    pass

class StoreBackend:
    STORE_REPO_URL = "https://github.com/StreamController/StreamController-Store" #"https://github.com/StreamController/StreamController-Store"
    STORE_CACHE_PATH = "Store/cache"
    # STORE_CACHE_PATH = os.path.join(gl.DATA_PATH, STORE_CACHE_PATH)
    STORE_BRANCH = "1.5.0"


    def __init__(self):
        self.store_cache = StoreCache()

        self.official_store_branch_cache: str = None

        self.official_authors = asyncio.run(self.get_official_authors())

    async def get_stores(self) -> list[tuple[str, str]]:
        settings = gl.settings_manager.get_app_settings()

        stores = []
        branch = await self.get_official_store_branch()
        log.info(f"Official store branch: {branch}")
        stores.append((self.STORE_REPO_URL, branch))

        if settings.get("store", {}).get("enable-custom-stores", False):
            for store in settings.get("store", {}).get("custom-stores", {}):
                stores.append((store.get("url"), store.get("branch")))

        return stores
    
    def get_custom_plugins(self) -> list[tuple[str, str]]:
        settings = gl.settings_manager.get_app_settings()

        plugins = []
        if settings.get("store", {}).get("enable-custom-plugins", False):
            for plugin in settings.get("store", {}).get("custom-plugins", []):
                plugins.append((plugin.get("url"), plugin.get("branch")))

        return plugins
    
    async def get_official_store_branch(self) -> str:
        if self.official_store_branch_cache is not None:
            return self.official_store_branch_cache
        versions_file = await self.get_remote_file(self.STORE_REPO_URL, "versions.json", branch_name="versions", force_refetch=True)
        if isinstance(versions_file, NoConnectionError):
            return versions_file
        versions = json.loads(versions_file)
        v = versions.get(gl.APP_VERSION, "main")
        self.official_store_branch_cache = v
        return v

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

    async def get_remote_file(self, repo_url: str, file_path: str, branch_name: str = "main", data_type: str = "text", force_refetch: bool = False):
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
        byte_suffix = ""
        if data_type == "content":
            byte_suffix = "b"

        is_cached = False
        if not force_refetch:
            is_cached = self.store_cache.is_cached(
                url=repo_url,
                branch=branch_name,
                path=file_path
            )
        if is_cached:
            with self.store_cache.open_cache_file(url=repo_url, branch=branch_name, path=file_path, mode=f"r{byte_suffix}") as f:
                return f.read()
        else:
            pass

        url = self.build_url(repo_url, file_path, branch_name)

        answer = await self.request_from_url(url)

        if isinstance(answer, NoConnectionError):
            return answer
        
        if answer is None:
            return
        
        with self.store_cache.open_cache_file(url=repo_url, branch=branch_name, path=file_path, mode=f"w{byte_suffix}") as f:
            if answer is None:
                return
            if data_type == "text":
                f.write(answer.text)
            elif data_type == "content":
                f.write(answer.content)

        if data_type == "text":
            return answer.text
        elif data_type == "content":
            return answer.content
        
    async def get_last_commit(self, repo_url: str, branch_name: str = "main") -> str:
        url = f"https://api.github.com/repos/{self.get_user_name(repo_url)}/{self.get_repo_name(repo_url)}/commits?sha={branch_name}&per_page=1"
        response = requests.get(url)

        if response.status_code != 200:
            return
        
        commits = response.json()
        if len(commits) == 0:
            return
        return commits[0].get("sha")
    
    async def get_official_authors(self) -> list:
        authors_json = await self.get_remote_file(self.STORE_REPO_URL, "OfficialAuthors.json", self.STORE_BRANCH, force_refetch=True)
        if isinstance(authors_json, NoConnectionError):
            return authors_json
        authors_json = json.loads(authors_json)
        return authors_json
    
    async def fetch_and_parse_store_json(self, url: str, filename: str, branch: str, n_stores_with_errors: int = 0):
        try:
            store_file_json = await self.get_remote_file(url, filename, branch, force_refetch=True)
            if isinstance(store_file_json, NoConnectionError):
                n_stores_with_errors += 1
                return None, n_stores_with_errors
            store_file_json = json.loads(store_file_json)
            return store_file_json, n_stores_with_errors
        except (json.decoder.JSONDecodeError, TypeError) as e:
            n_stores_with_errors += 1
            log.error(e)
            return None, n_stores_with_errors

    async def process_store_data(self, filename: str, process_func: callable, get_custom_func: callable, data_class, include_images=True):
        n_stores_with_errors = 0
        data_list = []

        stores = await self.get_stores()

        for url, branch in stores:
            store_file_json, n_stores_with_errors = await self.fetch_and_parse_store_json(url, filename, branch, n_stores_with_errors)
            if store_file_json is not None:
                data_list.extend(store_file_json)

        if n_stores_with_errors >= len(stores):
            return NoConnectionError()

        prepare_tasks = [process_func(data, include_images, True) for data in data_list]

        if get_custom_func is not None:
            for url, branch in get_custom_func():
                asset = {
                    "url": url,
                    "branch": branch
                }
                prepare_tasks.append(process_func(asset, include_images, False))

        results = await asyncio.gather(*prepare_tasks)
        results = [result for result in results if isinstance(result, data_class)]

        return results

    async def get_all_plugins_async(self, include_images: bool = True) -> int:
        return await self.process_store_data("Plugins.json", self.prepare_plugin, self.get_custom_plugins, PluginData, include_images)

    async def get_all_icons(self) -> int:
        return await self.process_store_data("Icons.json", self.prepare_icon, None, IconData)

    async def get_all_wallpapers(self) -> int:
        return await self.process_store_data("Wallpapers.json", self.prepare_wallpaper, None, WallpaperData)
    
    async def get_manifest(self, url:str, commit:str) -> dict:
        # url = self.build_url(url, "manifest.json", commit)
        manifest = await self.get_remote_file(url, "manifest.json", commit)
        if isinstance(manifest, NoConnectionError):
            return manifest
        if manifest is None:
            return
        return json.loads(manifest)
    
    def remove_old_manifest_cache(self, url:str, commit_sha:str):
        for cached_url in list(self.manifest_cache.keys()):
            if self.get_repo_name(cached_url) == self.get_repo_name(url) and not commit_sha in cached_url:
                if os.path.isfile(self.manifest_cache[cached_url]):
                    os.remove(self.manifest_cache[cached_url])
                del self.manifest_cache[cached_url]

    async def get_attribution(self, url:str, commit:str) -> dict:
        result = await self.get_remote_file(url, "attribution.json", commit)
        if isinstance(result, NoConnectionError):
            return result
        
        try:
            return json.loads(result)
        except (json.decoder.JSONDecodeError, TypeError) as e:
            return {}
    
    def remove_old_attribution_cache(self, url:str, commit_sha:str):
        for cached_url in list(self.attribution_cache.keys()):
            if self.get_repo_name(cached_url) == self.get_repo_name(url) and not commit_sha in cached_url:
                if os.path.isfile(self.attribution_cache[cached_url]):
                    os.remove(self.attribution_cache[cached_url])
                del self.attribution_cache[cached_url]

    async def prepare_plugin(self, plugin, include_image: bool = True, verified: bool = False):
        url = plugin["url"]

        # Check if suitable version is available
        compatible = True
        commit: str = None
        if "commits" in plugin:
            version = self.get_newest_compatible_version(plugin["commits"])
            if version is None:
                compatible = False
                version = self.get_newest_version(list(plugin["commits"].keys()))
                if version is None:
                    return NoCompatibleVersion #TODO
            commit = plugin["commits"][version]

        branch = plugin.get("branch")
        if branch is not None:
            commit = await self.get_last_commit(url, branch)

        manifest = await self.get_manifest(url, commit or branch)
        if isinstance(manifest, NoConnectionError):
            return manifest

        image = None
        thumbnail_path = manifest.get("thumbnail")
        if include_image:
            image = await self.get_web_image(url, thumbnail_path, commit or branch)
            if isinstance(manifest, NoConnectionError):
                return image
        
        attribution = await self.get_attribution(url, commit or branch)
        if isinstance(attribution, NoConnectionError):
            return attribution
        attribution = attribution.get("generic", {}) #TODO: Choose correct attribution

        stargazers = await self.get_stargazers(url)

        author = self.get_user_name(url)

        translated_description = gl.lm.get_custom_translation(manifest.get("descriptions", {}))
        translated_short_description = gl.lm.get_custom_translation(manifest.get("short-descriptions", {}))

        return PluginData(
            descriptions=manifest.get("descriptions") or None,
            short_descriptions=manifest.get("short-descriptions") or None,
            description=translated_description or manifest.get("description"),
            short_description=translated_short_description or manifest.get("short-description"),

            github=url or None,
            author=author or None, # Formerly: user_name
            official=author in self.official_authors or False,
            commit_sha=commit,
            branch=branch,
            local_sha=await self.get_local_sha(os.path.join(gl.PLUGIN_DIR, manifest.get("id"))),
            minimum_app_version=manifest.get("minimum-app-version") or None,
            app_version=manifest.get("app-version") or None,
            repository_name=self.get_repo_name(url),
            tags=manifest.get("tags") or None,

            thumbnail=thumbnail_path or None,
            image=image or None,

            copyright=attribution.get("copyright") or None,
            original_url=attribution.get("original-url") or None,
            license=attribution.get("licence") or None,
            license_descriptions=attribution.get("licence-descriptions", attribution.get("descriptions")) or None,

            plugin_name=manifest.get("name") or None,
            plugin_version=manifest.get("version") or None,
            plugin_id=manifest.get("id") or None,

            is_compatible=compatible,
            verified=verified
        )
    
    def get_current_git_commit_hash_without_git(self, repo_path: str) -> str:
        try:
            # Construct the path to the FETCH_HEAD file
            fetch_head_path = os.path.join(repo_path, '.git', 'FETCH_HEAD')
            
            # Read the contents of the FETCH_HEAD file
            with open(fetch_head_path, 'r') as file:
                lines = file.readlines()
                
                # The first line contains the latest commit hash
                if lines:
                    latest_commit_hash = lines[0].split()[0]
                    return latest_commit_hash
                else:
                    raise ValueError("FETCH_HEAD file is empty")
                    
        except Exception as e:
            raise RuntimeError(f"Unable to retrieve git commit hash: {e}")
    
    async def get_local_sha(self, git_dir: str):
        if not os.path.exists(git_dir):
            return
        
        if os.path.exists(os.path.join(git_dir, ".git")):
            try:
                sha = self.get_current_git_commit_hash_without_git(git_dir)
                if sha is not None:
                    return sha
            except (ValueError, RuntimeError) as e:
                log.error(e)

        version_file_path = os.path.join(git_dir, "VERSION")
        if not os.path.exists(version_file_path):
            return ""
        
        with open(version_file_path, "r") as f:
            return f.read().strip()
    
    async def prepare_icon(self, icon, include_image: bool = True, verified: bool = False):
        if not include_image:
            raise NotImplementedError("Not yet implemented") #TODO
        if "url" not in icon:
            return None

        url = icon["url"]

        # Check if suitable version is available
        compatible = True
        version = self.get_newest_compatible_version(icon["commits"])
        if version is None:
            compatible = False
            version = self.get_newest_version(list(icon["commits"].keys()))
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

        thumbnail_path = manifest.get("thumbnail")
        image = await self.get_web_image(url, thumbnail_path, commit)
        if isinstance(image, NoConnectionError):
            return image

        author = self.get_user_name(url)

        stargazers = await self.get_stargazers(url)
        if isinstance(stargazers, NoConnectionError):
            return stargazers
        
        translated_description = gl.lm.get_custom_translation(manifest.get("descriptions", {}))
        translated_short_description = gl.lm.get_custom_translation(manifest.get("short-descriptions", {}))

        return IconData(
            description=translated_description or manifest.get("description"),
            short_description=translated_short_description or manifest.get("short-description"),

            github=url or None,
            descriptions=manifest.get("descriptions") or None,
            short_descriptions=manifest.get("short-descriptions") or None,
            author=author or None,  # Formerly: user_name
            official=author in self.official_authors or False,
            commit_sha=commit,
            local_sha=await self.get_local_sha(os.path.join(gl.DATA_PATH, "icons", (manifest.get("id") or ""))),
            minimum_app_version=manifest.get("minimum-app-version") or None,
            app_version=manifest.get("app-version") or None,
            repository_name=self.get_repo_name(url),
            tags=manifest.get("tags") or None,

            thumbnail=thumbnail_path or None,
            image=image or None,

            copyright=attribution.get("copyright") or None,
            original_url=attribution.get("original-url") or None,
            license=attribution.get("licence") or None,
            license_descriptions=attribution.get("licence-descriptions", attribution.get("descriptions")) or None,

            icon_name=manifest.get("name") or None,
            icon_version=manifest.get("version") or None,
            icon_id=manifest.get("id") or None,

            is_compatible=compatible,
            verified=verified
        )

    
    async def prepare_wallpaper(self, wallpaper, include_image: bool = True, verified: bool = False):
        if not include_image:
            raise NotImplementedError("Not yet implemented") #TODO
        if "url" not in wallpaper:
            return None

        url = wallpaper["url"]

        # Check if suitable version is available
        compatible = True
        version = self.get_newest_compatible_version(wallpaper["commits"])
        if version is None:
            compatible = False
            version = self.get_newest_version(list(wallpaper["commits"].keys()))
            if version is None:
                return NoCompatibleVersion
        commit = wallpaper["commits"][version]

        manifest = await self.get_manifest(url, commit)
        if isinstance(manifest, NoConnectionError):
            return manifest

        thumbnail_path = manifest.get("thumbnail")
        image = await self.get_web_image(url, thumbnail_path, commit)
        if isinstance(image, NoConnectionError):
            return image
        attribution = await self.get_attribution(url, commit)
        if isinstance(attribution, NoConnectionError):
            return attribution
        attribution = attribution.get("generic", {}) #TODO: Choose correct attribution
        
        author = self.get_user_name(url)

        translated_description = gl.lm.get_custom_translation(manifest.get("descriptions", {}))
        translated_short_description = gl.lm.get_custom_translation(manifest.get("short-descriptions", {}))

        return WallpaperData(
            description=translated_description or manifest.get("description"),
            short_description=translated_short_description or manifest.get("short-description"),

            github=url or None,
            descriptions=manifest.get("descriptions") or None,
            short_descriptions=manifest.get("short-descriptions") or None,
            author=author or None,  # Formerly: user_name
            official=author in self.official_authors or False,
            commit_sha=commit,
            local_sha=await self.get_local_sha(os.path.join(gl.DATA_PATH, "wallpapers", (manifest.get("id") or ""))),
            minimum_app_version=manifest.get("minimum-app-version") or None,
            app_version=manifest.get("app-version") or None,
            repository_name=self.get_repo_name(url),
            tags=manifest.get("tags") or None,

            thumbnail=thumbnail_path or None,
            image=image or None,

            copyright=attribution.get("copyright") or None,
            original_url=attribution.get("original-url") or None,
            license=attribution.get("licence") or None,
            license_descriptions=attribution.get("licence-descriptions", attribution.get("descriptions")) or None,

            wallpaper_name=manifest.get("name") or None,
            wallpaper_version=manifest.get("version") or None,
            wallpaper_id=manifest.get("id") or None,

            is_compatible=compatible,
            verified=verified
        )

    async def get_web_image(self, url: str, path: str, branch: str = "main") -> Image:
        try:
            result = await self.get_remote_file(url, path, branch, data_type="content")
        except:
            return
        if isinstance(result, NoConnectionError):
            return result
        try:
            return Image.open(BytesIO(result))
        except:
            return
    
    async def get_stargazers(self, repo_url: str) -> int:
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
            with open(os.path.join(gl.DATA_PATH, self.STORE_CACHE_PATH, "api.json"), "w") as f:
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
    
    def get_all_plugins(self, include_images: bool = True) -> list[PluginData]:
        return asyncio.run(self.get_all_plugins_async(include_images))
    
    def get_newest_compatible_version(self, available_versions: list[str]) -> str:
        if gl.exact_app_version_check:
            if gl.APP_VERSION in available_versions:
                return gl.APP_VERSION
            else:
                return None
            
        current_major = version.parse(gl.APP_VERSION).major

        compatible_versions = [v for v in available_versions if version.parse(v).major == current_major]
        parsed_compatible_versions = [version.parse(v) for v in compatible_versions]

        if compatible_versions:
            max_index = parsed_compatible_versions.index(max(parsed_compatible_versions))
            return compatible_versions[max_index]
        else:
            return None
        
    def get_newest_version(self, available_versions: list[str]) -> str:
        parsed_versions = [version.parse(v) for v in available_versions]
        
        max_index = parsed_versions.index(max(parsed_versions))
        return available_versions[max_index]

    ## Install
    async def subp_call(self, args):
        return subprocess.call(args)
    
    async def os_sys(self, args):
        return os.system(args)
    
    def get_main_folder_of_zip(self, zip_path: str) -> str:
        extracted_folder_name = None
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_contents = zip_ref.namelist()
            for item in zip_contents:
                if not item.endswith("/"): # Directories end with /
                    continue
                if item.count("/") > 1:
                    continue
                
                if extracted_folder_name is not None:
                    log.error("Multiple folders in zip")
                    return 400
                extracted_folder_name = item.split("/")[0]


        if extracted_folder_name is None:
            log.error("Could not find extracted folder name")
            return 400
        
        return extracted_folder_name
    
    async def download_repo(self, repo_url:str, directory:str, commit_sha:str = None, branch_name:str = None):
        if not is_flatpak() and gl.argparser.parse_args().devel:
            await self.clone_repo(repo_url, directory, commit_sha, branch_name)
            return


        username = self.get_user_name(repo_url)
        projectname = self.get_repo_name(repo_url).lower()
        sha = commit_sha
        if commit_sha is None and branch_name is not None:
            # Used to write the version
            sha = self.get_last_commit(repo_url, branch_name)
        zip_url = f"https://github.com/{username}/{projectname}/archive/{sha}.zip"
        
        # Download
        try:
            # Create cache dir
            os.makedirs(os.path.join(gl.DATA_PATH, "cache"), exist_ok=True)
            urllib.request.urlretrieve(zip_url, os.path.join(gl.DATA_PATH, "cache", f"{projectname}-{sha}.zip"))
        except TypeError as e:
            log.error(e)
            return NoConnectionError()
        
        ## Extract
        if os.path.exists(os.path.join(gl.DATA_PATH, "cache", f"{projectname}-{sha}")):
            shutil.rmtree(os.path.join(gl.DATA_PATH, "cache", f"{projectname}-{sha}"))
        shutil.unpack_archive(os.path.join(gl.DATA_PATH, "cache", f"{projectname}-{sha}.zip"), os.path.join(gl.DATA_PATH, "cache"))


        ## Why - because github is not case sensitive for the urls, so the casing of the zip file might be different than the one of the contained folder
        extracted_folder_name = self.get_main_folder_of_zip(os.path.join(gl.DATA_PATH, "cache", f"{projectname}-{sha}.zip"))
        
        extracted_folder = os.path.join(gl.DATA_PATH, "cache", extracted_folder_name)

        # Remove destination folder
        if os.path.isdir(directory):
            shutil.rmtree(directory)
        if os.path.isfile(directory): # No idea how this could happen - but just in case
            os.remove(directory)

        # Create empty destination folder
        os.makedirs(directory, exist_ok=True)

        for name in os.listdir(extracted_folder):
            shutil.move(os.path.join(extracted_folder, name), directory)


        os.remove(os.path.join(gl.DATA_PATH, "cache", f"{projectname}-{sha}.zip"))
        shutil.rmtree(extracted_folder)
        
        ## Write version
        path = os.path.join(directory, "VERSION")
        with open(path, "w") as f:
            f.write(sha)
        
        return 200
    
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

        # Run git pull to create .git/FETCH_HEAD. This allows us to check for available updates
        await self.os_sys(f"cd '{local_path}' && git pull")


        ## Write version
        path = os.path.join(local_path, "VERSION")
        with open(path, "w") as f:
            f.write(commit_sha or branch_name)

        # Set repository to the given commit_sha
        if commit_sha is not None:
            await self.os_sys(f"cd '{local_path}' && git reset --hard {commit_sha}")
            return
        
        if branch_name is not None:
            await self.os_sys(f"cd '{local_path}' && git switch {branch_name}")
            return
        
        
    async def install_plugin(self, plugin_data:PluginData, auto_update: bool = False):
        url = plugin_data.github

        local_path = os.path.join(gl.PLUGIN_DIR, plugin_data.plugin_id)

        response = await self.download_repo(repo_url=url, directory=local_path, commit_sha=plugin_data.commit_sha, branch_name=plugin_data.branch)

        # Run install script if present. Make sure to use python binary used to run this process to not break venv dependency installations
        if os.path.isfile(os.path.join(local_path, "__install__.py")):
            subprocess.run(f"{sys.executable} {os.path.join(local_path, '__install__.py')}", shell=True, start_new_session=True)

        # Install requirements from requirements.txt
        if os.path.isfile(os.path.join(local_path, "requirements.txt")):
            subprocess.run(f"{sys.executable} -m pip install -r {os.path.join(local_path, 'requirements.txt')}", shell=True, start_new_session=True)

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
                    controller.active_page.load_action_objects()
                    controller.load_page(controller.active_page)

        # Notify plugin actions
        gl.signal_manager.trigger_signal(Signals.PluginInstall, plugin_data.plugin_id)

        log.success(f"Plugin {plugin_data.plugin_id} installed successfully under: {local_path} with sha: {plugin_data.commit_sha}")
        
    def uninstall_plugin(self, plugin_id:str, remove_from_pages:bool = False, remove_files:bool = True) -> bool:
        ## 1. Remove all action objects in all pages
        for deck_controller in gl.deck_manager.deck_controller:
            # Track all keys controlled by this plugin
            if deck_controller.active_page is None:
                continue
            #keys = deck_controller.active_page.get_keys_with_plugin(plugin_id=plugin_id)

            deck_controller.active_page.remove_plugin_action_objects(plugin_id=plugin_id)
            if remove_from_pages:
                deck_controller.active_page.remove_plugin_actions_from_json(plugin_id=plugin_id)

            #TODO: figure out
            # Clear all keys in this page which were controlled by this plugin
            #for key in keys:
            #    key_index = deck_controller.coords_to_index(key.split("x"))
            #    deck_controller.load_key(key_index, deck_controller.active_page)

        ## 2. Inform plugin base
        plugins = gl.plugin_manager.get_plugins()
        plugin = gl.plugin_manager.get_plugin_by_id(plugin_id)
        if plugin is None:
            return
        if remove_files:
            plugin.on_uninstall()
            
            ## 3. Remove plugin folder
            if os.path.islink(plugin.PATH):
                symlink_target = os.readlink(plugin.PATH)
                log.warning(f"Plugin {plugin.plugin_name} is inside a Symlink!")
                plugin.PATH = symlink_target

            shutil.rmtree(plugin.PATH)

        ## 4. Delete plugin base object
        # plugin_obj = gl.plugin_manager.get_plugin_by_id(plugin_id)
        gl.plugin_manager.remove_plugin_from_list(plugin)

        gl.plugin_manager.generate_action_index()


        del plugin

        GLib.idle_add(gl.app.main_win.sidebar.action_chooser.plugin_group.update)
        GLib.idle_add(gl.app.main_win.sidebar.page_selector.update)


        base_module = f"plugins.{plugin_id}"
        for module in sys.modules.copy():
            if module.startswith(base_module):
                del sys.modules[module]

        # for controller in gl.deck_manager.deck_controller:
            # controller.active_page.update_inputs_with_actions_from_plugin(plugin_id)

        ## Update page
        for controller in gl.deck_manager.deck_controller:
            ## Checks required to prevent errors after auto-update
            if hasattr(controller, "active_page"):
                if controller.active_page is not None:
                    # Load action objects
                    controller.active_page.load_action_objects()
                    controller.load_page(controller.active_page)

    async def install_icon(self, icon_data:IconData):
        icon_path = os.path.join(gl.DATA_PATH, "icons", icon_data.icon_id)

        await self.uninstall_icon(icon_data)

        await self.download_repo(repo_url=icon_data.github, directory=icon_path, commit_sha=icon_data.commit_sha)

    async def uninstall_icon(self, icon_data:IconData):
        folder_name = icon_data.icon_id
        if os.path.exists(os.path.join(gl.DATA_PATH, "icons", folder_name)):
            shutil.rmtree(os.path.join(gl.DATA_PATH, "icons", folder_name))

    async def install_wallpaper(self, wallpaper_data:WallpaperData):
        wallpaper_path = os.path.join(gl.DATA_PATH, "wallpapers", wallpaper_data.wallpaper_id)

        await self.uninstall_wallpaper(wallpaper_data)

        await self.download_repo(repo_url=wallpaper_data.github, directory=wallpaper_path, commit_sha=wallpaper_data.commit_sha)

    async def uninstall_wallpaper(self, wallpaper_data:WallpaperData):
        folder_name = wallpaper_data.wallpaper_id
        if os.path.exists(os.path.join(gl.DATA_PATH, "wallpapers", folder_name)):
            shutil.rmtree(os.path.join(gl.DATA_PATH, "wallpapers", folder_name))

    async def get_plugin_for_id(self, plugin_id):
        plugins = await self.get_all_plugins_async()
        for plugin in plugins:
            if plugin.plugin_id == plugin_id:
                return plugin
            
    ## Updates
    async def get_plugins_to_update(self):
        plugins =  await self.get_all_plugins_async()
        if isinstance(plugins, NoConnectionError):
            return plugins

        plugins_to_update: list[PluginData] = []

        for plugin in plugins:
            if plugin.local_sha is None:
                # Plugin is not installed
                continue
            if plugin.local_sha != plugin.commit_sha:
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
                self.uninstall_plugin(plugin.plugin_id, remove_from_pages=False, remove_files=False)
            except Exception as e:
                log.error(e)
            await self.install_plugin(plugin)
        
        return len(plugins_to_update)

    async def get_icons_to_update(self):
        icons = await self.get_all_icons()
        if isinstance(icons, NoConnectionError):
            return icons

        icons_to_update: list[IconData] = []

        for icon in icons:
            if icon.local_sha is None:
                # Plugin is not installed
                continue
            if icon.local_sha != icon.commit_sha:
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

        wallpapers_to_update: list[WallpaperData] = []

        for wallpaper in wallpapers:
            if wallpaper.local_sha is None:
                # Plugin is not installed
                continue
            if wallpaper.local_sha != wallpaper.commit_sha:
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
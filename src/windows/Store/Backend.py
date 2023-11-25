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

# Import globals
import globals as gl

class StoreBackend:
    def __init__(self):
        # API cache file
        if not os.path.exists("/mnt/P3/Development/Programmieren/Python/StreamController/src/windows/Store/cache"):
            os.mkdir("/mnt/P3/Development/Programmieren/Python/StreamController/src/windows/Store/cache")
        with open("/mnt/P3/Development/Programmieren/Python/StreamController/src/windows/Store/cache/api.json", "r") as f:
            self.api_cache = json.load(f)
        
        # Image cache file
        if not os.path.exists("/mnt/P3/Development/Programmieren/Python/StreamController/src/windows/Store/cache/images"):
            os.mkdir("/mnt/P3/Development/Programmieren/Python/StreamController/src/windows/Store/cache/images")
        with open("/mnt/P3/Development/Programmieren/Python/StreamController/src/windows/Store/cache/images.json", "r") as f:
            self.image_cache = json.load(f)

    @alru_cache(maxsize=None)
    async def request_from_url(self, url: str) -> requests.Response:
        req = requests.get(url, stream=True)
        if req.status_code == 200:
            return req
    
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

    @alru_cache(maxsize=None)
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
        print(url)

        answer = await self.request_from_url(url)

        return answer
    
    async def get_all_plugins_async(self):
        result = await self.get_remote_file("https://github.com/Core447/StreamController-Store", "Plugins.json")
        plugins_json = result.text
        plugins_json = json.loads(plugins_json)
        print(plugins_json)
        print()

        plugins = []

        for plugin in plugins_json:
            plugins.append(await self.prepare_plugin(plugin))

        return plugins

    async def prepare_plugin(self, plugin):
        url = plugin["url"]
        manifest = await self.get_remote_file(url, "manifest.json", plugin["verified-commit"])
        manifest = json.loads(manifest.text)

        image = await self.image_from_url(self.build_url(url, manifest.get("thumbnail"), plugin["verified-commit"]))

        description = manifest.get("description")

        user_name = self.get_user_name(url)
        repo_name = self.get_repo_name(url)

        stargazers = await self.get_stargazers(url)

        return {
            "name": manifest.get("name"),
            "description": description,
            "url": url,
            "user_name": user_name,
            "repo_name": repo_name,
            "image": image,
            "stargazers": stargazers,
            "official": True,
            "commit_sha": plugin["verified-commit"],
            "id": manifest.get("id")
        }

    async def image_from_url(self, url):
        # Search in cache
        if url in self.image_cache:
            if os.path.isfile(self.image_cache[url]):
                return Image.open(self.image_cache[url])
        
        result = await self.request_from_url(url)
        img = Image.open(BytesIO(result.content))
        
        ## Save to cache
        image_uuid = str(uuid.uuid4())
        save_path = f"/mnt/P3/Development/Programmieren/Python/StreamController/src/windows/Store/cache/images/{image_uuid}.png"
        img.save(save_path)
        self.image_cache[url] = save_path
        # Update image cache json file
        with open("/mnt/P3/Development/Programmieren/Python/StreamController/src/windows/Store/cache/images.json", "w") as f:
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
            self.api_cache[api_call_url] = {}
            self.api_cache[api_call_url]["answer"] = resp.json()
            self.api_cache[api_call_url]["time-code"] = datetime.now().strftime("%d-%m-%y-%H-%M")
            with open("/mnt/P3/Development/Programmieren/Python/StreamController/src/windows/Store/cache/api.json", "w") as f:
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
        return repo_url.split("/")[-1]
    
    def get_all_plugins(self):
        return asyncio.run(self.get_all_plugins_async())
    

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
        await self.subp_call(["git", "config", "--global", "--add", "safe.directory", os.path.abspath(local_path)])

        # Set repository to the given commit_sha
        if commit_sha is not None:
            await self.os_sys(f"cd {local_path} && git reset --hard {commit_sha}")
            return
        
        if branch_name is not None:
            await self.os_sys(f"cd {local_path} && git switch {branch_name}")
            return
        
    async def install_plugin(self, plugin_dict:dict):
        url = plugin_dict["url"]

        PLUGINS_FOLDER = "plugins"
        local_path = f"{PLUGINS_FOLDER}/{plugin_dict['id']}"

        response = await self.clone_repo(repo_url=url, local_path=local_path, commit_sha=plugin_dict["commit_sha"])

        if response == 404:
            return 404
        
        # Update plugin manager
        gl.plugin_manager.load_plugins()
        gl.plugin_manager.init_plugins()
        gl.plugin_manager.generate_action_index()

        # Update ui
        gl.app.main_win.rightArea.action_chooser.plugin_group.build()

        # Update page
        # TODO
        
        log.success(f"Plugin {plugin_dict['id']} installed successfully under: {local_path} with sha: {plugin_dict['commit_sha']}")
        
b = StoreBackend()
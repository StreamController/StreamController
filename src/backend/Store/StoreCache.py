import json
import os

import globals as gl

class StoreCache:
    def __init__(self):
        self.CACHE_PATH = os.path.join(gl.DATA_PATH, "Store" , "cache")

        self.files_json = os.path.join(self.CACHE_PATH, "files.json")
        self.files_dir = os.path.join(self.CACHE_PATH, "files")

        self.create_cache_dirs()
        self.create_cache_files()

    def create_cache_dirs(self):
        os.makedirs(self.CACHE_PATH, exist_ok=True)

    def create_cache_files(self):
        files = [self.files_json]

        for file in files:
            os.makedirs(os.path.dirname(file), exist_ok=True)
            if not os.path.exists(file):
                with open(file, "w") as f:
                    json.dump({}, f, indent=4)

    def get_user_name(self, repo_url:str) -> str:
        splitted =  repo_url.split("/")
        domain = "github.com"
        if domain not in splitted:
            domain = "raw.githubusercontent.com"

        return splitted[splitted.index(domain)+1]
    
    def get_repo_name(self, repo_url:str) -> str:
        github_split = repo_url.split("github")
        if len(github_split) < 2:
            return
        split = github_split[1].split("/")
        if len(split) < 3:
            return
        return split[2]

    def generate_cache_string(self, url: str, path: str, branch: str = "main", data_type: str = "text") -> str:
        user = self.get_user_name(url)
        repo = self.get_repo_name(url)
        return f"{user}::{repo}::{branch}::{data_type}::{path}"
    
    def generate_cache_path(self, url: str, path: str, branch: str = "main", data_type: str = "text") -> str:
        return os.path.join(self.files_dir, self.generate_cache_string(url, path, branch, data_type))
    
    def is_cached(self, url: str, path: str, branch: str = "main", data_type: str = "text") -> bool:
        return os.path.isfile(self.generate_cache_path(url, path, branch, data_type))

    def open_cache_file(self, url: str, path: str, branch: str = "main", data_type: str = "text", mode: str = "r") -> str:
        path = self.generate_cache_path(url, path, branch, data_type)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        return open(path, mode)
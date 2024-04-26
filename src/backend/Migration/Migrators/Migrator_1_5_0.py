from src.backend.Migration.Migrator import Migrator
import json
import os

import globals as gl

class Migrator_1_5_0(Migrator):
    def __init__(self):
        super().__init__("1.5.0")
        
    def migrate(self):
        # Change page properties
        pages_dir = os.path.join(gl.DATA_PATH, "pages")
        for page_path in os.listdir(pages_dir):
            if not page_path.endswith(".json"):
                continue
            page_path = os.path.join(pages_dir, page_path)
            with open(page_path, "r") as f:
                page = json.load(f)

            for key in page.get("keys", {}):
                for label in page["keys"][key].get("labels", {}):
                    if page["keys"][key]["labels"][label].get("text") == "":
                        page["keys"][key]["labels"][label]["text"] = None

                    if page["keys"][key]["labels"][label].get("font-family") == "":
                        page["keys"][key]["labels"][label]["font-family"] = None

                    if page["keys"][key]["labels"][label].get("font-size") == 15:
                        page["keys"][key]["labels"][label]["font-size"] = None

                    if page["keys"][key]["labels"][label].get("color") == [255, 255, 255, 255]:
                        page["keys"][key]["labels"][label]["color"] = None

            with open(page_path, "w") as f:
                json.dump(page, f, indent=4)

        # Update icons and wallapers to id system
        if os.path.exists(os.path.join(gl.DATA_PATH, "icons", "Core447::Material Icons")):
            os.rename(os.path.join(gl.DATA_PATH, "icons", "Core447::Material Icons"), os.path.join(gl.DATA_PATH, "icons", "com_core447_MaterialIcons"))

        if os.path.exists(os.path.join(gl.DATA_PATH, "wallpapers", "Core447::Pixabay Favorites")):
            os.rename(os.path.join(gl.DATA_PATH, "wallpapers", "Core447::Pixabay Favorites"), os.path.join(gl.DATA_PATH, "wallpapers", "com_core447_PixabayFavorites"))

        self.set_migrated(True)
from src.backend.Migration.Migrator import Migrator
import json
import os

import globals as gl

class Migrator_1_5_0(Migrator):
    def __init__(self):
        super().__init__("1.5.0")
        
    def migrate(self):
        self.migrate_pages()
        self.migrate_deck_settings()

        # Update icons and wallapers to id system
        if os.path.exists(os.path.join(gl.DATA_PATH, "icons", "Core447::Material Icons")):
            os.rename(os.path.join(gl.DATA_PATH, "icons", "Core447::Material Icons"), os.path.join(gl.DATA_PATH, "icons", "com_core447_MaterialIcons"))

        if os.path.exists(os.path.join(gl.DATA_PATH, "wallpapers", "Core447::Pixabay Favorites")):
            os.rename(os.path.join(gl.DATA_PATH, "wallpapers", "Core447::Pixabay Favorites"), os.path.join(gl.DATA_PATH, "wallpapers", "com_core447_PixabayFavorites"))

        self.set_migrated(True)

    def migrate_deck_settings(self):
        path = os.path.join(gl.DATA_PATH, "settings", "decks")
        if not os.path.exists(path):
            return
        for deck_path in os.listdir(path):
            if not deck_path.endswith(".json"):
                continue
            deck_path = os.path.join(gl.DATA_PATH, "settings", "decks", deck_path)
            with open(deck_path, "r") as f:
                deck = json.load(f)

            background_path = deck.get("background", {}).get("path", "")
            if background_path is None:
                background_path = ""
            if "Core447::Material Icons" in background_path:
                deck["background"]["path"] = deck["background"]["path"].replace("Core447::Material Icons", "com_core447_MaterialIcons")
            if "Core447::Pixabay Favorites" in background_path:
                deck["background"]["path"] = deck["background"]["path"].replace("Core447::Pixabay Favorites", "com_core447_PixabayFavorites")

            screensaver_path = deck.get("screensaver", {}).get("path", "")
            if screensaver_path is None:
                screensaver_path = ""
            if "Core447::Material Icons" in screensaver_path:
                deck["screensaver"]["path"] = deck["screensaver"]["path"].replace("Core447::Material Icons", "com_core447_MaterialIcons")
            if "Core447::Pixabay Favorites" in screensaver_path:
                deck["screensaver"]["path"] = deck["screensaver"]["path"].replace("Core447::Pixabay Favorites", "com_core447_PixabayFavorites")

            with open(deck_path, "w") as f:
                json.dump(deck, f, indent=4)

    def migrate_pages(self):
        pages_dir = os.path.join(gl.DATA_PATH, "pages")
        if not os.path.exists(pages_dir):
            return
        
        for page_path in os.listdir(pages_dir):
            if not page_path.endswith(".json"):
                continue
            page_path = os.path.join(pages_dir, page_path)
            with open(page_path, "r") as f:
                page = json.load(f)

            background_path = page.get("background", {}).get("path", "")
            if background_path is None:
                background_path = ""
            if "Core447::Material Icons" in background_path:
                page["background"]["path"] = page["background"]["path"].replace("Core447::Material Icons", "com_core447_MaterialIcons")
            if "Core447::Pixabay Favorites" in background_path:
                page["background"]["path"] = page["background"]["path"].replace("Core447::Pixabay Favorites", "com_core447_PixabayFavorites")

            screensaver_path = page.get("screensaver", {}).get("path", "")
            if screensaver_path is None:
                screensaver_path = ""
            if "Core447::Material Icons" in screensaver_path:
                page["screensaver"]["path"] = page["screensaver"]["path"].replace("Core447::Material Icons", "com_core447_MaterialIcons")
            if "Core447::Pixabay Favorites" in screensaver_path:
                page["screensaver"]["path"] = page["screensaver"]["path"].replace("Core447::Pixabay Favorites", "com_core447_PixabayFavorites")

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

                media_path = page["keys"][key].get("media", {}).get("path", "")
                if media_path is None:
                    media_path = ""
                if "Core447::Material Icons" in media_path:
                    page["keys"][key]["media"]["path"] = page["keys"][key]["media"]["path"].replace("Core447::Material Icons", "com_core447_MaterialIcons")

                if "Core447::Pixabay Favorites" in media_path:
                    page["keys"][key]["media"]["path"] = page["keys"][key]["media"]["path"].replace("Core447::Pixabay Favorites", "com_core447_PixabayFavorites")

            with open(page_path, "w") as f:
                json.dump(page, f, indent=4)
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
# Import Python modules
import os
import threading
from PIL import Image, ImageDraw, ImageFont, ImageOps
from StreamDeck.DeviceManager import DeviceManager
from StreamDeck.ImageHelpers import PILHelper
from PIL import Image, ImageSequence
from StreamDeck.Transport.Transport import TransportError
from time import sleep
import math
from copy import copy
import time
import cv2
from loguru import logger as log
import pickle
import gzip

# Import own modules
from src.backend.DeckManagement.HelperMethods import *
from src.backend.DeckManagement.ImageHelpers import *
from src.backend.DeckManagement.Subclasses.DeckMediaHandler import DeckMediaHandler
from src.backend.PageManagement.Page import Page
from src.backend.DeckManagement.ScreenSaver import ScreenSaver

# Import globals
import globals as gl

class DeckController:
    key_spacing = (36, 36)
    key_images = None # list with all key images
    background_key_tiles = None # list with all background key image tiles
    background_image = None

    # Used to inform ui about progress of background video processing
    set_background_task_id = None

    @log.catch
    def __init__(self, deck_manager, deck):
        self.deck = deck
        self.deck_manager = deck_manager
        if not deck.is_open():
            deck.open()
        
        # Default brightness
        self.current_brightness = None
        self.set_brightness(75)

        self.deck.reset()

        self.key_images = [None]*self.deck.key_count() # Fill with None
        self.background_key_tiles = [None]*self.deck.key_count() # Fill with None

        # Save all changes made with hidden key grid
        self.ui_grid_buttons_changes_while_hidden = {}

        self.media_handler = None
        self.media_handler = DeckMediaHandler(self)

        self.deck.set_key_callback(self.key_change_callback)

        # Active page
        self.active_page = None

        # Get deck settings
        self.deck_settings = self.get_deck_settings()

        # Init screen saver
        self.screen_saver = ScreenSaver(self)

        # Load default page #TODO: maybe remove from this class
        default_page = gl.page_manager.get_default_page_for_deck(self.deck.get_serial_number())
        if default_page != None:
            page = gl.page_manager.get_page_by_name(default_page)
            if page != None:
                self.active_page = page
                self.load_page(page)


    @log.catch
    def generate_key_image(self, image_path=None, image=None, labels=None, image_margins=[0, 0, 0, 0], key=None, add_background=True, shrink=False):
        # margins = [left, top, right, bottom]
        DEFAULT_FONT = "Assets/Fonts/Roboto-Regular.ttf"
        if image != None:
            image = image
        elif image_path != None:
            log.debug("Loading image from {}".format(image_path))
            image = Image.open(image_path)
        else:
            image = Image.new("RGBA", (72, 72), (0, 0, 0, 0))
        
        image_height = math.floor(self.deck.key_image_format()["size"][1]-image_margins[1]-image_margins[3])
        image_width = math.floor(self.deck.key_image_format()["size"][0]-image_margins[0]-image_margins[2])

        image = image.resize((image_width, image_height), Image.Resampling.LANCZOS)

        # Generate transparent background to draw everything on
        alpha_bg = Image.new("RGBA", self.deck.key_image_format()["size"], (0, 0, 0, 0))

        # paste image onto background if exists
        if image != None:
            alpha_bg.paste(image, (image_margins[0], image_margins[1]))

        # Add labels
        draw = ImageDraw.Draw(alpha_bg)
        if labels != None:
            # Draw labels onto the image
            for label in list(labels.keys()):
                # Use default font if no font is specified
                if labels[label]["font"] is None:
                    labels[label]["font"] = DEFAULT_FONT
                font = ImageFont.truetype(labels[label]["font"], labels[label]["font-size"])
                # Top text
                if label == "top":
                    draw.text((image.width / 2, labels[label]["font-size"] - 3), text=labels[label]["text"], font=font, anchor="ms",
                              fill=tuple(labels[label]["color"]), stroke_width=labels[label]["stroke-width"])
                # Center text
                if label == "center":
                    draw.text((image.width / 2, (image.height + labels[label]["font-size"]) / 2 - 3), text=labels[label]["text"], font=font, anchor="ms",
                              fill=tuple(labels[label]["color"]), stroke_width=labels[label]["stroke-width"])
                # Bottom text
                if label == "bottom":
                    draw.text((image.width / 2, image.height - 3), text=labels[label]["text"], font=font, anchor="ms",
                              fill=tuple(labels[label]["color"]), stroke_width=labels[label]["stroke-width"])
                    

        if add_background and self.background_key_tiles[key] != None:
            bg = self.background_key_tiles[key].copy() # Load background tile
        else:
            bg = Image.new("RGB", (72, 72), (0, 0, 0)) # Create black background
        bg.paste(alpha_bg, (0, 0), alpha_bg)

        if shrink:
            bg = shrink_image(bg)

        # return image in native format
        return PILHelper.to_native_format(self.deck, bg), alpha_bg, bg
    
    @log.catch
    def set_image(self, key, image_path=None, image=None, labels=None, image_margins=[0, 0, 0, 0], add_background=True, bypass_task = False, shrink=False, update_ui=True):
        native_image, pillow_image, ui_image = self.generate_key_image(image_path=image_path, image=image, labels=labels, image_margins=image_margins,
                                            key=key, add_background=add_background, shrink=shrink)
        
        # Set key image
        if bypass_task:
            with self.deck:
                self.deck.set_key_image(key, native_image)
                if update_ui or True:
                    self.set_ui_key(key, ui_image)
        else:
            if not update_ui:
                ui_image = None
            self.media_handler.add_image_task(key, native_image, ui_image)

        self.key_images[key] = pillow_image

    def set_key(self, key, image=None, media_path=None, labels=None, margins=[0, 0, 0, 0], add_background=True, loop=True, fps=30, bypass_task=False, update_ui=True):
        if media_path in [None, ""]:
            # Load image
            self.set_image(key, image=image, labels=labels, image_margins=margins, add_background=add_background, update_ui=update_ui, bypass_task=bypass_task)
        else:
            extention = os.path.splitext(media_path)[1]
            if extention in [".png", ".jpg", ".jpeg"]:
                # Load image
                self.set_image(key, media_path, labels=labels, image_margins=margins, add_background=add_background, bypass_task=bypass_task, update_ui=update_ui)
                pass
            else:
                # Load video
                self.set_video(key, media_path, labels=labels, image_margins=margins, add_background=add_background, loop=loop, fps=fps)

    def set_video(self, key, video_path, labels=None, image_margins=[0, 0, 0, 0], add_background=True, loop=True, fps=30):
        self.media_handler.add_video_task(key, video_path, loop=loop, fps=fps)

    def set_background(self, media_path, loop=True, fps=30, reload=True, bypass_task=False):
        return self.media_handler.set_background(media_path, loop=loop, fps=fps, reload=reload, bypass_task=bypass_task)

    @log.catch
    def reload_keys(self, skip_gifs=True, bypass_task=False, update_ui=True):
        # tasks = {}
        # Stop gif animations to prevent sending conflicts resulting in strange artifacts
        for i in range(self.deck.key_count()):
            if skip_gifs:
                if i in self.media_handler.video_tasks.keys():
                    if "loop" not in self.media_handler.video_tasks[i]:
                        continue
                    loop = self.media_handler.video_tasks[i]["loop"]
                    n_frames = len(self.media_handler.video_tasks[i]["frames"])
                    frame = self.media_handler.video_tasks[i]["active_frame"]
                    # Check if video/gif is still playing
                    if loop:
                        continue
                    else:
                        if frame < n_frames:
                            continue

            image = self.key_images[i]
            original_bg_image = copy(self.background_key_tiles[i])
            if image == None:
                if original_bg_image:
                    if self.deck.key_states()[i]:
                        # Shrink image
                        bg_image = shrink_image(original_bg_image.copy()) 
                    else:
                        bg_image = original_bg_image
                    native_image = PILHelper.to_native_format(self.deck, bg_image)
                    if not update_ui:
                        bg_image = None
                    if bypass_task:
                        self.set_key_image(i, native_image)
                        self.set_ui_key(i, original_bg_image)
                        # tasks[i] = native_image
                    else:
                        # tasks[i] = (native_image, bg_image)
                        self.media_handler.add_image_task(i, native_image, ui_image=original_bg_image)
                continue
            original_bg_image.paste(image, (0, 0), image)

            if self.deck.key_states()[i]:
                # Shrink image
                bg_image = shrink_image(original_bg_image.copy()) 
            else:
                bg_image = original_bg_image

            native_image = PILHelper.to_native_format(self.deck, bg_image)
            if not update_ui:
                bg_image = None
            if bypass_task:
                # tasks[i] = native_image
                self.set_key_image(i, native_image)
                self.set_ui_key(i, original_bg_image)
            else:
                # tasks[i] = (native_image, bg_image)
                # default
                self.media_handler.add_image_task(i, native_image=native_image, ui_image=original_bg_image)


            # Load tasks
            # for i, task in tasks.items():
            #     if bypass_task:
            #         self.deck.set_key_image(i, task)
            #     else:
            #         self.media_handler.add_image_task(i, task[0], ui_image=task[1])

            # time.sleep(2)

    def key_change_callback(self, deck, key, state):
        # Ignore key press if screen saver is active
        if not self.screen_saver.showing:
            self.handle_shrink_animation(deck, key, state)

        self.screen_saver.on_key_change()

    @log.catch
    def handle_shrink_animation(self, deck, key, state):
        # Skip if background is animated
        if self.media_handler.background_playing:
            return

        if state:
            self.show_shrinked_image(key)
        else:
            self.show_normal_image(key)
        pass

    @log.catch
    def show_shrinked_image(self, key):
        bg_image = copy(self.background_key_tiles[key])
        image = self.key_images[key]
        if bg_image == None:
            # Theoretically not needed but without it the image gets a weird white outline
            bg_image = Image.new("RGB", (72, 72), (0, 0, 0))
        if image != None:
            bg_image.paste(image, (0, 0), image)
        image = shrink_image(bg_image)

        image_native = PILHelper.to_native_format(self.deck, image)
        self.media_handler.add_image_task(key, image_native)
        # self.set_image(key, image=image)

    @log.catch
    def show_normal_image(self, key):
        bg_image = copy(self.background_key_tiles[key])
        image = self.key_images[key]
        if bg_image == None:
            # Theoretically not needed but without it the image gets a weird white outline
            bg_image = Image.new("RGB", (72, 72), (0, 0, 0))
        if image != None:
            bg_image.paste(image, (0, 0), image)
        image = bg_image.convert("RGB")
        image_native = PILHelper.to_native_format(self.deck, image)
        self.media_handler.add_image_task(key, image_native)


    @log.catch
    def load_page(self, page:Page, load_brightness:bool = True, load_background:bool = True, load_keys:bool = True, load_screen_saver:bool = True) -> None:
        log.info(f"Loading page {page.keys()}")
        self.active_page = page

        def load_background(self):
            def get_from_deck_settings(self):
                if self.deck_settings["background"]["enable"] == False:
                    set_background_to_none(self)
                    return
                if os.path.isfile(self.deck_settings["background"]["path"]) == False: return
                path, loop, fps = self.deck_settings["background"].setdefault("path", None), self.deck_settings["background"].setdefault("loop", True), self.deck_settings["background"].setdefault("fps", 30)
                return path, loop, fps
            
            def get_from_page(self, page):
                if "background" not in page: 
                    set_background_to_none(self)
                    return
                if page["background"]["show"] == False: 
                    set_background_to_none(self)
                    return
                if os.path.isfile(page["background"]["path"]) == False: return
                path, loop, fps = page["background"].setdefault("path", None), page["background"].setdefault("loop", True), page["background"].setdefault("fps", 30)
                return path, loop, fps
            
            def set_background_to_none(self):
                print(self.media_handler.background_video_task)
                self.media_handler.background_video_task = {}
                self.background_key_tiles = [None] * self.deck.key_count()
                if not load_keys:
                    load_all_keys()

            page["background"].setdefault("overwrite", False)
            if page["background"]["overwrite"] == False and "background" in self.deck_settings:
                data = get_from_deck_settings(self)
                if data == None: return
                path, loop, fps = data
            else:
                data = get_from_page(self, page)
                if data == None: return
                path, loop, fps = data

            # Add background task - no reload required if load_keys is True because load_keys() will do this later
            self.set_background_task_id = self.set_background(path, loop=loop, fps=fps, reload=not load_all_keys)

        def load_key(coords: str):
            x = int(coords.split("x")[0])
            y = int(coords.split("x")[1])
            index = self.coords_to_index((x, y))
            # Ignore key if it is out of bounds
            if index > self.key_count(): return

            labels = None
            if "labels" in page["keys"][coords]:
                labels = page["keys"][coords]["labels"]
            media_path, media_loop, media_fps = None, None, None
            if "media" in page["keys"][coords]:
                if page["keys"][coords] not in ["", None]:
                    media_path = page["keys"][coords]["media"]["path"]
                    media_loop = page["keys"][coords]["media"]["loop"]
                    media_fps = page["keys"][coords]["media"]["fps"]
            self.set_key(index, media_path=media_path, labels=labels, loop=media_loop, fps=media_fps, bypass_task=True, update_ui=True)

        def load_all_keys():
            loaded_indices = []
            for coords in page["keys"]:
                load_key(coords)
                loaded_indices.append(self.coords_to_index(coords.split("x")))
            # return
            # Clear all keys that are not used on this page
            for i in range(self.key_count()):
                if i not in loaded_indices:
                    clear_key(i)

        def clear_key(index):
            from PIL import Image
            self.key_images[index] = None
            # if self.background_key_tiles[index] == None:
                # image = Image.new("RGB", (72, 72), (0, 0, 0))
            if self.background_key_tiles[index] != None:
                print("clearing with background")
            # Image = Image.new("RGB", (72, 72), (0, 0, 0))
            # native = PILHelper.to native_format(self.deck, Image)
            # self.deck.set_key_image(index, native)
            self.set_key(index, bypass_task=False, update_ui=True, add_background=True)
        # time.sleep(2)

        def load_brightness(self):
            def get_from_deck_settings(self):
                ds = self.deck_settings.copy()
                ds.setdefault("brightness", {})
                value = ds["brightness"].setdefault("value", 75)
                return value
            
            def get_from_page(self, page):
                p = page.copy()
                p.setdefault("brightness", {})
                value = p["brightness"].setdefault("value", 75)
                value = page["brightness"].setdefault("value", 75)
                return value
            
            if page["brightness"]["overwrite"] == False and "brightness" in self.deck_settings:
                value = get_from_deck_settings(self)
            else:
                value = get_from_page(self, page)
            self.set_brightness(value)

        def load_screensaver(self):
            def get_from_deck_settings(self):
                ds = self.deck_settings.copy()
                ds.setdefault("screensaver", {})
                path = ds["screensaver"].setdefault("path", None)
                overwrite = ds["screensaver"].setdefault("overwrite", False)
                enable = ds["screensaver"].setdefault("enable", False)
                loop = ds["screensaver"].setdefault("loop", False)
                fps = ds["screensaver"].setdefault("fps", 30)
                time = ds["screensaver"].setdefault("time-delay", 5)
                brightness = ds["screensaver"].setdefault("brightness", 75)
                return overwrite, enable, loop, fps, time, path, brightness
            
            def get_from_page(self, page):
                p = page.copy()
                p.setdefault("screensaver", {})
                path = p["screensaver"].setdefault("path", None)
                overwrite = p["screensaver"].setdefault("overwrite", False)
                enable = p["screensaver"].setdefault("enable", False)
                loop = p["screensaver"].setdefault("loop", False)
                fps = p["screensaver"].setdefault("fps", 30)
                time = p["screensaver"].setdefault("time-delay", 5)
                brightness = p["screensaver"].setdefault("brightness", 75)
                return overwrite, enable, loop, fps, time, path, brightness
            
            if page["screensaver"]["overwrite"]:
                data = get_from_page(self, page)
            else:
                data = get_from_deck_settings(self)

            if data == None: return
            overwrite, enable, loop, fps, time, path, brightness = data
            # Set screensaver
            self.screen_saver.media_path = path
            self.screen_saver.loop = loop
            self.screen_saver.fps = fps
            self.screen_saver.set_enable(enable)
            self.screen_saver.set_time(time)
            self.screen_saver.set_brightness(brightness)
            if enable:
                print("")
            # if overwrite and not enable:
                # print()
            # if not overwrite and not 

        if load_brightness:
            load_brightness(self)
        if load_background:
            load_background(self)
        if load_all_keys:
            load_all_keys()
        if load_screensaver:
            load_screensaver(self)

    def reload_page(self, load_brightness: bool = True, load_background: bool = True, load_keys: bool = True, load_screen_saver: bool = True):
        print(f"Reload brightness: {load_brightness}")
        print(f"Reload background: {load_background}")
        print(f"Reload keys: {load_keys}")
        # Reset deck
        if load_background or load_keys:
            with self.deck:
                self.deck.reset()
        # Reset images
        if load_keys:
            self.key_images = [None]*self.deck.key_count() # Fill with None
        if load_background:
            self.background_key_tiles = [None]*self.deck.key_count() # Fill with None

        self.load_page(self.active_page, load_brightness=load_brightness, load_background=load_background, load_all_keys=load_keys, load_screen_saver=load_screen_saver)

    def get_deck_settings(self):
        return gl.settings_manager.get_deck_settings(self.deck.get_serial_number())

    def index_to_coords(self, index):
        rows, cols = self.deck.key_layout()    
        y = index // cols
        x = index % cols
        return x, y
    
    def coords_to_index(self, coords):
        x, y = map(int, coords)
        rows, cols = self.deck.key_layout()
        return y * cols + x

    # Pass deck functions to deck
    def key_count(self):
        return self.deck.key_count()
    
    def set_key_image(self, key, image):
        with self.deck:
            self.deck.set_key_image(key, image)

    def set_brightness(self, brightness):
        self.current_brightness = int(brightness)
        with self.deck:
            self.deck.set_brightness(int(brightness))

    def get_brightness(self):
        return self.current_brightness

    def key_state(self, key):
        return self.deck.key_state(key)
    
    def get_own_key_grid(self):
        if not recursive_hasattr(gl, "app.main_win.leftArea.deck_stack"): return
        serial_number = self.deck.get_serial_number()
        deck_stack = gl.app.main_win.leftArea.deck_stack
        return deck_stack.get_child_by_name(serial_number).grid_page
    
    def set_ui_key(self, index, image, force_add_background=False):
        if image == None or index == None:
            return

        y, x = self.index_to_coords(index)

        if force_add_background:
            bg = copy(self.background_key_tiles[index])
            if bg != None:
                image = image.resize(bg.size, Image.Resampling.LANCZOS)
                bg.paste(image, (0, 0), image)
                image = bg

        pixbuf = image2pixbuf(image.convert("RGBA"), force_transparency=True)
        
        if self.get_own_key_grid() == None:
            # Save to use later
            self.ui_grid_buttons_changes_while_hidden[(x, y)] = pixbuf
            return
        buttons = self.get_own_key_grid().buttons
        buttons[x][y].set_image(image)

    def reload_ui_keys(self):
        for i in range(self.deck.key_count()):
            key_image = copy(self.key_images[i])
            bg_image = copy(self.background_key_tiles[i])
            if bg_image == None:
                bg_image = Image.new("RGB", (72, 72), (0, 0, 0))
            if key_image == None:
                key_image = Image.new("RGBA", (72, 72), (0, 0, 0, 0))

            key_image = Image.new("RGBA", (72, 72), (255, 255, 255, 255))

            key_image.save(f"keys/{i}.png")
            # bg_image.paste(key_image, (0, 0), key_image)
            self.set_ui_key(i, key_image, force_add_background=True)


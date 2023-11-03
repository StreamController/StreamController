from loguru import logger as log

class ActionBase:
    # Change to match your action
    ACTION_NAME = ""
    PLUGIN_BASE = None

    def __init__(self, deck_controller, page, coords):
        # Verify variables
        if self.ACTION_NAME in ["", None]:
            raise ValueError("Please specify an action name")
        
        self.deck_controller = deck_controller
        self.page = page
        self.page_coords = coords
        self.coords = coords.split("x")
        self.index = self.deck_controller.coords_to_index(self.coords)

        self.labels = {}
        self.current_key = {}

        log.info(f"Loaded action {self.ACTION_NAME}")
        
    def set_deck_controller(self, deck_controller):
        """
        Internal function, do not call manually
        """
        self.deck_controller = deck_controller
 
    def set_page(self, page):
        """
        Internal function, do not call manually
        """
        self.page = page

    def set_coords(self, coords):
        """
        Internal function, do not call manually
        """
        self.coords = coords
    
    def on_key_down(self):
        pass

    def on_key_up(self):
        pass

    def on_tick(self):
        pass

    def on_load(self):
        pass

    def on_tick(self):
        pass

    def get_custom_config_area(self) -> "Gtk.Widget":
        return None
    
    def set_key(self, image = None, media_path=None, margins=[0, 0, 0, 0],
                add_background=True, loop=True, fps=30, bypass_task=False, update_ui=True, reload: bool = False):
        """
        Sets the key image for the key of the action.

        Parameters:
            image (optional): The image to be displayed.
            media_path (optional): The path to the media file.
            margins (optional): The margins for the image.
            add_background (optional): Whether to add a background.
            loop (optional): Whether to loop the video. (does only work for videos)
            fps (optional): The frames per second. (does only work for videos)
            bypass_task (optional): Whether to bypass the task.
            update_ui (optional): Whether to update the UI.
        """
        if not reload:
            self.current_key = {
                "key": self.index,
                "image": image,
                "media_path": media_path,
                "margins": margins,
                "add_background": add_background,
                "loop": loop,
                "fps": fps,
                "bypass_task": bypass_task,
                "update_ui": update_ui
            }
        elif self.current_key == {}:
            log.warning("No key to reload")
            return
        self.deck_controller.set_key(**self.current_key, labels=self.labels)

    def set_label(self, text: str, position: str = "bottom", color: list[int] = [255, 255, 255], stroke_width: int = 0,
                      font_family: str = "", font_size = 18):
        if position not in ["top", "center", "bottom"]:
            raise ValueError("Position must be 'top', 'center' or 'bottom'")
        
        if text == None:
            if position in self.labels:
                del self.labels[position]
        else:
            self.labels[position] = {
                "text": text,
                "color": color,
                "stroke-width": stroke_width,
                "font-family": font_family,
                "font-size": font_size
            }

        # Reload key
        self.set_key(reload=True)

    def set_top_label(self, text: str, color: list[int] = [255, 255, 255], stroke_width: int = 0,
                      font_family: str = "", font_size = 18):
        self.set_label(text, "top", color, stroke_width, font_family, font_size)
    
    def set_center_label(self, text: str, color: list[int] = [255, 255, 255], stroke_width: int = 0,
                      font_family: str = "", font_size = 18):
        self.set_label(text, "center", color, stroke_width, font_family, font_size)
    
    def set_bottom_label(self, text: str, color: list[int] = [255, 255, 255], stroke_width: int = 0,
                      font_family: str = "", font_size = 18):
        self.set_label(text, "bottom", color, stroke_width, font_family, font_size)

    def get_config_rows(self) -> "list[Adw.PreferencesRow]":
        return []
    
    def get_settings(self) -> dir:
        # self.page.load()
        return self.page.get_settings_for_action(self, coords = self.page_coords)
    
    def set_settings(self, settings: dict):
        self.page.set_settings_for_action(self, settings=settings, coords = self.page_coords)
        self.page.save()
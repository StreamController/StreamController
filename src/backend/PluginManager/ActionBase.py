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
        self.coords = coords
        
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

    def get_custom_config_area(self) -> "Gtk.Widget":
        return None
    
    def get_config_rows(self) -> "list[Adw.PreferencesRow]":
        return []
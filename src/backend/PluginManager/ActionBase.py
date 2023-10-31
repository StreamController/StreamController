class ActionBase:
    # Change to match your action
    ACTION_NAME = ""

    def __init__(self):
        # Verify variables
        if self.ACTION_NAME in ["", None]:
            raise ValueError("Please specify an action name")
        
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
    
    def onKeyDown(self):
        pass

    def onKeyUp(self):
        pass

    def onTick(self):
        pass
class Signal:
    pass


class PageRename(Signal):
    """
    Callback:
    old_path: str
    new_path: str
    """

class PageDelete(Signal):
    """
    Callback:
    path: str
    """

class PageAdd(Signal):
    """
    Callback:
    path: str
    """

class ChangePage(Signal):
    """
    Callback:
    controller: DeckController
    old_path: str
    new_path: str
    """

class PluginInstall(Signal):
    """
    Callback:
    id: str
    """
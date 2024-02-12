class Signal:
    def __init__(self, code):
        self.code = code

PageRename = Signal(0)
PageDelete = Signal(1)
PageAdd = Signal(2)
ChangePage = Signal(3)
PluginInstall = Signal(4)

"""
PageRename:
    Callback:
    old_path: str
    new_path: str

PageDelete:
    Callback:
    path: str

PageAdd:
    Callback:
    path: str

ChangePage:
    Callback:
    controller: DeckController
    old_path: str
    new_path: str

PluginInstall:
    Callback:
    id: str
"""
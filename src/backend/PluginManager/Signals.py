class Signal:
    def __init__(self, code):
        self.code = code

PageRename = Signal(0)
PageDelete = Signal(1)
PageAdd = Signal(2)
ChangePage = Signal(3)

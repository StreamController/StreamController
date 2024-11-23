from os.path import isfile

from src.backend.DeckManagement.Media.Media import Media
from os.path import isfile

class Asset:
    def __init__(self, *args, **kwargs):
        self.change(*args, **kwargs)

    def change(self, *args, **kwargs):
        pass

    def get_values(self):
        pass

    def to_json(self):
        pass

    @classmethod
    def from_json(cls, *args):
        return None

class Color(Asset):
    def __init__(self, *args, **kwargs):
        self._color: tuple[int, int, int, int] = (0,0,0,0)

        super().__init__(*args, **kwargs)

    def change(self, *args, **kwargs):
        self._color = kwargs.get("color", (0,0,0,0))

    def get_values(self):
        return self._color

    def to_json(self):
        return list(self._color)

    @classmethod
    def from_json(cls, *args):
        return cls(color=tuple(args[0]))

class Icon(Asset):
    def __init__(self, *args, **kwargs):
        self._icon: Media = None
        self._rendered: Media = None
        self._path: str = None

        super().__init__(*args, **kwargs)

    def change(self, *args, **kwargs):
        path = kwargs.get("path", "")

        if isfile(path):
            self._path = path
            self._icon = Media.from_path(path)
            self._rendered = self._icon.get_final_media()

    def get_values(self):
        return self._icon, self._rendered

    def to_json(self):
        return self._path

    @classmethod
    def from_json(cls, *args):
        return cls(path=args[0])
from os.path import isfile

from src.backend.DeckManagement.Media.Media import Media
from os.path import isfile

class Asset:
    def __init__(self, *args, **kwargs):
        pass

    def get_values(self):
        pass

    def to_json(self):
        pass

    @classmethod
    def from_json(cls, *args, **kwargs):
        return None

class Color(Asset):
    def __init__(self, color: tuple[int, int, int, int], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._color: tuple[int, int, int, int] = color

    def get_values(self):
        return self._color

    def to_json(self):
        return list(self._color)

    @classmethod
    def from_json(cls, *args, **kwargs):
        return cls(color=args[1])

class Icon(Asset):
    def __init__(self, path: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if isfile(path):
            self._path = path
            self._icon = Media.from_path(path)
            self._rendered = self._icon.get_final_media()
        else:
            self._path: str = None
            self._icon: Media = None
            self._rendered: Media = None

    def get_values(self):
        return self._icon, self._rendered

    def to_json(self):
        return self._path

    @classmethod
    def from_json(cls, *args, **kwargs):
        return cls(path=args[0])
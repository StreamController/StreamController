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
        return cls(color=tuple(args[0]))

class Icon(Asset):
    def __init__(self, path: str, size=1.0, valign=0.0, halign=0.0, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if isfile(path):
            self._path = path
            self._icon = Media.from_path(path, size=size, valign=valign, halign=halign)
            self._rendered = self._icon.get_final_media()
        else:
            self._path: str = None
            self._icon: Media = None
            self._rendered: Media = None

    def get_values(self):
        return self._icon, self._rendered

    def to_json(self):
        save_data = {
            "path": self._path,
            "size": self._icon.size,
            "halign": self._icon.halign,
            "valign": self._icon.valign
        }
        return save_data

    @classmethod
    def from_json(cls, *args, **kwargs):
        save_data: dict = args[0]

        path = save_data.get("path", "")
        size = save_data.get("size", 1.0)
        halign = save_data.get("halign", 0.00)
        valign = save_data.get("valign", 0.00)

        return cls(path, size, halign, valign)
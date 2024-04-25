from dataclasses import dataclass, field
from PIL import Image

@dataclass
class StoreData:
    github: [str, None] = None
    """Link to the github repository"""
    descriptions: dict[str, str] = field(default_factory=dict)
    """All the translations for the description"""
    short_descriptions: dict[str, str] = field(default_factory=dict)
    """All the translations for the short descriptions"""
    author: [str, None] = None
    """Author of the Content"""
    official: [bool, None] = None
    """If the Content is Officially Made or not"""
    commit_sha: [str, None] = None
    """SHA of the github commit that gets used"""
    local_sha: [str, None] = None
    """The Local SHA that is used to verify if plugins are installed"""
    minimum_app_version: [str, None] = None # OPTIONAL
    """Minimum app version that is required to use the Content"""
    app_version: [str, None] = None
    """The Current app version the Plugin is made for"""
    repository_name: [str, None] = None
    """Name of the Repository"""
    tags: list[str] = field(default_factory=list)


@dataclass
class ImageData:
    thumbnail: [str, None] = None # Path to image
    """Path to the Thumbnail used in the Store"""
    image: [Image.Image, None] = None #Actual Image
    """The Image that gets displayed in the Store"""

@dataclass
class LicenceData:
    copyright: [str, None] = None
    original_url: [str, None] = None
    license: [str, None] = None
    """The actual licence"""
    license_descriptions: dict[str, str] = field(default_factory=dict)
    """Translations for the Licence Description"""

@dataclass
class PluginData(StoreData, ImageData, LicenceData):
    plugin_name: [str, None] = None
    """Name of the Plugin"""
    plugin_version: [str, None] = None
    """Version of the Plugin"""
    plugin_id: [str, None] = None
    """Plugin ID in the com.author.name format"""


@dataclass
class IconData(StoreData, ImageData, LicenceData):
    icon_name: [str, None] = None
    """Name of the icon"""
    icon_version: [str, None] = None
    """Version of the icons"""
    icon_id: [str, None] = None
    """Icon ID in the com.author.name format"""


@dataclass
class WallpaperData(StoreData, ImageData, LicenceData):
    wallpaper_name: [str, None] = None
    """Name of the wallpaper"""
    wallpaper_version: [str, None] = None
    """Version of the wallpaper"""
    wallpaper_id: [str, None] = None
    """Icon ID in the com.author.name format"""
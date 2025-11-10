"""
Author: Core447
Year: 2023

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This programm comes with ABSOLUTELY NO WARRANTY!

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.

The functions:
create_full_deck_sized_image, create_wallpaper_image_array; crop_key_image_from_deck_sized_image
are based on the functions in the examples of: https://github.com/abcminiuser/python-elgato-streamdeck
Shoutout to Dean Camera alias abcminiuser for his amazing work!
"""
from PIL import Image, ImageOps
from StreamDeck.ImageHelpers import PILHelper

from gi.repository import GLib, GdkPixbuf

from loguru import logger as log

def create_full_deck_sized_image(deck, image_filename = None, image = None):
        key_rows, key_cols = deck.key_layout()
        key_width, key_height = deck.key_image_format()['size']
        spacing_x, spacing_y = (36, 36)
    
        # Compute total size of the full StreamDeck image, based on the number of
        # buttons along each axis. This doesn't take into account the spaces between
        # the buttons that are hidden by the bezel.
        key_width *= key_cols
        key_height *= key_rows
    
        # Compute the total number of extra non-visible pixels that are obscured by
        # the bezel of the StreamDeck.
        spacing_x *= key_cols - 1
        spacing_y *= key_rows - 1
    
        # Compute final full deck image size, based on the number of buttons and
        # obscured pixels.
        full_deck_image_size = (key_width + spacing_x, key_height + spacing_y)
    
        # Resize the image to suit the StreamDeck's full image size. We use the
        # helper function in Pillow's ImageOps module so that the image's aspect
        # ratio is preserved.
        if image_filename != None:
            with Image.open(image_filename) as image:
                image = image.copy().convert("RGBA")
        elif image != None:
            image = image.convert("RGBA")
        image = ImageOps.fit(image, full_deck_image_size, Image.Resampling.LANCZOS)
        return image

def create_wallpaper_image_array(deck, progress_dir = None, image = None):
        # Maybe use 2D array instead
        if progress_dir != None:
            image = create_full_deck_sized_image(deck, image_filename=progress_dir)
        elif image != None:
            image = create_full_deck_sized_image(deck, image=image)
    
        key_images = []
        for i in range(deck.key_count()):
            key_images.append(crop_key_image_from_deck_sized_image(deck, image, i)[1])
        return key_images

def crop_key_image_from_deck_sized_image(deck, image, key):
        key_rows, key_cols = deck.key_layout()
        key_width, key_height = deck.key_image_format()['size']
        spacing_x, spacing_y = (36, 36)
    
        # Determine which row and column the requested key is located on.
        row = key // key_cols
        col = key % key_cols
    
        # Compute the starting X and Y offsets into the full size image that the
        # requested key should display.
        start_x = col * (key_width + spacing_x)
        start_y = row * (key_height + spacing_y)
    
        # Compute the region of the larger deck image that is occupied by the given
        # key, and crop out that segment of the full image.
        region = (start_x, start_y, start_x + key_width, start_y + key_height)
        segment = image.crop(region)
    
        # Create a new key-sized image, and paste in the cropped section of the
        # larger image.
        key_image = PILHelper.create_image(deck)
        key_image.paste(segment)
    
        return PILHelper.to_native_format(deck, key_image), key_image

def shrink_image(image):
        image = image.resize((50, 50), Image.Resampling.LANCZOS)
        bg = Image.new("RGB", (72, 72), (0, 0, 0))
        bg.paste(image, (11, 11))
        return bg

def is_transparent(img: Image.Image):
    """
    Determines if an image has transparency.

    Args:
        img (PIL.Image.Image): The image to check for transparency.

    Returns:
        bool: True if the image has transparency, False otherwise.
    """
    return img.has_transparency_data

    if img.info.get("transparency", None) is not None:
        return True
    if img.mode == "P":
        transparent = img.info.get("transparency", -1)
        for _, index in img.getcolors():
            if index == transparent:
                return True
    elif img.mode == "RGBA":
        extrema = img.getextrema()
        if extrema[3][0] < 255:
            return True

    return False

def image2pixbuf(img, force_transparency=False):
    """
    Converts an image to a GdkPixbuf.Pixbuf object.

    Args:
        img (PIL.Image.Image): The image to convert.

    Returns:
        GdkPixbuf.Pixbuf: The converted GdkPixbuf.Pixbuf object.
    """
    img = img.convert("RGBA")
    force_transparency = True

    data = img.tobytes()
    w, h = img.size
    data = GLib.Bytes.new(data)
    transparent = True if force_transparency else is_transparent(img)
    channels = 4 if transparent else 3

    try:
        if w == 0 or h == 0:
            return
        pix = GdkPixbuf.Pixbuf.new_from_bytes(data, GdkPixbuf.Colorspace.RGB,
                transparent, 8, w, h, w * channels)
        # Clean up memory
        data = None
        w, h = None, None
        del data
        return pix
    except TypeError:
         # This usually happens if the image is a non RGB image
        return

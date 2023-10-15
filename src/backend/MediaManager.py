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
"""
# Import Python modules
import os
import cv2
import imageio
from PIL import Image, ImageSequence

# Import own modules
from src.backend.DeckManagement.HelperMethods import sha256, file_in_dir

class MediaManager:
    def __init__(self):
        pass

    def get_thumbnail(self, file_path):
        hash = sha256(file_path)
        if not os.path.exists("cache"):
            os.mkdir("cache")
        if not os.path.exists("cache/thumbnails"):
            os.mkdir("cache/thumbnails")
        
        # Check if thumbnail has already been cached:
        cached = file_in_dir(os.path.join("cache/thumbnails", f"{hash}.jpg"))
        if cached:
            return Image.open(os.path.join("cache/thumbnails", f"{hash}.jpg"))
        else:
            return self.generate_thumbnail(file_path)

    def generate_thumbnail(self, file_path):
        print(os.path.splitext(file_path)[1])
        if os.path.splitext(file_path)[1] in [".jpg", ".jpeg", ".png"]:
            return self.generate_image_thumbnail(file_path)
        elif os.path.splitext(file_path)[1] in [".gif", ".GIF"]:
            return self.generate_gif_thumbnail(file_path)
        else:
            return self.generate_video_thumbnail(file_path)

    def generate_video_thumbnail(self, file_path):
        cap = cv2.VideoCapture(file_path)
        success, frame = cap.read()
        if not success:
            return None
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb_frame)
        return pil_img

    def generate_image_thumbnail(self, file_path):
        return Image.open(file_path)
    
    def generate_gif_thumbnail(self, file_path):
        # This is the same as load_video but with transparency support
        gif = Image.open(file_path)
        iterator = ImageSequence.Iterator(gif)
        n_frames = 0
        for frame in iterator: n_frames += 1 #TODO: Find a better way to do this
        frame = iterator[n_frames // 2] # Gifs tend to have a empty frame at the beginning
        frame = frame.convert("RGBA")
        return frame
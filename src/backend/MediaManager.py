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
from copy import copy
import os
import cv2
import imageio
from PIL import Image, ImageSequence

import os, psutil
process = psutil.Process()

# Import own modules
from src.backend.DeckManagement.HelperMethods import sha256, file_in_dir


# Import globals
import globals as gl

class MediaManager:
    def __init__(self):
        pass

    def get_thumbnail(self, file_path):
        hash = sha256(file_path)

        thumbnail_dir = os.path.join(gl.DATA_PATH, "cache", "thumbnails")
        thumbnail_path = os.path.join(thumbnail_dir, f"{hash}.png")
        
        os.makedirs(thumbnail_dir, exist_ok=True)

        
        # Check if thumbnail has already been cached:
        cached = file_in_dir(f"{hash}.png", thumbnail_dir)
        if cached is None:
            cached = False

        if cached:
            img = Image.open(thumbnail_path)
            img.thumbnail((250, 250), resample=Image.Resampling.LANCZOS)
            return img
        else:
            thumbnail = self.generate_thumbnail(file_path)
            thumbnail.thumbnail((250, 250), resample=Image.Resampling.LANCZOS)
            thumbnail.save(thumbnail_path)
            return thumbnail

    def generate_thumbnail(self, file_path):
        if os.path.splitext(file_path)[1] in [".jpg", ".jpeg", ".png"]:
            return self.generate_image_thumbnail(file_path)
        elif os.path.splitext(file_path)[1] in [".gif", ".GIF"]:
            return self.generate_gif_thumbnail(file_path)
        else:
            thumbnail = self.generate_video_thumbnail(file_path)
            return thumbnail

    def generate_video_thumbnail(self, video_path: str) -> Image.Image:
        cap = cv2.VideoCapture(video_path)
        cap.set(cv2.CAP_PROP_POS_FRAMES, 1)
        ret, frame = cap.read()
        cap.release()

        frame_rgb = cv2.cvtColor(copy(frame), cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(frame_rgb)
        return pil_image
            

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
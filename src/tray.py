class TrayIcon:
    def stop(self):
        pass



# import os
# os.environ["PYSTRAY_BACKEND"] = "appindicator"
# # import pystray

# from pystray import _appindicator
# from PIL import Image
# from pystray import Menu, MenuItem

# class TrayIcon(_appindicator.Icon):
#     def __init__(self):
#         icon_image = Image.open("flatpak/icon_256.png")
#         menu = Menu(
#             MenuItem("StreamController", enabled=False, action=None),
#             MenuItem("Open", self.on_open),
#             MenuItem("Quit", self.on_quit)
#         )
#         super().__init__("StreamController", icon_image, menu=menu, title="StreamController")

#     def on_open(self):
#         print("Open")

#     def on_quit(self):
#         print("Quit")
#         self.stop()  # Stop the icon running when "Quit" is clicked

# if __name__ == "__main__":
#     # Usage
#     stream_controller_icon = TrayIcon()
#     stream_controller_icon.run()
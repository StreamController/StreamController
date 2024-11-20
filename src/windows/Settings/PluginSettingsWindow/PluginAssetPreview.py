import gi

from src.backend.DeckManagement.ImageHelpers import image2pixbuf

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, GdkPixbuf, Pango, Gdk

class AssetPreview(Gtk.FlowBoxChild):
    def __init__(self, window: "PluginSettingsPage", name: str, size: tuple[int, int] = (50,50), *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_css_classes(["asset-preview"])
        self.set_margin_start(5)
        self.set_margin_end(5)
        self.set_margin_top(5)
        self.set_margin_bottom(5)

        self.name = name
        self.size = size

        self.set_size_request(self.size[0], self.size[1])
        self.create_base_ui()

        self.reset_button.connect("clicked", window.reset_button_clicked, self)

    def create_base_ui(self):
        self.overlay = Gtk.Overlay()

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.main_box.set_size_request(self.size[0], self.size[1])

        self.overlay.set_child(self.main_box)

        self.reset_button = Gtk.Button(icon_name="edit-undo-symbolic")
        self.reset_button.set_halign(Gtk.Align.END)
        self.reset_button.set_valign(Gtk.Align.START)
        self.reset_button.set_margin_top(10)
        self.reset_button.set_margin_end(10)
        self.overlay.add_overlay(self.reset_button)

        self.set_child(self.overlay)

        self.set_size_request(self.size[0], self.size[1])

    def build(self):
        pass

class IconPreview(AssetPreview):
    def __init__(self, image, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.image = image
        self.pixbuf = image2pixbuf(image)
        self.build()

    def scale_pixbuf(self):
        original_width = self.pixbuf.get_width()
        original_height = self.pixbuf.get_height()
        w = self.size[0]
        h = self.size[1]

        scale = min(w / original_width, h / original_height)

        new_width = int(original_width * scale)
        new_height = int(original_height * scale)

        return self.pixbuf.scale_simple(new_width, new_height, GdkPixbuf.InterpType.BILINEAR)

    def build(self):
        self.picture = Gtk.Picture(width_request=self.size[0], height_request=self.size[1], overflow=Gtk.Overflow.HIDDEN,
                                   content_fit=Gtk.ContentFit.COVER,
                                   hexpand=False, vexpand=False, keep_aspect_ratio=True)
        self.picture.set_pixbuf(self.scale_pixbuf())

        self.main_box.append(self.picture)

        self.label = Gtk.Label(label=self.name, xalign=Gtk.Align.CENTER, hexpand=False, ellipsize=Pango.EllipsizeMode.END,
                               max_width_chars=20,
                               margin_start=20, margin_end=20)
        self.main_box.append(self.label)

    def set_image(self, image):
        self.image = image
        self.pixbuf = image2pixbuf(self.image)
        self.picture.set_pixbuf(self.scale_pixbuf())

class ColorPreview(AssetPreview):
    def __init__(self, color: tuple[int, int, int, int], *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.color = color
        self.build()

    def build(self):
        self.color_button = Gtk.ColorButton(title="Pick Color")
        self.color_button.set_sensitive(False)
        self.set_color(self.color)
        self.color_button.set_size_request(self.size[0], self.size[1])

        self.main_box.append(self.color_button)

        self.label = Gtk.Label(label=self.name, xalign=Gtk.Align.CENTER, hexpand=False, ellipsize=Pango.EllipsizeMode.END,
                               max_width_chars=20,
                               margin_start=20, margin_end=20)
        self.main_box.append(self.label)

    def set_color(self, color: tuple[int, int, int, int]):
        self.color = color
        self.color_button.set_rgba(self.get_rgba())

    def set_color_rgba(self, color: Gdk.RGBA):
        normalized = (color.red * 255,
                      color.green * 255,
                      color.blue * 255,
                      color.alpha * 255)
        self.color = normalized
        self.color_button.set_rgba(color)

    def get_rgba(self):
        rgba = Gdk.RGBA()
        normalized = tuple(color / 255.0 for color in self.color)
        rgba.red = normalized[0]
        rgba.green = normalized[1]
        rgba.blue = normalized[2]
        rgba.alpha = normalized[3]
        return rgba
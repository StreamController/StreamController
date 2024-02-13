"""
Author: Core447
Year: 2024

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This programm comes with ABSOLUTELY NO WARRANTY!

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
# Import gtk modules
import gi


gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

# Import typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from windows.mainWindow.mainWindow import MainWindow


class OnboardingWindow(Gtk.ApplicationWindow):
    def __init__(self, application, main_win: "MainWindow"):
        super().__init__(application=application)
        self.set_title("Onboarding")
        self.set_transient_for(main_win)
        self.set_modal(True)
        self.set_default_size(700, 700)
        
        self.build()

    def build(self):
        self.header = Adw.HeaderBar(css_classes=["flat"])
        self.set_titlebar(self.header)

        self.overlay = Gtk.Overlay()
        self.set_child(self.overlay)

        self.carousel = Adw.Carousel(
            allow_long_swipes=True,
            allow_scroll_wheel=True,
            allow_mouse_drag=True,
            reveal_duration=200,
        )
        self.carousel.connect("page-changed", self.on_page_changed)
        self.overlay.set_child(self.carousel)

        self.carousel.append(OnboardingScreen("Assets/Onboarding/logo.png", "Welcome to StreamController!", "The Linux app for the Elgato StreamDeck"))
        self.carousel.append(OnboardingScreen("Assets/Onboarding/store.png", "Asset Store", "Download plugins, icons and wallpapers"))
        self.carousel.append(OnboardingScreen("Assets/Onboarding/multiple.png", "Multi Deck Support", "Control multiple Elgato StreamDecks at once"))
        self.carousel.append(OnboardingScreen("Assets/Onboarding/productive.png", "Be more productive", "With your personal shortcuts"))
        self.carousel.append(OnboardingScreen5(self))

        self.carousel_indicator_dots = Adw.CarouselIndicatorDots(carousel=self.carousel)
        self.header.set_title_widget(self.carousel_indicator_dots)

        self.forward_button = Gtk.Button(icon_name="go-next", css_classes=["onboarding-nav-button", "circular"],
                                         halign=Gtk.Align.END, valign=Gtk.Align.CENTER, margin_end=15)
        self.forward_button.connect("clicked", self.on_forward_button_click)
        self.overlay.add_overlay(self.forward_button)

        self.back_button = Gtk.Button(icon_name="go-previous", css_classes=["onboarding-nav-button", "circular"],
                                      halign=Gtk.Align.START, valign=Gtk.Align.CENTER, margin_start=15,
                                      visible=False)
        self.back_button.connect("clicked", self.on_back_button_click)
        self.overlay.add_overlay(self.back_button)

    def on_forward_button_click(self, button):
        pos = self.carousel.get_position()
        pos += 1

        # Theoretically not necessary because on_page_changed handles it but it takes some time and therefore doesn't feel nice
        if pos >= self.carousel.get_n_pages() -1:
            self.forward_button.set_visible(False)
        self.back_button.set_visible(True)

        scroll_to_widget = self.carousel.get_nth_page(pos)
        self.carousel.scroll_to(scroll_to_widget, True)

    def on_back_button_click(self, button):
        pos = self.carousel.get_position()
        pos -= 1

        # Theoretically not necessary because on_page_changed handles it but it takes some time and therefore doesn't feel nice
        if pos <= 0:
            self.back_button.set_visible(False)
        self.forward_button.set_visible(True)

        scroll_to_widget = self.carousel.get_nth_page(pos)
        self.carousel.scroll_to(scroll_to_widget, True)

    def on_page_changed(self, carousel: Adw.Carousel, page_index: int) -> None:
        if page_index > 0:
            self.back_button.set_visible(True)
        else:
            self.back_button.set_visible(False)

        if page_index < carousel.get_n_pages() - 1:
            self.forward_button.set_visible(True)
        else:
            self.forward_button.set_visible(False)

class OnboardingScreen(Gtk.Box):
    def __init__(self, image_file: str, label: str, detail: str):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.image_file = image_file
        self.label = label
        self.detail = detail

        self.build()

    def build(self):
        self.image = Gtk.Image(file=self.image_file, css_classes=["onboarding-icon"],
                               margin_top=120)
        self.append(self.image)

        self.label = Gtk.Label(label=self.label, css_classes=["onboarding-welcome-label"],
                               margin_top=50)
        self.append(self.label)

        self.detail = Gtk.Label(label=self.detail, css_classes=["onboarding-welcome-detail-label"],)
        self.append(self.detail)


class OnboardingScreen5(Gtk.Box):
    def __init__(self, onboarding_window: OnboardingWindow):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True,
                         halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        self.onboarding_window = onboarding_window

        self.build()

    def build(self):
        self.label = Gtk.Label(label="Ready?", css_classes=["onboarding-welcome-label"],
                               margin_top=50)
        self.append(self.label)

        self.start_button = Gtk.Button(label="Start", css_classes=["onboarding-start-button"], margin_top=20)
        self.start_button.connect("clicked", self.on_start_button_click)
        self.append(self.start_button)

    def on_start_button_click(self, button):
        self.onboarding_window.close()
        self.onboarding_window.destroy()
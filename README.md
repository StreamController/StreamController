# StreamController

[![Flathub Downloads](https://img.shields.io/flathub/downloads/com.core447.StreamController?style=flat&label=Flathub%20Downloads&link=https%3A%2F%2Fflathub.org%2Fapps%2Fcom.core447.StreamController)](https://flathub.org/apps/com.core447.StreamController)
[![Discord](https://img.shields.io/discord/1221536306367303690?label=Discord&link=https%3A%2F%2Fdiscord.gg%2FMSyHM8TN3u)](https://discord.gg/MSyHM8TN3u)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Made with Python](https://img.shields.io/badge/Made%20with-Python-ff7b3f.svg)](https://www.python.org/)
[![Flathub Version](https://img.shields.io/flathub/v/com.core447.StreamController?label=Flathub%20Version)](https://flathub.org/apps/com.core447.StreamController)

**StreamController** is an elegant Linux application designed for the Elgato Stream Deck, offering advanced features like plug-ins and automatic page switching to enhance your streaming and productivity setup.

![Main Screen](https://streamcontroller.core447.com/assets/screenshots/main_screen.png)  
*Background image by [kvacm](https://kvacm.artstation.com)*

## In Action
[![YouTube](http://i.ytimg.com/vi/kIJOj_6Jimk/hqdefault.jpg)](https://www.youtube.com/watch?v=kIJOj_6Jimk)  
(click on the image to play)

@danie10 created this amazing video going over all the details and features of StreamController. You can use the available timestamps to jump to specific parts of the video.

## Supported Devices

StreamController supports the following Elgato Stream Deck models:

- Stream Deck Original
- Stream Deck Mini
- Stream Deck Mini Discord Edition
- Stream Deck XL
- Stream Deck Pedal
- Stream Deck Plus
- Stream Deck Plus XL
- Stream Deck Neo
- Stream Deck Studio
- Stream Deck Modules

Support for devices from other manufacturers is experimental:

- Mirabox Stream Dock 293S (no hotplug support yet - connect it before starting the app)
- Ulanzi Stream Controller D200 (no hotplug support yet - connect it before starting the app)

## Features

### Plugins

StreamController features plugin support with a built-in store to download your favorite actions. You can also publish your own plugins. For more details, visit the [Wiki](https://streamcontroller.github.io/docs).

### Wallpapers

Customize your Stream Deck pages with cool wallpapers and videos to make them more engaging.

### Screen Saver

Set up a custom screen saver to display a picture or video when your Stream Deck is in idle.

### Automatic Page Switching

Available for GNOME (using our GNOME Shell extension), Hyprland, Sway, Mangowm, KDE (when kdotool is installed) and all X11 desktops, this feature allows you to automatically change your active page based on the active window. For example, you can switch to your favorite music albums when you open Spotify, your projects when you open VSCode, or your favorite websites in Firefox.

### Auto-Lock

Lock your Stream deck when your system is locked, preventing unwanted use from third parties. This works on every session where systemd-logind reports the lock, with dedicated support for Hyprland, GNOME, KDE and Cinnamon.

### Sticky actions

Maybe you want to have your specialy party mode button on all your pages. With sticky actions you can do this, without needing to copy it to all pages manually.

### Command Line & API

StreamController can be scripted. While the app is running you can switch pages, change states, emulate button presses, set the brightness or put a deck to sleep - and you can read back the current devices, pages and actions, with `--json` for machine-readable output. Pages can also be created, renamed, duplicated, exported and edited (labels, icons, background colors, states) without the app running at all.

```sh
flatpak run com.core447.StreamController --list-devices --json
flatpak run com.core447.StreamController --change-page ABC12345678 "Gaming"
flatpak run com.core447.StreamController --set-label "Gaming" 0,0 0 center text "Play"
```

Run it with `--help` for the full list. Everything is also available over the D-Bus API at `com.core447.StreamController`, so external tools can integrate with StreamController directly.

**And many more.**

## Installation

To install StreamController, click the button below or follow the [installation instructions](https://streamcontroller.github.io/docs/latest/installation/):

<a href='https://flathub.org/apps/details/com.core447.StreamController'><img width='200px' alt='Download on Flathub' src='https://flathub.org/assets/badges/flathub-badge-en.png'/></a>

To install the head of main as a Flatpak just run the following command:

```sh
bash -c "$(wget -O - https://raw.githubusercontent.com/StreamController/StreamController/main/flatpak/install.sh)"
```

#### Unofficial Packages

The following packages are functional but unofficial and maintained by our community:

[![Packaging status](https://repology.org/badge/vertical-allrepos/streamcontroller.svg)](https://repology.org/project/streamcontroller/versions)

## Warning

StreamController is currently in beta. Please report any issues you encounter.

### Known issues
* High memory can be a problem. We are actively working to resolve this. 

## Contributing

We welcome contributions! Feel free to open pull requests to improve StreamController.

If you're interested in helping with the development of this app, you can contact me on our [Discord server](https://discord.gg/MSyHM8TN3u) to request write access to our [Dev planning board](https://github.com/orgs/StreamController/projects/2). For more information see [Dev-Planning-Board](Dev-Planning-Board.md).

### Contributors

Thank you to all our contributors for your hard work and support!

<a href="https://github.com/streamcontroller/streamcontroller/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=streamcontroller/streamcontroller"/>
</a>

## Links

- [Website](https://core447.com)
- [Wiki](https://streamcontroller.github.io/docs)
- [Discord](https://discord.gg/MSyHM8TN3u)

## Note

This application is unofficial and not affiliated with Elgato in any way.

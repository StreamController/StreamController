"""
deck.connected() ends up in LibUSBHIDAPI.Device.connected(), which asks hidapi
to enumerate *without* a vid/pid filter. The hidapi libusb backend - the only
one the streamdeck library loads - answers such an enumeration by opening every
HID device on the system and reading its string descriptors, Stream Deck or not.

FlatpakDeckDisconnectThread does that every two seconds. Devices with sloppy
firmware don't survive it: they stop answering, the kernel resets the port and
the device re-enumerates, over and over, for as long as we are running (see
issue #396).

Filtering the enumeration by the deck's own vid/pid keeps hidapi from touching
anything but Stream Decks.
"""

from StreamDeck.Transport.LibUSBHIDAPI import LibUSBHIDAPI


def _connected(self) -> bool:
    with self.mutex:
        devices = self.hidapi.enumerate(vendor_id=self.device_info["vendor_id"],
                                        product_id=self.device_info["product_id"])

    return any(device["path"] == self.device_info["path"] for device in devices)


def patch_connected() -> None:
    """
    Let every deck use our connected() instead of the one from the streamdeck
    library. Has to run before anything asks a deck whether it is still there.
    """
    LibUSBHIDAPI.Device.connected = _connected

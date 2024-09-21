from StreamDeck.ProductIDs import USBVendorIDs, USBProductIDs
from StreamDeck.Devices.StreamDeckMini import StreamDeckMini
from StreamDeck.Devices.StreamDeckOriginal import StreamDeckOriginal
from StreamDeck.Devices.StreamDeckOriginalV2 import StreamDeckOriginalV2
from StreamDeck.Devices.StreamDeckXL import StreamDeckXL
from StreamDeck.Devices.StreamDeckPedal import StreamDeckPedal
from StreamDeck.Devices.StreamDeckPlus import StreamDeckPlus
from .StreamDeckNeo import StreamDeckNeo
from loguru import logger as log

def enumerate(self):
    log.info("Using patched new_enumerate")
    """
    Detect attached StreamDeck devices.

    :rtype: list(StreamDeck)
    :return: list of :class:`StreamDeck` instances, one for each detected device.
    """

    products = [
        (USBVendorIDs.USB_VID_ELGATO, USBProductIDs.USB_PID_STREAMDECK_ORIGINAL, StreamDeckOriginal),
        (USBVendorIDs.USB_VID_ELGATO, USBProductIDs.USB_PID_STREAMDECK_ORIGINAL_V2, StreamDeckOriginalV2),
        (USBVendorIDs.USB_VID_ELGATO, USBProductIDs.USB_PID_STREAMDECK_MINI, StreamDeckMini),
        (USBVendorIDs.USB_VID_ELGATO, USBProductIDs.USB_PID_STREAMDECK_XL, StreamDeckXL),
        (USBVendorIDs.USB_VID_ELGATO, USBProductIDs.USB_PID_STREAMDECK_MK2, StreamDeckOriginalV2),
        (USBVendorIDs.USB_VID_ELGATO, USBProductIDs.USB_PID_STREAMDECK_PEDAL, StreamDeckPedal),
        (USBVendorIDs.USB_VID_ELGATO, USBProductIDs.USB_PID_STREAMDECK_MINI_MK2, StreamDeckMini),
        (USBVendorIDs.USB_VID_ELGATO, USBProductIDs.USB_PID_STREAMDECK_XL_V2, StreamDeckXL),
        (USBVendorIDs.USB_VID_ELGATO, USBProductIDs.USB_PID_STREAMDECK_PLUS, StreamDeckPlus),
        (USBVendorIDs.USB_VID_ELGATO, USBProductIDs.USB_PID_STREAMDECK_NEO, StreamDeckNeo),
    ]

    streamdecks = list()

    for vid, pid, class_type in products:
        found_devices = self.transport.enumerate(vid=vid, pid=pid)
        streamdecks.extend([class_type(d) for d in found_devices])

    return streamdecks
import types
import StreamDeck
import StreamDeck.Devices
from StreamDeck.DeviceManager import DeviceManager
from cairo import Device

from src.patcher.Patch import Patch
from src.patcher.patches.sd_neo.new_enumerate import enumerate as new_enumerate

from .StreamDeckNeo import StreamDeckNeo
from StreamDeck.ProductIDs import USBProductIDs

StreamDeck.Devices.StreamDeckNeo = StreamDeckNeo

# Device Manager
# from StreamDeck import DeviceManager

class SDNeoPatch(Patch):
    def patch(self):
        DeviceManager.USB_PID_STREAMDECK_NEO = 0x009a
        USBProductIDs.USB_PID_STREAMDECK_NEO = 0x009a

        # DeviceManager.enumerate = types.MethodType(new_enumerate, DeviceManager)
        DeviceManager.enumerate = new_enumerate
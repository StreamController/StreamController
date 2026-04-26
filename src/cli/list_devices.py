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


def handle_list_devices():
    """List connected StreamDeck devices and print info about each."""
    print("Scanning for connected StreamDeck devices...")
    print()

    # We need to initialize deck manager to scan for devices
    try:
        # Minimal initialization to scan for devices
        from StreamDeck.DeviceManager import DeviceManager
        devices = DeviceManager().enumerate()

        if not devices:
            print("No StreamDeck devices found.")
            print("\nTips:")
            print("- Make sure your StreamDeck is connected via USB")
            print("- Check that the device is recognized by your system")
            print("- Try running with sudo if you have permission issues")
            return True

        print(f"Found {len(devices)} StreamDeck device(s):")
        print()

        for i, device in enumerate(devices):
            print(f"Device {i+1}:")
            try:
                # Try to get basic info without opening if possible
                device_id = getattr(device, 'id', lambda: 'Unknown')()
                print(f"  Device ID: {device_id}")

                # Try to get info that doesn't require opening the device
                try:
                    deck_type = getattr(device, 'deck_type', lambda: 'Unknown StreamDeck')()
                    print(f"  Product Name: {deck_type}")
                except Exception:
                    print(f"  Product Name: Unknown (permission issue)")

                # Try to open device to get detailed info
                device_opened = False
                try:
                    if not device.is_open():
                        device.open()
                        device_opened = True

                    print(f"  Serial Number: {device.get_serial_number()}")
                    key_layout = device.key_layout()
                    print(f"  Key Layout: {key_layout[1]}x{key_layout[0]} ({device.key_count()} keys)")

                    if hasattr(device, 'dial_count') and device.dial_count() > 0:
                        print(f"  Dials: {device.dial_count()}")
                    if hasattr(device, 'is_touch') and device.is_touch():
                        print(f"  Touchscreen: Yes")
                    print(f"  Connected: {'Yes' if device.connected() else 'No'}")

                    if device_opened:
                        device.close()

                except PermissionError:
                    print(f"  Status: Permission denied")
                    print(f"  Note: Run 'sudo python main.py --list-devices' or install udev rules")
                except Exception as open_error:
                    print(f"  Status: Could not access device ({open_error})")
                    print(f"  Note: This may be a permission issue or device is in use")

            except Exception as e:
                print(f"  Error: {e}")
                if "permission" in str(e).lower() or "access" in str(e).lower():
                    print(f"  Note: Try running with sudo or install proper udev rules")

            print()
    except ImportError:
        print("Error: StreamDeck library not available")
    except Exception as e:
        print(f"Error scanning devices: {e}")

    # Add helpful information about permissions
    print("\nTroubleshooting:")
    print("- If you see permission errors, try: sudo python main.py --list-devices")
    print("- For permanent fix, install udev rules: sudo cp udev.rules /etc/udev/rules.d/70-streamdeck.rules")
    print("- Then run: sudo udevadm control --reload-rules && sudo udevadm trigger")
    print("- After installing udev rules, unplug and replug your StreamDeck")

    return True

from telnetlib import RSP
import dbus

# Connect to the session bus
bus = dbus.SessionBus()

# Get a proxy for the GNOME Shell Extensions interface
gnome_shell_extensions = bus.get_object("org.gnome.Shell", "/org/gnome/Shell")
interface = dbus.Interface(gnome_shell_extensions, "org.gnome.Shell.Extensions")

for extension in interface.ListExtensions():
    print(extension)

response = interface.InstallRemoteExtension("Bluetooth-Battery-Meter@maniacx.github.com")
if response == "cancelled":
    response = False
elif response == "successful":
    response = True
print(response)
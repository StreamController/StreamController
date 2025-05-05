# Inspired by code of deltragon/SafeEyes repo.
# Link: https://github.com/deltragon/SafeEyes/blob/f25f554585c79a11621e3a505cc6ce5af08a3d58/safeeyes/plugins/trayicon/plugin.py

import gi
gi.require_version("Gtk","4.0")
from gi.repository import Gio, GLib

SNI_NODE_INFO = Gio.DBusNodeInfo.new_for_xml("""
<?xml version="1.0" encoding="UTF-8"?>
<node>
    <interface name="org.kde.StatusNotifierItem">
        <property name="Category" type="s" access="read"/>
        <property name="Id" type="s" access="read"/>
        <property name="Title" type="s" access="read"/>
        <property name="ToolTip" type="(sa(iiay)ss)" access="read"/>
        <property name="Menu" type="o" access="read"/>
        <property name="ItemIsMenu" type="b" access="read"/>
        <property name="IconName" type="s" access="read"/>
        <property name="IconThemePath" type="s" access="read"/>
        <property name="Status" type="s" access="read"/>
        <signal name="NewIcon"/>
        <signal name="NewTooltip"/>

        <property name="XAyatanaLabel" type="s" access="read"/>
        <signal name="XAyatanaNewLabel">
            <arg type="s" name="label" direction="out" />
            <arg type="s" name="guide" direction="out" />
        </signal>
    </interface>
</node>""").interfaces[0]

MENU_NODE_INFO = Gio.DBusNodeInfo.new_for_xml("""
<?xml version="1.0" encoding="UTF-8"?>
<node>
    <interface name="com.canonical.dbusmenu">
        <method name="GetLayout">
            <arg type="i" direction="in"/>
            <arg type="i" direction="in"/>
            <arg type="as" direction="in"/>
            <arg type="u" direction="out"/>
            <arg type="(ia{sv}av)" direction="out"/>
        </method>
        <method name="GetGroupProperties">
                        <arg type="ai" name="ids" direction="in"/>
                        <arg type="as" name="propertyNames" direction="in" />
                        <arg type="a(ia{sv})" name="properties" direction="out" />
                </method>
        <method name="GetProperty">
                        <arg type="i" name="id" direction="in"/>
                        <arg type="s" name="name" direction="in"/>
                        <arg type="v" name="value" direction="out"/>
                </method>
        <method name="Event">
            <arg type="i" direction="in"/>
            <arg type="s" direction="in"/>
            <arg type="v" direction="in"/>
            <arg type="u" direction="in"/>
        </method>
        <method name="EventGroup">
                        <arg type="a(isvu)" name="events" direction="in" />
                        <arg type="ai" name="idErrors" direction="out" />
                </method>
        <method name="AboutToShow">
            <arg type="i" direction="in"/>
            <arg type="b" direction="out"/>
        </method>
        <method name="AboutToShowGroup">
                        <arg type="ai" name="ids" direction="in" />
                        <arg type="ai" name="updatesNeeded" direction="out" />
                        <arg type="ai" name="idErrors" direction="out" />
                </method>
        <signal name="LayoutUpdated">
            <arg type="u"/>
            <arg type="i"/>
        </signal>
    </interface>
</node>""").interfaces[0]

class DBusService:
    def __init__(self, interface_info, object_path, bus):
        self.interface_info = interface_info
        self.object_path = object_path
        self.bus = bus
        self.registration_id = None

    def register(self):
        self.registration_id = self.bus.register_object(
            object_path=self.object_path,
            interface_info=self.interface_info,
            method_call_closure=self.on_method_call,
            get_property_closure=self.on_get_property
        )

        if not self.registration_id:
            raise GLib.Error(f"Failed to register object with path {self.object_path}")

        self.interface_info.cache_build()

    def unregister(self):
        self.interface_info.cache_release()

        if self.registration_id is not None:
            self.bus.unregister_object(self.registration_id)
            self.registration_id = None

    def on_method_call(self, _connection, _sender, _path, _interface_name, method_name, parameters, invocation):
        method_info = self.interface_info.lookup_method(method_name)
        method = getattr(self, method_name)
        result = method(*parameters.unpack())
        out_arg_types = "".join([arg.signature for arg in method_info.out_args])
        return_value = None

        if method_info.out_args:
            return_value = GLib.Variant(f"({out_arg_types})", result)

        invocation.return_value(return_value)

    def on_get_property(self, _connection, _sender, _path, _interface, property_name):
        property_info = self.interface_info.lookup_property(property_name)
        return GLib.Variant(property_info.signature, getattr(self, property_name))

    def emit_signal(self, signal_name, args = None):
        signal_info = self.interface_info.lookup_signal(signal_name)
        if len(signal_info.args) == 0:
            parameters = None
        else:
            arg_types = "".join([arg.signature for arg in signal_info.args])
            parameters = GLib.Variant(f"({arg_types})", args)

        self.bus.emit_signal(
            destination_bus_name=None,
            object_path=self.object_path,
            interface_name=self.interface_info.name,
            signal_name=signal_name,
            parameters=parameters
        )

class DBusMenuService(DBusService):
    DBusPath = "/com/example/TrayApp/Menu"

    revision = 0

    items = []
    idToItems = {}

    def __init__(self, session_bus, items, path=DBusPath):
        super().__init__(
            interface_info=MENU_NODE_INFO,
            object_path=path,
            bus=session_bus
        )

        self.dbus_path = path

        self.set_items(items)

    def set_items(self, items):
        self.items = items

        self.idToItems = self.getItemsFlat(items, {})

        self.revision += 1

        self.LayoutUpdate(self.revision, 0)

    @staticmethod
    def getItemsFlat(items, idToItems):
        for item in items:
            if item.get('hidden', False) == True:
                continue

            idToItems[item['id']] = item

            if 'children' in item:
                idToItems = DBusMenuService.getItemsFlat(item['children'], idToItems)

        return idToItems

    @staticmethod
    def singleItemToDbus(item):
        props = DBusMenuService.itemPropsToDbus(item)

        return (item['id'], props)

    @staticmethod
    def itemPropsToDbus(item):
        result = {}

        string_props = ['label', 'icon-name', 'type', 'children-display']
        for key in string_props:
            if key in item:
                result[key] = GLib.Variant('s', item[key])

        bool_props = ['enabled']
        for key in bool_props:
            if key in item:
                result[key] = GLib.Variant('b', item[key])

        return result

    @staticmethod
    def itemToDbus(item, recursion_depth):
        if item.get('hidden', False) == True:
            return None

        props = DBusMenuService.itemPropsToDbus(item)

        children = []
        if recursion_depth > 1 or recursion_depth == -1:
            if "children" in item:
                children = [DBusMenuService.itemToDbus(item, recursion_depth - 1) for item in item['children']]
                children = [i for i in children if i is not None]

        return GLib.Variant("(ia{sv}av)", (item['id'], props, children))

    def findItemWithParent(self, parent_id, items):
        for item in items:
            if item.get('hidden', False) == True:
                continue
            if 'children' in item:
                if item['id'] == parent_id:
                    return item['children']
                else:
                    ret = self.findItemWithParent(parent_id, item['children'])
                    if ret is not None:
                        return ret
        return None

    def GetLayout(self, parent_id, recursion_depth, property_name):
        children = []

        if parent_id == 0:
            children = self.items
        else:
            children = self.findItemWithParent(parent_id, self.items)
            if children is None:
                children = []

        children = [self.itemToDbus(item, recursion_depth) for item in children]
        children = [i for i in children if i is not None]

        ret = (
            self.revision,
            (
                0,
                {'children-display': GLib.Variant('s', 'submenu')},
                children
            )
        )

        return ret

    def GetGroupProperties(self, ids, property_names):
        ret = []

        for idx in ids:
            if idx in self.idToItems:
                props = DBusMenuService.singleItemToDbus(self.idToItems[idx])
                if props is not None:
                    ret.append(props)
        return (ret,)

    def GetProperty(self, idx, name):
        ret = None

        if idx in self.idToItems:
            props = DBusMenuService.singleItemToDbus(self.idToItems[idx])
            if props is not None and name in props:
                ret = props[name]

        return ret

    def Event(self, idx, event_id, data, timestamp):
        if event_id != "clicked":
            return

        if idx in self.idToItems:
            item = self.idToItems[idx]
            if 'callback' in item:
                item['callback']()

    def EventGroup(self, events):
        not_found = []

        for (idx, event_id, data, timestamp) in events:
            if idx not in self.idToItems:
                not_found.append(idx)
                continue

            if event_id != "clicked":
                continue

            item = self.idToItems[idx]
            if 'callback' in item:
                item['callback']()

        return not_found

    def AboutToShow(self, item_id):
        return (False,)

    def AboutToShowGroup(self, ids):
        not_found = []

        for idx in ids:
            if idx not in self.idToItems:
                not_found.append(idx)
                continue

        return ([], not_found)

    def LayoutUpdate(self, revision, parent):
        self.emit_signal(
            'LayoutUpdated',
            (revision, parent)
        )

class StatusNotifierItemService(DBusService):
    DBusPath = "/org/ayatana/NotificationItem/com_example_TrayApp"
    Category = 'ApplicationStatus'
    Id = 'com.example.TrayApp'
    Title = 'Safe Eyes'
    Status = 'Active'
    IconName = 'alienarena'
    IconThemePath = ''
    ToolTip = ('', [], 'Safe Eyes', '')
    XAyatanaLabel = ""
    ItemIsMenu = True
    Menu = None

    def __init__(self, session_bus, menu_items, path=DBusPath, menu_path=""):
        super().__init__(
            interface_info=SNI_NODE_INFO,
            object_path=path,
            bus=session_bus
        )

        self.bus = session_bus
        self.dbus_path = path

        if menu_path == "":
            self._menu = DBusMenuService(session_bus, menu_items)
        else:
            self._menu = DBusMenuService(session_bus, menu_items, menu_path)
        self.Menu = self._menu.dbus_path

    def register(self):
        self._menu.register()
        super().register()

        watcher = Gio.DBusProxy.new_sync(
            connection=self.bus,
            flags=Gio.DBusProxyFlags.DO_NOT_LOAD_PROPERTIES,
            info=None,
            name='org.kde.StatusNotifierWatcher',
            object_path='/StatusNotifierWatcher',
            interface_name='org.kde.StatusNotifierWatcher',
            cancellable=None
        )

        watcher.RegisterStatusNotifierItem('(s)', self.dbus_path)

    def unregister(self):
        super().unregister()
        self._menu.unregister()

    def set_items(self, items):
        self._menu.set_items(items)

    def set_icon(self, icon, path: str = ""):
        self.IconName = icon
        self.IconThemePath = path

        self.emit_signal(
            'NewIcon'
        )

    def set_tooltip(self, title, description):
        self.ToolTip = ('', [], title, description)

        self.emit_signal(
            'NewTooltip'
        )

    def set_xayatanalabel(self, label):
        self.XAyatanaLabel = label

        self.emit_signal(
            "XAyatanaNewLabel",
            (label, "")
        )

class DBusTrayIcon:
    def __init__(self, menu = None, path = "", menu_path = "", app_id = "", title = ""):
        session_bus = Gio.bus_get_sync(Gio.BusType.SESSION)

        self.menu = menu

        kwargs = {
            "session_bus": session_bus,
            "menu_items": self.menu.get_items()
        }
        if path != "":
            kwargs["path"] = path

        if menu_path != "":
            kwargs["menu_path"] = menu_path

        self.sni_service = StatusNotifierItemService(**kwargs)
        if app_id != "":
            self.sni_service.Id = app_id

        if title != "":
            self.sni_service.Title = title

    def set_icon(self, icon, path: str = ""):
        self.sni_service.set_icon(icon, path)

    def set_tooltip(self, title, description = ""):
        self.sni_service.set_tooltip(title, description)

    def set_label(self, label):
        self.sni_service.set_xayatanalabel(label)

    def update_menu(self):
        self.sni_service.set_items(self.menu.get_items())

    def register(self):
        self.sni_service.register()

    def unregister(self):
        self.sni_service.unregister()

class DBusMenu:
    def __init__(self):
        self.menu_items = []

    def add_menu_item(self, menu_id, menu_label="", menu_type="", icon_name="", callback=None):
        item = {'id': menu_id}
        if menu_label != "":
            item['label'] = menu_label
        if menu_type != "":
            item['type'] = menu_type
        if icon_name != "":
            item['icon-name'] = icon_name
        if callback:
            item['callback'] = callback

        self.menu_items.append(item)

    def get_items(self):
        return self.menu_items

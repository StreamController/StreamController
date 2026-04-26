# Inspired by code of deltragon/SafeEyes repo.
# Link: https://github.com/deltragon/SafeEyes/blob/f25f554585c79a11621e3a505cc6ce5af08a3d58/safeeyes/plugins/trayicon/plugin.py


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

class PluginPage(StorePage):
    def __init__(self, store: Store):
        super().__init__(store=store)
        self.search_entry.set_placeholder_text("Search for plugins")

        self.load()

    def load(self):
        plugins = self.store.backend.get_all_plugins()
        for plugin in plugins:
            self.flow_box.append(PluginPreview(plugin_page=self, plugin_dict=plugin))

import asyncio
from loguru import logger as log

class EventHolder:
    """
        Holder for Event Callbacks for the specified Event ID
    """
    def __init__(self, plugin_base: "PluginBase",
                 event_id: str = None,
                 event_id_suffix: str = None):
        if event_id in ["", None] and event_id_suffix in ["", None]:
            raise ValueError("Please specify a signal id")

        self.plugin_base = plugin_base
        self.event_id = event_id or f"{self.plugin_base.get_plugin_id()}::{event_id_suffix}"
        self.observers: list = []

    def add_listener(self, callback: callable):
        if callback not in self.observers:
            self.observers.append(callback)
        else:
            log.warning(f"Callback {callback.__name__} is already subscribed to: {self.event_id}")

    def remove_listener(self, callback: callable):
        if callback in self.observers:
            self.observers.remove(callback)

    def trigger_event(self, *args, **kwargs):
        # FIX: This can throw an error, if this happens apply the fix from Observer.py
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._run_event(self.event_id, *args, **kwargs))

    async def _run_event(self, *args, **kwargs):
        coroutines = [self._ensure_coroutine(observer, *args, **kwargs) for observer in self.observers]
        await asyncio.gather(*coroutines)

    async def _ensure_coroutine(self, callback: callable, *args, **kwargs):
        if asyncio.iscoroutinefunction(callback):
            return await callback(*args, **kwargs)
        else:
            try:
                return await asyncio.to_thread(callback, *args, **kwargs)
            except Exception as e:
                log.error(f"Callback {callback.__name__} in {self.event_id} could not be called")
                return await asyncio.sleep(0)

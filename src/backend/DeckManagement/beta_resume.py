import time

from StreamDeck.Devices.StreamDeck import ControlType, DialEventType
from StreamDeck.Transport.Transport import TransportError

def _read(self):
    """
    Read handler for the underlying transport, listening for button state
    changes on the underlying device, caching the new states and firing off
    any registered callbacks.
    """
    while self.run_read_thread:
        try:
            control_states = self._read_control_states()
            if control_states is None:
                time.sleep(1.0 / self.read_poll_hz)
                continue

            if ControlType.KEY in control_states and self.key_callback is not None:
                for k, (old, new) in enumerate(zip(self.last_key_states, control_states[ControlType.KEY])):
                    if old != new:
                        self.last_key_states[k] = new
                        self.key_callback(self, k, new)

            elif ControlType.DIAL in control_states and self.dial_callback is not None:
                if DialEventType.PUSH in control_states[ControlType.DIAL]:
                    for k, (old, new) in enumerate(zip(self.last_dial_states,
                                                        control_states[ControlType.DIAL][DialEventType.PUSH])):
                        if old != new:
                            self.last_dial_states[k] = new
                            self.dial_callback(self, k, DialEventType.PUSH, new)

                if DialEventType.TURN in control_states[ControlType.DIAL]:
                    for k, amount in enumerate(control_states[ControlType.DIAL][DialEventType.TURN]):
                        if amount != 0:
                            self.dial_callback(self, k, DialEventType.TURN, amount)

            elif ControlType.TOUCHSCREEN in control_states and self.touchscreen_callback is not None:
                self.touchscreen_callback(self, *control_states[ControlType.TOUCHSCREEN])

        except TransportError:
            self.run_read_thread = False
            self.close()

            if self.reconnect_after_suspend:
                if self.connected() and not self.is_open():
                    # This is the case when resuming from suspend
                    TIMEOUT = 10
                    start_time = time.time()
                    while True:
                        try:
                            self.open()
                            break
                        except TransportError:
                            time.sleep(0.1)

                        if not self.connected():
                            break

                        if time.time() - start_time > TIMEOUT:
                            break
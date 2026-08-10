import time

from loguru import logger as log
from StreamDeck.Devices.StreamDeck import ControlType, DialEventType, StreamDeck
from StreamDeck.Transport.Transport import TransportError

# How long we keep trying to open the deck again after a transport error
RECONNECT_TIMEOUT = 10
# A deck that is plugged in but broken would make us reopen it in a tight loop,
# so we only reconnect a few times in a row before giving up
MAX_RECONNECTS_IN_ROW = 5
# Reading fine for this long means the next error is a new one, not a retry
RECONNECT_RESET_TIME = 30


def _read(self):
    """
    Read handler for the underlying transport, listening for button state
    changes on the underlying device, caching the new states and firing off
    any registered callbacks.

    Unlike the version in the streamdeck library this one reconnects after
    *any* transport error - not just after a resume from suspend - and logs
    what happened. A transient usb hiccup used to kill this thread for good,
    leaving a deck that looks perfectly connected but ignores every key press.
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

        except TransportError as e:
            self.run_read_thread = False
            self.close()

            if not self.reconnect_after_suspend:
                # We are closing the deck ourselves, see DeckController.stop_reader
                log.info(f"Read thread of deck {self.id()} stopped while the deck was being closed: {e}")
                return

            log.warning(f"Read thread of deck {self.id()} hit a transport error, trying to reconnect: {e}")
            _reconnect(self)
            # A successful open() starts a new read thread, so this one is done
            # either way - continuing here would give us two readers on one deck
            return


def _reconnect(deck: StreamDeck) -> bool:
    """Open the deck again after a transport error. Returns whether it worked."""
    if not _allow_reconnect(deck):
        log.error(f"Deck {deck.id()} failed {MAX_RECONNECTS_IN_ROW} times in a row, not reconnecting again")
        return False

    start_time = time.time()
    while True:
        try:
            deck.open()
            log.success(f"Reconnected deck {deck.id()} after a transport error, reading again")
            return True
        except TransportError:
            # Without the close the stale handle would make every open() a no-op
            deck.close()
            time.sleep(0.1)

        if not deck.connected():
            log.error(f"Deck {deck.id()} is no longer connected, giving up on reconnecting it")
            return False

        if time.time() - start_time > RECONNECT_TIMEOUT:
            log.error(f"Timed out reconnecting deck {deck.id()} after a transport error")
            return False


def _allow_reconnect(deck: StreamDeck) -> bool:
    now = time.time()
    if now - getattr(deck, "last_reconnect_time", 0) > RECONNECT_RESET_TIME:
        deck.n_reconnects_in_row = 0

    deck.n_reconnects_in_row = getattr(deck, "n_reconnects_in_row", 0) + 1
    deck.last_reconnect_time = now

    return deck.n_reconnects_in_row <= MAX_RECONNECTS_IN_ROW


def patch_read_thread() -> None:
    """
    Let every deck use our read thread instead of the one from the streamdeck
    library. open(resume_from_suspend=True) picks the method up by name, so this
    has to run before any deck is opened.
    """
    StreamDeck._read_with_resume_from_suspend = _read

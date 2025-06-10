from StreamDeck.Devices import StreamDeck

class BetterDeck():
    def __init__(self, deck: StreamDeck, rotation: int = 0):
        self.deck = deck
        self.rotation: int = rotation # [0, 90, 180, 270]


    def open(self):
        """
        Opens the device for input/output. This must be called prior to setting
        or retrieving any device state.

        .. seealso:: See :func:`~StreamDeck.close` for the corresponding close method.
        """
        self.deck.open()

    def close(self):
        """
        Closes the device for input/output.

        .. seealso:: See :func:`~StreamDeck.open` for the corresponding open method.
        """
        self.deck.close()

    def is_open(self):
        """
        Indicates if the StreamDeck device is currently open and ready for use.

        :rtype: bool
        :return: `True` if the deck is open, `False` otherwise.
        """
        return self.deck.is_open()

    def connected(self):
        """
        Indicates if the physical StreamDeck device this instance is attached to
        is still connected to the host.

        :rtype: bool
        :return: `True` if the deck is still connected, `False` otherwise.
        """
        return self.deck.connected()

    def vendor_id(self):
        """
        Retrieves the vendor ID attached StreamDeck. This can be used
        to determine the exact type of attached StreamDeck.

        :rtype: int
        :return: Vendor ID of the attached device.
        """
        return self.deck.vendor_id()

    def product_id(self):
        """
        Retrieves the product ID attached StreamDeck. This can be used
        to determine the exact type of attached StreamDeck.

        :rtype: int
        :return: Product ID of the attached device.
        """
        return self.deck.product_id()

    def id(self):
        """
        Retrieves the physical ID of the attached StreamDeck. This can be used
        to differentiate one StreamDeck from another.

        :rtype: str
        :return: Identifier for the attached device.
        """
        return self.deck.id()

    def key_count(self):
        """
        Retrieves number of physical buttons on the attached StreamDeck device.

        :rtype: int
        :return: Number of physical buttons.
        """
        return self.deck.key_count()

    def touch_key_count(self):
        """
        Retrieves number of touch buttons on the attached StreamDeck device.

        :rtype: int
        :return: Number of touch buttons.
        """
        return self.deck.touch_key_count()

    def dial_count(self):
        """
        Retrieves number of physical dials on the attached StreamDeck device.

        :rtype: int
        :return: Number of physical dials
        """
        return self.deck.dial_count()

    def deck_type(self):
        """
        Retrieves the model of Stream Deck.

        :rtype: str
        :return: String containing the model name of the StreamDeck device.
        """
        return self.deck.deck_type()

    def is_visual(self):
        """
        Returns whether the Stream Deck has a visual display output.

        :rtype: bool
        :return: `True` if the deck has a screen, `False` otherwise.
        """
        return self.deck.is_visual()

    def is_touch(self):
        """
        Returns whether the Stream Deck can receive touch events

        :rtype: bool
        :return: `True` if the deck can receive touch events, `False` otherwise
        """
        return self.deck.is_touch()

    def key_layout(self):
        """
        Retrieves the physical button layout on the attached StreamDeck device.

        :rtype: (int, int)
        :return (rows, columns): Number of button rows and columns.
        """
        rows, cols = self.deck.key_layout()
        if self.rotation in [0, 180]:
            return rows, cols
        else:
            return cols, rows

    def key_image_format(self):
        """
        Retrieves the image format accepted by the attached StreamDeck device.
        Images should be given in this format when setting an image on a button.

        .. seealso:: See :func:`~StreamDeck.set_key_image` method to update the
                     image displayed on a StreamDeck button.

        :rtype: dict()
        :return: Dictionary describing the various image parameters
                 (size, image format, image mirroring and rotation).
        """
        return self.deck.key_image_format()

    def touchscreen_image_format(self):
        """
        Retrieves the image format accepted by the touchscreen of the Stream
        Deck. Images should be given in this format when drawing on
        touchscreen.

        .. seealso:: See :func:`~StreamDeck.set_touchscreen_image` method to
                     draw an image on the StreamDeck touchscreen.

        :rtype: dict()
        :return: Dictionary describing the various image parameters
                 (size, image format).
        """
        return self.deck.touchscreen_image_format()

    def screen_image_format(self):
        """
        Retrieves the image format accepted by the screen of the Stream
        Deck. Images should be given in this format when drawing on
        screen.

        .. seealso:: See :func:`~StreamDeck.set_screen_image` method to
                     draw an image on the StreamDeck screen.

        :rtype: dict()
        :return: Dictionary describing the various image parameters
                 (size, image format).
        """
        return self.deck.screen_image_format()
    
    def set_poll_frequency(self, hz):
        """
        Sets the frequency of the button polling reader thread, determining how
        often the StreamDeck will be polled for button changes.

        A higher frequency will result in a higher CPU usage, but a lower
        latency between a physical button press and a event from the library.

        :param int hz: Reader thread frequency, in Hz (1-1000).
        """
        self.deck.set_poll_frequency(hz)

    def set_key_callback(self, callback):
        """
        Sets the callback function called each time a button on the StreamDeck
        changes state (either pressed, or released).

        .. note:: This callback will be fired from an internal reader thread.
                  Ensure that the given callback function is thread-safe.

        .. note:: Only one callback can be registered at one time.

        .. seealso:: See :func:`~StreamDeck.set_key_callback_async` method for
                     a version compatible with Python 3 `asyncio` asynchronous
                     functions.

        :param function callback: Callback function to fire each time a button
                                state changes.
        """
        def remapper_callback(deck, key, state):
            logical_key = self.get_logical_index(key)
            callback(deck, logical_key, state)

        self.deck.set_key_callback(remapper_callback)

    def set_key_callback_async(self, async_callback, loop=None):
        """
        Sets the asynchronous callback function called each time a button on the
        StreamDeck changes state (either pressed, or released). The given
        callback should be compatible with Python 3's `asyncio` routines.

        .. note:: The asynchronous callback will be fired in a thread-safe
                  manner.

        .. note:: This will override the callback (if any) set by
                  :func:`~StreamDeck.set_key_callback`.

        :param function async_callback: Asynchronous callback function to fire
                                        each time a button state changes.
        :param asyncio.loop loop: Asyncio loop to dispatch the callback into
        """
        async def remapper_callback(deck, key, state):
            logical_key = self.get_logical_index(key)
            await async_callback(deck, logical_key, state)

        self.set_key_callback_async(remapper_callback, loop)

    def set_dial_callback(self, callback):
        """
        Sets the callback function called each time there is an interaction
        with a dial on the StreamDeck.

        .. note:: This callback will be fired from an internal reader thread.
                  Ensure that the given callback function is thread-safe.

        .. note:: Only one callback can be registered at one time.

        .. seealso:: See :func:`~StreamDeck.set_dial_callback_async` method
                     for a version compatible with Python 3 `asyncio`
                     asynchronous functions.

        :param function callback: Callback function to fire each time a button
                                state changes.
        """
        self.deck.set_dial_callback(callback)

    def set_dial_callback_async(self, async_callback, loop=None):
        """
        Sets the asynchronous callback function called each time there is an
        interaction with a dial on the StreamDeck. The given callback should
        be compatible with Python 3's `asyncio` routines.

        .. note:: The asynchronous callback will be fired in a thread-safe
                  manner.

        .. note:: This will override the callback (if any) set by
                  :func:`~StreamDeck.set_dial_callback`.

        :param function async_callback: Asynchronous callback function to fire
                                        each time a button state changes.
        :param asyncio.loop loop: Asyncio loop to dispatch the callback into
        """

        self.set_dial_callback_async(async_callback, loop)

    def set_touchscreen_callback(self, callback):
        """
        Sets the callback function called each time there is an interaction
        with a touchscreen on the StreamDeck.

        .. note:: This callback will be fired from an internal reader thread.
                  Ensure that the given callback function is thread-safe.

        .. note:: Only one callback can be registered at one time.

        .. seealso:: See :func:`~StreamDeck.set_touchscreen_callback_async`
                     method for a version compatible with Python 3 `asyncio`
                     asynchronous functions.

        :param function callback: Callback function to fire each time a button
                                state changes.
        """
        self.deck.set_touchscreen_callback(callback)

    def set_touchscreen_callback_async(self, async_callback, loop=None):
        """
        Sets the asynchronous callback function called each time there is an
        interaction with the touchscreen on the StreamDeck. The given callback
        should be compatible with Python 3's `asyncio` routines.

        .. note:: The asynchronous callback will be fired in a thread-safe
                  manner.

        .. note:: This will override the callback (if any) set by
                  :func:`~StreamDeck.set_touchscreen_callback`.

        :param function async_callback: Asynchronous callback function to fire
                                        each time a button state changes.
        :param asyncio.loop loop: Asyncio loop to dispatch the callback into
        """

        self.set_touchscreen_callback_async(async_callback, loop)

    def key_states(self):
        """
        Retrieves the current states of the buttons on the StreamDeck.

        :rtype: list(bool)
        :return: List describing the current states of each of the buttons on
                 the device (`True` if the button is being pressed, `False`
                 otherwise).
        """
        return self.reorder_physical_for_rotation(self.deck.key_states())

    def dial_states(self):
        """
        Retrieves the current states of the dials (pressed or not) on the
        Stream Deck

        :rtype: list(bool)
        :return: List describing the current states of each of the dials on
                 the device (`True` if the dial is being pressed, `False`
                 otherwise).
        """
        return self.deck.dial_states()

    def reset(self):
        """
        Resets the StreamDeck, clearing all button images and showing the
        standby image.
        """
        self.deck.reset()

    def set_brightness(self, percent):
        """
        Sets the global screen brightness of the StreamDeck, across all the
        physical buttons.

        :param int/float percent: brightness percent, from [0-100] as an `int`,
                                  or normalized to [0.0-1.0] as a `float`.
        """
        self.deck.set_brightness(percent)

    def get_serial_number(self):
        """
        Gets the serial number of the attached StreamDeck.

        :rtype: str
        :return: String containing the serial number of the attached device.
        """
        return self.deck.get_serial_number()

    def get_firmware_version(self):
        """
        Gets the firmware version of the attached StreamDeck.

        :rtype: str
        :return: String containing the firmware version of the attached device.
        """
        return self.deck.get_firmware_version()

    def set_key_image(self, key, image):
        """
        Sets the image of a button on the StreamDeck to the given image. The
        image being set should be in the correct format for the device, as an
        enumerable collection of bytes.

        .. seealso:: See :func:`~StreamDeck.key_image_format` method for
                     information on the image format accepted by the device.

        :param int key: Index of the button whose image is to be updated.
        :param enumerable image: Raw data of the image to set on the button.
                                 If `None`, the key will be cleared to a black
                                 color.
        """
        physical_key = self.get_physical_index(key)
        self.deck.set_key_image(physical_key, image)

    def set_touchscreen_image(self, image, x_pos=0, y_pos=0, width=0, height=0):
        """
        Draws an image on the touchscreen in a certain position. The image
        should be in the correct format for the devices, as an enumerable
        collection of bytes.

        .. seealso:: See :func:`~StreamDeck.touchscreen_image_format` method for
                     information on the image format accepted by the device.

        :param enumerable image: Raw data of the image to set on the button.
                                 If `None`, the touchscreen will be cleared.
        :param int x_pos: Position on x axis of the image to draw
        :param int y_pos: Position on y axis of the image to draw
        :param int width: width of the image
        :param int height: height of the image

        """
        self.deck.set_touchscreen_image(image, x_pos, y_pos, width, height)

    def set_screen_image(self, image):
        """
        Draws an image on the touchless screen of the StreamDeck.

        .. seealso:: See :func:`~StreamDeck.screen_image_format` method for
                     information on the image format accepted by the device.

        :param enumerable image: Raw data of the image to set on the button.
                                 If `None`, the screen will be cleared.
        """
        self.deck.set_screen_image(image)

    def set_key_color(self, key, r, g, b):
        """
        Sets the color of the touch buttons. These buttons are indexed
        in order after the standard keys.

        :param int key: Index of the button
        :param int r: Red value
        :param int g: Green value
        :param int b: Blue value

        """
        physical_key = self.get_physical_index(key)
        self.deck.set_key_color(physical_key, r, g, b)

    def set_screen_image(self, image):
        """
        Draws an image on the touchless screen of the StreamDeck.

        .. seealso:: See :func:`~StreamDeck.screen_image_format` method for
                     information on the image format accepted by the device.

        :param enumerable image: Raw data of the image to set on the button.
                                 If `None`, the screen will be cleared.
        """
        self.deck.set_screen_image(image)

    def set_rotation(self, value: int):
        if not value in [0, 90, 180, 270]:
            value = 0
        self.rotation = value

    def get_physical_index(self, logical_index):
        physical_rows, physical_cols = self.deck.key_layout()
        if self.rotation == 0:
            return logical_index
        elif self.rotation == 90:
            return ((physical_rows - 1 - (logical_index % physical_rows)) ) * physical_cols + (logical_index // physical_rows )
        elif self.rotation == 180:
            return (physical_rows * physical_cols) - logical_index - 1
        elif self.rotation == 270:
            return ((logical_index % physical_rows) * physical_cols ) + (physical_cols - 1 - (logical_index // physical_rows ))
    
        raise ValueError("Invalid rotation")
    
    def get_logical_index(self, physical_index):
        rows, cols = self.deck.key_layout()
        if self.rotation == 0:
            return physical_index
        elif self.rotation == 90:
            return (physical_index % cols) * rows + (rows - 1 - (physical_index // cols))
        elif self.rotation == 180:
            return rows * cols - physical_index - 1
        elif self.rotation == 270:
            return (cols - 1 - (physical_index % cols)) * rows + (physical_index // cols)
        else:
            return None
    
    def reorder_physical_for_rotation(self, original_list):
        pysical_rows, physical_cols = self.deck.key_layout()
        total = pysical_rows * physical_cols
        reordered = [None] * total
        
        for physical_index in range(total):
            logical_index = self.get_logical_index(physical_index)
            if logical_index is not None and 0 <= logical_index < total:
                reordered[physical_index] = original_list[logical_index]
        
        return reordered
        
    def get_rotation(self):
        return self.rotation
# Import globals first to get IS_MAC
import globals as gl

if not gl.IS_MAC:
    from evdev import ecodes as e

if not gl.IS_MAC:
    _SPECIAL_KEYS = {
        "plus": "+",
        "comma": ",",
        "delay": "delay",
    }
    _OLD_NUMPAD_KEYS = {
        "numpad_0": e.KEY_KP0,
        "numpad_1": e.KEY_KP1,
        "numpad_2": e.KEY_KP2,
        "numpad_3": e.KEY_KP3,
        "numpad_4": e.KEY_KP4,
        "numpad_5": e.KEY_KP5,
        "numpad_6": e.KEY_KP6,
        "numpad_7": e.KEY_KP7,
        "numpad_8": e.KEY_KP8,
        "numpad_9": e.KEY_KP9,
        "numpad_enter": e.KEY_ENTER,
        "numpad_decimal": e.KEY_KPDOT,
        "numpad_divide": e.KEY_KPSLASH,
        "numpad_multiply": e.KEY_KPASTERISK,
        "numpad_subtract": e.KEY_KPMINUS,
        "numpad_add": e.KEY_KPPLUS,
    }
    _OLD_PYNPUT_KEYS = {
        "media_volume_mute": e.KEY_MUTE,
        "media_volume_down": e.KEY_VOLUMEDOWN,
        "media_volume_up": e.KEY_VOLUMEUP,
        "media_play_pause": e.KEY_PLAYPAUSE,
        "media_previous_track": e.KEY_PREVIOUSSONG,
        "media_previous": e.KEY_PREVIOUSSONG,
        "media_next_track": e.KEY_NEXTSONG,
        "media_next": e.KEY_NEXTSONG,
        "media_stop": e.KEY_STOPCD,
        "num_lock": e.KEY_NUMLOCK,
        "caps_lock": e.KEY_CAPSLOCK,
        "scroll_lock": e.KEY_SCROLLLOCK,
    }
    _MODIFIER_KEYS = {
        "ctrl": e.KEY_LEFTCTRL,
        "alt": e.KEY_LEFTALT,
        "alt_gr": e.KEY_RIGHTALT,
        "shift": e.KEY_LEFTSHIFT,
        "meta": e.KEY_LEFTMETA,
        "super": e.KEY_LEFTMETA,
        "win": e.KEY_LEFTMETA,
    }

    _BAD_ECODES = ['KEY_MAX', 'KEY_CNT']
    _KEY_MAPPING = {
        'a': e.KEY_A,
        'b': e.KEY_B,
        'c': e.KEY_C,
        'd': e.KEY_D,
        'e': e.KEY_E,
        'f': e.KEY_F,
        'g': e.KEY_G,
        'h': e.KEY_H,
        'i': e.KEY_I,
        'j': e.KEY_J,
        'k': e.KEY_K,
        'l': e.KEY_L,
        'm': e.KEY_M,
        'n': e.KEY_N,
        'o': e.KEY_O,
        'p': e.KEY_P,
        'q': e.KEY_Q,
        'r': e.KEY_R,
        's': e.KEY_S,
        't': e.KEY_T,
        'u': e.KEY_U,
        'v': e.KEY_V,
        'w': e.KEY_W,
        'x': e.KEY_X,
        'y': e.KEY_Y,
        'z': e.KEY_Z,
        'A': e.KEY_A,
        'B': e.KEY_B,
        'C': e.KEY_C,
        'D': e.KEY_D,
        'E': e.KEY_E,
        'F': e.KEY_F,
        'G': e.KEY_G,
        'H': e.KEY_H,
        'I': e.KEY_I,
        'J': e.KEY_J,
        'K': e.KEY_K,
        'L': e.KEY_L,
        'M': e.KEY_M,
        'N': e.KEY_N,
        'O': e.KEY_O,
        'P': e.KEY_P,
        'Q': e.KEY_Q,
        'R': e.KEY_R,
        'S': e.KEY_S,
        'T': e.KEY_T,
        'U': e.KEY_U,
        'V': e.KEY_V,
        'W': e.KEY_W,
        'X': e.KEY_X,
        'Y': e.KEY_Y,
        'Z': e.KEY_Z,
        '1': e.KEY_1,
        '2': e.KEY_2,
        '3': e.KEY_3,
        '4': e.KEY_4,
        '5': e.KEY_5,
        '6': e.KEY_6,
        '7': e.KEY_7,
        '8': e.KEY_8,
        '9': e.KEY_9,
        '0': e.KEY_0,
        '-': e.KEY_MINUS,
        '=': e.KEY_EQUAL,
        '[': e.KEY_LEFTBRACE,
        ']': e.KEY_RIGHTBRACE,
        '\\': e.KEY_BACKSLASH,
        ';': e.KEY_SEMICOLON,
        "'": e.KEY_APOSTROPHE,
        ',': e.KEY_COMMA,
        '.': e.KEY_DOT,
        '/': e.KEY_SLASH,
        ' ': e.KEY_SPACE,
        '\n': e.KEY_ENTER,
        '\t': e.KEY_TAB,
        '`': e.KEY_GRAVE,
        '!': e.KEY_1,
        '@': e.KEY_2,
        '#': e.KEY_3,
        '$': e.KEY_4,
        '%': e.KEY_5,
        '^': e.KEY_6,
        '&': e.KEY_7,
        '*': e.KEY_8,
        '(': e.KEY_9,
        ')': e.KEY_0,
        '_': e.KEY_MINUS,
        '+': e.KEY_EQUAL,
        '{': e.KEY_LEFTBRACE,
        '}': e.KEY_RIGHTBRACE,
        '|': e.KEY_BACKSLASH,
        ':': e.KEY_SEMICOLON,
        '"': e.KEY_APOSTROPHE,
        '<': e.KEY_COMMA,
        '>': e.KEY_DOT,
        '?': e.KEY_SLASH,
        '~': e.KEY_GRAVE,
    }
    _SHIFT_KEY_MAPPING = {
        '!': e.KEY_1,
        '@': e.KEY_2,
        '#': e.KEY_3,
        '$': e.KEY_4,
        '%': e.KEY_5,
        '^': e.KEY_6,
        '&': e.KEY_7,
        '*': e.KEY_8,
        '(': e.KEY_9,
        ')': e.KEY_0,
        '_': e.KEY_MINUS,
        '+': e.KEY_EQUAL,
        '{': e.KEY_LEFTBRACE,
        '}': e.KEY_RIGHTBRACE,
        '|': e.KEY_BACKSLASH,
        ':': e.KEY_SEMICOLON,
        '"': e.KEY_APOSTROPHE,
        '<': e.KEY_COMMA,
        '>': e.KEY_DOT,
        '?': e.KEY_SLASH,
        '~': e.KEY_GRAVE,
        'A': e.KEY_A,
        'B': e.KEY_B,
        'C': e.KEY_C,
        'D': e.KEY_D,
        'E': e.KEY_E,
        'F': e.KEY_F,
        'G': e.KEY_G,
        'H': e.KEY_H,
        'I': e.KEY_I,
        'J': e.KEY_J,
        'K': e.KEY_K,
        'L': e.KEY_L,
        'M': e.KEY_M,
        'N': e.KEY_N,
        'O': e.KEY_O,
        'P': e.KEY_P,
        'Q': e.KEY_Q,
        'R': e.KEY_R,
        'S': e.KEY_S,
        'T': e.KEY_T,
        'U': e.KEY_U,
        'V': e.KEY_V,
        'W': e.KEY_W,
        'X': e.KEY_X,
        'Y': e.KEY_Y,
        'Z': e.KEY_Z,
    }
    # we remove KEY_ from the key names to make it easier to type
    _SUPPORTED_KEYS = [key.replace("KEY_", "").lower() for key in dir(e) if key.startswith("KEY_") and key not in _BAD_ECODES]
    _SUPPORTED_KEY_CONSTANTS = [value for name, value in vars(e).items() if name.startswith('KEY_') and name not in _BAD_ECODES]
    # fmt: on

def parse_keys_as_keycodes(keys: str) -> list[list[str]]:
    stripped = keys.strip().replace(" ", "").lower()
    if not stripped:
        return []
    # split by , for sections
    sections = stripped.split(",")
    parsed_keys = []
    for section in sections:
        # split by + for individual keys
        individual = section.split("+")
        # filter empty strings
        individual = list(filter(None, individual))
        # replace any string with e.KEY_<string>
        individual = [getattr(e, f"KEY_{key.upper()}", key) for key in individual]
        # check if delay
        individual = [(int(key.replace("delay", "")) + _DELAY_KEYSYM) if isinstance(key, str) and key.startswith("delay") else key for key in individual]  # type: ignore # fmt: skip
        # replace special keys
        individual = [_SPECIAL_KEYS.get(key, key) for key in individual]
        # replace old numpad keys
        individual = [_OLD_NUMPAD_KEYS.get(key, key) for key in individual]
        # replace old media keys
        individual = [_OLD_PYNPUT_KEYS.get(key, key) for key in individual]
        # replace modifier keys
        individual = [_MODIFIER_KEYS.get(key, key) for key in individual]
        # replace key names with key codes
        individual = [_KEY_MAPPING.get(key, key) for key in individual]

        # if any value is not an int, raise an error
        if not all(isinstance(key, int) for key in individual):
            invalid_keys = [key for key in individual if not isinstance(key, int)]
            raise ValueError(f"Invalid keys: {invalid_keys}")

        if len(individual) > 0:
            parsed_keys.append(individual)

    return parsed_keys
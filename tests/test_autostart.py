import ast
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock


def load_autostart():
    path = Path(__file__).resolve().parent.parent / "autostart.py"
    tree = ast.parse(path.read_text())
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    namespace = {"IS_MAC": False, "log": Mock()}
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(path), "exec"), namespace)
    namespace["is_flatpak"] = Mock(return_value=False)
    namespace["setup_autostart_desktop_entry"] = Mock()
    return namespace


class TestAutostart(unittest.TestCase):
    def test_native_disable_does_not_request_portal(self):
        module = load_autostart()
        module["setup_autostart_flatpak"] = Mock()
        module["setup_autostart"](False)
        module["setup_autostart_flatpak"].assert_not_called()
        module["setup_autostart_desktop_entry"].assert_called_once_with(False)

    def test_flatpak_disable_still_requests_portal(self):
        module = load_autostart()
        module["is_flatpak"].return_value = True
        module["setup_autostart_flatpak"] = Mock()
        module["setup_autostart"](False)
        module["setup_autostart_flatpak"].assert_called_once_with(False)

    def test_failed_portal_callback_preserves_requested_state(self):
        for enable in (True, False):
            for raises in (True, False):
                with self.subTest(enable=enable, raises=raises):
                    module = load_autostart()
                    portal = Mock()
                    portal.request_background_finish.return_value = False
                    if raises:
                        portal.request_background_finish.side_effect = RuntimeError("portal unavailable")
                    module["Xdp"] = SimpleNamespace(
                        Portal=SimpleNamespace(new=lambda: portal),
                        BackgroundFlags=SimpleNamespace(AUTOSTART=1, ACTIVATABLE=2),
                    )
                    module["setup_autostart_flatpak"](enable)
                    callback = portal.request_background.call_args.args[5]
                    callback(portal, object(), None)
                    module["setup_autostart_desktop_entry"].assert_called_once_with(enable)


if __name__ == "__main__":
    unittest.main()

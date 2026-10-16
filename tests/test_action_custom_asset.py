import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock

_orig_argv = sys.argv
sys.argv = [sys.argv[0]]
try:
    from src.backend.PluginManager.ActionCore import ActionCore
finally:
    sys.argv = _orig_argv


class TestActionCustomAsset(unittest.TestCase):
    def setUp(self):
        self.action = ActionCore.__new__(ActionCore)
        self.action.get_is_present = MagicMock(return_value=True)
        self.action.page = MagicMock()
        self.action.state = 0
        self.action.input_ident = MagicMock()

    def test_not_present_returns_false(self):
        self.action.get_is_present.return_value = False
        self.assertFalse(self.action.has_custom_user_asset())

    def test_none_or_missing_media_path_returns_false(self):
        self.action.input_ident.get_config.return_value = {
            "states": {"0": {"media": {}}}
        }
        self.assertFalse(self.action.has_custom_user_asset())

        self.action.input_ident.get_config.return_value = {
            "states": {"0": {"media": {"path": None}}}
        }
        self.assertFalse(self.action.has_custom_user_asset())

        self.action.input_ident.get_config.return_value = {
            "states": {"0": {"media": {"path": ""}}}
        }
        self.assertFalse(self.action.has_custom_user_asset())

    def test_non_existent_file_path_returns_false(self):
        self.action.input_ident.get_config.return_value = {
            "states": {"0": {"media": {"path": "/non/existent/path/icon.png"}}}
        }
        self.assertFalse(self.action.has_custom_user_asset())

    def test_existing_file_path_returns_true(self):
        with tempfile.NamedTemporaryFile() as tmp:
            self.action.input_ident.get_config.return_value = {
                "states": {"0": {"media": {"path": tmp.name}}}
            }
            self.assertTrue(self.action.has_custom_user_asset())


if __name__ == "__main__":
    unittest.main()

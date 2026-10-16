import sys
import unittest
from unittest.mock import MagicMock

_orig_argv = sys.argv
sys.argv = [sys.argv[0]]
try:
    from src.backend.DeckManagement.Subclasses.ActionPermissionManager import ActionPermissionManager
finally:
    sys.argv = _orig_argv


class TestActionPermissionManager(unittest.TestCase):
    def setUp(self):
        self.state_mock = MagicMock()
        self.perm_manager = ActionPermissionManager(self.state_mock)

    def test_single_action_defaults_to_control_index_zero(self):
        # A state with exactly 1 action and no explicit permission keys
        dummy_state_dict = {
            "actions": [{"id": "test_plugin::TestAction", "settings": {}}]
        }
        self.perm_manager.get_state_dict = MagicMock(return_value=dummy_state_dict)

        self.assertEqual(self.perm_manager.get_image_control_index(), 0)
        self.assertEqual(self.perm_manager.get_label_control_indices(), [0, 0, 0])
        self.assertEqual(self.perm_manager.get_label_control_index(0), 0)
        self.assertEqual(self.perm_manager.get_label_control_index(1), 0)
        self.assertEqual(self.perm_manager.get_label_control_index(2), 0)
        self.assertEqual(self.perm_manager.get_background_control_index(), 0)

    def test_multi_action_without_defaults_returns_none(self):
        # A state with multiple actions and no explicit permission keys
        dummy_state_dict = {
            "actions": [
                {"id": "test_plugin::Action1", "settings": {}},
                {"id": "test_plugin::Action2", "settings": {}},
            ]
        }
        self.perm_manager.get_state_dict = MagicMock(return_value=dummy_state_dict)

        self.assertIsNone(self.perm_manager.get_image_control_index())
        self.assertEqual(self.perm_manager.get_label_control_indices(), [None, None, None])
        self.assertIsNone(self.perm_manager.get_label_control_index(0))
        self.assertIsNone(self.perm_manager.get_background_control_index())

    def test_explicit_permissions_are_respected(self):
        dummy_state_dict = {
            "actions": [
                {"id": "test_plugin::Action1", "settings": {}},
                {"id": "test_plugin::Action2", "settings": {}},
            ],
            "image-control-action": 1,
            "label-control-actions": [1, 0, None],
            "background-control-action": 1,
        }
        self.perm_manager.get_state_dict = MagicMock(return_value=dummy_state_dict)

        self.assertEqual(self.perm_manager.get_image_control_index(), 1)
        self.assertEqual(self.perm_manager.get_label_control_indices(), [1, 0, None])
        self.assertEqual(self.perm_manager.get_label_control_index(0), 1)
        self.assertEqual(self.perm_manager.get_label_control_index(1), 0)
        self.assertIsNone(self.perm_manager.get_label_control_index(2))
        self.assertEqual(self.perm_manager.get_background_control_index(), 1)


if __name__ == "__main__":
    unittest.main()

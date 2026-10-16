import sys
import unittest
from unittest.mock import MagicMock
_orig_argv = sys.argv
sys.argv = [sys.argv[0]]
try:
    from src.backend.DeckManagement.InputIdentifier import Input
    from src.backend.PageManagement.Page import Page
    from src.backend.PluginManager.ActionCore import ActionCore
finally:
    sys.argv = _orig_argv


class TestPageStateRemoval(unittest.TestCase):
    def setUp(self):
        self.page = object.__new__(Page)
        self.page.action_objects = {}

    def test_remove_state_evicts_actions_and_updates_indices(self):
        input_ident = Input.Key("0x0")

        action_0 = MagicMock(spec=ActionCore)
        action_0.state = 0
        action_1 = MagicMock(spec=ActionCore)
        action_1.state = 1
        action_2 = MagicMock(spec=ActionCore)
        action_2.state = 2

        self.page.action_objects = {
            "keys": {
                "0x0": {
                    0: {0: action_0},
                    1: {0: action_1},
                    2: {0: action_2},
                }
            }
        }

        # Simulate removing state 1, mapping 0->0 and 2->1
        state_map = {0: 0, 2: 1}
        self.page.remove_state(input_ident, state=1, state_map=state_map)

        # Action 1 must have been evicted and cleaned up
        action_1.on_removed_from_cache.assert_called_once()
        self.assertIsNone(action_1.page)

        # State 0 and State 1 (formerly 2) must remain
        states = self.page.action_objects["keys"]["0x0"]
        self.assertEqual(set(states.keys()), {0, 1})
        self.assertIs(states[0][0], action_0)
        self.assertIs(states[1][0], action_2)
        self.assertEqual(action_2.state, 1)

    def test_fix_action_objects_order_preserves_state_structure(self):
        input_ident = Input.Key("0x0")
        action_a = MagicMock(spec=ActionCore)
        action_b = MagicMock(spec=ActionCore)

        self.page.action_objects = {
            "keys": {
                "0x0": {
                    0: {0: action_a, 2: action_b}
                }
            }
        }

        self.page.fix_action_objects_order(input_ident, state=0)
        actions = self.page.action_objects["keys"]["0x0"][0]
        self.assertEqual(list(actions.keys()), [0, 1])
        self.assertIs(actions[0], action_a)
        self.assertIs(actions[1], action_b)


if __name__ == "__main__":
    unittest.main()

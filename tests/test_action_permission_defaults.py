"""
Tests for the control defaults of ActionPermissionManager.

A key state created without the action UI (AddPage over DBus, the CLI or a
hand-written page json) has no "image-control-action",
"background-control-action" or "label-control-actions". Such states must
behave like the UI's default (action 0 controls everything), otherwise every
set_media()/set_label()/set_background_color() of the action is silently
dropped. An explicit None means the user turned the control off and must stay
off.

Run with:

    python3 -m unittest discover -s tests -t .
"""
import unittest

from src.backend.DeckManagement.Subclasses.ActionPermissionManager import ActionPermissionManager


class FakePage:
    def __init__(self):
        self.saved = 0

    def save(self):
        self.saved += 1


class Probe(ActionPermissionManager):
    """ActionPermissionManager on a plain state dict, without a deck."""

    def __init__(self, state_dict: dict):
        self.state_dict = state_dict
        self.page = FakePage()

    def get_state_dict(self) -> dict:
        return self.state_dict

    def get_own_page(self):
        return self.page


class TestControlDefaults(unittest.TestCase):
    def test_missing_entries_default_to_first_action(self):
        manager = Probe({"actions": [{"id": "x::y", "settings": {}}]})
        self.assertEqual(manager.get_image_control_index(), 0)
        self.assertEqual(manager.get_background_control_index(), 0)
        self.assertEqual(manager.get_label_control_indices(), [0, 0, 0])

    def test_explicit_none_stays_off(self):
        manager = Probe({
            "image-control-action": None,
            "background-control-action": None,
            "label-control-actions": [None, None, None],
        })
        self.assertIsNone(manager.get_image_control_index())
        self.assertIsNone(manager.get_background_control_index())
        self.assertEqual(manager.get_label_control_indices(), [None, None, None])

    def test_explicit_index_is_kept(self):
        manager = Probe({"image-control-action": 1, "label-control-actions": [None, 1, 0]})
        self.assertEqual(manager.get_image_control_index(), 1)
        self.assertEqual(manager.get_label_control_index(1), 1)

    def test_toggling_one_label_keeps_the_default_of_the_others(self):
        manager = Probe({})
        manager.set_label_control_index(1, None, reload_pages=False)
        self.assertEqual(manager.get_label_control_indices(), [0, None, 0])

    def test_default_list_is_not_shared(self):
        first, second = Probe({}), Probe({})
        first.get_label_control_indices()[0] = None
        self.assertEqual(second.get_label_control_indices(), [0, 0, 0])


if __name__ == "__main__":
    unittest.main()

"""Regression: daemon-only UI stash must not retain every rendered key frame."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from PIL import Image


class FakeDeckController:
    def __init__(self):
        self.ui_image_changes_while_hidden = {}

    # Copied behavior under test (keeps the test free of GTK / deck hardware).
    def store_ui_image_while_hidden(self, identifier, image: Image.Image) -> None:
        if image is None:
            return
        previous = self.ui_image_changes_while_hidden.get(identifier)
        if previous is not None and previous is not image:
            previous.close()
        self.ui_image_changes_while_hidden[identifier] = image

    def clear_ui_image_changes_while_hidden(self) -> None:
        for image in self.ui_image_changes_while_hidden.values():
            if image is not None:
                image.close()
        self.ui_image_changes_while_hidden.clear()


class UiImageStashTests(unittest.TestCase):
    def test_store_closes_previous_image_for_same_key(self):
        deck = FakeDeckController()
        key = "keys:0x0"
        first = MagicMock(spec=Image.Image)
        second = MagicMock(spec=Image.Image)

        deck.store_ui_image_while_hidden(key, first)
        deck.store_ui_image_while_hidden(key, second)

        first.close.assert_called_once_with()
        second.close.assert_not_called()
        self.assertIs(deck.ui_image_changes_while_hidden[key], second)

    def test_store_keeps_distinct_keys(self):
        deck = FakeDeckController()
        a = MagicMock(spec=Image.Image)
        b = MagicMock(spec=Image.Image)

        deck.store_ui_image_while_hidden("keys:0x0", a)
        deck.store_ui_image_while_hidden("keys:1x0", b)

        a.close.assert_not_called()
        b.close.assert_not_called()
        self.assertEqual(len(deck.ui_image_changes_while_hidden), 2)

    def test_clear_closes_all(self):
        deck = FakeDeckController()
        a = MagicMock(spec=Image.Image)
        b = MagicMock(spec=Image.Image)
        deck.store_ui_image_while_hidden("keys:0x0", a)
        deck.store_ui_image_while_hidden("keys:1x0", b)

        deck.clear_ui_image_changes_while_hidden()

        a.close.assert_called_once_with()
        b.close.assert_called_once_with()
        self.assertEqual(deck.ui_image_changes_while_hidden, {})


if __name__ == "__main__":
    unittest.main()

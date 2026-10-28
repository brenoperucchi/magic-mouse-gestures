import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import magic_mouse_gestures as mmg


class GestureActionTest(unittest.TestCase):
    def test_default_swipe_right_goes_back(self):
        with mock.patch.object(mmg, 'SWIPE_REVERSE', False):
            self.assertEqual(mmg.gesture_action('swipe_right')[:2], ('alt', 'Left'))
            self.assertEqual(mmg.gesture_action('swipe_left')[:2], ('alt', 'Right'))

    def test_reverse_swaps_back_and_forward(self):
        with mock.patch.object(mmg, 'SWIPE_REVERSE', True):
            self.assertEqual(mmg.gesture_action('swipe_right')[:2], ('alt', 'Right'))
            self.assertEqual(mmg.gesture_action('swipe_left')[:2], ('alt', 'Left'))

    def test_no_gesture_means_no_action(self):
        self.assertIsNone(mmg.gesture_action(None))


if __name__ == '__main__':
    unittest.main()

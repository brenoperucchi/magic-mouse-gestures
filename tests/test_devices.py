import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import magic_mouse_gestures as mmg

MM1 = mmg.DEVICE_MODELS[0x030D]
MM2 = mmg.DEVICE_MODELS[0x0269]


def touch_record(x=100, y=100, state=4):
    # 8 bytes: x/y packed in 0-2, size in byte 5, state in the high nibble of byte 7
    return bytes([x & 0xFF, ((y & 0x0F) << 4) | (x >> 8), y >> 4, 10, 10, 0x20, 0, state << 4])


def report(model, fingers):
    header = bytearray(model['header_size'])
    header[0] = model['report_id']
    return bytes(header) + b''.join(touch_record(x=100 + i * 50) for i in range(fingers))


class ParseHidIdTest(unittest.TestCase):
    def test_reads_vendor_and_product(self):
        self.assertEqual(mmg.parse_hid_id('DRIVER=magicmouse\nHID_ID=0005:0000004C:00000269\nHID_NAME=x\n'), (0x4C, 0x269))
        self.assertEqual(mmg.parse_hid_id('HID_ID=0003:000005AC:0000030D\n'), (0x5AC, 0x30D))

    def test_missing_line(self):
        self.assertIsNone(mmg.parse_hid_id('HID_NAME=x\n'))

    def test_supported_ids(self):
        for ids in ((0x4C, 0x269), (0x5AC, 0x269), (0x5AC, 0x30D), (0x4C, 0x323), (0x5AC, 0x323)):
            self.assertIn(ids, mmg.SUPPORTED_DEVICES)
        # Magic Keyboard / Trackpad must not match
        self.assertNotIn((0x4C, 0x26C), mmg.SUPPORTED_DEVICES)


class ParseReportTest(unittest.TestCase):
    def test_magic_mouse_2_header_is_14_bytes(self):
        self.assertEqual(len(mmg.parse_report(report(MM2, 2), MM2)), 2)

    def test_magic_mouse_1_header_is_6_bytes(self):
        self.assertEqual(len(mmg.parse_report(report(MM1, 2), MM1)), 2)

    def test_mouse_1_report_is_not_read_with_mouse_2_layout(self):
        # 6 + 2*8 = 22 bytes; read with a 14-byte header it would be 1 finger of garbage
        self.assertEqual(mmg.parse_report(report(MM1, 2), MM2), [])

    def test_other_report_ids_are_ignored(self):
        data = bytearray(report(MM2, 1))
        data[0] = 0x10
        self.assertEqual(mmg.parse_report(bytes(data), MM2), [])

    def test_short_report(self):
        self.assertEqual(mmg.parse_report(bytes([0x12] * 8), MM2), [])


if __name__ == '__main__':
    unittest.main()

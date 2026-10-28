import os
import subprocess
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import magic_mouse_gestures as mmg


def fake_run(failing):
    calls = []

    def run(cmd, **kwargs):
        if cmd[0] == 'id':
            return subprocess.CompletedProcess(cmd, 0, stdout='1000\n')
        calls.append(cmd[0])
        if cmd[0] in failing:
            raise subprocess.CalledProcessError(1, cmd)
        return subprocess.CompletedProcess(cmd, 0)

    return run, calls


class SendKeyTest(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(mmg, '_ydotool_syntax', 'code')
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_wtype_is_used_first(self):
        run, calls = fake_run(failing=())
        with mock.patch.object(mmg, 'KEY_BACKEND', 'auto'), \
                mock.patch.object(mmg.subprocess, 'run', run):
            self.assertTrue(mmg.send_key('alt', 'Left'))
        self.assertEqual(calls, ['wtype'])

    def test_falls_back_to_ydotool_when_wtype_fails(self):
        run, calls = fake_run(failing=('wtype',))
        with mock.patch.object(mmg, 'KEY_BACKEND', 'auto'), \
                mock.patch.object(mmg.subprocess, 'run', run):
            self.assertTrue(mmg.send_key('alt', 'Left'))
        self.assertEqual(calls, ['wtype', 'ydotool'])

    def test_ydotool_sends_alt_left_and_alt_right(self):
        with mock.patch.object(mmg, 'KEY_BACKEND', 'ydotool'), \
                mock.patch.object(mmg, '_ydotool_syntax', 'code'):
            left = mmg.build_key_commands('alt', 'Left')[0][1]
            right = mmg.build_key_commands('alt', 'Right')[0][1]
        self.assertEqual(left, ['ydotool', 'key', '56:1', '105:1', '105:0', '56:0'])
        self.assertEqual(right, ['ydotool', 'key', '56:1', '106:1', '106:0', '56:0'])

    def test_ydotool_0x_gets_key_names_not_codes(self):
        with mock.patch.object(mmg, 'KEY_BACKEND', 'ydotool'), \
                mock.patch.object(mmg, '_ydotool_syntax', 'name'):
            left = mmg.build_key_commands('alt', 'Left')[0][1]
            right = mmg.build_key_commands('alt', 'Right')[0][1]
        self.assertEqual(left, ['ydotool', 'key', 'alt+Left'])
        self.assertEqual(right, ['ydotool', 'key', 'alt+Right'])

    def test_help_text_decides_syntax(self):
        help_1x = 'Usage: ydotool <cmd> <args>\nAvailable commands:\n  key\nUse environment variable YDOTOOL_SOCKET to specify daemon socket.\n'
        help_0x = 'Usage: ydotool <cmd> <args>\nAvailable commands:\n  key\n'
        cases = (
            (help_1x, '', 'code'),   # 1.x prints help to stdout
            ('', help_0x, 'name'),   # 0.x prints help to stderr
            ('', 'something odd', 'code'),  # unrecognised output: assume 1.x
        )
        for out, err, expected in cases:
            run = lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0, stdout=out, stderr=err)
            with mock.patch.object(mmg, '_ydotool_syntax', None), \
                    mock.patch.object(mmg.subprocess, 'run', run):
                os.environ.pop('YDOTOOL_SYNTAX', None)
                self.assertEqual(mmg.detect_ydotool_syntax(), expected)

    def test_ydotool_missing_assumes_1x_without_caching(self):
        def run(cmd, **kw):
            raise FileNotFoundError('ydotool')
        with mock.patch.object(mmg, '_ydotool_syntax', None), \
                mock.patch.object(mmg.subprocess, 'run', run):
            os.environ.pop('YDOTOOL_SYNTAX', None)
            self.assertEqual(mmg.detect_ydotool_syntax(), 'code')
            self.assertIsNone(mmg._ydotool_syntax)

    def test_env_override_wins(self):
        with mock.patch.object(mmg, '_ydotool_syntax', None), \
                mock.patch.dict(os.environ, {'YDOTOOL_SYNTAX': 'name'}):
            self.assertEqual(mmg.detect_ydotool_syntax(), 'name')

    def test_returns_false_when_all_backends_fail(self):
        run, calls = fake_run(failing=('wtype', 'ydotool'))
        with mock.patch.object(mmg, 'KEY_BACKEND', 'auto'), \
                mock.patch.object(mmg.subprocess, 'run', run):
            self.assertFalse(mmg.send_key('alt', 'Left'))

    def test_forced_backend_skips_the_other(self):
        run, calls = fake_run(failing=())
        with mock.patch.object(mmg, 'KEY_BACKEND', 'ydotool'), \
                mock.patch.object(mmg.subprocess, 'run', run):
            self.assertTrue(mmg.send_key('alt', 'Left'))
        self.assertEqual(calls, ['ydotool'])


if __name__ == '__main__':
    unittest.main()

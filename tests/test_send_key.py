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

    def test_version_flag_decides_syntax(self):
        def version(rc):
            return lambda cmd, **kw: subprocess.CompletedProcess(cmd, rc)
        for rc, expected in ((0, 'code'), (1, 'name')):
            with mock.patch.object(mmg, '_ydotool_syntax', None), \
                    mock.patch.dict(os.environ, {}, clear=False), \
                    mock.patch.object(mmg.subprocess, 'run', version(rc)):
                os.environ.pop('YDOTOOL_SYNTAX', None)
                self.assertEqual(mmg.detect_ydotool_syntax(), expected)

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

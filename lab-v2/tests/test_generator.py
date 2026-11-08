"""Exercise the generator's endpoint, timeout and stop boundaries without Docker."""
import importlib.util
import json
import subprocess
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

path = Path(__file__).resolve().parents[1] / 'ansible/files/mac_flapping_generator.py'
spec = importlib.util.spec_from_file_location('generator', path)
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)


class Clock:
    def __init__(self):
        self.now = 0
        self.stopped = False

    def is_set(self):
        return self.stopped

    def wait(self, seconds):
        self.now += seconds


class GeneratorTests(unittest.TestCase):
    def run_generator(self, clock, send_error=None, on_started=None):
        commands = []

        def command(argv, **kwargs):
            commands.append((argv, kwargs))
            if argv[1] == 'inspect':
                return SimpleNamespace(stdout=json.dumps([{'Name': '/' + argv[2], 'State': {'Running': True}}]))
            if send_error:
                raise send_error
            return SimpleNamespace(returncode=0)

        with patch.object(generator.subprocess, 'run', side_effect=command), patch.object(generator.time, 'monotonic', side_effect=lambda: clock.now):
            frames = generator.run(10, clock, on_started=on_started)
        return frames, commands

    def test_duration_bound_and_fixed_dataplane(self):
        clock = Clock()
        frames, commands = self.run_generator(clock)
        self.assertGreater(frames, 0)
        self.assertLessEqual(clock.now, 10)
        sent = [argv for argv, _ in commands if argv[1] == 'exec']
        self.assertEqual({argv[2] for argv in sent}, {'clab-macflap-v2-host-a', 'clab-macflap-v2-host-b'})
        self.assertTrue(all(argv[argv.index('--interface') + 1] == 'eth1' for argv in sent))
        self.assertTrue(all(argv[argv.index('--mac') + 1] == '02:00:00:00:00:aa' for argv in sent))
        self.assertTrue(all(kwargs['timeout'] <= 10 for _, kwargs in commands))

    def test_stop_prevents_more_frames(self):
        clock = Clock()
        clock.stopped = True
        frames, commands = self.run_generator(clock)
        self.assertEqual(frames, 0)
        self.assertFalse(any(argv[1] == 'exec' for argv, _ in commands))

    def test_timeout_aborts_instead_of_relaunching(self):
        with self.assertRaises(subprocess.TimeoutExpired):
            self.run_generator(Clock(), subprocess.TimeoutExpired('docker', 5))

    def test_readiness_requires_both_endpoint_frames(self):
        ready = []
        clock = Clock()
        self.run_generator(clock, on_started=lambda: ready.append(clock.now))
        self.assertEqual(len(ready), 1)
        self.assertGreater(ready[0], 0)
        ready.clear()
        with self.assertRaises(subprocess.TimeoutExpired):
            self.run_generator(Clock(), subprocess.TimeoutExpired('docker', 5), on_started=lambda: ready.append(True))
        self.assertEqual(ready, [])

    def test_systemd_readiness_socket_payload(self):
        with patch.dict(generator.os.environ, {'NOTIFY_SOCKET': '@test-generator'}), patch.object(generator.socket, 'AF_UNIX', 1, create=True), patch.object(generator.socket, 'socket') as socket:
            generator.notify_ready()
        socket.return_value.__enter__.return_value.sendto.assert_called_once_with(b'READY=1', '\0test-generator')

    def test_stopped_or_wrong_container_is_refused(self):
        for row in [{'Name': '/clab-macflap-v2-host-a', 'State': {'Running': False}}, {'Name': '/clab-macflap-host-a', 'State': {'Running': True}}]:
            with patch.object(generator.subprocess, 'run', return_value=SimpleNamespace(stdout=json.dumps([row]))), self.assertRaises(RuntimeError):
                generator.run(10, Clock())

    def test_invalid_duration_never_calls_docker(self):
        for duration in [0, 9, 1801, '600', 10.5]:
            with patch.object(generator.subprocess, 'run') as command, self.assertRaises(ValueError):
                generator.run(duration, Clock())
            command.assert_not_called()


if __name__ == '__main__':
    unittest.main()

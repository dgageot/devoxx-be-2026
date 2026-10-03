"""Offline lifecycle checks for the slide-scoped trace viewer."""

import signal
import subprocess
import unittest
from unittest.mock import Mock, patch

import trace_viewer


class TraceViewerTests(unittest.TestCase):
    def setUp(self):
        trace_viewer.STOP = False
        self.config = '{"services":{"jaeger":{"image":"pinned-image","ports":[{"host_ip":"127.0.0.1","published":"16686","target":16686},{"host_ip":"127.0.0.1","published":"4318","target":4318}]}}}'

    def tearDown(self):
        trace_viewer.STOP = False

    def run_viewer(self, start_error=None, log_error=None, removal_error=None, during_wait=False):
        handlers = {}
        logs = Mock()
        logs.poll.return_value = None if removal_error or during_wait else 0

        def run(*args):
            if args[0] == "config":
                raise AssertionError("Use the dedicated Compose config.")
            if args[0] == "compose":
                return Mock(stdout=self.config)
            if args[0] == "create":
                return Mock(stdout="owned-container-id\n")
            if args[0] == "start":
                if start_error:
                    raise start_error
                if not during_wait:
                    handlers[signal.SIGHUP](signal.SIGHUP, None)
            if args[0] == "rm" and removal_error:
                raise removal_error
            return Mock(stdout="")

        with patch.object(trace_viewer.signal, "signal", side_effect=lambda sig, fn: handlers.update({sig: fn})), \
                patch.object(trace_viewer, "docker", side_effect=run) as docker, \
                patch.object(trace_viewer.subprocess, "Popen", return_value=logs, side_effect=log_error), \
                patch.object(trace_viewer.time, "sleep", side_effect=lambda _: handlers[signal.SIGHUP](signal.SIGHUP, None)):
            if start_error or log_error or removal_error:
                with self.assertRaises((OSError, subprocess.SubprocessError)):
                    trace_viewer.main()
            else:
                trace_viewer.main()
        if removal_error or during_wait:
            logs.terminate.assert_called_once()
            logs.wait.assert_called_once_with(timeout=5)
        return docker, handlers

    def test_terminal_hangup_removes_only_created_container(self):
        docker, handlers = self.run_viewer()
        for sig in (signal.SIGHUP, signal.SIGINT, signal.SIGTERM):
            self.assertIn(sig, handlers)
        create = next(call.args for call in docker.call_args_list if call.args[0] == "create")
        self.assertIn("never", create)
        self.assertIn("127.0.0.1:16686:16686", create)
        self.assertIn("127.0.0.1:4318:4318", create)
        docker.assert_any_call("rm", "--force", "owned-container-id")
        self.assertFalse(any(call.args[0] in ("stop", "kill") for call in docker.call_args_list))

    def test_start_failure_still_removes_owned_container(self):
        docker, _ = self.run_viewer(start_error=subprocess.CalledProcessError(1, "docker start"))
        docker.assert_any_call("rm", "--force", "owned-container-id")

    def test_hangup_during_polling_cleans_up(self):
        docker, _ = self.run_viewer(during_wait=True)
        docker.assert_any_call("rm", "--force", "owned-container-id")

    def test_removal_failure_still_reaps_log_process(self):
        self.run_viewer(removal_error=subprocess.CalledProcessError(1, "docker rm"))

    def test_log_start_failure_still_removes_owned_container(self):
        docker, _ = self.run_viewer(log_error=OSError("cannot start logs"))
        docker.assert_any_call("rm", "--force", "owned-container-id")


if __name__ == "__main__":
    unittest.main()

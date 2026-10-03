#!/usr/bin/env python3
"""Keep one detached, host-native arena per presentation root.

Opening another terminal preserves sealed entries (FAIR-1). Only explicit reset
or stop discards in-memory state. Native mode remains loopback-only.
"""

import argparse
import fcntl
import http.client
import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path


class StartupError(RuntimeError):
    pass


@contextmanager
def startup_lock(path, timeout=125):
    # Keep the inode: unlinking allows two shells to lock different files.
    with path.open("a") as lock:
        deadline = time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise StartupError("Timed out waiting for another arena startup") from None
                time.sleep(0.1)
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def process_identity(pid):
    # Never request environment output or log a process's command line.
    result = subprocess.run(["ps", "-ww", "-p", str(pid), "-o", "lstart=", "-o", "stat=", "-o", "command="],
                            capture_output=True, text=True, timeout=5,
                            env={**os.environ, "LC_ALL": "C"}, check=False)
    if result.returncode == 1 and not result.stdout.strip():
        return None
    fields = result.stdout.strip().split(None, 6)
    if result.returncode or len(fields) != 7:
        raise StartupError("Cannot verify arena process identity; refusing automatic recovery")
    # Zombies and macOS exiting processes have no live backend.
    if fields[5].startswith("Z") or "E" in fields[5]:
        return None
    return {"birth": " ".join(fields[:5]), "command": fields[6]}


def control_path(instance):
    # A short path also works with long presentation roots on macOS.
    return Path("/tmp") / f"devoxx-arena-{instance}" / "control.sock"


def read_message(stream):
    line = stream.readline(4097)
    if len(line) > 4096 or not line.endswith(b"\n"):
        raise StartupError("Invalid arena control response; refusing adoption")
    try:
        value = json.loads(line)
    except (ValueError, UnicodeError, RecursionError) as error:
        raise StartupError("Invalid arena control response; refusing adoption") from error
    if not isinstance(value, dict):
        raise StartupError("Invalid arena control response; refusing adoption")
    return value


def send_message(stream, value):
    stream.write(json.dumps(value).encode() + b"\n")
    stream.flush()


class ArenaProcess:
    def __init__(self, root, port=8090):
        if type(port) is not int or not 1 <= port <= 65535:
            raise StartupError("DEMO_ARENA_PORT must be an integer between 1 and 65535")
        self.root = Path(root).resolve()
        if not (self.root / "demoit.html").is_file() or not (self.root / "scripts/arena_api.py").is_file():
            raise StartupError("Presentation root or native arena backend is missing")
        self.port = port
        self.state = self.root / ".state"
        self.state.mkdir(exist_ok=True)
        self.record_path = self.state / "arena-process.json"
        self.child = None

    def worker_args(self, port, instance):
        return ["-I", str(Path(__file__).resolve()), "--serve", "--root", str(self.root),
                "--port", str(port), "--instance", instance]

    def load_record(self):
        try:
            record = json.loads(self.record_path.read_text())
        except FileNotFoundError:
            return None
        except (ValueError, UnicodeError, RecursionError) as error:
            raise StartupError("Invalid arena ownership record; human review required") from error
        if (not isinstance(record, dict) or record.get("version") != 1 or
                record.get("root") != str(self.root) or type(record.get("pid")) is not int or
                record["pid"] <= 1 or type(record.get("port")) is not int or
                not 1 <= record["port"] <= 65535 or not isinstance(record.get("instance"), str) or
                not re.fullmatch(r"[0-9a-f]{32}", record["instance"]) or
                not isinstance(record.get("birth"), str) or not record["birth"] or
                not isinstance(record.get("command"), str) or
                not record["command"].endswith(" " + " ".join(self.worker_args(record["port"], record["instance"])))):
            raise StartupError("Arena ownership mismatch; refusing adoption or modification")
        return record

    def owned_identity(self, record):
        identity = process_identity(record["pid"])
        if identity is not None and any(identity[key] != record[key] for key in ("birth", "command")):
            raise StartupError("Arena PID was reused or ownership changed; refusing to modify it")
        return identity

    def control(self, record, action="status"):
        if self.owned_identity(record) is None:
            raise StartupError("Owned arena exited; explicitly reset or stop it")
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
            connection.settimeout(2)
            connection.connect(str(control_path(record["instance"])))
            with connection.makefile("rwb") as stream:
                greeting = read_message(stream)
                expected = {key: record[key] for key in ("root", "pid", "port", "instance")}
                if greeting != expected:
                    raise StartupError("Arena control ownership mismatch; refusing adoption or modification")
                # Use the verified connection, not a PID signal that could race PID reuse.
                if self.owned_identity(record) is None:
                    raise StartupError("Owned arena exited; explicitly reset or stop it")
                send_message(stream, {"instance": record["instance"], "action": action})
                reply = read_message(stream)
                if reply != {"status": "stopping" if action == "stop" else "running"}:
                    raise StartupError("Arena control unavailable; human review required")

    def healthy(self, port):
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
        try:
            connection.request("GET", "/health")
            response = connection.getresponse()
            data = response.read(4097)
            value = json.loads(data) if len(data) <= 4096 else None
            return (response.status == 200 and isinstance(value, dict) and
                    value.get("status") == "ok" and value.get("synthetic") is True and
                    value.get("loopback_only") is True and value.get("deployment") == "native")
        except (OSError, ValueError, RecursionError, http.client.HTTPException):
            return False
        finally:
            connection.close()

    def require_free_port(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind(("127.0.0.1", self.port))
                probe.listen(1)
            except OSError as error:
                raise StartupError(f"Port {self.port} is unavailable; refusing to adopt or stop its listener") from error

    def log(self, message):
        # Only fixed lifecycle messages; backend output and environment stay private.
        with (self.state / "arena-startup.log").open("a") as log:
            log.write(message + "\n")

    def start(self):
        self.require_free_port()
        instance = uuid.uuid4().hex
        path = control_path(instance)
        path.parent.mkdir(mode=0o700)
        args = self.worker_args(self.port, instance)
        try:
            self.child = subprocess.Popen([sys.executable, *args], cwd=self.root,
                                          stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                          stderr=subprocess.DEVNULL, start_new_session=True, close_fds=True)
        except OSError:
            path.parent.rmdir()
            raise
        deadline = time.monotonic() + 5
        while True:
            identity = process_identity(self.child.pid)
            if path.exists() and identity is not None and identity["command"].endswith(" " + " ".join(args)):
                break
            if self.child.poll() is not None:
                try:
                    path.parent.rmdir()
                except FileNotFoundError:
                    pass
                raise StartupError("Native arena exited before ownership could be verified")
            if time.monotonic() >= deadline:
                raise StartupError("Native arena ownership verification timed out; human review required")
            time.sleep(0.05)
        record = {"version": 1, "root": str(self.root), "port": self.port,
                  "pid": self.child.pid, "instance": instance, **identity}
        temporary = self.record_path.with_suffix(f".{instance}.tmp")
        try:
            with open(temporary, "x", opener=lambda path, flags: os.open(path, flags, 0o600)) as output:
                json.dump(record, output)
            temporary.replace(self.record_path)
        finally:
            temporary.unlink(missing_ok=True)
        self.log("Native arena launched; ownership recorded")
        deadline = time.monotonic() + 25
        while True:
            try:
                self.control(record)
                if self.healthy(self.port):
                    self.log("Native arena ready on loopback")
                    return
            except OSError:
                pass
            if self.owned_identity(record) is None:
                raise StartupError("Native arena exited during startup; explicitly reset or stop it")
            if time.monotonic() >= deadline:
                raise StartupError("DATA-1: Native arena is not healthy; human review required; explicitly reset or stop it")
            time.sleep(0.1)

    def stop(self, record):
        if self.owned_identity(record) is not None:
            try:
                self.control(record, "stop")
            except OSError as error:
                raise StartupError("Cannot verify arena control ownership; refusing to stop it") from error
            deadline = time.monotonic() + 10
            while True:
                identity = process_identity(record["pid"])
                # Stop was acknowledged on the original connection; never touch a replacement PID.
                if identity is None or any(identity[key] != record[key] for key in ("birth", "command")):
                    break
                if time.monotonic() >= deadline:
                    raise StartupError("Owned arena did not stop; human review required (no PID signals sent)")
                time.sleep(0.1)
        if self.child is not None and self.child.pid == record["pid"]:
            self.child.wait(timeout=2)
        path = control_path(record["instance"])
        path.unlink(missing_ok=True)
        try:
            path.parent.rmdir()
        except FileNotFoundError:
            pass
        self.record_path.unlink()
        self.log("Owned native arena stopped; local state discarded")

    def execute(self, action="start", quiet=False):
        with startup_lock(self.state / "arena-start.lock"):
            record = self.load_record()
            if record and action in ("start", "reset") and record["port"] != self.port:
                raise StartupError("Arena port differs; explicitly stop the owned arena before reconfiguration")
            if action == "status":
                if record is None:
                    status, port = "not started", self.port
                elif self.owned_identity(record) is None:
                    status, port = "stopped", record["port"]
                else:
                    self.control(record)
                    status = "healthy" if self.healthy(record["port"]) else "needs review (DATA-1)"
                    port = record["port"]
                print(f"Arena {status}: http://127.0.0.1:{port}/ (native)")
                return
            if action in ("stop", "reset") and record:
                self.stop(record)
                record = None
            if action == "stop":
                if not quiet:
                    print("Owned arena stopped; next start creates an empty arena")
                return
            if record and action == "start" and self.owned_identity(record) is None:
                # A dead worker has no surviving in-memory entries. Never stop a live one.
                self.require_free_port()
                self.stop(record)
                self.log("Stale arena ownership cleared; restarting exited worker")
                record = None
            if record:
                try:
                    self.control(record)
                except OSError as error:
                    raise StartupError("Owned arena control unavailable; refusing replacement; human review required") from error
                if not self.healthy(record["port"]):
                    raise StartupError("DATA-1: Owned arena is unhealthy; human review required; explicitly reset it")
            else:
                self.start()
            if not quiet:
                print(f"Arena ready: http://127.0.0.1:{self.port}/")


def serve(root, port, instance):
    """Detached worker; only its authenticated control connection can stop it."""
    if not re.fullmatch(r"[0-9a-f]{32}", instance):
        raise StartupError("Invalid native worker identity")
    path = control_path(instance)
    try:
        sys.path.insert(0, str(root / "scripts"))
        from arena_api import ArenaServer

        with ArenaServer(("127.0.0.1", port), fixtures_dir=root / "fixtures") as server:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as control:
                control.bind(str(path))
                path.chmod(0o600)
                control.listen(4)
                control.settimeout(1)
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                confirmed = False
                deadline = time.monotonic() + 30
                try:
                    while thread.is_alive():
                        if not confirmed and time.monotonic() >= deadline:
                            return
                        try:
                            connection, _ = control.accept()
                        except socket.timeout:
                            continue
                        with connection:
                            connection.settimeout(2)
                            try:
                                with connection.makefile("rwb") as stream:
                                    send_message(stream, {"root": str(root), "pid": os.getpid(),
                                                          "port": port, "instance": instance})
                                    request = read_message(stream)
                                    if request not in ({"instance": instance, "action": "status"},
                                                       {"instance": instance, "action": "stop"}):
                                        continue
                                    confirmed = True
                                    stopping = request["action"] == "stop"
                                    send_message(stream, {"status": "stopping" if stopping else "running"})
                                    if stopping:
                                        return
                            except (OSError, StartupError):
                                continue
                finally:
                    server.shutdown()
                    thread.join(timeout=2)
    finally:
        path.unlink(missing_ok=True)
        path.parent.rmdir()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("start", "status", "reset", "stop"), nargs="?", default="start")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--port", default=os.environ.get("DEMO_ARENA_PORT", "8090"))
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--serve", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--instance", default="", help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        manager = ArenaProcess(args.root, int(args.port))
        if args.serve:
            serve(manager.root, manager.port, args.instance)
        else:
            manager.execute(args.action, args.quiet)
    except (StartupError, OSError, ValueError, subprocess.TimeoutExpired) as error:
        detail = str(error) if isinstance(error, StartupError) else "Native arena startup failed; inspect status or .state/arena-startup.log"
        print(f"Arena unavailable: {detail}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

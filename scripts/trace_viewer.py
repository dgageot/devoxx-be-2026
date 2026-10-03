#!/usr/bin/env python3
"""Keep a local Jaeger viewer alive only while this slide terminal is open."""

import json
from pathlib import Path
import signal
import subprocess
import time
import uuid

ROOT = Path(__file__).resolve().parent.parent
STOP = False


def request_stop(*_):
    global STOP
    STOP = True


def docker(*args):
    # Terminal hangup is handled here, not forwarded as a Jaeger config reload.
    return subprocess.run(["docker", *args], cwd=ROOT, check=True, text=True,
                          stdout=subprocess.PIPE, start_new_session=True, timeout=30)


def main():
    for sig in (signal.SIGHUP, signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, request_stop)
    config = json.loads(docker("compose", "-p", "devoxx-tracing", "-f",
                               "compose.tracing.yaml", "config", "--format", "json").stdout)
    service = config["services"]["jaeger"]
    run_id = uuid.uuid4().hex
    args = ["create", "--pull", "never", "--name", f"devoxx-trace-{run_id}",
            "--label", f"devoxx.trace-session={run_id}", "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges:true"]
    for port in service["ports"]:
        if port.get("host_ip") != "127.0.0.1":
            raise ValueError("Trace viewer ports must remain loopback-only.")
        args.extend(["--publish", f"127.0.0.1:{port['published']}:{port['target']}"])
    if STOP:
        return
    container_id = docker(*args, service["image"]).stdout.strip()
    logs = None
    try:
        if STOP:
            return
        docker("start", container_id)
        print("Jaeger: http://127.0.0.1:16686/search — closes with this terminal.", flush=True)
        logs = subprocess.Popen(["docker", "logs", "--follow", container_id],
                                cwd=ROOT, start_new_session=True)
        while not STOP and logs.poll() is None:
            time.sleep(0.25)
    finally:
        # Remove only the immutable ID created by this invocation, never a name/port occupant.
        try:
            docker("rm", "--force", container_id)
        finally:
            if logs is not None:
                if logs.poll() is None:
                    logs.terminate()
                try:
                    logs.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logs.kill()
                    logs.wait(timeout=5)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        raise SystemExit(f"Trace viewer failed: {error}") from error

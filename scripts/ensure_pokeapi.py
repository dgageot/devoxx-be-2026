#!/usr/bin/env python3
"""Start the prepared PokéAPI container, recovering one failed demo container."""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from ensure_arena import StartupError, startup_lock

INSPECT = '''{"id":{{json .Id}},"service":{{json (index .Config.Labels "com.docker.compose.service")}},"root":{{json (index .Config.Labels "com.docker.compose.project.working_dir")}},"files":{{json (index .Config.Labels "com.docker.compose.project.config_files")}},"status":{{json .State.Status}},"health":{{if .State.Health}}{{json .State.Health.Status}}{{else}}null{{end}}}'''


def pokeapi_running(root):
    # Query current Docker state; a cached readiness result could hide a stopped service.
    command = ["docker", "ps", "--no-trunc",
               "--filter", "label=com.docker.compose.service=pokeapi",
               "--filter", "label=com.docker.compose.oneoff=False",
               "--filter", f"label=com.docker.compose.project.working_dir={root}",
               "--filter", f"label=com.docker.compose.project.config_files={root / 'compose.yaml'}",
               "--filter", "status=running", "--filter", "health=healthy", "--format", "{{.ID}}"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0 and re.fullmatch(r"[0-9a-f]{64}", result.stdout.strip()) is not None


def ensure_pokeapi(root):
    root = Path(root).resolve()
    state = root / ".state"
    state.mkdir(exist_ok=True)
    compose = ["docker", "compose", "--project-directory", str(root), "--env-file", "/dev/null",
               "-f", str(root / "compose.yaml")]
    up = [*compose, "up", "-d", "--no-deps", "--no-build", "--pull", "never", "--no-recreate",
          "--wait", "--wait-timeout", "60", "pokeapi"]
    with startup_lock(state / "pokeapi-start.lock", timeout=180), (state / "pokeapi-startup.log").open("a") as log:
        if pokeapi_running(root):
            return
        try:
            if subprocess.run(up, stdout=log, stderr=log, timeout=75, check=False).returncode == 0:
                return
        except subprocess.TimeoutExpired:
            log.write("PokéAPI startup timed out; checking owned container for recovery\n")
            log.flush()
        result = subprocess.run([*compose, "ps", "--all", "--quiet", "pokeapi"],
                                capture_output=True, text=True, timeout=10, check=True)
        container = result.stdout.strip()
        if not re.fullmatch(r"[0-9a-f]{64}", container):
            raise StartupError("No single demo container to recover; check Docker and build the image beforehand")
        result = subprocess.run(["docker", "inspect", "--format", INSPECT, container],
                                capture_output=True, text=True, timeout=10, check=True)
        value = json.loads(result.stdout)
        if (value.get("id") != container or value.get("service") != "pokeapi" or
                value.get("root") != str(root) or value.get("files") != str(root / "compose.yaml")):
            raise StartupError("Container ownership mismatch; refusing automatic recovery")
        if value.get("status") == "running" and value.get("health") == "healthy":
            return
        if (value.get("status") not in ("created", "exited", "dead") and
                not (value.get("status") == "running" and value.get("health") == "unhealthy")):
            raise StartupError("Container is still starting or paused; refusing automatic replacement")
        # The immutable ID and Compose labels scope removal to this stateless demo service.
        log.write("Recovering failed demo PokéAPI container once\n")
        log.flush()
        subprocess.run(["docker", "rm", "--force", container], stdout=log, stderr=log, timeout=15, check=True)
        if subprocess.run(up, stdout=log, stderr=log, timeout=75, check=False).returncode:
            raise StartupError("Recovery failed; check Docker and port 8000; human review required (DATA-1)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()
    try:
        ensure_pokeapi(args.root)
    except (StartupError, OSError, ValueError, subprocess.SubprocessError) as error:
        detail = str(error) if isinstance(error, StartupError) else "Check Docker and build the image beforehand with docker compose build pokeapi"
        print(f"PokéAPI unavailable: {detail}. See .state/pokeapi-startup.log.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

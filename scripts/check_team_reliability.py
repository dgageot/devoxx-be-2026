#!/usr/bin/env python3
"""Measure proposal validity without submitting entries or starting tournaments."""

import argparse
import hashlib
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import time
from datetime import datetime, timezone

import yaml

from arena_rules import validate_team

ROOT = Path(__file__).resolve().parent.parent
PROHIBITED_TOOLS = ["join_local_arena", "submit_tournament_team", "create_tournament", "spar_team",
                    "run_background_agent", "wait_background_agents", "transfer_task"]


def proposal_config(value):
    """Preserve building behavior, but technically deny state-changing demo tools."""
    value.setdefault("permissions", {})["deny"] = PROHIBITED_TOOLS
    value.setdefault("runtime", {})["safety"] = "restricted"
    return value


def check_proposal(answer, challenge, catalog):
    if not isinstance(answer, dict):
        raise ValueError("Expected a JSON object")
    if answer.get("status", "proposed") != "proposed":
        raise ValueError("Response is not a successful untested proposal (DATA-1)")
    validation = validate_team(challenge, answer.get("team"), catalog)
    if validation["status"] != "ready":
        raise ValueError(validation["reason"])
    total = answer.get("stat_total")
    if type(total) not in (int, float) or total != validation["stat_total"]:
        raise ValueError("Reported total disagrees with captured facts (DATA-1)")
    return validation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("agent", type=Path)
    parser.add_argument("--agent-name", default="root")
    parser.add_argument("--repeat", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.repeat < 1 or args.concurrency < 1:
        parser.error("repeat and concurrency must be positive")
    catalog = json.loads((ROOT / "fixtures/arena-catalog.json").read_text())
    challenges = json.loads((ROOT / "fixtures/arena-challenges.json").read_text())
    # Same Water request, plus other published constraints; no registration authority.
    names = ["water-budget"] * 4 + ["fire-budget", "grass-budget", "electric-budget", "water-open"]
    env = dict(os.environ, DOCKER_AGENT_DATA_DIR=str(ROOT / ".state/reliability/data"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    overlay = args.output.with_suffix(".agent.yaml")
    overlay.write_text(yaml.safe_dump(proposal_config(yaml.safe_load(args.agent.read_text())),
                                      sort_keys=False, width=10000))
    captured_at = datetime.now(timezone.utc).isoformat()
    inputs = [args.agent.resolve(), Path(__file__).resolve(), ROOT / "agents/team-building.md",
              ROOT / "fixtures/arena-catalog.json", ROOT / "fixtures/arena-challenges.json"]
    hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
              for path in inputs}

    def run(index):
        name = names[index % len(names)]
        prompt = (
            f"Propose only a legal team for {name}, using seed {index + 1} to vary the shortlist. "
            "Do not spar, submit any entry, join a match, create or run a tournament. "
            "Return only a JSON object with team and stat_total."
        )
        command = ["docker", "agent", "run", "--exec", "--last", "--agent", args.agent_name,
                   str(overlay.resolve()), prompt]
        start = time.monotonic()
        result = {"seed": index + 1, "challenge_id": name}
        try:
            process = subprocess.run(command, cwd=ROOT, env=env, capture_output=True,
                                     text=True, timeout=90, check=True)
            text = process.stdout.strip()
            if text.startswith("```json\n") and text.endswith("\n```"):
                text = text[8:-4]
            answer = json.loads(text)
            validation = check_proposal(answer, challenges[name], catalog)
            result.update(valid=True, team=validation["team"], stat_total=validation["stat_total"])
        except ValueError as error:
            result.update(valid=False, error=str(error))
        except subprocess.SubprocessError as error:
            # Do not persist process output, environment, or provider diagnostics.
            result.update(valid=False, error=type(error).__name__)
        result["duration_seconds"] = round(time.monotonic() - start, 3)
        return result

    start = time.monotonic()
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        results = list(executor.map(run, range(args.repeat)))
    report = {"agent": str(args.agent), "agent_name": args.agent_name,
              "proposal_only": True, "prohibited_tools": PROHIBITED_TOOLS,
              "captured_at": captured_at, "concurrency": args.concurrency, "input_sha256": hashes,
              "overlay_sha256": hashlib.sha256(overlay.read_bytes()).hexdigest(),
              "validity_scope": "fixture-legal team and accurate total; live lookup evidence not audited",
              "runs": len(results),
              "valid": sum(item["valid"] for item in results),
              "duration_seconds": round(time.monotonic() - start, 3), "results": results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(f"{report['valid']}/{report['runs']} valid proposals; {report['duration_seconds']}s")
    if report["valid"] != report["runs"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

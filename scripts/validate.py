#!/usr/bin/env python3
"""Offline agent-config and eval checks. Never calls an LLM or reads credentials."""

import argparse
import json
import re
import subprocess
from pathlib import Path

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema", type=Path, required=True, help="Docker Agent agent-schema.json")
    parser.add_argument("--cli", action="store_true", help="Also parse with installed docker agent")
    args = parser.parse_args()
    schema = json.loads(args.schema.read_text())
    for path in sorted((ROOT / "agents").glob("*.yaml")):
        data = yaml.safe_load(path.read_text())
        jsonschema.validate(data, schema)
        if args.cli:
            subprocess.run(["docker", "agent", "debug", "config", str(path)], check=True, stdout=subprocess.DEVNULL)

    for directory in ("evals/arena", "evals/arena-heldout", "evals/arena-stretch"):
        for path in (ROOT / directory).glob("*.json"):
            test = json.loads(path.read_text())
            assert test["messages"][0]["message"]["message"]["role"] == "user"
            for assertion in test["evals"]["assertions"]:
                if assertion["type"] == "regex":
                    re.compile(assertion["value"])
    agents = len(list((ROOT / 'agents').glob('*.yaml')))
    evals = sum(len(list((ROOT / directory).glob('*.json'))) for directory in ('evals/arena', 'evals/arena-heldout', 'evals/arena-stretch'))
    print(f'Validated {agents} agent schemas and {evals} eval cases.')


if __name__ == "__main__":
    main()

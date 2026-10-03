#!/usr/bin/env python3
"""Minimal OpenAI-compatible chat client."""

import argparse
import json
import math
import os
import shutil
import textwrap
from urllib.request import Request, urlopen

def validate_plan(value):
    fields = {"challenge_id", "team", "stat_total", "status", "rules_version", "rule_ids", "sparring",
              "reason"}
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError("Incomplete or unexpected arena plan fields")
    if not isinstance(value["challenge_id"], str) or not value["challenge_id"]:
        raise ValueError("Invalid challenge")
    if value["rules_version"] != "arena-v3":
        raise ValueError("Invalid rules version")
    if value["status"] not in ("proposed", "ready", "ineligible", "needs_review"):
        raise ValueError("Invalid team disposition")
    if not isinstance(value["team"], list) or not all(isinstance(name, str) for name in value["team"]):
        raise ValueError("Invalid team")
    total = value["stat_total"]
    if total is not None and (type(total) not in (int, float) or not math.isfinite(total) or total < 0):
        raise ValueError("Invalid stat total")
    if value["status"] == "ready" and (len(value["team"]) != 3 or len(set(value["team"])) != 3 or total is None):
        raise ValueError("Ready plan lacks a legal team")
    if not isinstance(value["reason"], str) or not isinstance(value["rule_ids"], list):
        raise TypeError("Invalid explanation or rule references")
    if not value["rule_ids"] or not all(isinstance(rule, str) for rule in value["rule_ids"]):
        raise ValueError("Invalid rule references")
    if not isinstance(value["sparring"], list):
        raise TypeError("Invalid sparring results")
    if value["status"] == "ready" and not value["sparring"]:
        raise ValueError("Ready plan has no measured practice evidence")
    for result in value["sparring"]:
        if (not isinstance(result, dict) or set(result) != {"level", "outcome", "left_score", "right_score"} or
                result["level"] not in ("beginner", "intermediate", "advanced") or
                result["outcome"] not in ("win", "loss", "draw") or
                any(type(result[key]) not in (int, float) or not math.isfinite(result[key]) or result[key] < 0
                    for key in ("left_score", "right_score"))):
            raise ValueError("Invalid sparring result")
    return value


def say(text):
    # Tool/model text must not control the presentation terminal.
    print("".join(char if char.isprintable() or char in "\n\t" else "?" for char in text), flush=True)


def show_plan(plan):
    width = min(68, max(44, shutil.get_terminal_size().columns - 2))
    status = {
        "proposed": "Proposal — not yet tested",
        "ready": "Practice complete",
        "ineligible": "Team does not meet the rules",
        "needs_review": "Human review required (DATA-1)",
    }[plan["status"]]
    say("\n" + "─" * width)
    say("POKÉMON TEAM  /  " + plan["challenge_id"])
    say(status)
    say("─" * width)
    if plan["team"]:
        for index, name in enumerate(plan["team"], 1):
            say(f"  {index}. {name.replace('-', ' ').title()}")
    else:
        say("Team: Not determined")
    total = plan["stat_total"]
    say("\nCombined base stats: " + (str(total).removesuffix(".0") if total is not None else "Unknown"))

    say("\nSPARRING")
    if plan["sparring"]:
        say(f"{'Tier':<14} {'Result':<7} {'Our team':>10} {'Opponent':>10}")
        say("─" * 44)
        for result in plan["sparring"]:
            left = str(result["left_score"]).removesuffix(".0")
            right = str(result["right_score"]).removesuffix(".0")
            say(f"{result['level'].title():<14} {result['outcome'].upper():<7} {left:>10} {right:>10}")
    else:
        say("No practice results returned.")

    say("\nWHY THIS TEAM")
    for paragraph in plan["reason"].splitlines():
        say(textwrap.fill(paragraph, width=width))
    say("─" * width)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prompt", nargs="?", default="Propose a team for the water-budget challenge.")
    parser.add_argument("--url", default="http://127.0.0.1:8080")
    parser.add_argument("--model", default="root", help="Agent name exposed by /v1/models")
    args = parser.parse_args()
    headers = {"Content-Type": "application/json"}
    token = os.environ.get("DEMO_API_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps({
        "model": args.model,
        "messages": [{"role": "user", "content": args.prompt}],
        "stream": False,
    }).encode()
    say("Request: " + args.prompt)
    say("Waiting for the team builder...")
    request = Request(args.url.rstrip("/") + "/v1/chat/completions", data=body, headers=headers)
    with urlopen(request, timeout=150) as response:
        completion = json.load(response)
    if not isinstance(completion, dict) or "error" in completion:
        raise ValueError("Chat request failed; no recommendation available (DATA-1).")
    choices = completion.get("choices", [])
    if (not isinstance(choices, list) or len(choices) != 1
            or not isinstance(choices[0], dict) or choices[0].get("finish_reason") != "stop"):
        raise ValueError("Chat request did not return a completed recommendation (DATA-1).")
    message = choices[0].get("message", {})
    if (not isinstance(message, dict) or message.get("role") != "assistant"
            or not isinstance(message.get("content"), str)):
        raise ValueError("Chat response has no final recommendation (DATA-1).")
    decision = validate_plan(json.loads(message["content"]))
    show_plan(decision)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, TypeError, KeyError) as error:
        raise SystemExit(str(error)) from error

"""Offline regressions for the measured eval story and final builders."""

import hashlib
import html
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import unittest

import yaml

from arena_rules import validate_team
from check_team_reliability import PROHIBITED_TOOLS, check_proposal, proposal_config

ROOT = Path(__file__).resolve().parent.parent


def config(name):
    return yaml.safe_load((ROOT / "agents" / name).read_text())


class EvalStoryTests(unittest.TestCase):
    def test_capture_has_genuine_error_and_current_cases(self):
        provenance = json.loads((ROOT / "evals/baselines/arena.provenance.json").read_text())
        path = ROOT / "evals/baselines/arena.json"
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), provenance["run_sha256"])
        run = json.loads(path.read_text())
        self.assertEqual(len(run["sessions"]), 25)
        failures = [s for s in run["sessions"] if not s["eval_result"]["passed"]]
        self.assertEqual(len(failures), provenance["failed_cases"])
        self.assertEqual([s["id"] for s in failures], provenance["failure_session_ids"])
        self.assertIn("duplicate-team", {s["input_id"] for s in failures})
        for session in run["sessions"]:
            case = json.loads((ROOT / "evals/arena" / (session["input_id"] + ".json")).read_text())
            self.assertEqual(session["evals"], case["evals"])

    def test_measured_runs_are_intact(self):
        provenance = json.loads((ROOT / "evals/measurements/provenance.json").read_text())
        for name, measurement in provenance["measurements"].items():
            with self.subTest(name=name):
                path = ROOT / measurement["run_file"]
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), measurement["run_sha256"])
                data = json.loads(path.read_text())
                if "sessions" in data:
                    self.assertEqual(sum(s["eval_result"]["passed"] for s in data["sessions"]), measurement["passed"])
                    self.assertEqual(data["config"]["judge_model"], provenance["judge_model"])
                else:
                    self.assertTrue(data["proposal_only"])
                    self.assertEqual(sum(x["valid"] for x in data["results"]), measurement["valid"])

    def test_repeat5_rehearsals_match_current_cases_and_settings(self):
        provenance = json.loads((ROOT / "evals/stability/provenance.json").read_text())
        for path, digest in provenance["input_sha256"].items():
            self.assertEqual(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), digest, path)
        for measurement in provenance["measurements"].values():
            path = ROOT / measurement["run_file"]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), measurement["run_sha256"])
            run = json.loads(path.read_text())
            self.assertEqual(len(run["sessions"]), 25)
            self.assertEqual(run["config"]["concurrency"], 5)
            self.assertEqual(run["config"]["judge_model"], provenance["judge_model"])
            self.assertEqual(sum(s["eval_result"]["passed"] for s in run["sessions"]), measurement["passed"])
            errors = [s["id"] for s in run["sessions"] if any(
                m["message"]["message"].get("is_error") for m in s["messages"])]
            self.assertEqual(errors, measurement["tool_error_sessions"])
            for session in run["sessions"]:
                case = json.loads((ROOT / "evals/arena" / (session["input_id"] + ".json")).read_text())
                self.assertEqual(session["evals"], case["evals"])
        self.assertFalse((ROOT / "evals/arena/water-advanced.json").exists())
        self.assertTrue((ROOT / "evals/arena-stretch/water-advanced.json").exists())

    def test_compact_facts_preserve_evidence_without_computing_totals(self):
        hook = config("11-builder.yaml")["agents"]["root"]["hooks"]["tool_response_transform"][0]["hooks"][0]
        command = hook["command"]
        source = {"name": "squirtle", "is_default": True, "species": {"name": "squirtle", "url": "http://example"},
                  "stats": [{"base_stat": n, "effort": 0, "stat": {"name": str(i)}}
                            for i, n in enumerate([44, 48, 65, 50, 64, 43])],
                  "types": [{"slot": 1, "type": {"name": "water", "url": "http://example"}}]}
        result = subprocess.run(["sh", "-c", command], input=json.dumps({"tool_response": json.dumps(source)}),
                                capture_output=True, text=True, check=True)
        text = json.loads(result.stdout)["hook_specific_output"]["updated_tool_response"]
        facts = json.loads(text)
        self.assertLess(len(text.encode()), 500)
        self.assertEqual([s["base_stat"] for s in facts["stats"]], [s["base_stat"] for s in source["stats"]])
        self.assertEqual(facts["types"][0]["type"]["name"], "water")
        self.assertEqual(facts["species"]["name"], "squirtle")
        self.assertTrue(facts["is_default"])
        self.assertNotIn("stat_total", facts)
        result = subprocess.run(["sh", "-c", command], input=json.dumps({"tool_error": True, "tool_response": "failure"}),
                                capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(result.stdout), {})

    def test_eval_slides_show_native_commands_and_same_repeat_policy(self):
        slides = (ROOT / "demoit.html").read_text()
        expected = {
            "Run the evals": [],
            "Change one thing. Run again.": ["--flavor", "checked-totals", "--baseline", "evals/baselines/arena.json"],
            "Same task. Different model.": ["--flavor", "alternate-model", "--baseline", "evals/baselines/arena.json"],
        }
        history = (ROOT / ".demoit/.bash_history").read_text().splitlines()
        for path in ["demoit.html", "README.md", ".demoit/.bash_history"]:
            self.assertNotIn("--concurrency", (ROOT / path).read_text())
        for title, variant_flags in expected.items():
            slide = next(s for s in slides.split("\n---\n") if f"<h1>{title}</h1>" in s)
            command, = re.findall(r'<web-term[^>]* command="([^"]+)"', slide)
            self.assertEqual(shlex.split(command), [
                "docker", "agent", "eval", "agents/11-builder.yaml", "evals/arena", *variant_flags,
                "--repeat", "5", "--judge-model", "openai/gpt-5.6-terra",
            ])
            self.assertIn(command, history)
            self.assertIn(command, (ROOT / "README.md").read_text())

    def test_prompt_optimizer_slide_follows_comparison_and_precedes_holdout(self):
        slides = (ROOT / "demoit.html").read_text().split("\n---\n")
        index = next(i for i, slide in enumerate(slides)
                     if "<h1>An agent improves the prompt</h1>" in slide)
        slide = slides[index]
        self.assertIn("<h1>Keep it only if it helps</h1>", slides[index - 1])
        self.assertIn("<h1>Do not train on the final exam</h1>", slides[index + 1])
        self.assertIn('class="optional-marker"', slide)
        self.assertIn('<span class="stage">03</span>Prove', slide)
        self.assertIn('files="11-prompt-optimizer.yaml"', slide)
        command, = re.findall(r'<web-term[^>]* command="([^"]+)"', slide)
        command = html.unescape(command)
        self.assertEqual(shlex.split(command), [
            "docker", "agent", "run", "agents/11-prompt-optimizer.yaml",
            "Improve the builder prompt using development evals. Try at most three candidates.",
        ])
        for path in ["README.md", ".demoit/.bash_history"]:
            self.assertIn(command, (ROOT / path).read_text())
        for boundary in ["DATA-1", "FAIR-1", "do not sandbox shell", "held-out",
                         "not the child eval", "prompt-only gains", "Sessions JSON"]:
            self.assertIn(boundary, slide)

    def test_prompt_optimizer_scopes_filesystem_writes_and_asks_for_shell(self):
        value = config("11-prompt-optimizer.yaml")
        agent = value["agents"]["root"]
        reader, writer, shell = agent["toolsets"]
        self.assertTrue(reader["readonly"])
        self.assertFalse(reader["ignore_vcs"])
        self.assertEqual(set(reader["tools"]), {"read_file", "read_multiple_files"})
        self.assertEqual(reader["allow_list"], [
            "agents/11-builder.yaml", "agents/team-building.md", "agents/eval-setup.sh",
            "evals/arena", ".state/prompt-loop",
        ])
        self.assertFalse(writer["ignore_vcs"])
        self.assertEqual(set(writer["tools"]), {"write_file", "edit_file"})
        self.assertEqual(writer["allow_list"], [".state/prompt-loop"])
        self.assertEqual(shell, {"type": "shell"})
        self.assertEqual(value["runtime"]["safety"], "strict")
        self.assertEqual(value["permissions"]["ask"], ["shell"])
        self.assertNotIn("shell", value["permissions"]["allow"])
        self.assertGreater(value["budget"]["max_cost"], 0)
        self.assertGreater(value["budget"]["max_tokens"], 0)

    def test_prompt_optimizer_preserves_eval_policy_and_native_setup(self):
        instruction = config("11-prompt-optimizer.yaml")["agents"]["root"]["instruction"]
        for requirement in ["never overwrite the source or captured results",
                            "Do not read credentials, old/, evals/arena-heldout",
                            "Do not change eval cases, guidelines, setup, tools, hooks, models, flavors or schemas",
                            "Change only agents.root.instruction", "timeout 600", "one hypothesis",
                            "at most three candidate eval runs", "Do not retry to cherry-pick",
                            "human review, not promotion", "Child eval spend is outside your budget",
                            "Preserve every attempt and its raw results", "Sessions JSON path"]:
            self.assertIn(requirement, instruction)
        for support in ["agents/team-building.md", "agents/eval-setup.sh", "/configs"]:
            self.assertIn(support, instruction)
        for flag in ["--repeat 5", "--judge-model openai/gpt-5.6-terra"]:
            self.assertEqual(instruction.count(flag), 2)
        self.assertIn("--baseline <best_json> --output <run>/attempt-N", instruction)
        self.assertIn("native baseline gate reports no regression", instruction)
        self.assertIn("sessions[].eval_result.passed", instruction)
        self.assertIn("Save a copy as configs/attempt-N.yaml before evaluating", instruction)
        self.assertNotIn("--flavor", instruction)
        for rule in ["TEAM-1", "SPECIES-1", "BUDGET-1", "COVERAGE-1", "DATA-1", "FAIR-1"]:
            self.assertIn(rule, instruction)

    def test_submission_slides_hide_tournament_brackets(self):
        slides = (ROOT / "demoit.html").read_text().split("\n---\n")
        for title, fragment in [("Submit Agent A's team", "arena"),
                                ("Submit Agent B's team", "arena"),
                                ("32 players. One champion.", "tournaments")]:
            with self.subTest(title=title):
                slide = next(s for s in slides if f"<h1>{title}</h1>" in s)
                self.assertIn(f'<web-browser src="http://127.0.0.1:8090/#{fragment}">', slide)
        arena = (ROOT / "arena/index.html").read_text()
        self.assertIn('<div id="arena" class="grid">', arena)
        self.assertIn('body:has(#arena:target) .tournaments { display: none; }', arena)

    def test_introductory_sparring_uses_first_legal_team_without_extra_tools(self):
        value = config("10-sparring.yaml")
        agent = value["agents"]["root"]
        instruction = agent["instruction"]
        self.assertIn("try squirtle, bulbasaur and charmander first if allowed", instruction)
        self.assertIn("verify membership, types and stats", instruction)
        self.assertIn("For an exact requested team, check it unchanged", instruction)
        self.assertIn("Stop at the first verified legal team", instruction)
        self.assertIn("do not compare teams or optimize strength", instruction)
        self.assertIn("Call spar_team once per requested tier", instruction)
        self.assertIn("Do not replace the team or retry to turn a loss into a win", instruction)
        self.assertIn("If facts are missing, a call fails or facts disagree, require human review", instruction)
        self.assertEqual([t["type"] for t in agent["toolsets"]], ["openapi", "api"])
        self.assertEqual(agent["toolsets"][1]["api_config"]["endpoint"], "http://127.0.0.1:8090/spar")
        self.assertNotIn("structured_output", agent)
        self.assertEqual(value["models"][agent["model"]]["thinking_budget"], "none")
        catalog = json.loads((ROOT / "fixtures/arena-catalog.json").read_text())
        challenge = json.loads((ROOT / "fixtures/arena-challenges.json").read_text())["water-budget"]
        validation = validate_team(challenge, ["squirtle", "bulbasaur", "charmander"], catalog)
        self.assertEqual(validation["status"], "ready")
        self.assertEqual(validation["stat_total"], 941)

    def test_final_agents_share_fast_model_and_arithmetic_tool(self):
        builder = config("11-builder.yaml")
        patch = builder["flavors"]["checked-totals"]
        expected_tool = patch["agents"]["root"]["toolsets+"][0]
        for name, agent in [("13-service.yaml", "root"), ("15-arena.yaml", "root"), ("16-tournament.yaml", "player")]:
            with self.subTest(name=name):
                value = config(name)
                model = value["models"][value["agents"][agent]["model"]]
                self.assertEqual(model["model"], "gpt-6-luna")
                self.assertEqual(model["thinking_budget"], "none")
                tools = [t for t in value["agents"][agent]["toolsets"] if t["type"] == "script"]
                self.assertEqual(tools, [expected_tool])
                self.assertIn("sum_team_stats", value["permissions"]["allow"])
        self.assertNotIn("toolsets+", builder["flavors"]["alternate-model"]["agents"]["root"])

    def test_arithmetic_tool_sums_all_stats_and_duplicates(self):
        tool = config("11-builder.yaml")["flavors"]["checked-totals"]["agents"]["root"]["toolsets+"][0]
        command = tool["shell"]["sum_team_stats"]["cmd"]
        squirtle = [44, 48, 65, 50, 64, 43]
        bulbasaur = [45, 49, 49, 65, 65, 45]
        stats = squirtle + squirtle + bulbasaur
        result = subprocess.run(["sh", "-c", command], env=dict(os.environ, stats=",".join(map(str, stats))),
                                capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(result.stdout), {"stat_total": 946})
        for invalid in ["", "1,2", ",".join(["-1"] * 18), ",".join(["1.5"] * 18), ",".join(["x"] * 18)]:
            with self.subTest(invalid=invalid):
                result = subprocess.run(["sh", "-c", command], env=dict(os.environ, stats=invalid), capture_output=True)
                self.assertNotEqual(result.returncode, 0)

    def test_proposal_check_rejects_invalid_teams_and_totals(self):
        catalog = json.loads((ROOT / "fixtures/arena-catalog.json").read_text())
        challenge = json.loads((ROOT / "fixtures/arena-challenges.json").read_text())["water-budget"]
        answer = {"team": ["squirtle", "bulbasaur", "charmander"], "stat_total": 941}
        self.assertEqual(check_proposal(answer, challenge, catalog)["status"], "ready")
        for invalid in [dict(answer, status="needs_review"), dict(answer, stat_total=0), dict(answer, stat_total=True),
                        {"team": ["squirtle", "squirtle", "bulbasaur"], "stat_total": 946},
                        {"team": ["onix", "eevee", "squirtle"], "stat_total": 1024}]:
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                check_proposal(invalid, challenge, catalog)

    def test_proposal_overlay_denies_entry_and_background_authority(self):
        for name in ["15-arena.yaml", "16-tournament.yaml"]:
            value = proposal_config(config(name))
            self.assertEqual(value["runtime"]["safety"], "restricted")
            self.assertEqual(value["permissions"]["deny"], PROHIBITED_TOOLS)
            self.assertIn("sum_team_stats", value["permissions"]["allow"])

    def test_eval_forwarders_are_eof_correct_and_loopback_only(self):
        setup = (ROOT / "agents/eval-setup.sh").read_text()
        self.assertNotIn("busybox nc", setup)
        for port in [8000, 8090]:
            self.assertIn(f"TCP-LISTEN:{port},bind=127.0.0.1,reuseaddr,fork", setup)
            self.assertIn(f"TCP-CONNECT:host.docker.internal:{port}", setup)


if __name__ == "__main__":
    unittest.main()

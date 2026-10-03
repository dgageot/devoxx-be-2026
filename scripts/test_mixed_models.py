"""Offline checks for the optional, model-only multi-agent comparison."""

from html.parser import HTMLParser
from pathlib import Path
import shlex
import unittest

import yaml

ROOT = Path(__file__).resolve().parent.parent


class SlideElements(HTMLParser):
    def __init__(self):
        super().__init__()
        self.commands = []
        self.source = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "web-term":
            self.commands.append(attrs["command"])
        elif tag == "source-code":
            self.source = attrs


class MixedModelTests(unittest.TestCase):
    def setUp(self):
        self.config = yaml.safe_load((ROOT / "agents/12-team.yaml").read_text())
        self.slides = (ROOT / "demoit.html").read_text().split("\n---\n")
        self.index = next(i for i, slide in enumerate(self.slides)
                          if "<h1>Not every request needs the same model</h1>" in slide)
        self.slide = self.slides[self.index]

    def test_optional_detour_preserves_service_flow(self):
        self.assertIn("<h1>Wire the specialists in YAML</h1>", self.slides[self.index - 1])
        self.assertIn("<h1>Expose the team builder as a service</h1>", self.slides[self.index + 1])
        self.assertIn('class="optional-marker"', self.slide)
        self.assertIn('aria-label="Optional slide"', self.slide)
        self.assertIn('<span class="stage">04</span>Serve', self.slide)
        self.assertIn("skip straight to exposing the builder", self.slide)
        self.assertNotIn("<web-browser", self.slide)

    def test_flavors_change_only_models_and_disable_thinking(self):
        expected = {
            "all-strong": {"root": "stronger", "builder": "stronger", "coach": "stronger"},
            "mixed": {"root": "lightweight", "builder": "stronger", "coach": "lightweight"},
        }
        self.assertEqual(set(self.config["flavors"]), set(expected))
        for flavor, assignments in expected.items():
            self.assertEqual(self.config["flavors"][flavor], {
                "agents": {role: {"model": model} for role, model in assignments.items()},
            })
        self.assertEqual(self.config["models"], {
            "stronger": {"provider": "openai", "model": "gpt-6-sol", "thinking_budget": "none"},
            "lightweight": {"provider": "openai", "model": "gpt-6-luna", "thinking_budget": "none"},
        })
        self.assertEqual({name: agent["model"] for name, agent in self.config["agents"].items()}, {
            "root": "openai/gpt-6-luna", "builder": "openai/gpt-6-luna", "coach": "openai/gpt-4.1",
        })
        self.assertEqual(self.config["runtime"], {"safety": "restricted"})
        self.assertEqual(set(self.config["toolsets"]), {"get_arena_rules", "spar_team"})

    def test_identical_requests_and_displayed_flavors_are_runnable(self):
        elements = SlideElements()
        elements.feed(self.slide)
        self.assertEqual(len(elements.commands), 2)
        for flavor, command in zip(["all-strong", "mixed"], elements.commands):
            self.assertEqual(shlex.split(command), [
                "docker", "agent", "run", "agents/12-team.yaml", "--flavor", flavor,
                "Propose a team for water-budget and spar against beginner.",
            ])
            for path in ["README.md", ".demoit/.bash_history"]:
                self.assertIn(command, (ROOT / path).read_text())
        source = elements.source
        self.assertEqual(source["files"], "12-team.yaml 12-team.yaml")
        self.assertEqual(source["start-lines"], ";")
        self.assertEqual(source["end-lines"], ";")
        lines = (ROOT / source["folder"] / "12-team.yaml").read_text().splitlines()
        for key, focus in zip(["flavors", "models"], source["focus-lines"].split(";")):
            start, end = map(int, focus.split("-"))
            self.assertLessEqual(end, len(lines))
            excerpt = yaml.safe_load("\n".join(lines[start - 1:end]))
            self.assertEqual(excerpt, {key: self.config[key]})

    def test_measurement_notes_keep_quality_and_authority_boundaries(self):
        for requirement in ["/cost", "Command-Enter", "estimated cost", "Provider billing is authoritative",
                            "time docker agent run --exec", "at least five times", "alternate their order",
                            "medians with success counts", "not an automatic complexity router",
                            "extra handoffs", "exact chosen team", "actual beginner result",
                            "No measured savings or speedup", "its own eval assertions",
                            "TEAM-1", "SPECIES-1", "BUDGET-1", "COVERAGE-1", "DATA-1", "FAIR-1"]:
            self.assertIn(requirement, self.slide)


if __name__ == "__main__":
    unittest.main()

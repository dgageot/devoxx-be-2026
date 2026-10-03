"""Offline checks for the foreground Compose demo and its deployment wiring."""

from html.parser import HTMLParser
from pathlib import Path
import shlex
import unittest

import yaml

ROOT = Path(__file__).resolve().parent.parent


class Widgets(HTMLParser):
    def __init__(self):
        super().__init__()
        self.items = []

    def handle_starttag(self, tag, attrs):
        if tag in {"web-term", "web-browser", "source-code"}:
            self.items.append((tag, dict(attrs)))


class ComposeSlideTests(unittest.TestCase):
    def test_slide_has_two_terminals_after_the_compose_source(self):
        slides = (ROOT / "demoit.html").read_text().split("\n---\n")
        matches = [i for i, slide in enumerate(slides)
                   if "<h1>Run the packaged agent</h1>" in slide]
        self.assertEqual(len(matches), 1)
        index, = matches
        slide = slides[index]
        self.assertIn("<h1>Package the agent</h1>", slides[index - 1])
        self.assertIn("<h1>Ship the exact agent you evaluated</h1>", slides[index + 1])
        self.assertIn('<span class="stage">04</span>Serve', slide)
        self.assertIn("<split-view>", slide)
        self.assertNotIn("terminal-stack", slide)
        widgets = Widgets()
        widgets.feed(slide)
        self.assertEqual([tag for tag, _ in widgets.items], ["web-term", "web-term"])
        server, client = [attrs for _, attrs in widgets.items]
        self.assertEqual(server["path"], ".")
        self.assertEqual(client["path"], ".")
        self.assertEqual(shlex.split(server["command"]), [
            "OPENAI_API_KEY=op://Team AI Agent/cagent-proxy/OPENAI_API_KEY",
            "op", "run", "--", "docker", "compose", "--env-file", "/dev/null",
            "up", "--no-build", "--pull", "never",
        ])
        self.assertEqual(shlex.split(client["command"]), ["python3", "scripts/api_client.py"])
        for _, attrs in widgets.items:
            for path in ["README.md", ".demoit/.bash_history"]:
                self.assertIn(attrs["command"], (ROOT / path).read_text())

    def test_speaker_notes_cover_preparation_readiness_and_cleanup(self):
        slide = next(slide for slide in (ROOT / "demoit.html").read_text().split("\n---\n")
                     if "<h1>Run the packaged agent</h1>" in slide)
        self.assertIn("<speaker-notes>", slide)
        for detail in ["OPENAI_API_KEY", "1Password CLI", "op run", "desktop integration",
                       "container's environment", "container inspection", "masking is best-effort",
                       "read-only root filesystem", "docker/docker-agent:latest",
                       "transform_json", "max_output_bytes", "gpt-6-luna", "8080", "8000",
                       "Wait for healthy dependencies", "keep the separate host arena",
                       "Ctrl-C", "terminal disconnect", "docker compose --env-file /dev/null stop",
                       "DATA-1", "FAIR-1", "no entry, practice or tournament"]:
            with self.subTest(detail=detail):
                self.assertIn(detail, slide)

    def test_compose_and_client_use_the_same_loopback_chat_endpoint(self):
        compose = yaml.safe_load((ROOT / "compose.yaml").read_text())
        service = compose["services"]["pokemon-arena"]
        self.assertEqual(service["ports"], ["127.0.0.1:8080:8080"])
        self.assertIn('default="http://127.0.0.1:8080"',
                      (ROOT / "scripts/api_client.py").read_text())
        self.assertEqual(service["environment"]["POKEAPI_URL"], "http://pokeapi:8000/openapi.yml")
        self.assertEqual(service["environment"]["OPENAI_API_KEY"], "${OPENAI_API_KEY:-}")
        self.assertNotIn("secrets", compose)
        for name in ["pokemon-arena", "arena", "pokeapi"]:
            self.assertNotIn("secrets", compose["services"][name])
        for name in ["arena", "pokeapi"]:
            self.assertNotIn("OPENAI_API_KEY", compose["services"][name].get("environment", {}))
        self.assertEqual(service["depends_on"], {
            "pokeapi": {"condition": "service_healthy"},
            "arena": {"condition": "service_healthy"},
        })
        command = service["command"]
        self.assertEqual(command[command.index("--flavor") + 1], "container")
        config = yaml.safe_load((ROOT / "agents/13-service.yaml").read_text())
        tools = config["flavors"]["container"]["toolsets"]
        self.assertEqual(tools["get_arena_rules"]["api_config"]["endpoint"], "http://arena:8090/rules")
        self.assertEqual(tools["spar_team"]["api_config"]["endpoint"], "http://arena:8090/spar")
        self.assertNotIn("ports", compose["services"]["arena"])
        self.assertTrue(service["read_only"])
        self.assertIn("./agents:/work/agents:ro", service["volumes"])
        self.assertIn("./AGENTS.md:/work/AGENTS.md:ro", service["volumes"])


if __name__ == "__main__":
    unittest.main()

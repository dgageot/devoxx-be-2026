"""Offline checks for the MCP demo's headless launch and tool contract."""

import shlex
import unittest
from html.parser import HTMLParser
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CLIENT = "agents/14-mcp-client.yaml"


class TerminalCommands(HTMLParser):
    def __init__(self):
        super().__init__()
        self.commands = []

    def handle_starttag(self, tag, attrs):
        if tag == "web-term":
            self.commands.append(dict(attrs).get("command", ""))


class MCPDemoTests(unittest.TestCase):
    def test_one_shot_launches_avoid_tui_startup_race(self):
        slides = TerminalCommands()
        slides.feed((ROOT / "demoit.html").read_text())
        sources = {
            "slide": slides.commands,
            "README": (ROOT / "README.md").read_text().splitlines(),
            "history": (ROOT / ".demoit/.bash_history").read_text().splitlines(),
        }
        expected = [
            "docker", "agent", "run", "--exec", CLIENT,
            "Propose a team for water-budget.",
        ]
        for source, lines in sources.items():
            with self.subTest(source=source):
                launches = [
                    shlex.split(line) for line in lines
                    if CLIENT in line and line.startswith("docker agent run ")
                ]
                self.assertEqual(launches, [expected])

    def test_client_tool_matches_server_agent(self):
        client = yaml.safe_load((ROOT / CLIENT).read_text())
        service = yaml.safe_load((ROOT / "agents/13-service.yaml").read_text())
        toolset, = client["agents"]["root"]["toolsets"]
        self.assertEqual(toolset["type"], "mcp")
        self.assertEqual(toolset["remote"], {
            "url": "http://127.0.0.1:8081",
            "transport_type": "streamable",
        })
        self.assertNotIn("name", toolset)  # A name would prefix the root tool.
        self.assertEqual(list(service["agents"]), ["root"])
        self.assertIn("Call the root tool", client["agents"]["root"]["instruction"])
        self.assertEqual(client["permissions"], {"allow": ["root"]})
        self.assertEqual(client["runtime"]["safety"], "restricted")
        self.assertTrue(toolset["allow_private_ips"])
        self.assertEqual(toolset["lifecycle"]["profile"], "strict")


if __name__ == "__main__":
    unittest.main()

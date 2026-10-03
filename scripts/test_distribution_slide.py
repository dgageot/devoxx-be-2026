"""Offline checks for the optional OCI release slide."""

from html.parser import HTMLParser
from pathlib import Path
import shlex
import unittest

ROOT = Path(__file__).resolve().parent.parent
TITLE = "<h1>Ship the exact agent you evaluated</h1>"


class SlideContent(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_pre = False
        self.commands = []
        self.widgets = []

    def handle_starttag(self, tag, attrs):
        if tag == "pre":
            self.in_pre = True
        if tag in {"web-term", "web-browser", "source-code"}:
            self.widgets.append(tag)

    def handle_endtag(self, tag):
        if tag == "pre":
            self.in_pre = False

    def handle_data(self, data):
        if self.in_pre:
            self.commands.append(data)


class DistributionSlideTests(unittest.TestCase):
    def setUp(self):
        self.slides = (ROOT / "demoit.html").read_text().split("\n---\n")
        matches = [i for i, slide in enumerate(self.slides) if TITLE in slide]
        self.assertEqual(len(matches), 1)
        self.index = matches[0]
        self.slide = self.slides[self.index]

    def test_optional_detour_preserves_the_flow(self):
        self.assertIn("<h1>Run the packaged agent</h1>", self.slides[self.index - 1])
        self.assertIn("<h1>Package the agent</h1>", self.slides[self.index - 2])
        self.assertIn("<h1>From sparring to a leaderboard</h1>",
                      self.slides[self.index + 1])
        self.assertIn('class="optional-marker"', self.slide)
        self.assertIn('aria-label="Optional slide"', self.slide)
        self.assertIn('<span class="stage">04</span>Serve', self.slide)
        self.assertEqual(self.slide.count('<span class="stage">'), 1)
        self.assertIn("skip straight to the leaderboard", self.slide)
        self.assertIn("<speaker-notes>", self.slide)

    def test_commands_are_static_and_digest_pinned(self):
        parsed = SlideContent()
        parsed.feed(self.slide)
        self.assertEqual(parsed.widgets, [])
        commands = "".join(parsed.commands).replace("\\\n", "").splitlines()
        self.assertEqual(len(commands), 2)
        self.assertEqual(shlex.split(commands[0]), [
            "docker", "agent", "share", "push", "release.yaml",
            "myorg/team-builder:v1",
        ])
        self.assertEqual(shlex.split(commands[1]), [
            "docker", "agent", "serve", "chat",
            "myorg/team-builder@sha256:<digest>",
            "--listen", "127.0.0.1:8080",
        ])
        self.assertIn("are placeholders", self.slide)
        self.assertIn("full manifest digest", self.slide)
        self.assertIn("do not use the local YAML checksum", self.slide)

    def test_notes_distinguish_packaging_from_release_evidence(self):
        for boundary in [
            "add_prompt_files remain external path references",
            "instruction_file contents are inlined",
            "Missing prompt files can be silently skipped",
            "share push itself has no --flavor option",
            "before evaluation",
            "Do not assume 11-builder.yaml results certify",
            "does not automatically attach eval evidence",
            "Tags, even v1, can be overwritten",
            "model, tool, environment or policy overrides",
            "published in clear",
            "do not freeze hosted model behavior",
            "DATA-1", "FAIR-1",
        ]:
            with self.subTest(boundary=boundary):
                self.assertIn(boundary, self.slide)
        self.assertIn("https://docker.github.io/docker-agent/concepts/distribution/",
                      self.slide)
        self.assertIn("OCI distribution: ship the exact agent you evaluated",
                      (ROOT / "README.md").read_text())


if __name__ == "__main__":
    unittest.main()

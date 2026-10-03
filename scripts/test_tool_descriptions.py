"""Offline checks for the optional tool-description slide."""

from html.parser import HTMLParser
from pathlib import Path
import unittest

import yaml

ROOT = Path(__file__).resolve().parent.parent
TITLE = "<h1>Your tools are part of the prompt</h1>"


class Excerpts(HTMLParser):
    def __init__(self):
        super().__init__()
        self.examples = []
        self.in_pre = False
        self.widgets = []

    def handle_starttag(self, tag, attrs):
        if tag == "pre":
            self.in_pre = True
            self.examples.append("")
        if tag in {"web-term", "web-browser", "source-code"}:
            self.widgets.append(tag)

    def handle_endtag(self, tag):
        if tag == "pre":
            self.in_pre = False

    def handle_data(self, data):
        if self.in_pre:
            self.examples[-1] += data


class ToolDescriptionTests(unittest.TestCase):
    def setUp(self):
        self.slides = (ROOT / "demoit.html").read_text().split("\n---\n")
        matches = [i for i, slide in enumerate(self.slides) if TITLE in slide]
        self.assertEqual(len(matches), 1)
        self.index = matches[0]
        self.slide = self.slides[self.index]

    def test_optional_detour_preserves_flow_without_live_calls(self):
        self.assertIn("<h1>Use existing Web APIs as tools</h1>",
                      self.slides[self.index - 1])
        self.assertIn("<h1>Keep only the facts we need</h1>",
                      self.slides[self.index + 1])
        self.assertIn('class="optional-marker"', self.slide)
        self.assertIn('aria-label="Optional slide"', self.slide)
        self.assertIn('<span class="stage">02</span>Connect', self.slide)
        self.assertIn("skip straight to response trimming", self.slide)
        parsed = Excerpts()
        parsed.feed(self.slide)
        self.assertEqual(parsed.widgets, [])

    def test_excerpts_change_only_model_facing_guidance(self):
        parsed = Excerpts()
        parsed.feed(self.slide)
        self.assertEqual(len(parsed.examples), 2)
        vague, useful = [yaml.safe_load(text) for text in parsed.examples]
        spec = yaml.safe_load((ROOT / "agents/openapi.yml").read_text())
        operation = spec["paths"]["/api/v2/pokemon/{id}/"]["get"]
        for example in [vague, useful]:
            self.assertEqual(set(example), {"operationId", "summary", "parameters"})
            self.assertEqual(example["operationId"], operation["operationId"])
            parameter, = example["parameters"]
            for key in ["name", "in", "required", "schema"]:
                self.assertEqual(parameter[key], operation["parameters"][0][key])
        self.assertEqual(vague["summary"], operation["summary"])
        self.assertNotEqual(vague["summary"], useful["summary"])
        self.assertIn("types and base stats", useful["summary"])
        self.assertIn('("pikachu")', useful["parameters"][0]["description"])
        self.assertIn('("25")', useful["parameters"][0]["description"])

    def test_notes_explain_mapping_and_limits(self):
        notes = self.slide.split("<speaker-notes>")[1]
        for boundary in ["summary supplies the tool description", "Only without a summary",
                         "not a verbatim copy", "does not trim", "no measured reliability claim",
                         "does not grant authority", "DATA-1", "human review"]:
            with self.subTest(boundary=boundary):
                self.assertIn(boundary, notes)
        self.assertIn("https://docker.github.io/docker-agent/tools/openapi/", notes)
        self.assertIn("Tool descriptions: your tools are part of the prompt",
                      (ROOT / "README.md").read_text())


if __name__ == "__main__":
    unittest.main()

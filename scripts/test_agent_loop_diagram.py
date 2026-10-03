"""Offline regressions for the agent-loop diagram."""

from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
NS = {"svg": "http://www.w3.org/2000/svg"}


class AgentLoopDiagramTests(unittest.TestCase):
    def test_slide_embeds_the_accessible_vector_asset(self):
        slide = next(slide for slide in (ROOT / "demoit.html").read_text().split("\n---\n")
                     if "<h1>How an agent works</h1>" in slide)
        self.assertIn('src="/images/agent-loop.svg"', slide)
        self.assertIn('width="1786" height="540"', slide)
        self.assertIn('alt="Instructions guide the model.', slide)
        self.assertIn("runs the loop and calls tools", slide)
        self.assertNotIn("<svg", slide)

    def test_diagram_preserves_guidance_and_loop_directions(self):
        svg = ET.parse(ROOT / ".demoit/images/agent-loop.svg").getroot()
        self.assertEqual(svg.get("viewBox"), "0 0 1786 540")
        labels = {text.text for text in svg.findall("svg:text", NS)}
        self.assertTrue({"Instructions", "User", "Model", "Tool", "Guide behavior",
                         "Question", "Answer", "Tool call", "Result back to model",
                         "Repeat until ready to answer"} <= labels)
        paths = {path.get("d"): path for path in svg.findall("svg:path", NS)}
        for direction, marker in [("M865 143V186", "guidance"),
                                  ("M360 260H675", "arrow"),
                                  ("M690 335H360", "arrow"),
                                  ("M1040 250C1150 132 1300 132 1415 250", "arrow"),
                                  ("M1425 335C1310 451 1150 451 1050 335", "arrow")]:
            with self.subTest(direction=direction):
                path = paths[direction]
                if path.get("class") in {"link", "return"}:
                    self.assertIn("marker-end:url(#arrow)", svg.find(".//svg:style", NS).text)
                else:
                    self.assertEqual(path.get("marker-end"), f"url(#{marker})")
        ids = {element.get("id") for element in svg.iter() if element.get("id")}
        for element in svg.iter():
            for value in element.attrib.values():
                if value.startswith("url(#"):
                    self.assertIn(value[5:-1], ids)
        self.assertFalse(svg.findall(".//svg:image", NS))
        self.assertFalse(svg.findall(".//svg:script", NS))


if __name__ == "__main__":
    unittest.main()

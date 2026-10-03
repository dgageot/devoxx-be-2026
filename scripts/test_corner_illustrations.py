"""Offline checks for the presentation's conceptual corner illustrations."""

from html.parser import HTMLParser
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
ILLUSTRATIONS = {
    "Pokémon today. Your business tomorrow.": "rocket.svg",
    "The model is not the product": "model-component.svg",
    "You do need a model": "model-chip.svg",
    "Turn requests into eval cases": "eval-checklist.svg",
    "Keep it only if it helps": "improvement-chart.svg",
    "From facts to a business action": "sparring-gloves.svg",
    "What should a good team builder do?": "balance-scales.svg",
    "Split responsibilities": "connected-team.svg",
    "Expose the team builder as a service": "plug-socket.svg",
}


class Images(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images = []

    def handle_starttag(self, tag, attrs):
        if tag == "img":
            self.images.append(dict(attrs))


class CornerIllustrationTests(unittest.TestCase):
    def test_concept_slides_have_valid_documented_corner_images(self):
        slides = (ROOT / "demoit.html").read_text().split("\n---\n")
        credits = (ROOT / ".demoit/images/README.md").read_text()
        for title, filename in ILLUSTRATIONS.items():
            with self.subTest(title=title):
                slide, = [slide for slide in slides
                          if f"<h1>{title}</h1>" in slide and "<split-view" not in slide]
                parser = Images()
                parser.feed(slide)
                image, = parser.images
                self.assertIn("slide-corner", image["class"].split())
                self.assertEqual(image["src"], f"/images/{filename}")
                self.assertTrue(image.get("alt", "").strip())
                svg = ET.parse(ROOT / ".demoit/images" / filename).getroot()
                self.assertEqual(svg.tag, "{http://www.w3.org/2000/svg}svg")
                self.assertEqual(svg.attrib["viewBox"], "0 0 240 240")
                for dimension in ["width", "height"]:
                    self.assertEqual(image[dimension], svg.attrib[dimension])
                self.assertIn(f"`{filename}`", credits)

    def test_model_demo_has_no_corner_illustration(self):
        slides = (ROOT / "demoit.html").read_text().split("\n---\n")
        slide, = [slide for slide in slides
                  if "<h1>You do need a model</h1>" in slide and "<split-view" in slide]
        self.assertNotIn("slide-corner", slide)


if __name__ == "__main__":
    unittest.main()

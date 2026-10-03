"""Offline regressions for the application and MCP service diagrams."""

from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
SVG = ROOT / ".demoit/images/application-builder.svg"
NS = {"svg": "http://www.w3.org/2000/svg"}


class ServiceDiagramTests(unittest.TestCase):
    def test_application_slide_embeds_the_vector_asset(self):
        slide = next(slide for slide in (ROOT / "demoit.html").read_text().split("\n---\n")
                     if "<h1>An application calls the builder</h1>" in slide)
        self.assertIn('src="/images/application-builder.svg"', slide)
        self.assertIn('width="1786" height="600"', slide)
        self.assertIn('alt="A Python application', slide)
        self.assertNotIn("<svg", slide)

    def test_mcp_slide_embeds_the_vector_asset(self):
        slide = next(slide for slide in (ROOT / "demoit.html").read_text().split("\n---\n")
                     if "<h1>An agent calls the builder as a tool</h1>" in slide)
        self.assertIn('src="/images/mcp-builder.svg"', slide)
        self.assertIn('width="1786" height="600"', slide)
        self.assertIn('alt="A caller agent', slide)
        self.assertNotIn("<svg", slide)

    def test_mcp_diagram_preserves_protocol_and_component_details(self):
        svg = ET.parse(ROOT / ".demoit/images/mcp-builder.svg").getroot()
        labels = {text.text: text for text in svg.findall("svg:text", NS)}
        self.assertTrue({"MCP client", "MCP server", "MCP · JSON-RPC",
                         "Streamable HTTP", ":8081", "tools/list →",
                         "tools/call (root)", "Tool result", "agent: root",
                         "13-service.yaml", ":8000", ":8090"} <= labels.keys())
        for label, bounds in [("14-mcp-client.yaml", (30, 200, 360, 460)),
                              ("13-service.yaml", (675, 87, 1185, 547)),
                              ("tools/list →", (360, 298, 675, 392)),
                              ("tools/call (root)", (360, 298, 675, 392))]:
            with self.subTest(label=label):
                text = labels[label]
                self.assertTrue(bounds[0] < float(text.get("x")) < bounds[2])
                self.assertTrue(bounds[1] < float(text.get("y")) < bounds[3])
        self.assertEqual(svg.get("viewBox"), "0 0 1786 600")

    def test_implementation_labels_stay_with_their_components(self):
        svg = ET.parse(SVG).getroot()
        labels = {text.text: text for text in svg.findall("svg:text", NS)}
        for label, bounds in [("api_client.py", (30, 200, 360, 460)),
                              ("13-service.yaml", (675, 87, 1185, 547)),
                              ("POST", (360, 298, 675, 392)),
                              ("/v1/chat/completions", (360, 298, 675, 392))]:
            with self.subTest(label=label):
                text = labels[label]
                self.assertTrue(bounds[0] < float(text.get("x")) < bounds[2])
                self.assertTrue(bounds[1] < float(text.get("y")) < bounds[3])
        self.assertEqual(svg.get("viewBox"), "0 0 1786 600")

    def test_diagram_is_self_contained_and_preserves_service_details(self):
        svg = ET.parse(SVG).getroot()
        ids = {element.get("id") for element in svg.iter() if element.get("id")}
        for element in svg.iter():
            for value in element.attrib.values():
                if value.startswith("url(#"):
                    self.assertIn(value[5:-1], ids)
        labels = {text.text for text in svg.findall("svg:text", NS)}
        self.assertTrue({"agent: root", ":8080", ":8000", ":8090",
                         "PokéAPI", "Arena backend", "/api/v2/…",
                         "/rules · /spar", "Structured plan"} <= labels)
        self.assertFalse(svg.findall(".//svg:image", NS))
        self.assertFalse(svg.findall(".//svg:script", NS))


if __name__ == "__main__":
    unittest.main()

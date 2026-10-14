"""Validate source fidelity, self-contained assets, DOM references and demo evidence."""
import base64
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess

from build_study_guide import ROOT, calculations, digest
from src.pipeline import DataAnalyzer


class Document(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = []
        self.links = []
        self.images = []
        self.excerpts = {}
        self.questions = []
        self.labels = []
        self.controls = []
        self.current_excerpt = None
        self.in_code = False
        self.in_line_number = False
        self.depth = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag == "a":
            self.links.append(attrs.get("href", ""))
        if tag == "img":
            self.images.append(attrs)
        if "data-question" in attrs:
            self.questions.append(attrs["data-question"])
        if tag == "label" and "for" in attrs:
            self.labels.append(attrs["for"])
        if tag in ("select", "input") and attrs.get("type") != "checkbox":
            self.controls.append(attrs.get("id"))
        if "data-excerpt" in attrs:
            self.current_excerpt = attrs["data-excerpt"]
            self.excerpts[self.current_excerpt] = ""
        if tag == "code" and self.current_excerpt:
            self.in_code = True
        if tag == "span" and self.in_code:
            self.depth += 1
            if attrs.get("class") == "line-num":
                self.in_line_number = True

    def handle_endtag(self, tag):
        if tag == "span" and self.in_code:
            if self.in_line_number:
                self.in_line_number = False
            self.depth -= 1
        if tag == "code":
            self.in_code = False
        if tag == "figure":
            self.current_excerpt = None

    def handle_data(self, data):
        if self.in_code and not self.in_line_number:
            self.excerpts[self.current_excerpt] += data


def main():
    study = ROOT / "study"
    text = (study / "a1-1.html").read_text(encoding="utf-8")
    doc = Document()
    doc.feed(text)
    assert len(doc.ids) == len(set(doc.ids)), "Duplicate HTML IDs"
    assert len(doc.questions) == 12 and len(set(doc.questions)) == 12
    assert len(doc.images) == 8
    assert len(doc.excerpts) == 18
    assert not re.search(r"@@[A-Z]+[:@]", text), "Unresolved template marker"
    assert all(link[1:] in doc.ids for link in doc.links if link.startswith("#"))
    assert set(doc.controls).issubset(doc.labels), "Every editable control needs a label"
    ui = re.search(r'<script id="guide-ui">([\s\S]*?)</script>', text).group(1)
    referenced = set(re.findall(r"\$\('([^']+)'\)", ui))
    assert referenced.issubset(doc.ids), f"Missing DOM elements: {referenced - set(doc.ids)}"
    assert not re.search(r"\b(fetch|XMLHttpRequest|WebSocket)\s*\(", ui), "Unexpected network dependency"
    manifest = json.loads((study / "source-manifest.json").read_text(encoding="utf-8"))
    embedded = json.loads(re.search(r'<script id="guide-data"[^>]*>([\s\S]*?)</script>', text).group(1))
    for file, expected in manifest["files"].items():
        actual = digest((ROOT / file).read_bytes(), text=Path(file).suffix not in (".npy", ".png"))
        assert actual == expected, f"Source changed: {file}"
    for file, source in embedded["sources"].items():
        assert source["text"] == (ROOT / file).read_text(encoding="utf-8")
    for name, excerpt in manifest["excerpts"].items():
        current = "\n".join((ROOT / excerpt["file"]).read_text(encoding="utf-8").splitlines()[excerpt["start"]-1:excerpt["end"]])
        assert current == excerpt["text"] == doc.excerpts[name], f"Excerpt mismatch: {name}"
    pngs = sorted((ROOT / "results/figures").glob("*.png")) + [ROOT / 'results/bonus/image_features.png', ROOT / 'results/bonus/cohort_retention.png']
    for image, file in zip(doc.images, pngs):
        assert image.get("alt") and image["src"].startswith("data:image/png;base64,")
        assert base64.b64decode(image["src"].split(",", 1)[1]) == file.read_bytes()
    analyzer = DataAnalyzer(ROOT / "data/sample/transactions.csv")
    analyzer.load_data(); analyzer.handle_missing_values(); analyzer.engineer_features(); analyzer.calculate_rfm()
    evidence = json.loads((study / "calculation-evidence.json").read_text(encoding="utf-8"))
    assert calculations(analyzer) == evidence, "Python example evidence changed"
    subprocess.run(["node", str(ROOT / "tools/verify_study_math.mjs")], cwd=ROOT, check=True)
    print(json.dumps({"passed": True, "chapters": 12, "questions": 12, "exact_excerpts": 18,
                      "embedded_sources": len(embedded['sources']), "offline_images": 8, "bytes": len(text.encode("utf-8"))}))


if __name__ == "__main__":
    main()

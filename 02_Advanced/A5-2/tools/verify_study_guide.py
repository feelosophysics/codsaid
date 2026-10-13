"""학습 자료가 현재 소스·결과와 일치하는지 검사하고, 브라우저 계산을 Node.js로 Python 기준값과 대조한다.

    uv run python tools/verify_study_guide.py
"""
import base64
import hashlib
import html
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "study"


def digest(data: bytes, text=False) -> str:
    if text:
        data = data.decode("utf-8").replace("\r\n", "\n").encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def main():
    page = (STUDY / "a5-2.html").read_text(encoding="utf-8")
    manifest = json.loads((STUDY / "source-manifest.json").read_text(encoding="utf-8"))
    problems = []

    # 1. 원본 파일이 생성 이후 바뀌지 않았는지
    for file, expected in manifest["files"].items():
        path = ROOT / file
        if not path.exists():
            problems.append(f"없는 파일: {file}")
            continue
        actual = digest(path.read_bytes(), text=path.suffix != ".png")
        if actual != expected:
            problems.append(f"생성 이후 바뀐 파일: {file} (다시 build 필요)")

    # 2. 코드 발췌가 원본의 해당 줄과 정확히 같은지
    for name, ex in manifest["excerpts"].items():
        lines = (ROOT / ex["file"]).read_text(encoding="utf-8").replace("\r\n", "\n").splitlines()
        if "\n".join(lines[ex["start"] - 1:ex["end"]]) != ex["text"]:
            problems.append(f"발췌 불일치: {name}")
        block = re.search(rf'<figure class="code-block" data-excerpt="{name}">(.*?)</figure>', page, re.S)
        if not block:
            problems.append(f"페이지에 없는 발췌: {name}")
            continue
        shown = re.findall(r'<span class="line-num" aria-hidden="true">\d+</span><span>(.*?)</span></span>', block.group(1))
        shown = [html.unescape(s) for s in shown]
        if [s if s != " " else "" for s in shown] != ex["text"].split("\n"):
            problems.append(f"표시된 발췌가 원본과 다름: {name}")

    # 3. 자리표시자, 내부 링크, 이미지, 레이블
    if re.search(r"@@[A-Z]+[:@]", page):
        problems.append("채워지지 않은 자리표시자가 있음")
    ids = set(re.findall(r'\sid="([^"]+)"', page))
    for target in re.findall(r'href="#([^"$]+)"', page):
        if target not in ids:
            problems.append(f"없는 내부 링크: #{target}")
    for js_id in re.findall(r"\$\('([a-z0-9-]+)'\)", page):
        if js_id not in ids and not js_id.startswith("src-l"):
            problems.append(f"스크립트가 찾는 요소 없음: #{js_id}")
    for label_for in re.findall(r'<label for="([^"]+)"', page):
        if label_for not in ids:
            problems.append(f"레이블 대상 없음: {label_for}")
    images = re.findall(r'src="data:image/png;base64,([^"]+)"', page)
    for b64 in images:
        if not base64.b64decode(b64).startswith(b"\x89PNG"):
            problems.append("PNG가 아닌 내장 이미지")
    if len(re.findall(r'<img [^>]*alt="[^"]+"', page)) != len(re.findall(r"<img ", page)):
        problems.append("대체 텍스트 없는 이미지")

    # 4. 내장 데이터가 결과 파일과 같은지
    data = json.loads(re.search(r'<script id="guide-data" type="application/json">(.*?)</script>', page, re.S).group(1))
    test = json.loads((ROOT / "results/test_explanations.json").read_text(encoding="utf-8"))
    for key in ("rows", "y", "proba", "shap", "cluster", "pca", "base_value"):
        if data[key] != test[key]:
            problems.append(f"내장 Test 데이터({key})가 results/test_explanations.json과 다름")

    if problems:
        print("\n".join(problems))
        sys.exit(1)
    print(json.dumps({"files": len(manifest["files"]), "excerpts": len(manifest["excerpts"]),
                      "images": len(images), "internal_links_ok": True}, ensure_ascii=False))

    # 5. 브라우저 계산 대조
    node = shutil.which("node")
    if not node:
        print("node가 없어 계산 대조를 건너뜀")
        sys.exit(1)
    subprocess.run([node, str(ROOT / "tools/verify_study_math.mjs")], check=True)


if __name__ == "__main__":
    main()

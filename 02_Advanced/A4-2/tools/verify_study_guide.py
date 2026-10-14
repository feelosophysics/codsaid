"""study/a4-2.html 의 JavaScript 엔진이 Python 구현과 같은 결과를 내는지 Node.js로 대조한다.

    uv run python tools/verify_study_guide.py          (Node.js 18 이상 필요)

1. 감성: NSMC dev·test 2,000건 + pool 무작위 3,000건 + 표적 문장 72개를 9단계 설정마다 분석해 점수(오차 1e-9)와 판정 비교.
   최종 설정에서는 토큰 조각(pieces)까지 비교
2. 추출: 추출 테스트 80문장 + 위 리뷰 전부에서 (유형, 원문, 정규화 값) 비교
3. 마스킹: 마스킹 테스트 20문장 + 추출 테스트 80문장의 마스킹 결과 문자열 비교
4. 속성: 속성 테스트 48문장 + test 리뷰 1,000건의 (속성, 극성) 쌍을 두 연결 방식으로 비교
5. 페이지 구조: getElementById / href="#..." 가 가리키는 id가 실제로 있는가
"""
from __future__ import annotations

import json
import random
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.aspect import AspectAnalyzer  # noqa: E402
from src.data import load_splits  # noqa: E402
from src.eval_sentiment import read_jsonl  # noqa: E402
from src.extract import extract, mask  # noqa: E402
from src.sentiment import ABLATION_STEPS, FINAL_CONFIG, SentimentAnalyzer  # noqa: E402

HTML = ROOT / "study" / "a4-2.html"
HANDMADE = ROOT / "data" / "handmade"

NODE_RUNNER = r"""
const fs = require("fs");
const [htmlPath, inPath, outPath] = process.argv.slice(2);
const html = fs.readFileSync(htmlPath, "utf8");
const data = JSON.parse(html.match(/<script id="study-data" type="application\/json">([\s\S]*?)<\/script>/)[1]);
const engineSrc = html.match(/<script id="engine">([\s\S]*?)<\/script>/)[1];
new Function(engineSrc)();
const E = globalThis.A42.makeEngine(data.engine);
const input = JSON.parse(fs.readFileSync(inPath, "utf8"));
const out = { sentiment: [], pieces: [], extract: [], mask: [], aspect: [] };
for (const step of data.engine.steps) {
  out.sentiment.push(input.texts.map(t => { const r = E.analyze(t, step.config); return [r.score, r.label]; }));
}
out.pieces = input.texts.map(t => E.analyze(t, data.engine.final_config).pieces);
out.extract = input.extract.map(t => E.extract(t).map(e => [e.type, e.text, e.value]));
out.mask = input.mask.map(t => E.mask(t)[0]);
out.aspect = input.aspect.map(t => [E.aspectPairs(t, "preceding"), E.aspectPairs(t, "nearest")]);
fs.writeFileSync(outPath, JSON.stringify(out));
"""


def run_node(payload: dict) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "runner.js").write_text(NODE_RUNNER, encoding="utf-8")
        (tmp / "in.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        subprocess.run(["node", str(tmp / "runner.js"), str(HTML), str(tmp / "in.json"), str(tmp / "out.json")], check=True)
        return json.loads((tmp / "out.json").read_text(encoding="utf-8"))


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    splits = load_splits()
    rng = random.Random(7)
    pool = [r["text"] for r in rng.sample(splits["pool"], 3000)]
    rules = [r["text"] for r in read_jsonl(HANDMADE / "sentiment_rules.jsonl")]
    pairs = [t for p in read_jsonl(HANDMADE / "intensity_pairs.jsonl") for t in (p["base"], p["modified"])]
    texts = [r["text"] for r in splits["dev"] + splits["test"]] + pool + rules + pairs
    ext_cases = [c["text"] for c in read_jsonl(HANDMADE / "extraction_cases.jsonl")]
    mask_cases = [c["text"] for c in read_jsonl(HANDMADE / "masking_cases.jsonl")]
    asp_cases = [c["text"] for c in read_jsonl(HANDMADE / "aspect_cases.jsonl")]
    payload = {"texts": texts, "extract": ext_cases + texts, "mask": mask_cases + ext_cases,
               "aspect": asp_cases + [r["text"] for r in splits["test"]]}
    print(f"Node 실행: 감성 {len(texts)}문장 × {len(ABLATION_STEPS)}설정, 추출 {len(payload['extract'])}, "
          f"마스킹 {len(payload['mask'])}, 속성 {len(payload['aspect'])}")
    js = run_node(payload)
    ok = True

    a = SentimentAnalyzer()
    mism = 0
    for (name, cfg), rows in zip(ABLATION_STEPS, js["sentiment"]):
        bad = 0
        for t, (score, label) in zip(texts, rows):
            r = a.analyze(t, cfg)
            if abs(r.score - score) > 1e-9 or r.label != label:
                bad += 1
                if bad <= 3:
                    print(f"  불일치 [{name}] {t[:50]!r} py={r.score},{r.label} js={score},{label}")
        mism += bad
    print(f"1. 감성 점수·판정: {len(texts) * len(ABLATION_STEPS):,}건 중 불일치 {mism}")
    ok &= mism == 0
    pbad = sum([list(p) for p in a.analyze(t, FINAL_CONFIG).pieces] != [list(x) for x in jp] for t, jp in zip(texts, js["pieces"]))
    print(f"   토큰 조각: {len(texts):,}건 중 불일치 {pbad}")
    ok &= pbad == 0

    ebad = 0
    for t, je in zip(payload["extract"], js["extract"]):
        pe = [[e.type, e.text, e.value] for e in extract(t)]
        if pe != je:
            ebad += 1
            if ebad <= 3:
                print(f"  불일치 {t[:60]!r} py={pe} js={je}")
    n_ent = sum(len(x) for x in js["extract"])
    print(f"2. 추출: {len(payload['extract']):,}문장(개체 {n_ent}) 중 불일치 {ebad}")
    ok &= ebad == 0

    mbad = sum(mask(t)[0] != jm for t, jm in zip(payload["mask"], js["mask"]))
    print(f"3. 마스킹: {len(payload['mask'])}문장 중 불일치 {mbad}")
    ok &= mbad == 0

    abad = 0
    analyzers = {"preceding": AspectAnalyzer("preceding"), "nearest": AspectAnalyzer("nearest")}
    for t, (jp, jn) in zip(payload["aspect"], js["aspect"]):
        for mode, jv in (("preceding", jp), ("nearest", jn)):
            pv = sorted([list(x) for x in analyzers[mode].pairs(t)])
            if pv != sorted(jv):
                abad += 1
                if abad <= 3:
                    print(f"  불일치 [{mode}] {t[:50]!r} py={pv} js={jv}")
    print(f"4. 속성: {len(payload['aspect']) * 2:,}건 중 불일치 {abad}")
    ok &= abad == 0

    html = HTML.read_text(encoding="utf-8")
    ids = set(re.findall(r'id="([^"]+)"', html))
    wanted = set(re.findall(r'getElementById\("([^"]+)"\)', html)) | set(re.findall(r'href="#([^"]+)"', html))
    wanted |= set(re.findall(r'\$\("#([A-Za-z][\w-]*)"\)', html))
    missing = sorted(wanted - ids)
    print(f"5. 구조: 참조하는 id {len(wanted)}개 중 없는 것 {len(missing)} {missing[:10]}")
    ok &= not missing
    print("통과" if ok else "실패")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

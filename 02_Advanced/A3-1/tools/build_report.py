"""REPORT.template.md의 자리표시자를 outputs/results.json 값으로 채워 REPORT.md를 만든다.

자리표시자:
  {{경로:형식}}   results.json 값. rows와 eda는 이미지 id로 찾는다. 예: {{rows.E03.error_ratio:pct2}}
                  형식: pct0·pct1·pct2(×100 후 %), f0·f1·f2·f3, int, ms(초 → 밀리초), x0·x1(배수)
  {{table:이름}}  표 전체. summary, data, rows, rules, dark, conv, sweep_images

실행:  python tools/build_report.py [--results outputs/results.json] [--labels data/synthetic/labels.json]
수치는 자동으로 바뀌지만 분석 문장은 합성 데이터 기준으로 쓴 것이다. 다른 데이터로 다시 돌리면 문장도 고쳐야 한다.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATUS_KO = {"success": "성공", "partial": "부분 성공", "fail": "실패", "unknown": "정답 없음"}
PAPER_KO = {"a4": "A4", "letter": "레터", "a5_form": "A5 신청서", "receipt": "영수증", "card": "명함"}


def context(results, labels):
    ctx = dict(results)
    ctx["rows"] = {r["id"]: r for r in results["rows"]}
    ctx["labels"] = {lab["id"]: lab for lab in labels}
    ctx["summary_by"] = {s["condition"]: s for s in results["summary"]}
    if results.get("rules"):
        ctx["rules_by"] = {v["name"].split()[0]: v for v in results["rules"]}
    if results.get("darkening"):
        ctx["dark_by"] = {f"x{round(r['factor'] * 100):03d}": r for r in results["darkening"]}
    return ctx


def lookup(ctx, path):
    cur = ctx
    for part in path.split("."):
        if isinstance(cur, list):
            cur = cur[int(part)]
        else:
            cur = cur[part]
    return cur


def fmt(value, spec):
    if spec is None:
        return str(value)
    if spec.startswith("pct"):
        return f"{value * 100:.{int(spec[3:])}f}%"
    if spec.startswith("f"):
        return f"{value:.{int(spec[1:])}f}"
    if spec == "int":
        return str(int(round(value)))
    if spec == "ms":
        return f"{value * 1000:.1f} ms"
    if spec.startswith("x"):
        return f"{value:.{int(spec[1:])}f}배"
    if spec == "list":
        return ", ".join(map(str, value))
    raise ValueError(f"모르는 형식: {spec}")


def md_table(header, rows, align=None):
    align = align or ["---"] * len(header)
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join(align) + " |"]
    lines += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(lines)


def table_summary(ctx):
    rows = []
    for s in ctx["summary"]:
        name = f"**{s['name']}**" if s["condition"] == "all" else s["name"]
        rows.append([name, s["n"], s["success"], s["partial"], s["fail"], f"{s['success_rate'] * 100:.0f}%"])
    return md_table(["조건", "테스트 수", "성공", "부분 성공", "실패", "성공률"], rows,
                    ["---", "---:", "---:", "---:", "---:", "---:"])


def table_data(ctx):
    rows = []
    for lab in ctx["labels"].values():
        a = lab["angle"]
        extras = ", ".join(f"{k}={v}" for k, v in lab.get("extras", {}).items()) or "-"
        rows.append([lab["id"], lab["condition_name"], PAPER_KO.get(lab["paper"], lab["paper"]),
                     lab["lighting"], f"{a['tilt_deg']:.0f}° (평면 회전 {a['roll']}°)",
                     f"{lab['background_complexity']} ({lab['background']})", extras])
    return md_table(["ID", "조건", "문서", "조명", "기울기", "배경 복잡도", "추가 요인"], rows)


def table_rows(ctx):
    rows = []
    for r in ctx["rows"].values():
        err = f"{r['error_ratio'] * 100:.2f}% ({r['max_error_px']:.1f}px)" if "error_ratio" in r else "-"
        aspect = f"{r['aspect_error'] * 100:.1f}% / {r['distance_aspect_error'] * 100:.1f}%" \
            if "aspect_error" in r and r["status"] != "fail" else "-"
        note = r["reason"] or ("결과가 90° 돌아감" if r.get("rotation_shift") else "")
        rows.append([r["id"], STATUS_KO[r["status"]], err, aspect, r["n_contours"], note])
    return md_table(["ID", "판정", "최대 꼭짓점 오차 (대각선 대비)", "종횡비 오차 (원근 / 변 길이)", "윤곽선 수", "비고"],
                    rows, ["---", "---", "---:", "---:", "---:", "---"])


def table_rules(ctx):
    base = ctx["rules"][0]["status"]
    rows = []
    for v in ctx["rules"]:
        if v is ctx["rules"][0]:
            rows.append([v["name"], f"{v['success']}/20", "(기준)", "(기준)"])
            continue
        better = [k for k, s in v["status"].items() if _rank(s) > _rank(base[k])]
        worse = [k for k, s in v["status"].items() if _rank(s) < _rank(base[k])]
        rows.append([v["name"], f"{v['success']}/20", ", ".join(better) or "-", ", ".join(worse) or "-"])
    return md_table(["변형", "성공", "좋아진 이미지", "나빠진 이미지"], rows, ["---", "---:", "---", "---"])


def _rank(s):
    return {"fail": 0, "partial": 1, "success": 2}.get(s, 1)


def table_dark(ctx):
    rows = []
    for r in ctx["darkening"]:
        rows.append([f"×{r['factor']:.2f}", f"{r['mean']:.0f}", f"{r['std']:.0f}", f"{r['boundary_gradient_median']:.0f}",
                     f"{r['boundary_edge_recall'] * 100:.0f}%", STATUS_KO.get(r["found"], r["found"])])
    return md_table(["밝기 배율", "평균 밝기", "표준편차", "경계 기울기 중앙값", "경계 엣지 검출률", "문서 검출"], rows,
                    ["---:", "---:", "---:", "---:", "---:", "---"])


def table_conv(ctx):
    c = ctx["convolution"]
    rows = []
    for name, sec in c["times"].items():
        rows.append([name, f"{sec * 1000:.2f} ms", f"{c['speedup_vs_loops'][name]:.0f}배",
                     f"{c['max_abs_diff_vs_opencv'][name]:.1e}"])
    return md_table(["방법", "시간", "이중 for문 대비", "OpenCV와 최대 차이"], rows, ["---", "---:", "---:", "---:"])


def table_sweep_images(ctx):
    s = ctx["sweep"]
    rows = []
    for i, rate in s["per_image_success_rate"].items():
        rows.append([i, f"{rate * 100:.0f}%", STATUS_KO[ctx["rows"][i]["status"]]])
    half = (len(rows) + 1) // 2
    merged = [a + b for a, b in zip(rows[:half], rows[half:] + [["", "", ""]] * (2 * half - len(rows)))]
    return md_table(["ID", "성공 조합 비율", "기본값 판정", "ID", "성공 조합 비율", "기본값 판정"], merged,
                    ["---", "---:", "---", "---", "---:", "---"])


TABLES = {"summary": table_summary, "data": table_data, "rows": table_rows, "rules": table_rules,
          "dark": table_dark, "conv": table_conv, "sweep_images": table_sweep_images}


def render(template, ctx):
    def repl(m):
        body = m.group(1).strip()
        if body.startswith("table:"):
            return TABLES[body[6:]](ctx)
        path, _, spec = body.partition(":")
        return fmt(lookup(ctx, path), spec or None)
    out = re.sub(r"\{\{(.+?)\}\}", repl, template)
    if "{{" in out:
        raise SystemExit("채워지지 않은 자리표시자가 남았다")
    return out


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", default="outputs/results.json")
    parser.add_argument("--labels", default="data/synthetic/labels.json")
    parser.add_argument("--template", default="REPORT.template.md")
    parser.add_argument("--out", default="REPORT.md")
    args = parser.parse_args(argv)
    results = json.loads((ROOT / args.results).read_text(encoding="utf-8"))
    labels = json.loads((ROOT / args.labels).read_text(encoding="utf-8"))["images"]
    text = render((ROOT / args.template).read_text(encoding="utf-8"), context(results, labels))
    (ROOT / args.out).write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {args.out} ({len(text)} chars)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""REPORT.template.md의 자리표시자를 outputs/results.json 값으로 채워 REPORT.md를 만든다.

자리표시자:
  {{경로:형식}}   results.json 값. 점으로 내려간다. 예: {{T.crossing.switch_events}}, {{BG.m002.single.f1:pct1}}
                  별칭: T(미션 표 행, 시나리오별), V(test 변형), VD(dev 변형), BG(배경 설정), F(특징점 표), G(일반화)
                  형식: pct0·pct1·pct2, f0·f1·f2, int
  {{table:이름}}  표 전체. main, log, features, lr, variants, byevent, sweep, hungarian, gen, video, speed, zone

실행:  python tools/build_report.py
수치는 자동으로 바뀌지만 분석 문장은 합성 데이터 기준으로 쓴 것이다. 다른 데이터로 다시 돌리면 문장도 고쳐야 한다.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BG_ALIAS = {"m0005": "mog2_0.0005", "m002": "mog2_0.002", "m01": "mog2_0.01", "m05": "mog2_0.05",
            "noshadow": "mog2_0.002_noshadow", "r002": "ravg_0.002", "r01": "ravg_0.01", "r05": "ravg_0.05",
            "fd": "framediff"}
BG_NAME = {"mog2_0.0005": "MOG2 α=0.0005", "mog2_0.002": "MOG2 α=0.002 (기본, =1/500)", "mog2_0.01": "MOG2 α=0.01",
           "mog2_0.05": "MOG2 α=0.05", "mog2_0.002_noshadow": "MOG2 α=0.002, 그림자 검출 끔",
           "ravg_0.002": "이동 평균 α=0.002", "ravg_0.01": "이동 평균 α=0.01", "ravg_0.05": "이동 평균 α=0.05",
           "framediff": "프레임 차분"}
FEAT_KEY = {"정면": "front", "30도 회전 (평면 안)": "roll30", "60도 회전 (평면 안)": "roll60", "30도 기울임 (3D)": "yaw30",
            "60도 기울임 (3D)": "yaw60", "30% 가림": "occ30", "50% 가림": "occ50"}
GEN_KEY = {"등록 물체 그대로": "same", "같은 시리즈 다른 권": "series", "무관한 표지": "other", "색 반전 (음화)": "neg",
           "윤곽선 그림": "sketch"}
SEG_KO = {"absent": "물체 없음", "enter": "들어옴 (일부 화면 밖)", "frontal": "정면", "roll": "평면 회전 0→60°",
          "roll_back": "평면 회전 60→0°", "yaw": "3D 기울임 0→65°", "yaw_back": "3D 기울임 65→0°",
          "occluded": "사람이 앞을 지나며 가림", "shrink": "멀어짐 (크기 0.42→0.17)"}
SCEN_KO = {"single": "단일", "crossing": "겹침", "crossing_same": "겹침(같은 옷)", "pause": "정지", "lighting": "조명"}


def context(res):
    ctx = dict(res)
    ctx["T"] = {r["scenario"]: r for r in res["table"]}
    ctx["TT"] = {r["scenario"]: r for r in res["tuned"]["test_table"]}
    ctx["V"] = {k: v["scenarios"] for k, v in res["variants"]["test"].items()}
    ctx["VD"] = {k: v["scenarios"] for k, v in res["variants"]["dev"].items()}
    ctx["BG"] = {a: res["background"][k] for a, k in BG_ALIAS.items() if k in res["background"]}
    ctx["F"] = {m: {FEAT_KEY[r["condition"]]: r for r in rows} for m, rows in res["features"]["table"].items()}
    ctx["G"] = {m: {GEN_KEY[r["case"]]: r for r in rows} for m, rows in res["features"]["generalization"].items()}
    ctx["VID"] = {}
    for s in res["features"]["video"]["segments"]:
        ctx["VID"].setdefault(s["kind"], s)
    ctx["EV"] = {sc: {e["kind"]: e for e in evs} for sc, evs in res["events"].items()}
    ctx["SPEED"] = {str(i): s for i, s in enumerate(res["speed"])}
    ctx["SW"] = {k.replace("|", "_"): {str(r["value"]): r for r in v} for k, v in res["sweeps"].items()}
    return ctx


def lookup(ctx, path):
    cur = ctx
    for part in path.split("."):
        cur = cur[int(part)] if isinstance(cur, list) else cur[part]
    return cur


def fmt(value, spec):
    if value is None:
        return "—"
    if spec is None:
        return str(value)
    if spec.startswith("pct"):
        return f"{value * 100:.{int(spec[3:])}f}%"
    if spec.startswith("f"):
        return f"{value:.{int(spec[1:])}f}"
    if spec == "int":
        return str(int(round(value)))
    raise ValueError(f"모르는 형식: {spec}")


def md_table(header, rows, align=None):
    align = align or ["---"] * len(header)
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join(align) + " |"]
    lines += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(lines)


def t_main(ctx):
    rows = []
    for r in ctx["table"]:
        note = []
        if r["switches"] != r["switch_events"]:
            note.append(f"ID Switch 총 {r['switches']}회")
        if r["merged"]:
            note.append(f"두 사람이 한 덩어리로 검출 {r['merged']}프레임 (ID 판정 보류)")
        if r["occluded"]:
            note.append(f"50% 이상 가림 {r['occluded']}프레임 (실패 판정 제외)")
        if r["false_ids"]:
            note.append(f"유령 ID {r['false_ids']}개")
        note.append(f"유지율 {r['retention'] * 100:.0f}%")
        rows.append([r["name"], r["tests"], r["switch_events"], r["fail_events"], "; ".join(note)])
    return md_table(["상황", "테스트 횟수", "ID Switch", "추적 실패", "비고"], rows, ["---", "---:", "---:", "---:", "---"])


def t_log(ctx):
    rows = [[r["video"], r["condition"], r["frames"], r["id_switch"], r["fail"], r["memo"]] for r in ctx["log"]]
    return md_table(["영상명", "조건", "프레임 범위", "ID Switch 수", "실패 수", "관찰 메모"], rows,
                    ["---", "---", "---", "---:", "---:", "---"])


def t_features(ctx):
    out = []
    for m, rows in ctx["features"]["table"].items():
        body = [[r["condition"], f"{r['n_ref']} / {r['n_scene_target']:.0f}", f"{r['n_correct']:.1f}",
                 f"{r['match_rate'] * 100:.1f}%", f"{r['n_good']:.1f}", f"{r['precision'] * 100:.0f}%",
                 f"{r['found_rate'] * 100:.0f}%"] for r in rows]
        out.append(f"**{m.upper()}** (장면 {len(rows)}조건 × 시행 평균)\n\n" + md_table(
            ["조건", "추출된 특징점 수 (등록 / 장면 대상 영역)", "매칭된 특징점 수 (정답)", "매칭률", "비율 검정 통과", "정밀도",
             "검출 성공"], body, ["---", "---:", "---:", "---:", "---:", "---:", "---:"]))
    return "\n\n".join(out)


def _stop(row, frames):
    s = next((x for x in row["pause"] if x["stop_frames"] == frames), None)
    if s is None:
        return "—"
    return "흡수 안 됨" if s["absorbed_after"] is None else f"{s['absorbed_after']}"


def _rec(row, kind):
    e = next(x for x in row["lighting"] if x["kind"] == kind)
    return "75 초과" if e["recovery"] is None else f"{e['recovery']}"


def t_lr(ctx):
    rows = []
    for k, r in ctx["background"].items():
        pt, lt = r["pause_tracking"], r["lighting_tracking"]
        rows.append([BG_NAME.get(k, k), _stop(r, 60), _stop(r, 90), _stop(r, 150),
                     sum(x["ghost_frames"] for x in r["pause"]), _rec(r, "on"), _rec(r, "off"), _rec(r, "lamp"),
                     f"{r['single']['f1'] * 100:.1f}%" if "single" in r else "—",
                     f"{pt['switch_events']} / {pt['fail_events']}", f"{lt['switch_events']} / {lt['fail_events']} / {lt['false_ids']}"])
    return md_table(["배경 모델", "2초 정지: 사라짐(프레임)", "3초", "5초", "유령 프레임 합", "조명 켜짐 회복", "꺼짐 회복",
                     "국소 조명 회복", "단일 영상 F1", "정지 영상 ID Switch / 실패", "조명 영상 ID Switch / 실패 / 유령 ID"], rows,
                    ["---"] + ["---:"] * 10)


def t_variants(ctx):
    rows = []
    for k, v in ctx["variants"]["test"].items():
        s = v["scenarios"]
        cell = lambda x: f"{x['switch_events']}건 ({x['switches']}회)"  # noqa: E731
        rows.append([v["label"], cell(s["crossing"]), cell(s["crossing_same"]), cell(s["single"]),
                     f"{s['pause']['switch_events']} / {s['pause']['fail_events']}",
                     f"{s['lighting']['fail_events']} / {s['lighting']['false_ids']}",
                     f"{s['crossing']['retention'] * 100:.0f}% / {s['crossing_same']['retention'] * 100:.0f}%"])
    return md_table(["추적기", "겹침 ID Switch", "겹침(같은 옷)", "단일", "정지 Switch / 실패", "조명 실패 / 유령 ID",
                     "유지율 (겹침 / 같은 옷)"], rows, ["---"] + ["---:"] * 6)


def t_byevent(ctx):
    keys = ["baseline", "kalman", "appearance", "kalman_appearance", "all_rules"]
    v = ctx["variants"]["test"]
    out = []
    for sc in ("crossing", "crossing_same"):
        evs = v["baseline"]["scenarios"][sc]["by_event"]
        rows = []
        for i, e in enumerate(evs):
            rows.append([f"{i + 1}. {e['label']}"] + [v[k]["scenarios"][sc]["by_event"][i]["switches"] for k in keys])
        rows.append(["**합계**"] + [sum(x["switches"] for x in v[k]["scenarios"][sc]["by_event"]) for k in keys])
        out.append(f"**{'옷 색이 다름 (파랑·빨강)' if sc == 'crossing' else '같은 옷 (둘 다 파랑)'}** — 이벤트별 ID Switch 횟수\n\n"
                   + md_table(["이벤트"] + [v[k]["label"] for k in keys], rows, ["---"] + ["---:"] * len(keys)))
    return "\n\n".join(out)


def t_sweep(ctx):
    out = []
    for p, label in (("max_distance", "거리 임계값 max_distance (px)"), ("max_missed", "기억 길이 max_missed (프레임)")):
        rows = []
        for d, t in zip(ctx["sweeps"][f"{p}|dev"], ctx["sweeps"][f"{p}|test"]):
            sw = lambda r: r["crossing"]["switches"] + r["crossing_same"]["switches"]  # noqa: E731
            fl = lambda r: sum(r[s]["fails"] for s in ("single", "pause", "lighting", "crossing"))  # noqa: E731
            fi = lambda r: sum(r[s]["false_ids"] for s in ("single", "pause", "lighting"))  # noqa: E731
            sd = next(x["score"] for x in ctx["tuned"]["dev_scores"][p] if x["value"] == d["value"])
            rows.append([d["value"], f"{sw(d)} / {fl(d)} / {fi(d)}", sd, f"{sw(t)} / {fl(t)} / {fi(t)}",
                         "**선택**" if d["value"] == ctx["tuned"]["chosen_on_dev"][p] else ""])
        out.append(md_table([label, "dev: 겹침 Switch / 실패 / 유령", "dev 점수 (합)", "test: 같은 순서", ""], rows,
                            ["---:", "---:", "---:", "---:", "---"]))
    return "\n\n".join(out)


def t_hungarian(ctx):
    h = ctx["hungarian"]
    rows = [[f"{r['n']}×{r['n']}", f"{r['greedy_suboptimal'] * 100:.0f}%", f"+{r['mean_excess_pct']:.0f}%"] for r in h["by_n"]]
    t1 = md_table(["무작위 비용 행렬", "탐욕이 최적이 아닌 비율", "그때 평균 추가 비용"], rows, ["---", "---:", "---:"])
    rows = [[f"{r['n']}×{r['n']}", f"{r['hungarian_ms']:.2f}", f"{r['greedy_ms']:.3f}"] for r in h["timing"]]
    t2 = md_table(["크기", "Hungarian (ms)", "탐욕 (ms)"], rows, ["---", "---:", "---:"])
    rows = [[SCEN_KO[sc], v["frames_multi"], v["frames_diff"]] for sc, v in h["tracking_disagreement"].items()]
    t3 = md_table(["영상", "추적 2개 이상·검출 2개 이상인 프레임", "두 방식의 할당이 다른 프레임"], rows, ["---", "---:", "---:"])
    return "\n\n".join([t1, t2, t3])


def t_gen(ctx):
    g = ctx["features"]["generalization"]
    rows = []
    for i, r in enumerate(g["orb"]):
        s = g["sift"][i]
        rows.append([r["case"], f"{r['found_rate'] * 100:.0f}% ({r['n_inliers']:.1f})", f"{s['found_rate'] * 100:.0f}% ({s['n_inliers']:.1f})"])
    return md_table(["장면에 놓인 것", "ORB: TARGET DETECTED 비율 (평균 inlier)", "SIFT"], rows, ["---", "---:", "---:"])


def t_video(ctx):
    rows = []
    for s in ctx["features"]["video"]["segments"]:
        def cell(d):
            if "false_positive" in d:
                return f"오검출 {d['false_positive'] * 100:.0f}%"
            err = "—" if d.get("median_err") is None else f"{d['median_err']:.1f}px"
            return f"{d['found_rate'] * 100:.0f}% / {d['detect_rate'] * 100:.0f}% / {err}"
        rows.append([SEG_KO.get(s["kind"], s["kind"]), f"{s['start']}–{s['end']}", cell(s["orb"]), cell(s["sift"])])
    ms = ctx["features"]["video"]["ms_per_frame"]
    return md_table(["구간", "프레임", f"ORB: 검출 / 정확한 위치 / 꼭짓점 오차 중앙값 ({ms['orb']:.0f} ms/프레임)",
                     f"SIFT ({ms['sift']:.0f} ms/프레임)"], rows, ["---", "---", "---:", "---:"])


def t_speed(ctx):
    rows = [[s["case"], f"{s['fps']:.0f}", f"{s['ms']:.1f}", f"{s.get('ms_worst', s['ms']):.1f}"] for s in ctx["speed"]]
    return md_table(["구성", "처리 FPS (가장 빠른 반복)", "프레임당 ms", "같은 실행의 가장 느린 반복 (ms)"], rows,
                    ["---", "---:", "---:", "---:"])


def t_zone(ctx):
    z = ctx["zone"]
    rows = [[e["frame"], e["track_id"], e["event"], f"({e['cx']:.0f}, {e['cy']:.0f})"] for e in z["events"]]
    return md_table(["프레임", "ID", "이벤트", "중심점"], rows, ["---:", "---:", "---", "---"])


TABLES = {"main": t_main, "log": t_log, "features": t_features, "lr": t_lr, "variants": t_variants, "byevent": t_byevent,
          "sweep": t_sweep, "hungarian": t_hungarian, "gen": t_gen, "video": t_video, "speed": t_speed, "zone": t_zone}


def render(template, ctx):
    def sub(m):
        key = m.group(1)
        if key.startswith("table:"):
            return TABLES[key[6:]](ctx)
        path, _, spec = key.partition(":")
        return fmt(lookup(ctx, path), spec or None)
    return re.sub(r"\{\{([^}]+)\}\}", sub, template)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    res = json.loads((ROOT / "outputs" / "results.json").read_text(encoding="utf-8"))
    tpl = (ROOT / "REPORT.template.md").read_text(encoding="utf-8")
    out = render(tpl, context(res))
    (ROOT / "REPORT.md").write_text(out, encoding="utf-8", newline="\n")
    left = re.findall(r"\{\{[^}]+\}\}", out)
    print(f"wrote REPORT.md ({len(out)} chars)" + (f", 남은 자리표시자 {left}" if left else ""))


if __name__ == "__main__":
    main()

"""results/*.json에서 리포트 5종(reports/*.md)을 만든다. 표의 숫자는 모두 실행 결과에서 가져온다.

  DIAGNOSIS_REPORT.md      편향/분산 진단과 해결 전략
  BASELINE_COMPARISON.md   딥러닝 vs 베이스라인 비교표와 개선율
  ERROR_ANALYSIS.md        오분류 태깅 표(30건 이상)와 통계, 처방 결과
  LEAKAGE.md               시계열 누수 방지 근거와 재현 실험
  BONUS.md                 하이퍼파라미터 탐색, Attention

실행: uv run python tools/build_reports.py
"""
import numpy as np

from perfdiag.common import REPORTS, RESULTS, load_json, utf8_console
from perfdiag.timeseries.data import SERIES, prepare
from perfdiag.vision.data import CLASS_KO

KEYS = ("MAE", "RMSE", "MAPE")


def f(v, d=4):
    return "-" if v is None else f"{v:,.{d}f}"


def pct(v):
    return "-" if v is None else f"{v:+.2f}%"


def acc(v):
    return f"{v * 100:.1f}%"


def table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "|".join(" --- " for _ in header) + "|"]
    out += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(out)


def write(name, text):
    path = REPORTS / name
    path.write_text(text.strip() + "\n", encoding="utf-8", newline="\n")
    print(f"저장: reports/{name}")


def load_all():
    ts = {}
    for name in SERIES:
        ts[name] = {"base": load_json(RESULTS / f"ts_baselines_{name}.json"),
                    "deep": load_json(RESULTS / f"ts_deep_{name}.json"), "prep": prepare(name)}
    optional = {k: load_json(RESULTS / f"{k}.json") if (RESULTS / f"{k}.json").exists() else None
                for k in ("vision_error_stats", "vision_improve", "bonus_hparam_search", "bonus_attention")}
    return ts, load_json(RESULTS / "vision_transfer.json"), load_json(RESULTS / "ts_leakage.json"), optional


# ----------------------------------------------------------------------------- 진단
def diagnosis_report(ts, vision, improve):
    parts = ["# 성능 진단 리포트 (Diagnosis Report)", "",
             "Train과 Validation의 성능 격차로 각 실험의 상태를 진단하고, 상태에 맞는 해결책을 적용해 그 효과를 다시 잰다.",
             "모든 곡선은 `figures/ts_*_loss_curves.png`, `figures/vision_loss_curves.png`에 있다.", "",
             "## 진단 기준", "",
             table(["상태", "Train Loss", "Validation Loss", "해결책"],
                   [["High Bias", "높음", "높음 (Train과 비슷)", "모델 복잡도↑, 학습 더 오래, 입력 피처 보강"],
                    ["High Variance", "낮음", "높음 (큰 격차)", "정규화(Dropout·Weight decay·조기 종료), 데이터↑, 학습 범위 축소"]]), "",
             "'높다'를 판단하는 기준선은 다음과 같이 정했다 (`src/perfdiag/diagnosis.py`).", "",
             "- **이미지 분류**: 오류율을 쓴다. 꽃 사진은 사람이 거의 틀리지 않으므로 기준 오류율(사람 수준)을 0으로 둔다.",
             "  Train 오류율 > 0.05이면 편향, Validation − Train 오류율 > 0.05이면 분산이다.",
             "- **시계열**: 구간마다 변동성이 달라 손실 크기를 그대로 비교할 수 없다. 같은 구간의 Naive 손실로 나눈 "
             "skill(= 모델 MSE ÷ Naive MSE)을 쓴다. Train skill ≥ 0.95이면 학습 구간에서도 '전날 값'보다 5% 넘게 낫지 못한 것이므로 "
             "편향으로 본다. Validation skill − Train skill > 0.10이면 분산이다.", ""]
    for name, d in ts.items():
        deep = d["deep"]
        rows = []
        for key, e in deep["experiments"].items():
            dg = e["diagnosis"]
            seed = next(s for s in e["seeds"] if s["seed"] == e["best_seed"])
            rows.append([e["label"] + (" ★" if key == deep["final"] else ""), f(dg["train"], 3), f(dg["validation"], 3),
                         f(dg["variance_gap"], 3), dg["label"], f"{seed['history']['epochs_run']} (복원 {seed['history']['best_epoch']})",
                         f(e["test_summary"]["MAE"]["mean"], 4)])
        parts += [f"## 시계열: {deep['title']}", "",
                  table(["실험", "Train skill", "Validation skill", "격차", "진단", "epoch", f"Test MAE ({deep['unit']})"], rows), "",
                  "★ = Validation MAE로 고른 최종 모델. skill과 epoch은 대표 seed(Validation 손실 최저) 기준, Test MAE는 seed 평균이다.", ""]
        parts += ts_findings(name, deep)
    parts += ["## 이미지: Few-shot 전이 학습 (꽃 8종)", "",
              table(["사진 수/클래스", "전략", "Train 정확도", "Validation 정확도", "Test 정확도", "격차(오류율)", "진단"],
                    [[r["shots"], r["label"] + (" ★" if r["is_main"] else ""), acc(r["train"]["accuracy"]),
                      acc(r["validation"]["accuracy"]), acc(r["test"]["accuracy"]), f(r["diagnosis"]["variance_gap"], 3),
                      r["diagnosis"]["label"]] for r in vision["runs"]]), "",
              "★ = 주 모델 (가장 많은 사진 수에서 Validation 정확도가 가장 높은 사전학습 모델). 모두 seed 0 한 번씩이다.", ""]
    parts += vision_findings(vision, improve)
    write("DIAGNOSIS_REPORT.md", "\n".join(parts))


def ts_findings(name, deep):
    e = deep["experiments"]
    lvl, dlt = e["lstm_level"], e["lstm_delta"]
    big, reg = e["probe_large"], e["probe_regularized"]
    gain_target = (lvl["test_summary"]["MAE"]["mean"] - dlt["test_summary"]["MAE"]["mean"]) / lvl["test_summary"]["MAE"]["mean"] * 100
    gain_reg = (big["test_summary"]["MAE"]["mean"] - reg["test_summary"]["MAE"]["mean"]) / big["test_summary"]["MAE"]["mean"] * 100
    lines = ["**관찰과 처방**", ""]
    lines.append(f"1. **v1 수준값 → v2 변화량**: v1 LSTM은 {lvl['diagnosis']['label']}로 진단됐다 "
                 f"(Train skill {lvl['diagnosis']['train']:.3f}, Validation skill {lvl['diagnosis']['validation']:.3f}). "
                 + ("Train에서도 Naive보다 못한 것은 모델 용량 문제가 아니라 문제 설정 문제다. 수준값을 MinMax로 넣으면 "
                    "Train 범위 밖의 가격을 외삽해야 하고, 출력이 전날 값을 그대로 따라가지 못해 늦게 반응한다. "
                    if lvl["diagnosis"]["train"] >= 0.95 else "")
                 + f"출력을 변화량으로 바꾸자 Test MAE가 {lvl['test_summary']['MAE']['mean']:.4f} → "
                 f"{dlt['test_summary']['MAE']['mean']:.4f}로 {gain_target:.1f}% 줄었다.")
    lines.append(f"2. **분산 확인 → 정규화**: 은닉 128×2층을 규제·조기 종료 없이 {len(big['seeds'][0]['history']['train_loss'])} epoch 학습하면 "
                 f"Train skill {big['diagnosis']['train']:.3f}, Validation skill {big['diagnosis']['validation']:.3f}으로 "
                 f"격차 {big['diagnosis']['variance_gap']:.3f}의 {big['diagnosis']['label']}가 된다. Dropout 0.3, Weight decay 1e-4, "
                 f"조기 종료를 적용하면 진단이 {reg['diagnosis']['label']}로 바뀌고, Test MAE가 "
                 f"{big['test_summary']['MAE']['mean']:.4f} → {reg['test_summary']['MAE']['mean']:.4f}로 {gain_reg:.1f}% 줄었다.")
    small = e["probe_small"]
    if dlt["diagnosis"]["state"] == "high_bias":
        lines.append(f"3. **남은 편향의 정체**: v2 LSTM은 Train skill {dlt['diagnosis']['train']:.3f}로 편향 판정이다. 그러나 은닉 2짜리 "
                     f"모델(Train skill {small['diagnosis']['train']:.3f})과 128×2층 모델이 모두 같은 자리에 머물고, 128×2층은 규제를 "
                     "풀면 Train만 외운다. 따라서 이 편향은 표현력 부족이 아니다. 과거 가격만으로는 다음 날 변화를 거의 예측할 수 없는 "
                     "데이터 자체의 한계(랜덤워크에 가까운 주가, Bayes 오차 ≈ Naive)다. 처방표대로 복잡도를 올리면 분산만 커진다. "
                     "이 경우 처방은 모델이 아니라 입력 정보다. 예를 들어 거시 지표, 뉴스, 다른 종목처럼 미래와 관련된 새 정보가 필요하다.")
    else:
        lines.append(f"3. **작은 모델로 충분하다**: 은닉 2짜리 모델도 {small['diagnosis']['label']}이고, Test MAE "
                     f"{small['test_summary']['MAE']['mean']:.4f}로 큰 모델과 비슷하다. 기온의 하루 변화는 소수의 선형에 가까운 관계"
                     "(계절, 전날 변화, 기압·습도)로 대부분 설명된다는 뜻이다. v2 LSTM은 Train skill "
                     f"{dlt['diagnosis']['train']:.3f}, Validation skill {dlt['diagnosis']['validation']:.3f}로 {dlt['diagnosis']['label']}다.")
    lines.append("")
    return lines


def vision_findings(vision, improve):
    runs = vision["runs"]
    shots = sorted({r["shots"] for r in runs})
    pick = {(r["shots"], r["strategy"]): r for r in runs}
    scratch = next((r for r in runs if r["strategy"] == "scratch"), None)
    main = next(r for r in runs if r["is_main"])
    n_val = vision["validation_size"]
    gaps = {s: [pick[(s, k)]["diagnosis"]["variance_gap"] for k in ("linear_probe", "partial", "full")] for s in shots}
    lines = ["**관찰과 처방**", ""]
    lines.append("1. **사진이 적을수록 분산이 크다.** 사전학습 모델은 모두 Train 정확도 100%에 이르고, 격차(Validation − Train 오류율)는 "
                 + ", ".join(f"{s}장 {min(g):.3f}~{max(g):.3f}" for s, g in gaps.items())
                 + "다. 5장에서는 모든 전략이 High Variance였고, 사진을 늘리자 격차가 줄었다(처방 '데이터↑'의 효과).")
    lp_rows = ", ".join(f"{s}장 {acc(pick[(s, 'linear_probe')]['validation']['accuracy'])} vs "
                        f"{acc(max(pick[(s, 'partial')]['validation']['accuracy'], pick[(s, 'full')]['validation']['accuracy']))}"
                        for s in shots)
    lines.append("2. **Freezing 범위: 교과서 규칙과 다른 결과.** 흔한 규칙은 '데이터가 아주 적으면 분류기만(Linear Probing)'이다. "
                 f"이 실험에서 Linear Probing은 어느 사진 수에서도 Validation 최선이 아니었고, 사진이 가장 적은 5장에서 오히려 차이가 가장 컸다"
                 f"(LP vs 몸통까지 학습한 최선: {lp_rows}). "
                 "이유로 세 가지를 본다. (1) ImageNet에는 민들레·머위 같은 클래스가 없어서, 마지막 블록의 특징이 이 둘을 가르도록 "
                 "다듬어져 있지 않다(도메인 차이). (2) 몸통 학습률을 분류기의 1/10(1e-4)로 두고 epoch을 20~30회로 제한한 것 자체가 강한 "
                 "규제로 작용해, 5장에서도 미세 조정이 무너지지 않았다. (3) 얼린 BatchNorm이 작은 미니배치 통계로 흔들리지 않는다. "
                 "결론: 최적 범위는 데이터 크기만이 아니라 사전학습 도메인과의 거리로도 정해진다. 이 데이터에서는 layer4+fc(부분)가 "
                 "모든 사진 수에서 최선이거나 그에 가까운 안전한 선택이었다.")
    lines.append(f"3. **Validation의 해상도 한계**: Validation은 {n_val}장이라 1장이 {100 / n_val:.2f}%p다. "
                 "전략 간 차이가 1~2장이면 seed를 바꿨을 때 순위가 바뀔 수 있다. 그래서 오차 분석 처방은 seed 3개로 다시 쟀다.")
    if scratch:
        lines.append(f"4. **직접 학습 대비 사전학습의 효용**: 같은 {scratch['shots']}장에서 무작위 초기화 ResNet18은 Test "
                     f"{acc(scratch['test']['accuracy'])}({scratch['diagnosis']['label']})이고, 주 모델은 {acc(main['test']['accuracy'])}다. "
                     "Train 오류율도 0이 되지 못했다. 사진 160장으로는 1,100만 개 파라미터를 처음부터 배울 수 없다. "
                     "8종 중 몇 종은 색(분홍 오스테오스페르뭄, 줄무늬 가자니아)만으로 구별되기 때문에 85%까지는 나온다.")
    if improve:
        lines.append(f"5. **오차 분석 기반 처방**: 오분류의 주 원인 '{improve['dominant_tag']}'에 맞춰 {prescription_text(improve)}을 적용했다. "
                     f"Test 정확도(seed 3개 평균)가 {acc(improve['before_test_accuracy']['mean'])} → "
                     f"{acc(improve['after_test_accuracy']['mean'])} ({improve['gain_points']:+.1f}%p)로 바뀌었다. "
                     "자세한 내용은 `reports/ERROR_ANALYSIS.md`에 있다.")
    lines.append("")
    return lines


# ----------------------------------------------------------------------------- 베이스라인 비교
def baseline_report(ts):
    parts = ["# 베이스라인 비교 리포트", "",
             "베이스라인 9개를 딥러닝 학습 **전에** 구현하고 측정했다(`scripts/ts_baselines.py`, 측정 시각은 결과 JSON에 기록). "
             "`scripts/ts_deep.py`는 베이스라인 결과가 없거나 Test 구간 지문(시점 번호와 실제값의 해시)이 다르면 실행을 거부한다. "
             "모든 모델은 같은 Test 구간에서 평가했다.", "",
             "- 개선율 = (베이스라인 오차 − 딥러닝 오차) ÷ 베이스라인 오차 × 100. 양수면 딥러닝이 더 좋다.",
             "- 최종 딥러닝 모델과 '최선의 베이스라인'은 둘 다 Validation MAE로 골랐다. Test는 비교에만 썼다.",
             "- 딥러닝 행은 seed 3개의 평균 ± 표준편차다. 개선율은 최종 모델의 대표 seed로 계산했다.",
             "- Diebold-Mariano 검정은 날마다의 오차 제곱 차이의 평균이 0인지 본다. p ≥ 0.05면 '정확도가 같다'를 기각하지 못한다.", ""]
    for name, d in ts.items():
        base, deep = d["base"], d["deep"]
        keys = KEYS if SERIES[name].with_mape else KEYS[:2]
        rows = [[m + (" (Validation 최선)" if m == base["best_by_validation"] else "")]
                + [f(v["test"][k], 3 if k == "MAPE" else 4) for k in keys] for m, v in base["metrics"].items()]
        for key, e in deep["experiments"].items():
            if e["role"] != "candidate":
                continue
            rows.append([f"**{e['label']}**" + (" ★" if key == deep["final"] else "")]
                        + [f"{f(e['test_summary'][k]['mean'], 3 if k == 'MAPE' else 4)} ± {f(e['test_summary'][k]['std'], 3 if k == 'MAPE' else 4)}"
                           for k in keys])
        imp = deep["improvement_vs_baselines"]
        dm = deep["diebold_mariano"]
        final = deep["experiments"][deep["final"]]
        info = base["split_info"]
        parts += [f"## {deep['title']} ({deep['unit']})", "",
                  f"Train {info['train']['start']} ~ {info['train']['end']} ({info['train']['n']}일), "
                  f"Validation {info['validation']['start']} ~ {info['validation']['end']} ({info['validation']['n']}일), "
                  f"Test {info['test']['start']} ~ {info['test']['end']} ({info['test']['n']}일)", "",
                  table(["Model"] + [f"{k}{'(%)' if k == 'MAPE' else ''}" for k in keys], rows), "",
                  f"★ 최종 모델: {final['label']} (seed {final['best_seed']}) — Test " + ", ".join(
                      f"{k} {f(deep['final_test'][k], 3 if k == 'MAPE' else 4)}" for k in keys), "",
                  "**최종 딥러닝 모델의 베이스라인 대비 개선율**", "",
                  table(["베이스라인"] + [f"{k} 개선율" for k in keys], [[m] + [pct(v.get(k)) for k in keys] for m, v in imp.items()]), "",
                  f"Diebold-Mariano: vs Naive 통계량 {dm['vs_naive']['statistic']:+.3f}, p = {dm['vs_naive']['p_value']:.4f}"
                  + ("" if dm["vs_best_baseline"]["model"] == "Naive" else
                     f" · vs {dm['vs_best_baseline']['model']} 통계량 {dm['vs_best_baseline']['statistic']:+.3f}, "
                     f"p = {dm['vs_best_baseline']['p_value']:.4f}")
                  + " (통계량이 음수면 딥러닝의 손실이 작다)", "", "**해석**", ""] + interpret(name, deep, base) + [
                  "", f"그림: `figures/ts_{name}_baseline_bars.png`, `figures/ts_{name}_prediction.png`", ""]
    parts += ["## MAPE를 기온에 쓰지 않은 이유", "",
              "MAPE = 평균(|y − ŷ| ÷ |y|)이다. 기온은 0℃ 근처를 지나므로 분모가 0에 가까워져 값이 발산한다. "
              "기온은 MAE·RMSE로만 비교하고, 미션이 요구한 MAPE는 주가(AAPL)에서 보고한다."]
    write("BASELINE_COMPARISON.md", "\n".join(parts))


def interpret(name, deep, base):
    imp = deep["improvement_vs_baselines"]
    naive_gain = imp["Naive"]["MAE"]
    best = base["best_by_validation"]
    p = deep["diebold_mariano"]["vs_naive"]["p_value"]
    lines = []
    if abs(naive_gain) < 1 and p >= 0.05:
        lines.append(f"- 최종 딥러닝 모델은 Naive와 사실상 같다. MAE 차이 {naive_gain:+.2f}%이고, DM 검정 p = {p:.3f}으로 "
                     "차이가 우연일 가능성을 배제할 수 없다. '딥러닝이 베이스라인보다 우수하다'는 이 데이터에서 증명되지 않았다.")
        lines.append("- 이유: 일별 주가 변화는 과거 가격으로 거의 예측되지 않는다(효율적 시장, 랜덤워크). v2 모델의 Train skill이 "
                     "1에 가깝다는 진단 결과와 같은 이야기다. 딥러닝은 '전날 값' 근처를 예측하도록 수렴하며, 그보다 나아지려 하면 "
                     "128×2층 실험처럼 Train의 잡음을 외워 Validation이 나빠진다.")
        lines.append("- 그래도 쓸모 있는 비교다. SMA·EMA·선형 추세보다는 낫고(표의 양수), v1 수준값 모델처럼 잘못 설계한 딥러닝은 "
                     "Naive보다 크게 나쁘다. '베이스라인을 먼저 측정하라'는 미션 제약이 이 착시를 막는다.")
    elif naive_gain > 0:
        lines.append(f"- 최종 딥러닝 모델은 Naive보다 Test MAE가 {naive_gain:.2f}% 낮고, Validation으로 고른 최선의 베이스라인 "
                     f"{best}보다 {imp[best]['MAE']:+.2f}% 낫다. DM 검정 p = {p:.4f}"
                     + ("로 통계적으로도 유의하다." if p < 0.05 else "로 통계적 유의성은 약하다."))
        lines.append("- 이유: 기온에는 계절성과 기상 변수 간 관계(기압·습도·일사량)가 있어 과거 30일에서 배울 구조가 있다. "
                     "선형 지연 모형보다 나은 부분이 이 비선형 관계에서 나온다.")
    else:
        lines.append(f"- 최종 딥러닝 모델이 Naive보다 Test MAE가 {-naive_gain:.2f}% 높다. DM 검정 p = {p:.4f}.")
    return lines


# ----------------------------------------------------------------------------- 오차 분석
def error_report(vision, stats, improve):
    if stats is None:
        return
    runs = {r["name"]: r for r in vision["runs"]}
    main = next(r for r in vision["runs"] if r["is_main"])
    n_review = stats["reviewed"]
    status = ("모든 행을 사용자가 검수했다." if n_review == stats["n_errors"] else
              f"**검수 상태: {n_review}/{stats['n_errors']}건 검수 완료.** 검수 전 행은 Claude가 사진을 직접 보고 단 초안"
              "(tagged_by = claude-draft)이며 사용자 검수를 기다린다. 검수는 `annotations/tagging.html`에서 한다.")
    parts = ["# 오차 분석 리포트 (Error Analysis)", "",
             "모델이 틀린 Test 사진에 원인 태그 초안을 달고 사람이 검수하는 흐름이다(Human-in-the-loop). "
             "태깅 도구 `tools/build_tagging_page.py`는 오분류 사진 옆에 실제 클래스와 예측 클래스의 Train 사진을 3장씩 나란히 보여 준다.", "",
             status, "",
             "원인 태그는 관찰에서 세운 가설이다. Test 오분류를 보고 선택한 처방의 같은 Test 재평가는 탐색적이며 독립 Test 검증이 아니다.", "",
             "## 분석 대상", "",
             f"주 모델({main['name']}, {main['label']})의 Test 오분류는 {vision['main']['errors']}건이다. "
             + (f"미션 기준 30건에 못 미쳐, 같은 Test 사진에서 다음 모델들의 오분류를 합쳤다: {', '.join(vision['error_analysis_models'])}. "
                "각 행의 '틀린 모델' 열에 어떤 모델이 틀렸는지 적었고, 예측·신뢰도는 목록에서 먼저 나온 모델(주 모델 우선)의 값이다. "
                "여러 모델이 함께 틀린 사진일수록 데이터 쪽 원인일 가능성이 크다."
                if len(vision["error_analysis_models"]) > 1 else "")
             + f" 분석 대상은 오분류 사진 {stats['n_errors']}장이다.", "",
             "## 원인 태그 통계", "",
             table(["주 원인 태그", "건수", "비율", "평균 신뢰도", "개선 방향"],
                   [[k, v["count"], f"{v['share'] * 100:.0f}%", f(v["mean_confidence"], 2) if v["mean_confidence"] else "-",
                     v["remedy"]] for k, v in stats["primary"].items()]), "",
             "세부 태그 (중복 가능): " + ", ".join(f"{k} {v}" for k, v in stats["detail"].items()), "",
             "자주 틀린 (실제 → 예측) 쌍: " + ", ".join(
                 f"{CLASS_KO.get(p.split(' → ')[0], p)}→{CLASS_KO.get(p.split(' → ')[1], p)} {v}" for p, v in list(stats["pairs"].items())[:8]), "",
             f"신뢰도 0.8 이상으로 틀린 사진: {stats['high_confidence_errors']}건", "",
             "그림: `figures/vision_error_gallery.png`(태그별 오분류 갤러리), `figures/vision_error_tags.png`(통계)", "",
             *patterns(stats),
             "## 오차 분석표", "",
             table(["번호", "파일명", "실제/예측", "신뢰도", "실패 원인 태그", "세부", "틀린 모델", "작성/검수"],
                   [[r["no"], f"`{r['file']}`", f"{CLASS_KO[r['true']]} → {CLASS_KO[r['pred']]}", f(r["confidence"], 2),
                     r["primary_tag"], r["detail"].replace(";", ", "), wrong_models(vision, r["file"]),
                     f"{r['tagged_by']} / {r['reviewed_by'] or '미검수'}"] for r in stats["table"]]), ""]
    if improve:
        fixed = ", ".join(f"{k} {v['before_correct']}→{v['after_correct']}/{v['total']}" for k, v in improve["fixed_by_tag"].items())
        b, a = improve["before"], improve["after"]
        parts += ["## 처방과 효과", "",
                  f"가장 많은 주 원인은 **{improve['dominant_tag']}**({stats['primary'][improve['dominant_tag']]['share'] * 100:.0f}%)다. "
                  f"구별 단서(머위의 비늘 줄기, 꽃잎 끝 모양)가 작고 세밀하므로 '특징 학습 강화' 처방으로 {prescription_text(improve)}을 적용했다. "
                  "학습 시간은 약 1.7배가 됐다.", "",
                  table(["", "전략", "증강", "입력", "Test 정확도 (seed 0/1/2)", "평균 ± 표준편차"],
                        [["처방 전", b["strategy"], b["augmentation"], f"{b['image_size']}px",
                          " / ".join(acc(x["test"]["accuracy"]) for x in improve["runs"]["before"]),
                          f"{acc(improve['before_test_accuracy']['mean'])} ± {improve['before_test_accuracy']['std'] * 100:.1f}%p"],
                         ["처방 후", a["strategy"], a["augmentation"], f"{a['image_size']}px",
                          " / ".join(acc(x["test"]["accuracy"]) for x in improve["runs"]["after"]),
                          f"{acc(improve['after_test_accuracy']['mean'])} ± {improve['after_test_accuracy']['std'] * 100:.1f}%p"]]), "",
                  f"Test 정확도 변화: **{improve['gain_points']:+.1f}%p**. 같은 Test의 탐색적 재평가다. "
                  "seed 3개의 표준편차만으로 통계적 유의성이나 독립 데이터의 개선을 주장할 수 없다. "
                  f"분석 대상 오분류 사진을 맞힌 수(태그별, seed 0, 처방 전→후/전체): {fixed}.", ""]
    write("ERROR_ANALYSIS.md", "\n".join(parts))


def patterns(stats):
    pairs = stats["pairs"]
    dc = pairs.get("common dandelion → colt's foot", 0) + pairs.get("colt's foot → common dandelion", 0)
    dark = sum(v for k, v in pairs.items() if k.split(" → ")[1] in ("sunflower", "black-eyed susan", "osteospermum")
               and k.split(" → ")[0] in ("english marigold", "gazania"))
    detail = stats["detail"]
    return [
        "## 사진을 보며 찾은 실패 패턴", "",
        f"1. **민들레 ↔ 머위가 {dc}건({dc / stats['n_errors']:.0%})**: 둘 다 노란 방사형 꽃이다. 사람은 머위의 붉은 비늘 줄기, "
        "꽃이 잎보다 먼저 피는 점, 민들레의 톱니 잎과 매끈한 줄기로 구별한다. 그런데 꽃만 크게 찍힌 사진에서는 이 단서가 화면 밖에 있다. "
        "줄기가 보이는 옆모습 사진(#7, #19)도 틀렸다. 모델이 줄기보다 꽃잎 질감과 색에 의존한다는 뜻이다.",
        f"2. **배경 편향**: 머위 Train 사진은 맨흙·자갈·낙엽 위가 많고, 민들레는 잔디 위가 많다. 자갈·낙엽 위의 민들레와 맨흙 위의 가자니아가 "
        f"머위로 예측됐다(세부 태그 '배경 편향' {detail.get('배경 편향(흙·자갈·낙엽)', 0)}건). 꽃이 아니라 배경을 학습한 흔적이다.",
        f"3. **짙은 꽃판 = 해바라기·루드베키아**: 꽃판이 짙은 금잔화·가자니아가 해바라기·루드베키아·오스테오스페르뭄으로 간 경우가 {dark}건이다. "
        "색 대비가 강한 중심부가 이 클래스들의 대표 특징으로 학습됐다.",
        f"4. **사진 품질**: 워터마크·글자 {detail.get('워터마크·글자', 0)}건, 작게 찍히거나 여러 송이가 있는 사진 "
        f"{detail.get('작은 객체·여러 송이', 0)}건. Test 안에 거의 같은 금잔화 사진 두 장(test_4201, test_4211)이 있어 둘 다 틀렸다.",
        "",
        "## 증강·개선 전략", "",
        table(["우선순위", "대상 패턴", "전략", "근거"], [
            ["1", "민들레↔머위 (클래스 유사성)", "더 깊은 층까지 미세 조정 + 224px 입력, 두 클래스의 줄기·잎이 보이는 사진 보강",
             "가장 많은 원인. 구별 단서(비늘 줄기·잎)가 작고 세밀해 해상도와 상위 층 특징이 필요하다"],
            ["2", "배경 편향", "RandomResizedCrop 범위 확대(꽃 위주로 자르기), 배경 교체·합성, 다양한 배경의 사진 수집",
             "배경이 클래스 단서가 되지 않도록 배경과 클래스의 상관을 끊는다"],
            ["3", "짙은 꽃판", "ColorJitter(색조·채도) 약하게", "중심부 색 하나에만 의존하지 않게 한다. 색이 실제 구별 단서인 클래스도 있어 약하게만 쓴다"],
            ["4", "워터마크·작은 객체", "RandomErasing(가림), 작은 크롭 비율", "글자·가림에 둔감하게"],
            ["5", "중복 사진", "Train·Validation·Test 사이 근접 중복 검사(perceptual hash)", "평가가 같은 사진을 두 번 세지 않게"],
        ]), "",
        "이번 미션에서는 1순위 처방을 실제로 적용해 효과를 쟀다(아래 '처방과 효과'). 2~5순위는 전략으로만 남긴다.", ""]


def prescription_text(improve):
    b, a = improve["before"], improve["after"]
    changes = []
    if a["strategy"] != b["strategy"]:
        changes.append(f"미세 조정 범위 {b['strategy']} → {a['strategy']}")
    if a["image_size"] != b["image_size"]:
        changes.append(f"입력 해상도 {b['image_size']} → {a['image_size']}px")
    if a["augmentation"] != b["augmentation"]:
        changes.append(f"증강 {b['augmentation']} → {a['augmentation']}")
    note = " (주 모델이 이미 전체 미세 조정이라 범위는 그대로)" if a["strategy"] == b["strategy"] == "full" else ""
    return ", ".join(changes) + note


def wrong_models(vision, file):
    import pandas as pd

    errors = pd.read_csv(RESULTS / "vision_errors.csv").set_index("file")
    return errors.loc[file, "wrong_models"].replace(";", ", ")


# ----------------------------------------------------------------------------- 누수
def leakage_report(ts, leakage):
    prep = ts["aapl"]["prep"]
    rows = []
    for v in leakage.values():
        rows.append([v["label"], v["violates_check"] or "-", f(v["test"]["MAE"], 3), f(v["test"]["MAPE"], 3) + "%",
                     f(v["validation"]["MAE"], 3)])
    info = {n: d["base"]["split_info"] for n, d in ts.items()}
    parts = ["# 데이터 누수(Data Leakage) 방지 근거", "",
             "시계열 처리에서 미래 정보가 학습에 들어가지 않도록 미션의 체크포인트 4개를 지켰다. 각 항목의 구현 위치와, "
             "그것을 자동으로 확인하는 테스트(`tests/test_requirements.py`의 `TimeSeriesLeakage`)를 함께 적는다.", "",
             "## 체크포인트", "",
             table(["No", "체크 항목", "구현", "근거", "검사"], [
                 ["1", "시간순 분할", "`chronological_split`", "예측 대상 시점 배열을 앞에서부터 7:1:2로 자른다. shuffle 없음. "
                  "Train 안에서 미니배치 순서만 섞는다(각 윈도우는 '과거 → 다음 값' 한 쌍이라 순서를 섞어도 미래가 들어오지 않는다).",
                  "`test_1_chronological_split_7_1_2`"],
                 ["2", "전처리 Fit 구간 제한", "`Prepared.train_rows`, `make_dataset`", "Scaler(Standard·MinMax)는 Train 구간 날짜 행으로만 "
                  "fit하고, Validation·Test에는 transform만 한다. 변화량의 정규화 통계도 Train 행에서만 잰다.",
                  "`test_2_scaler_fit_on_train_rows_only` (Validation·Test 값을 10배로 바꿔도 Scaler 통계가 같다)"],
                 ["3", "윈도우 생성 규칙", "`window_indices`", "시점 t의 입력은 t−L … t−1 행뿐이다. 입력 마지막 행이 t−1의 피처와 같은지 확인한다.",
                  "`test_3_window_has_no_future`"],
                 ["4", "피처 생성 시점", "`build_features`", "지연값·이동평균·변동성 피처는 분할 전에 전체 시계열에서 만든다. 모두 후행 창"
                  "(`diff`, `rolling`, `ewm(adjust=False)`)이라 날짜 d의 피처는 d와 그 이전 값만 쓴다. 분할 뒤에 만들면 Validation·Test "
                  "첫 20일의 이동평균이 비거나, Train 끝 값을 다시 이어 붙여야 해서 더 복잡해진다.",
                  "`test_4_features_use_only_past` (d일 이후 값을 바꿔도 d일 이전 피처가 같다)"],
             ]), "",
             "## 분할 결과", "",
             table(["데이터", "Train", "Validation", "Test"],
                   [[SERIES[n].title] + [f"{info[n][s]['start']} ~ {info[n][s]['end']} ({info[n][s]['n']}일)"
                                         for s in ("train", "validation", "test")] for n in info]), "",
             f"첫 {prep.first_target}행은 입력(최대 창 90일)과 20일 이동평균 준비에만 쓰고 예측 대상에서 뺐다. 모든 모델이 같은 예측 대상 "
             "시점을 쓰므로 Test 구간이 완전히 같다.", "",
             "## 추가로 지킨 것", "",
             "- **Test는 마지막에 한 번만**: 조기 종료, seed 선택, 최종 모델 선택, '최선의 베이스라인' 선택, 하이퍼파라미터 탐색은 모두 Validation만 본다.",
             "- **베이스라인도 과거만**: 모든 베이스라인은 시점 t를 예측할 때 y(t−1)까지만 읽는다. 선형 모형의 계수는 Train 시점으로만 적합한다 "
             "(`test_baselines_read_only_the_past`).",
             "- **데이터 공급 단계**: yfinance의 Adj Close는 나중에 지급된 배당을 과거 가격에 소급 반영한다. 그래서 주식 분할만 반영한 Close를 예측 대상으로 했다.",
             "- **시계열 증강 금지**: 미션의 주의 사항대로 Jittering·Time-warping 같은 증강은 쓰지 않았다.", "",
             "## 재현 실험: 일부러 어기면", "",
             "AAPL, LSTM 은닉 32, seed 0에서 체크포인트를 하나씩만 어겼다(`scripts/ts_leakage.py`).", "",
             table(["설정", "어긴 체크", "Test MAE", "Test MAPE", "Validation MAE"], rows), "",
             leakage_text(leakage), "", "그림: `figures/ts_leakage_demo.png`"]
    write("LEAKAGE.md", "\n".join(parts))


def leakage_text(lk):
    lines = []
    lvl, dlt = lk["correct_level"]["test"]["MAE"], lk["correct_delta"]["test"]["MAE"]
    for key, base in (("shuffled_split", lvl), ("scaler_all", lvl), ("lookahead_window", dlt), ("centered_feature", dlt)):
        v = lk[key]
        change = (base - v["test"]["MAE"]) / base * 100
        lines.append(f"- {v['label']}: Test MAE {base:.3f} → {v['test']['MAE']:.3f} ({'감소' if change > 0 else '증가'} {abs(change):.1f}%)")
    lines.append("")
    if lk["scaler_all"]["test"]["MAE"] >= lvl * 0.97:
        lines.append("②는 이 모델에서 점수를 거의 바꾸지 않았다. 새어 들어간 정보가 Test 구간의 최솟값·최댓값 두 숫자뿐이기 때문이다. "
                     "MinMax 범위가 넓어져 Test 값이 [0, 1] 안에 들어와도, 모델은 학습 중 높은 가격대의 입력·출력 쌍을 본 적이 없다. "
                     "그래서 외삽 문제는 그대로 남는다. 누수의 효과는 새어 들어간 정보의 양에 비례한다. 효과가 작았더라도 Test의 범위를 "
                     "미리 쓴 것이므로 규칙 위반이다. 평균·분산으로 정규화하거나 이상치를 자르는 전처리에서는 효과가 더 커질 수 있다.")
        lines.append("")
    lines.append("①은 Test 날짜가 무작위로 흩어져 있어, 정상 설정과 Test 구간이 다르다. Test 날짜 바로 앞뒤 날이 Train에 있으니 사실상 "
                 "보간 문제가 된다.")
    lines.append("")
    lines.append("누수 설정에서 점수가 크게 좋아지는 것은 모델이 나아진 것이 아니라 정답의 일부를 본 것이다. 실제 운영에서는 이 정보가 없으므로 "
                 "성능이 정상 설정 수준으로 돌아간다. 점수가 '너무 좋을 때' 먼저 의심해야 하는 이유다.")
    return "\n".join(lines)


# ----------------------------------------------------------------------------- 보너스
def bonus_report(hp, att):
    parts = ["# 보너스 리포트", ""]
    if hp:
        imp = sorted(hp["importance"].items(), key=lambda kv: -kv[1]["eta_squared"])
        best = hp["best"]
        fin, de = hp["final"]["test_summary"], hp["default"]["test_summary"]
        parts += ["## 1. Random Search → Coarse-to-Fine (서울 기온, LSTM 변화량)", "",
                  "Grid Search는 하이퍼파라미터 k개에 값 m개씩이면 m^k번 돌려야 하고, 중요한 축에서는 m개 값밖에 시험하지 못한다. "
                  "Random Search는 같은 예산으로 모든 축에서 매번 새 값을 시험한다(Bergstra & Bengio, 2012).", "",
                  table(["하이퍼파라미터", "1단계 범위", "2단계 범위", "최적값", "η² (중요도)", "Spearman ρ"],
                        [[k, str(hp["space"][k][1]), str([round(x, 6) if isinstance(x, float) else x for x in hp["fine_space"][k][1]]),
                          f"{best['params'][k]:.3g}" if isinstance(best["params"][k], float) else best["params"][k],
                          f"{v['eta_squared']:.3f}", f"{v['spearman']:+.3f}"] for k, v in imp]), "",
                  f"- 1단계 Coarse: 넓은 범위에서 무작위 {sum(t['stage'] == 'coarse' for t in hp['trials'])}회. "
                  f"2단계 Fine: 1단계 상위 4개가 차지한 범위로 좁혀 {sum(t['stage'] == 'fine' for t in hp['trials'])}회. "
                  f"각 trial은 최대 {hp['search_train']['epochs']} epoch, patience {hp['search_train']['patience']}.",
                  f"- 최적 trial #{best['trial']} ({best['stage']}): Validation skill {best['validation_skill']:.4f}.",
                  f"- 가장 영향이 큰 하이퍼파라미터는 **{imp[0][0]}**(η² {imp[0][1]['eta_squared']:.2f}), 그다음은 {imp[1][0]}"
                  f"(η² {imp[1][1]['eta_squared']:.2f})다. η²는 각 하이퍼파라미터를 3구간으로 나눴을 때, log(Validation MSE) 분산 중 "
                  "구간 차이로 설명되는 비율이다. 다른 하이퍼파라미터와의 상호작용은 따로 떼어 내지 못한다.",
                  f"- 최적 설정을 seed 3개로 다시 학습한 Test MAE: {fin['MAE']['mean']:.4f} ± {fin['MAE']['std']:.4f} "
                  f"(기본 설정 {de['MAE']['mean']:.4f} ± {de['MAE']['std']:.4f}, "
                  f"{(de['MAE']['mean'] - fin['MAE']['mean']) / de['MAE']['mean'] * 100:+.2f}%).",
                  f"- 해석: 탐색의 1등은 Validation skill {best['validation_skill']:.3f}였지만, seed를 바꿔 다시 학습하면 그 차이가 Test에서 "
                  "재현되지 않았다. 24개 설정 중 Validation 최저를 고르면 그 값에는 운(seed·Validation 잡음)이 섞인다(winner's curse). "
                  "기본 설정이 이미 좋은 구역에 있었다는 뜻이기도 하다. 그래서 최종 모델은 바꾸지 않았다. 탐색의 수확은 점수가 아니라 "
                  f"'무엇이 중요한가'다. 학습률(η² {hp['importance']['lr']['eta_squared']:.2f}, 높을수록 좋음: ρ "
                  f"{hp['importance']['lr']['spearman']:+.2f})과 규제 강도가 성능을 좌우했고, 은닉 크기·층 수는 거의 영향이 없었다.", "",
                  "그림: `figures/bonus_hparam_search.png`", ""]
    if att:
        parts += ["## 2. Attention 메커니즘", "",
                  "LSTM의 모든 시점 은닉 상태에 additive attention(질의 = 마지막 은닉 상태)을 붙인 모델과, 2층 Transformer 인코더를 "
                  "기본 LSTM과 비교했다. 모두 변화량(v2) 설정, seed 3개.", ""]
        for name, res in att.items():
            parts += [f"### {SERIES[name].title}", "",
                      table(["모델", "창", "파라미터", "Test MAE", "Test skill (MSE/Naive)"],
                            [[v["label"], v["window"], f"{v['parameters']:,}",
                              f"{np.mean(v['test_mae']):.4f} ± {np.std(v['test_mae']):.4f}", f"{np.mean(v['test_skill']):.3f}"]
                             for v in res.values()]), ""]
            for w in (30, 90):
                weights = np.asarray(res[f"lstm_attention_{w}"]["attention_mean"])
                top = np.argsort(weights)[::-1][:3]
                parts.append(f"- 창 {w}일: 가장 큰 평균 가중치는 " + ", ".join(f"{w - i}일 전 {weights[i]:.3f}" for i in top)
                             + f" (균등이면 {1 / w:.3f}). 최근 5일의 가중치 합 {weights[-5:].sum():.2f}.")
            parts.append("")
        parts += ["**해석**", "",
                  "- 두 시계열 모두 Attention을 붙인 LSTM이 기본 LSTM보다 낫지 않았다(Test skill이 같거나 약간 높다). "
                  "Transformer는 서울 기온 창 90일에서 MAE가 가장 낮았지만, skill(MSE 기준)은 LSTM과 비슷하고 학습 시간은 10배 이상이었다.",
                  "- AAPL의 가중치는 거의 균등하다. 고를 정보가 없다는 뜻이며, 예측이 Naive에 머문 것과 같은 결과다.",
                  "- 서울 기온 창 30일에서는 가장 오래된 날에 가중치가 몰렸다. 최근 정보는 마지막 은닉 상태 h_T가 이미 담고 있으므로, "
                  "Attention은 h_T에 없는 '한 달 전 기준점'을 가져오는 데 쓰였다.",
                  "- 30~90일은 LSTM이 감당할 만한 길이이고, 이 데이터에는 '먼 과거의 특정 시점'이 중요한 구조가 없다. Attention의 이점은 "
                  "시퀀스가 훨씬 길거나 중요한 위치가 예제마다 다를 때(문장, 로그) 커진다.", "",
                  "그림: `figures/bonus_attention.png`"]
    write("BONUS.md", "\n".join(parts))


def main():
    utf8_console()
    ts, vision, leakage, opt = load_all()
    diagnosis_report(ts, vision, opt["vision_improve"])
    baseline_report(ts)
    error_report(vision, opt["vision_error_stats"], opt["vision_improve"])
    leakage_report(ts, leakage)
    bonus_report(opt["bonus_hparam_search"], opt["bonus_attention"])


if __name__ == "__main__":
    main()

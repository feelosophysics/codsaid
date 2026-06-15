"""
Mini NPU Simulator
- MAC 연산 기반 패턴 판별기
- 모드 1: 사용자 입력 (3×3)
- 모드 2: data.json 분석 (5×5, 13×13, 25×25)
"""

import json
import time

# ============================================================
# 상수 정의
# ============================================================
EPSILON = 1e-9          # 동점 판정 허용오차
REPEAT  = 10            # 성능 측정 반복 횟수

# ============================================================
# 라벨 정규화
# 표준 라벨: "Cross", "X"
# ============================================================
def normalize_label(label: str) -> str:
    """
    다양한 표현을 표준 라벨로 변환한다.
    '+', 'cross', 'Cross', 'CROSS' → 'Cross'
    'x', 'X'                       → 'X'
    """
    mapping = {
        "+":     "Cross",
        "cross": "Cross",
        "Cross": "Cross",
        "CROSS": "Cross",
        "x":     "X",
        "X":     "X",
    }
    normalized = mapping.get(label.strip())
    if normalized is None:
        raise ValueError(f"알 수 없는 라벨: '{label}'")
    return normalized

# ============================================================
# MAC 연산 (외부 라이브러리 없이 순수 반복문)
# ============================================================
def mac_compute(pattern: list, filt: list) -> float:
    """
    두 N×N 2차원 배열을 위치별로 곱하고 모두 더해 반환.
    MAC(Multiply-Accumulate): score = Σ (pattern[r][c] * filt[r][c])
    시간 복잡도: O(N²)
    """
    n = len(pattern)
    score = 0.0
    for r in range(n):
        for c in range(n):
            score += pattern[r][c] * filt[r][c]
    return score

# ============================================================
# 판정 로직
# ============================================================
def decide(score_a: float, score_b: float,
           label_a: str = "A", label_b: str = "B") -> str:
    """
    두 점수를 epsilon 기반으로 비교하여 판정 결과 반환.
    동점(|score_a - score_b| < EPSILON)이면 'UNDECIDED'
    """
    if abs(score_a - score_b) < EPSILON:
        return "UNDECIDED"
    return label_a if score_a > score_b else label_b

# ============================================================
# 성능 측정 유틸리티
# ============================================================
def measure_mac_time(pattern: list, filt: list, repeat: int = REPEAT) -> float:
    """
    MAC 연산을 repeat회 반복 측정하고 평균 시간(ms)을 반환.
    I/O 시간 제외, 연산 함수 호출 구간만 측정.
    """
    start = time.perf_counter()
    for _ in range(repeat):
        mac_compute(pattern, filt)
    end = time.perf_counter()
    return (end - start) / repeat * 1000  # ms 단위

# ============================================================
# 입력 유틸리티
# ============================================================
def input_matrix(n: int, name: str) -> list:
    """
    콘솔에서 n×n 행렬을 한 줄씩 입력받는다.
    행/열 수 불일치, 숫자 파싱 실패 시 재입력 유도.
    """
    print(f"\n{name} ({n}줄 입력, 공백 구분)")
    matrix = []
    while len(matrix) < n:
        line = input().strip()
        try:
            row = [float(x) for x in line.split()]
        except ValueError:
            print(f"  입력 형식 오류: 숫자를 공백으로 구분해 입력하세요. 다시 입력:")
            continue
        if len(row) != n:
            print(f"  입력 형식 오류: 각 줄에 {n}개의 숫자를 입력하세요. "
                  f"(입력된 개수: {len(row)}) 다시 입력:")
            continue
        matrix.append(row)
    return matrix

# ============================================================
# 성능 분석 출력 (공통)
# ============================================================
def print_performance_table(cases: list):
    """
    cases: [(size_label, pattern, filt), ...]
    각 케이스에 대해 MAC 연산 시간을 측정하고 표로 출력.
    """
    print("\n#---------------------------------------")
    print(f"# [성능 분석] 평균 연산 시간 (반복: {REPEAT}회)")
    print("#---------------------------------------")
    print(f"{'크기':<10}{'평균 시간(ms)':>16}{'연산 횟수(N²)':>16}")
    print("-" * 44)
    for (label, pattern, filt) in cases:
        n = len(pattern)
        avg_ms = measure_mac_time(pattern, filt)
        print(f"{label:<10}{avg_ms:>16.4f}{n*n:>16}")

# ============================================================
# 패턴/필터 생성기 (보너스: 자동 생성)
# ============================================================
def make_cross(n: int) -> list:
    mid = n // 2
    return [[1 if (r == mid or c == mid) else 0
             for c in range(n)] for r in range(n)]

def make_x(n: int) -> list:
    return [[1 if (r == c or r == n - 1 - c) else 0
             for c in range(n)] for r in range(n)]

# ============================================================
# 모드 1: 사용자 입력 (3×3)
# ============================================================
def mode1_run():
    N = 3
    print("\n#----------------------------------------")
    print("# [1] 필터 입력")
    print("#----------------------------------------")

    filter_a = input_matrix(N, "필터 A")
    filter_b = input_matrix(N, "필터 B")

    print("\n#---------------------------------------")
    print("# [2] 패턴 입력")
    print("#---------------------------------------")

    pattern = input_matrix(N, "패턴")

    # MAC 연산 + 시간 측정
    score_a  = mac_compute(pattern, filter_a)
    score_b  = mac_compute(pattern, filter_b)
    avg_ms   = measure_mac_time(pattern, filter_a)

    result   = decide(score_a, score_b, "A", "B")

    print("\n#---------------------------------------")
    print("# [3] MAC 결과")
    print("#---------------------------------------")
    print(f"A 점수: {score_a}")
    print(f"B 점수: {score_b}")
    print(f"연산 시간 (평균/{REPEAT}회): {avg_ms:.4f} ms")

    if result == "UNDECIDED":
        print(f"판정: 판정 불가 (|A-B| < {EPSILON})")
    else:
        print(f"판정: {result}")

    # 성능 분석 (3×3)
    cross_3 = make_cross(3)
    x_3     = make_x(3)
    print_performance_table([("3×3", cross_3, x_3)])

# ============================================================
# 모드 2: data.json 분석
# ============================================================
def load_json(path: str = "data.json") -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"오류: '{path}' 파일을 찾을 수 없습니다.")
        return None
    except json.JSONDecodeError as e:
        print(f"오류: JSON 파싱 실패 - {e}")
        return None

def validate_filter_schema(filt_data: dict, size_key: str) -> tuple:
    """
    필터 딕셔너리에서 cross/x 키를 찾아 정규화 후 반환.
    반환: (cross_filter, x_filter) 또는 (None, None)
    """
    cross_filt = None
    x_filt     = None
    for key, val in filt_data.items():
        try:
            label = normalize_label(key)
        except ValueError:
            continue
        if label == "Cross":
            cross_filt = val
        elif label == "X":
            x_filt = val
    if cross_filt is None or x_filt is None:
        print(f"  경고: {size_key} 필터에서 cross/x를 찾을 수 없습니다.")
        return None, None
    return cross_filt, x_filt

def mode2_run():
    data = load_json()
    if data is None:
        return

    # ── 필터 로드 ──────────────────────────────────────────
    print("\n#---------------------------------------")
    print("# [1] 필터 로드")
    print("#---------------------------------------")

    filters = {}   # { "size_5": {"Cross": [...], "X": [...]}, ... }
    for size_key in ["size_5", "size_13", "size_25"]:
        if size_key not in data.get("filters", {}):
            print(f"  오류: '{size_key}' 필터가 없습니다.")
            continue
        cross_f, x_f = validate_filter_schema(data["filters"][size_key], size_key)
        if cross_f is None:
            continue
        filters[size_key] = {"Cross": cross_f, "X": x_f}
        print(f"  ✓ {size_key} 필터 로드 완료 (Cross, X)")

    # ── 패턴 분석 ──────────────────────────────────────────
    print("\n#---------------------------------------")
    print("# [2] 패턴 분석 (라벨 정규화 적용)")
    print("#---------------------------------------")

    patterns_data = data.get("patterns", {})
    total = 0
    passed = 0
    failed = 0
    fail_cases = []

    for pattern_key, pattern_info in patterns_data.items():
        total += 1
        print(f"\n--- {pattern_key} ---")

        # 키에서 N 추출: "size_5_1" → size_key="size_5", n=5
        parts = pattern_key.split("_")  # ['size', '5', '1']
        if len(parts) < 3:
            msg = f"키 형식 오류: '{pattern_key}'"
            print(f"  FAIL: {msg}")
            failed += 1
            fail_cases.append((pattern_key, msg))
            continue

        size_key = f"size_{parts[1]}"   # "size_5"

        # 필터 존재 확인
        if size_key not in filters:
            msg = f"'{size_key}' 필터 없음"
            print(f"  FAIL: {msg}")
            failed += 1
            fail_cases.append((pattern_key, msg))
            continue

        cross_f = filters[size_key]["Cross"]
        x_f     = filters[size_key]["X"]
        n       = len(cross_f)

        # 입력 패턴 로드
        inp = pattern_info.get("input")
        if inp is None:
            msg = "input 키 없음"
            print(f"  FAIL: {msg}")
            failed += 1
            fail_cases.append((pattern_key, msg))
            continue

        # 크기 검증
        if len(inp) != n or any(len(row) != n for row in inp):
            msg = (f"크기 불일치: 패턴={len(inp)}×{len(inp[0]) if inp else '?'}, "
                   f"필터={n}×{n}")
            print(f"  FAIL: {msg}")
            failed += 1
            fail_cases.append((pattern_key, msg))
            continue

        # expected 라벨 정규화
        raw_expected = pattern_info.get("expected", "")
        try:
            expected = normalize_label(raw_expected)
        except ValueError:
            msg = f"expected 라벨 파싱 실패: '{raw_expected}'"
            print(f"  FAIL: {msg}")
            failed += 1
            fail_cases.append((pattern_key, msg))
            continue

        # MAC 연산
        score_cross = mac_compute(inp, cross_f)
        score_x     = mac_compute(inp, x_f)
        result      = decide(score_cross, score_x, "Cross", "X")

        # PASS / FAIL 판정
        if result == "UNDECIDED":
            status = "FAIL"
            reason = f"동점(UNDECIDED) 처리 규칙에 따라 FAIL"
            failed += 1
            fail_cases.append((pattern_key, reason))
        elif result == expected:
            status = "PASS"
            passed += 1
        else:
            status = "FAIL"
            reason = f"판정={result}, expected={expected}"
            failed += 1
            fail_cases.append((pattern_key, reason))

        print(f"  Cross 점수: {score_cross}")
        print(f"  X     점수: {score_x}")
        if result == "UNDECIDED":
            print(f"  판정: UNDECIDED | expected: {expected} | FAIL (동점 규칙)")
        else:
            print(f"  판정: {result} | expected: {expected} | {status}")

    # ── 성능 분석 ──────────────────────────────────────────
    cross_3  = make_cross(3)
    x_3      = make_x(3)
    cross_5  = filters.get("size_5",  {}).get("Cross",  make_cross(5))
    x_5      = filters.get("size_5",  {}).get("X",      make_x(5))
    cross_13 = filters.get("size_13", {}).get("Cross",  make_cross(13))
    x_13     = filters.get("size_13", {}).get("X",      make_x(13))
    cross_25 = filters.get("size_25", {}).get("Cross",  make_cross(25))
    x_25     = filters.get("size_25", {}).get("X",      make_x(25))

    print_performance_table([
        ("3×3",    cross_3,  x_3),
        ("5×5",    cross_5,  x_5),
        ("13×13",  cross_13, x_13),
        ("25×25",  cross_25, x_25),
    ])

    # ── 결과 요약 ──────────────────────────────────────────
    print("\n#---------------------------------------")
    print("# [4] 결과 요약")
    print("#---------------------------------------")
    print(f"총 테스트: {total}개")
    print(f"통과     : {passed}개")
    print(f"실패     : {failed}개")

    if fail_cases:
        print("\n실패 케이스:")
        for (key, reason) in fail_cases:
            print(f"  - {key}: {reason}")
    else:
        print("\n실패 케이스: 없음")

    print("\n(상세 원인 분석 및 복잡도 설명은 README.md의 '결과 리포트' 섹션을 참고하세요.)")

# ============================================================
# 메인 진입점
# ============================================================
def main():
    print("=== Mini NPU Simulator ===")
    print("\n[모드 선택]")
    print("  1. 사용자 입력 (3×3)")
    print("  2. data.json 분석")

    while True:
        choice = input("선택: ").strip()
        if choice == "1":
            mode1_run()
            break
        elif choice == "2":
            mode2_run()
            break
        else:
            print("  1 또는 2를 입력하세요.")

if __name__ == "__main__":
    main()

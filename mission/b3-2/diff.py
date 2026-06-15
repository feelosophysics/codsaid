"""
diff.py — LCS 기반 Diff(파일 비교) 모듈
=========================================

[보너스 과제 5.1]

이 모듈은 두 텍스트 파일을 줄 단위로 비교하여
추가(+), 삭제(-), 공통( ) 줄을 구분해 출력합니다.

핵심 알고리즘은 LCS(Longest Common Subsequence, 최장 공통 부분수열)입니다.
difflib 라이브러리를 사용하지 않고 직접 구현합니다.

────────────────────────────────────────────
LCS(Longest Common Subsequence)란?
────────────────────────────────────────────
두 수열에서 순서를 유지하면서 공통으로 나타나는 가장 긴 부분수열입니다.

부분수열(Subsequence)은 부분문자열(Substring)과 다릅니다:
- 부분문자열: 연속해야 함   예: "ABC" → "AB", "BC" (O), "AC" (X)
- 부분수열:   연속 안 해도 됨 예: "ABC" → "AC" (O), "BC" (O)

예시:
  A = ["a", "b", "c", "d", "e"]
  B = ["a", "c", "e", "f"]
  LCS = ["a", "c", "e"] (길이 3)

이 공통 부분수열이 "변경되지 않은 줄"에 해당합니다.
LCS에 포함되지 않은 A의 줄은 "삭제", B의 줄은 "추가"입니다.

────────────────────────────────────────────
Diff에서 LCS를 사용하는 이유
────────────────────────────────────────────
파일 비교(diff)의 본질은 "두 파일에서 공통 부분을 찾고,
나머지를 변경 사항으로 표시"하는 것입니다.

LCS가 바로 "공통 부분"을 찾는 알고리즘입니다.
실제 Unix의 diff 명령어도 LCS 기반 알고리즘(Hunt-McIlroy 알고리즘)을 사용합니다.

────────────────────────────────────────────
동적 프로그래밍(Dynamic Programming, DP)
────────────────────────────────────────────
LCS는 DP로 효율적으로 풀 수 있습니다.

DP란?
큰 문제를 작은 하위 문제로 나누고,
하위 문제의 결과를 저장(메모이제이션)하여 중복 계산을 피하는 기법입니다.

LCS DP 테이블:
- dp[i][j] = A의 처음 i개와 B의 처음 j개의 LCS 길이
- A[i-1] == B[j-1]이면: dp[i][j] = dp[i-1][j-1] + 1
- 아니면:               dp[i][j] = max(dp[i-1][j], dp[i][j-1])

시간복잡도: O(m × n), 공간복잡도: O(m × n)
(m = A의 줄 수, n = B의 줄 수)
"""


def compute_lcs_table(lines_a, lines_b):
    """
    두 줄 목록의 LCS DP 테이블을 생성합니다.

    ── DP 테이블의 의미 ──
    dp[i][j]는 lines_a[:i]와 lines_b[:j]의 LCS 길이입니다.

    예시: A = ["a", "b", "c"], B = ["a", "c"]

        ""  "a" "c"
    ""   0   0   0
    "a"  0   1   1
    "b"  0   1   1
    "c"  0   1   2

    → LCS 길이 = dp[3][2] = 2 (LCS = ["a", "c"])

    ── 점화식(Recurrence Relation) ──
    if A[i-1] == B[j-1]:
        dp[i][j] = dp[i-1][j-1] + 1
        (마지막 원소가 같으면, 그것을 LCS에 포함)
    else:
        dp[i][j] = max(dp[i-1][j], dp[i][j-1])
        (마지막 원소가 다르면, 둘 중 하나를 빼고 더 긴 쪽을 선택)

    Args:
        lines_a (list): 첫 번째 파일의 줄 목록
        lines_b (list): 두 번째 파일의 줄 목록

    Returns:
        list[list[int]]: (len(lines_a)+1) × (len(lines_b)+1) 크기의 DP 테이블
    """
    m = len(lines_a)  # A의 줄 수
    n = len(lines_b)  # B의 줄 수

    # ── DP 테이블 초기화 ──
    # (m+1) × (n+1) 크기의 2차원 배열을 0으로 초기화합니다.
    # 첫 번째 행과 열은 0 (빈 수열과의 LCS는 0)
    dp = []
    for i in range(m + 1):
        row = []
        for j in range(n + 1):
            row.append(0)
        dp.append(row)

    # ── DP 테이블 채우기 ──
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if lines_a[i - 1] == lines_b[j - 1]:
                # ── 마지막 원소가 같은 경우 ──
                # 이 원소를 LCS에 포함시키므로, 양쪽 모두 한 칸 뒤로 가고 +1
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                # ── 마지막 원소가 다른 경우 ──
                # A를 한 칸 줄이거나, B를 한 칸 줄인 것 중 더 긴 LCS를 선택
                if dp[i - 1][j] >= dp[i][j - 1]:
                    dp[i][j] = dp[i - 1][j]
                else:
                    dp[i][j] = dp[i][j - 1]

    return dp


def compute_diff(lines_a, lines_b):
    """
    LCS 테이블을 역추적하여 diff 결과를 생성합니다.

    ── 역추적(Backtracking) 원리 ──
    DP 테이블의 오른쪽 아래(dp[m][n])에서 시작하여
    왼쪽 위(dp[0][0])로 이동하면서 LCS를 복원합니다.

    각 단계에서:
    1. A[i-1] == B[j-1]이면: 공통 줄 → " " (공백) 마크, i-1, j-1로 이동
    2. dp[i-1][j] >= dp[i][j-1]이면: A의 줄이 삭제됨 → "-" 마크, i-1로 이동
    3. 그렇지 않으면: B의 줄이 추가됨 → "+" 마크, j-1로 이동

    ── 출력 형식 ──
    각 줄은 (마크, 내용) 튜플입니다:
    - (" ", "공통 줄"): 두 파일에 모두 있는 줄
    - ("-", "삭제된 줄"): 파일1에만 있는 줄 (파일2에서 제거됨)
    - ("+", "추가된 줄"): 파일2에만 있는 줄 (파일2에서 추가됨)

    Args:
        lines_a (list): 첫 번째 파일의 줄 목록
        lines_b (list): 두 번째 파일의 줄 목록

    Returns:
        list[tuple]: [(마크, 줄 내용), ...] 형태의 diff 결과
    """
    # ── LCS 테이블 생성 ──
    dp = compute_lcs_table(lines_a, lines_b)

    # ── 역추적 ──
    diff_result = []  # diff 결과를 저장할 리스트
    i = len(lines_a)  # A의 끝에서 시작
    j = len(lines_b)  # B의 끝에서 시작

    while i > 0 or j > 0:
        if i > 0 and j > 0 and lines_a[i - 1] == lines_b[j - 1]:
            # ── Case 1: 공통 줄 ──
            # 두 파일에 같은 줄이 있음 → 변경 없음
            diff_result.append((" ", lines_a[i - 1]))
            i -= 1
            j -= 1
        elif i > 0 and (j == 0 or dp[i - 1][j] >= dp[i][j - 1]):
            # ── Case 2: 삭제된 줄 ──
            # 파일1에는 있지만 파일2에는 없는 줄
            diff_result.append(("-", lines_a[i - 1]))
            i -= 1
        else:
            # ── Case 3: 추가된 줄 ──
            # 파일2에는 있지만 파일1에는 없는 줄
            diff_result.append(("+", lines_b[j - 1]))
            j -= 1

    # ── 결과를 뒤집기 ──
    # 역추적은 끝에서 시작했으므로, 결과를 뒤집어야 올바른 순서가 됩니다.
    diff_result.reverse()

    return diff_result


def diff_files(file1_path, file2_path):
    """
    두 텍스트 파일을 비교하여 diff 결과를 문자열로 반환합니다.

    ── 동작 과정 ──
    1. 두 파일을 읽어 줄 목록으로 변환합니다.
    2. compute_diff()로 LCS 기반 diff를 수행합니다.
    3. 결과를 사람이 읽기 좋은 형태로 포맷팅합니다.

    ── 출력 형식 (실제 diff 명령어와 유사) ──
      공통 줄        (변경 없음)
    - 삭제된 줄      (파일1에만 존재)
    + 추가된 줄      (파일2에만 존재)

    Args:
        file1_path (str): 첫 번째 파일 경로
        file2_path (str): 두 번째 파일 경로

    Returns:
        str: diff 결과 문자열 또는 에러 메시지
    """
    # ── 파일 읽기 ──
    try:
        with open(file1_path, 'r', encoding='utf-8') as f:
            lines_a = f.read().splitlines()
            # splitlines()는 split('\n')과 비슷하지만,
            # 마지막 빈 줄을 포함하지 않고, \r\n도 처리합니다.
    except FileNotFoundError:
        return f"Error: File not found: {file1_path}"
    except Exception as e:
        return f"Error reading {file1_path}: {e}"

    try:
        with open(file2_path, 'r', encoding='utf-8') as f:
            lines_b = f.read().splitlines()
    except FileNotFoundError:
        return f"Error: File not found: {file2_path}"
    except Exception as e:
        return f"Error reading {file2_path}: {e}"

    # ── Diff 수행 ──
    diff_result = compute_diff(lines_a, lines_b)

    # ── 결과 포맷팅 ──
    output_lines = []
    output_lines.append(f"--- {file1_path}")
    output_lines.append(f"+++ {file2_path}")
    output_lines.append("")

    # 통계 카운터
    added = 0     # 추가된 줄 수
    removed = 0   # 삭제된 줄 수
    unchanged = 0 # 변경 없는 줄 수

    for mark, line in diff_result:
        if mark == "+":
            output_lines.append(f"+ {line}")
            added += 1
        elif mark == "-":
            output_lines.append(f"- {line}")
            removed += 1
        else:
            output_lines.append(f"  {line}")
            unchanged += 1

    # ── 요약 통계 ──
    output_lines.append("")
    output_lines.append(f"Summary: {added} addition(s), "
                        f"{removed} deletion(s), "
                        f"{unchanged} unchanged line(s)")

    return "\n".join(output_lines)

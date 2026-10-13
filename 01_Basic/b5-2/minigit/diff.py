"""두 UTF-8 텍스트 파일의 줄 단위 차이(선택 과제)."""

from __future__ import annotations

from minigit.constants import ConfigConstants, ErrorMessages


class DiffLimitError(ValueError):
    """파일 읽기 또는 LCS 표 할당의 상한을 넘긴 입력."""


def compute_lcs_table(lines_a: list[str], lines_b: list[str]) -> list[list[int]]:
    """dp[i][j] = A의 앞 i줄과 B의 앞 j줄에서 같은 순서로 남는 최대 줄 수.

    맨 위 행과 맨 왼쪽 열은 한쪽 파일이 비었을 때이므로 0이다.
    """
    rows = len(lines_a) + 1
    columns = len(lines_b) + 1
    cells = rows * columns
    if cells > ConfigConstants.MAX_DIFF_CELLS:
        raise DiffLimitError(
            f"LCS table needs {cells} cells; limit is {ConfigConstants.MAX_DIFF_CELLS}."
        )
    dp: list[list[int]] = []
    for _ in range(rows):
        # 각 행을 새로 만들어야 한 행 변경이 다른 행에 번지지 않는다.
        dp.append([0] * columns)

    for i in range(1, rows):
        for j in range(1, columns):
            # i, j는 '앞에서 몇 줄'이므로 실제 리스트 위치는 i-1, j-1이다.
            if lines_a[i - 1] == lines_b[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                # 현재 두 줄이 다르면 둘 중 한쪽 마지막 줄을 제외한 답 중 큰 값.
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    return dp


def compute_diff(lines_a: list[str], lines_b: list[str]) -> list[tuple[str, str]]:
    """LCS 표의 끝에서 거꾸로 걸으며 공통/삭제/추가 줄을 복원한다."""
    dp = compute_lcs_table(lines_a, lines_b)
    i = len(lines_a)
    j = len(lines_b)
    backwards: list[tuple[str, str]] = []

    # 오른쪽 아래에서 시작한다. 대각선=공통, 위=삭제, 왼쪽=추가.
    while i > 0 or j > 0:
        if i > 0 and j > 0 and lines_a[i - 1] == lines_b[j - 1]:
            backwards.append((" ", lines_a[i - 1]))
            i -= 1
            j -= 1
        elif i > 0 and (j == 0 or dp[i - 1][j] > dp[i][j - 1]):
            backwards.append(("-", lines_a[i - 1]))
            i -= 1
        else:
            backwards.append(("+", lines_b[j - 1]))
            j -= 1

    # 거꾸로 걸으며 쌓았으므로 사람이 읽는 원래 줄 순서로 뒤집는다.
    backwards.reverse()
    return backwards


def _read_lines(path: str) -> list[str]:
    """상한 내에서 파일을 읽고 UTF-8 줄 목록으로 바꾼다."""
    limit = ConfigConstants.MAX_DIFF_FILE_BYTES
    # 파일이 크더라도 상한보다 한 바이트만 더 읽어 초과를 판단한다.
    with open(path, "rb") as file:
        contents = file.read(limit + 1)
    if len(contents) > limit:
        raise DiffLimitError(f"{path} exceeds the {limit}-byte file limit.")
    return contents.decode("utf-8").splitlines()


def diff_files(file1_path: str, file2_path: str) -> str:
    """줄 앞의 공백/+/−로 공통/추가/삭제를 표시하고 개수를 요약한다."""
    # 따옴표로 묶어 전달한 경로의 공백도 파일 이름의 일부일 수 있다.
    first = file1_path
    second = file2_path
    contents: list[list[str]] = []
    for path in (first, second):
        try:
            lines = _read_lines(path)
        except FileNotFoundError:
            # 파일이 아예 없을 때는 어떤 경로가 문제인지 보여 준다.
            return ErrorMessages.FILE_NOT_FOUND.format(path=path)
        except DiffLimitError as error:
            return ErrorMessages.DIFF_LIMIT.format(reason=error)
        except (OSError, ValueError) as error:
            # NUL 경로의 ValueError와 UTF-8 해석 오류(하위 클래스)를 처리한다.
            return ErrorMessages.FILE_READ_ERROR.format(path=path, error=error)
        contents.append(lines)

    lines_a, lines_b = contents
    try:
        result = compute_diff(lines_a, lines_b)
    except DiffLimitError as error:
        return ErrorMessages.DIFF_LIMIT.format(reason=error)
    output = [f"--- {first}", f"+++ {second}", ""]
    added = removed = unchanged = 0
    # (기호, 줄 내용) 튜플을 두 변수로 나눠 받는 문법을 '언패킹'이라 한다.
    for mark, line in result:
        output.append(f"{mark} {line}")
        if mark == "+":
            added += 1
        elif mark == "-":
            removed += 1
        else:
            unchanged += 1
    output.append("")
    output.append(
        f"Summary: {added} addition(s), {removed} deletion(s), "
        f"{unchanged} unchanged line(s)"
    )
    return "\n".join(output)

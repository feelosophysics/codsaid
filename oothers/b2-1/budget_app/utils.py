"""
utils.py
애플리케이션 전반에서 사용되는 데이터 유효성 검사(Validation) 기능과
[보너스 과제 5.3] 외부 라이브러리 없이 터미널 화면에 보기 좋게 정렬된 '텍스트 표(Table)'를 출력해주는
화면 포맷터 기능을 모아둔 유틸리티 파일입니다.

특히 한글은 컴퓨터 터미널에서 영어/숫자에 비해 2배의 가로 크기를 차지하므로,
단순 글자 수 기반으로 표를 그리면 정렬이 어긋나는 문제가 생깁니다.
이를 표준 라이브러리 `unicodedata`를 활용해 완벽하게 보정했습니다.
"""

import unicodedata
from datetime import datetime
from typing import List, Dict, Any


def get_display_width(text: str) -> int:
    """
    문자열이 터미널 화면에 출력될 때 차지하는 실제 가로 칸 수(폭)를 계산합니다.
    - 알파벳, 숫자, 일반 기호: 1칸 (Half-width)
    - 한글, 한자, 일본어 등: 2칸 (Full-width)
    """
    width = 0
    for char in text:
        # unicodedata.east_asian_width는 해당 문자가 동아시아 전각 문자인지 반전각 문자인지 분류해 줍니다.
        status = unicodedata.east_asian_width(char)
        if status in ('W', 'F', 'A'): # 'Wide', 'Full-width', 'Ambiguous'
            width += 2
        else:
            width += 1
    return width


def pad_string(text: str, target_width: int, align: str = "left") -> str:
    """
    화면 실제 가로 칸 수를 고려하여 문자열에 공백을 패딩해 줍니다.
    - text: 정렬할 문자열
    - target_width: 목표로 하는 실제 칸 수
    - align: 'left', 'right', 'center' 중 선택
    """
    current_width = get_display_width(text)
    pad_needed = target_width - current_width
    
    if pad_needed <= 0:
        return text
        
    if align == "left":
        return text + (" " * pad_needed)
    elif align == "right":
        return (" " * pad_needed) + text
    else: # center
        left_pad = pad_needed // 2
        right_pad = pad_needed - left_pad
        return (" " * left_pad) + text + (" " * right_pad)


def print_table(headers: List[str], rows: List[List[Any]], alignments: List[str] = None) -> None:
    """
    [보너스 과제 5.3]
    전달받은 헤더와 행 데이터를 기준으로 예쁜 터미널 텍스트 표를 출력합니다.
    - headers: 각 열(Column)의 제목 리스트
    - rows: 출력할 데이터 행들의 리스트
    - alignments: 각 열의 정렬 방식 ('left', 'right', 'center') 리스트
    """
    if not headers:
        return
        
    # 기본 정렬 방식을 모두 'left'로 설정
    if not alignments:
        alignments = ["left"] * len(headers)
        
    # 1. 각 열(Column)별로 가장 긴 데이터의 폭을 구하여 적절한 열 너비를 계산합니다.
    col_widths = []
    for col_idx in range(len(headers)):
        # 헤더 글자 폭
        max_w = get_display_width(headers[col_idx])
        # 각 행에 있는 해당 열의 데이터 글자 폭 중 최댓값
        for row in rows:
            if col_idx < len(row):
                val_str = str(row[col_idx] if row[col_idx] is not None else "")
                max_w = max(max_w, get_display_width(val_str))
        col_widths.append(max_w)
        
    # 2. 표 위아래를 장식할 가로 구분선(Border)을 구성합니다.
    # 열과 열 사이에는 ' | ' 구분자를 넣어 주므로 너비를 더해 줍니다.
    border_parts = []
    for width in col_widths:
        border_parts.append("-" * width)
    border_line = "+-" + "-+-".join(border_parts) + "-+"

    # 3. 헤더 출력
    print(border_line)
    header_cells = []
    for col_idx, header in enumerate(headers):
        # 헤더는 기본적으로 가운데 정렬로 예쁘게 배치합니다.
        padded = pad_string(header, col_widths[col_idx], align="center")
        header_cells.append(padded)
    print("| " + " | ".join(header_cells) + " |")
    print(border_line)

    # 4. 데이터 행들 출력
    if not rows:
        # 데이터가 비어 있을 경우 안내 행 출력
        total_width = sum(col_widths) + 3 * (len(headers) - 1)
        empty_msg = pad_string("(조회된 내역이 없습니다)", total_width, align="center")
        print("| " + empty_msg + " |")
    else:
        for row in rows:
            row_cells = []
            for col_idx in range(len(headers)):
                val = row[col_idx] if col_idx < len(row) else ""
                val_str = str(val if val is not None else "")
                align = alignments[col_idx] if col_idx < len(alignments) else "left"
                
                padded = pad_string(val_str, col_widths[col_idx], align=align)
                row_cells.append(padded)
            print("| " + " | ".join(row_cells) + " |")
            
    print(border_line)


def validate_date(date_str: str) -> str:
    """
    날짜 문자열이 올바른 YYYY-MM-DD 형식이며, 실제로 존재하는 날짜인지 검증합니다.
    올바른 경우 포맷팅된 문자열을 돌려주고, 틀릴 경우 ValueError를 발생시킵니다.
    """
    try:
        # strptime을 사용하면 2월 30일이나 13월 같은 존재 불가능한 날짜를 차단할 수 있습니다.
        parsed_date = datetime.strptime(date_str, "%Y-%m-%d")
        return parsed_date.strftime("%Y-%m-%d")
    except ValueError:
        raise ValueError(f"날짜 '{date_str}'는 올바른 날짜 형식이 아니거나 존재하지 않는 날짜입니다. (형식: YYYY-MM-DD)")


def validate_amount(amount_str: str) -> int:
    """
    금액 문자열이 올바른 양수 정수인지 검증합니다.
    양수 정수인 경우 정수형(int) 값을 반환하고, 아닐 경우 ValueError를 발생시킵니다.
    """
    try:
        amount = int(amount_str)
        if amount <= 0:
            raise ValueError()
        return amount
    except ValueError:
        raise ValueError(f"금액 '{amount_str}'은(는) 0보다 큰 양의 정수(숫자)여야 합니다. (예: 15000)")


def validate_type(type_str: str) -> str:
    """
    거래 타입이 'income'(수입) 또는 'expense'(지출) 중 하나인지 검증합니다.
    대소문자를 구분하지 않고 판별한 후 소문자로 리턴하며, 틀릴 경우 ValueError를 발생시킵니다.
    """
    clean_type = type_str.strip().lower()
    if clean_type not in ("income", "expense"):
        raise ValueError(f"거래 타입 '{type_str}'은(는) 허용되지 않습니다. 반드시 'income' 또는 'expense' 중 하나여야 합니다.")
    return clean_type


def validate_month(month_str: str) -> str:
    """
    년월 문자열이 올바른 YYYY-MM 형식인지 검증합니다.
    """
    try:
        parsed_month = datetime.strptime(month_str, "%Y-%m")
        return parsed_month.strftime("%Y-%m")
    except ValueError:
        raise ValueError(f"년월 '{month_str}'은(는) 올바른 형식이 아닙니다. (형식: YYYY-MM, 예: 2026-05)")

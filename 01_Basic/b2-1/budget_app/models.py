"""
models.py
가계부 애플리케이션에서 사용하는 핵심 데이터의 구조를 정의하는 파일입니다.
파이썬의 'dataclass'를 사용하여, 복잡한 코드 없이 직관적이고 가독성 높은 클래스를 만듭니다.
초보자도 데이터의 흐름과 형태를 명확히 파악할 수 있도록 타입 힌트(Type Hints)와 풍부한 한글 주석을 작성했습니다.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Transaction:
    """
    가계부의 단일 거래 내역(수입 또는 지출)을 나타내는 클래스입니다.
    """
    id: str                  # 거래의 고유 식별자 (예: TX-000001)
    type: str                # 거래 종류 (수입: 'income', 지출: 'expense')
    date: str                # 거래 일자 (형식: YYYY-MM-DD)
    amount: int              # 거래 금액 (항상 0보다 큰 양수 정수)
    category: str            # 카테고리 이름 (예: 식비, 교통, 주거 등)
    memo: str = ""           # 간단한 메모 (선택 사항, 기본값은 빈 문자열)
    tags: List[str] = field(default_factory=list) # 태그 목록 (예: ['외식', '친구'])

    def to_dict(self) -> dict:
        """
        데이터 저장 및 가공을 위해 객체를 파이썬 기본 딕셔너리(dictionary) 형식으로 변환합니다.
        """
        return {
            "id": self.id,
            "type": self.type,
            "date": self.date,
            "amount": self.amount,
            "category": self.category,
            "memo": self.memo,
            "tags": self.tags
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Transaction":
        """
        저장 파일에서 읽어온 딕셔너리 데이터를 활용해 Transaction 객체를 새로 생성합니다.
        """
        return cls(
            id=data["id"],
            type=data["type"],
            date=data["date"],
            amount=int(data["amount"]),
            category=data["category"],
            memo=data.get("memo", ""),
            tags=data.get("tags", [])
        )


@dataclass
class Category:
    """
    거래에 할당될 수 있는 카테고리(분류)를 정의하는 클래스입니다.
    """
    name: str                # 카테고리명 (예: 식비, 교통, 주거, 수입, 기타 등)

    def to_dict(self) -> dict:
        return {"name": self.name}

    @classmethod
    def from_dict(cls, data: dict) -> "Category":
        return cls(name=data["name"])


@dataclass
class Budget:
    """
    특정 월의 한도 예산을 정의하는 클래스입니다.
    """
    month: str               # 대상 년월 (형식: YYYY-MM)
    amount: int              # 예산 설정 금액 (양수 정수)

    def to_dict(self) -> dict:
        return {
            "month": self.month,
            "amount": self.amount
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Budget":
        return cls(
            month=data["month"],
            amount=int(data["amount"])
        )


@dataclass
class RecurringRule:
    """
    [보너스 과제 5.2]
    매달 고정적으로 발생하는 반복 거래 내역(예: 월급, 월세, 보험료 등)의 생성 규칙을 정의합니다.
    """
    id: str                  # 반복 규칙 고유 ID (예: REC-000001)
    day_of_month: int        # 매달 며칠에 발생할 것인지 (1~31)
    type: str                # 거래 종류 ('income' 또는 'expense')
    amount: int              # 반복 발생할 금액
    category: str            # 카테고리 이름
    memo: str = ""           # 자동 입력될 메모
    tags: List[str] = field(default_factory=list) # 자동 입력될 태그 목록

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "day_of_month": self.day_of_month,
            "type": self.type,
            "amount": self.amount,
            "category": self.category,
            "memo": self.memo,
            "tags": self.tags
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RecurringRule":
        return cls(
            id=data["id"],
            day_of_month=int(data["day_of_month"]),
            type=data["type"],
            amount=int(data["amount"]),
            category=data["category"],
            memo=data.get("memo", ""),
            tags=data.get("tags", [])
        )

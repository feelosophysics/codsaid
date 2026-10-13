"""군집 번호에 사람이 읽을 페르소나 이름과 전략을 붙인다.

이름은 사람이 군집 프로파일을 보고 정한 것이다. 각 페르소나는 "어떤 변수가 평균보다 0.5 표준편차 이상
높거나 낮은가"라는 서명으로 정의하고, 실제 군집이 서명과 맞을 때만 이름을 붙인다.
데이터나 K가 바뀌어 서명이 맞지 않으면 예외를 내서, 낡은 이름이 다른 군집에 붙는 일을 막는다.
"""

from .clustering import DISTINGUISH_Z

# 서명: 변수 → +1(평균보다 높음) / -1(낮음). 서명에 없는 변수는 평균 근처여도, 아니어도 된다.
PERSONAS = [
    {
        "key": "repeat_delinquent",
        "en": "Repeat delinquent",
        "ko": "연체 반복형",
        "signature": {"overdue_count_6m": +1},
        "summary": "최근 6개월 연체가 모두 2회 이상이다. 다른 변수는 전체 평균과 비슷하다.",
        "target": "기존 고객 리스크 관리",
        "message": "상환 일정을 함께 조정해 연체를 끊는다",
        "action": "신규 한도 동결, 채무 조정 상담, 자동이체 전환 유도. 마케팅 발송 대상에서 제외",
    },
    {
        "key": "senior_high_debt",
        "en": "Senior high-debt",
        "ko": "고령·고부채 다카드형",
        "signature": {"age": +1, "debt_ratio": +1, "credit_card_count": +1},
        "summary": "나이가 많고 부채 비율과 카드 수가 높다. 연체 이력은 적지만 부채 부담이 크다.",
        "target": "보류 심사 집중 대상",
        "message": "흩어진 카드 부채를 하나로 모아 이자 부담을 줄인다",
        "action": "카드·부채 통합 대환 제안, 부채 비율 변화 모니터링, 신규 카드 발급 억제",
    },
    {
        "key": "young_high_debt_spender",
        "en": "Young high-debt spender",
        "ko": "청년·고부채 소비형",
        "signature": {"age": -1, "debt_ratio": +1, "credit_card_count": -1},
        "summary": "젊고 부채 비율이 높다. 카드는 적지만 소비 점수가 평균보다 높다.",
        "target": "성장 잠재 고객, 단계적 관리",
        "message": "쓰는 만큼 관리하면 한도가 함께 커진다",
        "action": "소액 한도로 시작해 상환 이력에 따라 단계적 상향, 소비 알림·예산 관리 기능 안내",
    },
    {
        "key": "young_multi_card_saver",
        "en": "Young multi-card saver",
        "ko": "청년·다카드 절약형",
        "signature": {"age": -1, "spending_score": -1, "credit_card_count": +1},
        "summary": "젊고 카드는 많지만 소비 점수가 낮다. 부채 비율은 평균 수준이다.",
        "target": "주거래 전환 마케팅",
        "message": "여러 카드의 혜택을 한 장으로 모은다",
        "action": "주거래 카드 통합 혜택, 적금 연계 상품, 사용하지 않는 카드 정리 안내",
    },
    {
        "key": "midage_frugal",
        "en": "Mid-age frugal",
        "ko": "중장년·저소비 실속형",
        "signature": {"spending_score": -1, "credit_card_count": -1},
        "summary": "소비 점수와 카드 수가 낮고, 부채 비율도 평균보다 조금 낮다.",
        "target": "예금·연금 교차 판매",
        "message": "모아 둔 자산을 안정적으로 불린다",
        "action": "예금·연금·저위험 투자 상품 제안, 간소화 심사로 대출 절차 단축",
    },
    {
        "key": "low_debt_spender",
        "en": "Low-debt spender",
        "ko": "저부채 고소비 우량형",
        "signature": {"debt_ratio": -1, "spending_score": +1},
        "summary": "부채 비율이 가장 낮고 소비 점수가 가장 높다.",
        "target": "VIP 육성",
        "message": "많이 쓰는 만큼 더 돌려받는다",
        "action": "프리미엄 카드, 한도 상향 사전 승인, 소비 리워드 강화",
    },
]


def _matches(z: dict, signature: dict) -> bool:
    return all(z[f] * sign >= DISTINGUISH_Z for f, sign in signature.items())


def assign(profiles: list[dict]) -> list[dict]:
    """군집마다 서명이 맞는 페르소나를 하나씩 붙인다. 맞는 것이 없거나 둘 이상이면 예외."""
    used, out = set(), []
    for p in profiles:
        hits = [d for d in PERSONAS if _matches(p["z"], d["signature"])]
        if len(hits) != 1 or hits[0]["key"] in used:
            raise ValueError(
                f"군집 {p['cluster']}의 페르소나를 정할 수 없습니다(후보 {[h['key'] for h in hits]}). "
                "데이터나 K가 바뀌었다면 src/personas.py의 서명을 다시 정하세요."
            )
        used.add(hits[0]["key"])
        out.append({k: v for k, v in hits[0].items() if k != "signature"} | {"cluster": p["cluster"]})
    return out


def short_label(persona: dict) -> str:
    return f"C{persona['cluster']} {persona['en']}"

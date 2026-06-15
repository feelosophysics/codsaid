# 🎓 초심자를 위한 극한 상세 학습 가이드 (Ultra-Detailed Study Guide)

> **이 문서의 목표**: "초심자인 내가 다른 초심자에게 설명할 수 있을 정도로" 미션의 함의와 코드의 로직·흐름을 완벽하게 이해하는 것.
>
> **작성 원칙**: 모든 설명은 실제 워크스페이스의 코드 파일과 1:1 대응합니다. "이론상 이럴 것이다"가 아니라 "실제로 코드가 이렇게 되어 있고, 이렇게 동작한다"를 증명합니다.

---

## 📋 전체 로드맵 (10단계)

| 단계 | 제목 | 핵심 질문 | 대응 파일 |
|:---:|:---|:---|:---|
| **1** | 큰 그림 — 미션의 본질과 프로그램 전체 흐름 | "이 프로그램은 뭘 하는 건데? 왜 이렇게 복잡해?" | 전체 구조 |
| **2** | 파이썬 패키지 시스템과 프로그램 진입점 | "`python -m budget_app`이 뭔데? 왜 이렇게 실행해야 해?" | `__init__.py`, `__main__.py` |
| **3** | 데이터 모델 — dataclass와 직렬화 | "Transaction이 뭐야? to_dict, from_dict는 왜 필요해?" | `models.py` |
| **4** | 저장소 계층 — 파일 I/O의 모든 것 | "데이터를 어떻게 파일에 저장하고 읽어오는 거야?" | `repository.py` |
| **5** | 제너레이터와 yield — 스트리밍의 원리 | "yield가 뭔데? 왜 한 번에 안 읽어?" | `repository.py` |
| **6** | 원자적 쓰기 — 데이터 안전의 핵심 | "수정/삭제할 때 파일이 깨지면 어떡해?" | `repository.py` |
| **7** | 비즈니스 서비스 — 두뇌의 로직 | "실제 계산, 검증, 판단은 어디서 해?" | `service.py` |
| **8** | 데코레이터 — 관심사 분리의 기술 | "데코레이터가 뭔데? 왜 분리해?" | `decorators.py` |
| **9** | CLI 표현 계층 — 사용자와의 대화 | "사용자 입력을 어떻게 받고 화면에 어떻게 보여줘?" | `cli.py`, `utils.py` |
| **10** | 평가 대비 — 16가지 기준 완전 정복 | "면접/평가에서 뭘 물어보고, 뭐라고 대답해?" | 체크리스트 |

> **읽는 법**: 1단계부터 순서대로 읽으세요. 각 단계는 이전 단계의 내용을 전제로 합니다.

---
---

# 📘 1단계: 큰 그림 — 미션의 본질과 프로그램 전체 흐름

> **이 단계의 목표**: 코드를 한 줄도 보기 전에, "이 프로그램이 도대체 뭘 하는 건지", "왜 이렇게 여러 파일로 나뉘어 있는지", "데이터는 어디에 어떻게 저장되는지"를 완벽히 이해합니다.

---

## 1.1 미션은 무엇을 요구하는가?

### 1.1.1 한 줄 요약
**"파이썬으로 콘솔(터미널)에서 동작하는 가계부 프로그램을 만들어라."**

### 1.1.2 좀 더 풀어서 설명하면

> *"'작은 서비스'란 기능이 많은 게 아니라 예외 상황에서도 데이터가 안전한 것을 말합니다."*

이 한 줄이 미션의 **핵심 철학**입니다. 단순히 "수입/지출을 기록하는 프로그램"이 아니라:

1. **데이터를 영구적으로 안전하게 저장**하고 (파일 기반 저장)
2. **잘못된 입력을 친절하게 거부**하며 (입력 검증 + 에러 힌트)
3. **대용량 데이터에도 메모리가 터지지 않게** 처리하고 (제너레이터)
4. **파일이 깨지지 않도록 안전하게 수정/삭제**하며 (원자적 쓰기)
5. **코드가 깔끔하게 분리**되어 있어야 합니다 (모듈화 + 데코레이터)

### 1.1.3 가계부가 해야 할 10가지 일

미션에서 요구하는 기능을 "일상생활 비유"로 바꿔보겠습니다:

| 기능 | 일상생활 비유 | 프로그램 명령어 |
|:---|:---|:---|
| **거래 추가** | 가계부 노트에 "오늘 점심 12,000원 지출" 적기 | `add` |
| **목록 보기** | 가계부 노트를 펼쳐서 최근 기록 쭉 보기 | `list` |
| **검색** | "지난달에 교통비를 얼마나 썼지?" 찾기 | `search` |
| **월별 요약** | "이번 달 총 수입/지출/잔액이 얼마지?" 계산 | `summary` |
| **예산 설정** | "이번 달 예산은 100만원으로 정하자" | `budget set` |
| **카테고리 관리** | "식비, 교통, 주거 같은 분류 만들기/지우기" | `category` |
| **수정** | "어제 적은 금액이 틀렸네, 고치자" | `update` |
| **삭제** | "이 기록은 잘못 넣었으니 지우자" | `delete` |
| **가져오기** | "엑셀에서 만든 파일을 가계부에 한꺼번에 넣기" | `import` |
| **내보내기** | "가계부 내용을 엑셀 파일로 빼내기" | `export` |

### 1.1.4 미션이 요구하는 "기술적 조건" — 왜 단순하지 않은가

미션은 단순히 "기능이 돌아가면 끝"이 아닙니다. **어떻게(How)** 만드는지에 대한 기술적 조건이 엄격합니다:

```
┌─────────────────────────────────────────────────────┐
│  미션의 5대 기술 조건                                │
│                                                      │
│  1. 제너레이터(yield) → 대용량 파일 스트리밍 처리     │
│  2. 데코레이터        → 공통 기능 분리                │
│  3. 타입 힌트         → 코드의 계약 명시              │
│  4. 모듈 분리(3+개)   → 책임 분리 아키텍처            │
│  5. 파일 영구 저장     → 최소 3개 파일                │
│     (transactions, categories, budgets)               │
└─────────────────────────────────────────────────────┘
```

**왜 이런 조건이 있을까요?**

실제 회사에서 프로그램을 만들 때는 이런 것들이 **기본**입니다:
- 데이터가 100만 건이면 한 번에 메모리에 올릴 수 없습니다 → **제너레이터** 필요
- 모든 함수마다 `try-except`를 복붙하면 코드가 엉망이 됩니다 → **데코레이터** 필요
- 함수가 무엇을 받고 무엇을 돌려주는지 안 써놓으면 협업이 불가능합니다 → **타입 힌트** 필요
- 파일 하나에 코드 2,000줄을 넣으면 아무도 읽을 수 없습니다 → **모듈 분리** 필요

---

## 1.2 프로그램의 물리적 구조 — 파일들은 어떻게 구성되어 있는가?

### 1.2.1 디렉토리 트리

우리 워크스페이스(`glad/`)의 실제 구조입니다:

```
glad/                          ← 최상위 프로젝트 폴더
├── budget_app/                ← 🧩 파이썬 패키지 (프로그램 코드 전체)
│   ├── __init__.py            ← 📦 "이 폴더는 패키지입니다" 선언
│   ├── __main__.py            ← 🚪 프로그램 진입점 (문 열고 들어오는 곳)
│   ├── cli.py                 ← 🖥️ 사용자 인터페이스 (화면 입출력)
│   ├── decorators.py          ← 🎀 공통 기능 래퍼 (에러/로그/시간)
│   ├── models.py              ← 💎 데이터 구조 정의 (거래, 카테고리 등)
│   ├── repository.py          ← 💾 파일 읽기/쓰기 전담
│   ├── service.py             ← 🧠 비즈니스 로직 (계산, 판단, 검증)
│   └── utils.py               ← 🔧 도구 모음 (검증 함수, 표 출력)
├── data/                      ← 📁 데이터 저장 폴더 (자동 생성)
│   ├── transactions.jsonl     ← 거래 내역 파일
│   ├── categories.jsonl       ← 카테고리 목록 파일
│   ├── budgets.jsonl          ← 월별 예산 파일
│   ├── recurring.jsonl        ← 반복 거래 규칙 파일
│   └── activity.log           ← 활동 감사 로그
└── backups/                   ← 🗄️ ZIP 백업 보관소 (자동 생성)
```

### 1.2.2 각 파일의 역할을 "회사 부서"에 비유하면

프로그램을 하나의 회사로 비유해 봅시다:

```
┌──────────────────────────────────────────────────────────┐
│                    🏢 가계부 주식회사                      │
│                                                           │
│  🚪 [접수 데스크]  __main__.py                            │
│     └→ 손님(사용자)이 문을 열고 들어오면 안내데스크로 이동  │
│                                                           │
│  🖥️ [고객 상담실]  cli.py                                 │
│     └→ 손님이 "뭘 원하시나요?"를 얘기하는 곳               │
│     └→ 잘못된 요청은 "이건 이렇게 해주세요" 안내           │
│                                                           │
│  🧠 [기획/전략실]  service.py                              │
│     └→ "이 요청을 어떻게 처리할지" 두뇌가 판단             │
│     └→ 카테고리 삭제해도 되는지? 예산 초과했는지? 등        │
│                                                           │
│  💾 [문서 보관실]  repository.py                           │
│     └→ 실제 서류(파일)를 금고에 넣고 꺼내는 곳             │
│     └→ 서류가 찢어지지 않게 안전하게 교체(원자적 쓰기)     │
│                                                           │
│  💎 [서류 양식]    models.py                               │
│     └→ "거래 내역서"라는 서류 양식(폼)의 규격을 정의       │
│                                                           │
│  🎀 [감사/보안팀]  decorators.py                           │
│     └→ 모든 부서를 감시: 에러 나면 보고, 시간 측정, 로깅   │
│                                                           │
│  🔧 [총무/관리팀]  utils.py                                │
│     └→ 날짜 형식 검사, 금액 검사, 표 그리기 같은 잡무 처리 │
└──────────────────────────────────────────────────────────┘
```

### 1.2.3 핵심 통찰: "한 파일에 다 넣으면 왜 안 되는가?"

초심자가 가장 흔히 하는 질문입니다. 답은 간단합니다:

**"식당에서 요리사가 주문도 받고, 요리도 하고, 서빙도 하고, 계산도 하고, 설거지도 하면 어떤 일이 벌어질까요?"**

→ 한 명이 모든 걸 하면 느리고, 실수가 많고, 한 곳이 고장 나면 전체가 멈춥니다.

그래서 역할을 나눕니다:
- `cli.py` = 주문 받는 사람 (사용자 입력만 처리)
- `service.py` = 요리사 (비즈니스 로직만 처리)
- `repository.py` = 냉장고 관리자 (재료=데이터 저장만 처리)
- `models.py` = 메뉴판 (데이터 구조만 정의)

이것을 컴퓨터 과학에서 **"책임 분리(Separation of Concerns)"** 또는 **"레이어드 아키텍처(Layered Architecture)"**라고 부릅니다.

---

## 1.3 데이터는 어디에, 어떤 모양으로 저장되는가?

### 1.3.1 JSONL이란 무엇인가?

우리 프로그램은 데이터를 **JSONL(JSON Lines)** 형식으로 저장합니다. 이것은:

```
한 줄 = 하나의 완전한 JSON 객체
```

실제 `data/transactions.jsonl` 파일을 열어보면 이런 모습입니다:

```json
{"id": "TX-000001", "type": "expense", "date": "2026-05-10", "amount": 12000, "category": "식비", "memo": "맛있는 점심", "tags": ["점심", "회사"]}
{"id": "TX-000002", "type": "income", "date": "2026-05-20", "amount": 2500000, "category": "수입", "memo": "월급", "tags": ["회사"]}
```

**왜 JSONL을 선택했을까요?** 세 가지 선택지를 비교해 봅시다:

#### 선택지 1: CSV (❌ 탈락)
```csv
TX-000001,expense,2026-05-10,12000,식비,맛있는 점심,"점심,회사"
```
- **문제**: 태그가 `["점심", "회사"]`처럼 리스트인데, CSV는 리스트를 표현할 방법이 없습니다
- 쉼표로 구분하는 CSV 안에 쉼표가 들어가면 파싱이 꼬입니다

#### 선택지 2: 단일 JSON 파일 (❌ 탈락)
```json
[
  {"id": "TX-000001", ...},
  {"id": "TX-000002", ...}
]
```
- **문제**: 거래 하나를 추가하려면 전체 파일을 읽어서 배열 끝에 넣고 다시 전체를 써야 합니다
- 10만 건이면 거래 1건 추가할 때마다 10만 건을 다시 쓰는 것입니다
- 쓰다가 중간에 에러 나면? 전체 데이터가 날아갑니다!

#### 선택지 3: JSONL (✅ 채택!)
```json
{"id": "TX-000001", ...}
{"id": "TX-000002", ...}
```
- **장점 1**: 거래 추가 시 파일 끝에 한 줄만 덧붙이면 됩니다 (매우 빠름!)
- **장점 2**: 한 줄씩 읽을 수 있으므로 10만 건이어도 메모리 1건분만 쓰면 됩니다
- **장점 3**: 태그 리스트 같은 복잡한 데이터도 JSON이니까 완벽하게 표현됩니다

### 1.3.2 저장 파일 4종 세트

우리 프로그램은 **4개의 JSONL 파일**을 사용합니다:

```
data/
├── transactions.jsonl   ← 거래 내역 (가장 중요!)
│   예: {"id":"TX-000001", "type":"expense", "date":"2026-05-10", 
│        "amount":12000, "category":"식비", "memo":"점심", "tags":["점심"]}
│
├── categories.jsonl     ← 카테고리 사전
│   예: {"name": "식비"}
│       {"name": "교통"}
│       {"name": "주거"}
│       {"name": "수입"}
│       {"name": "기타"}
│
├── budgets.jsonl        ← 월별 예산
│   예: {"month": "2026-05", "amount": 1000000}
│
└── recurring.jsonl      ← 반복 거래 규칙 (보너스)
    예: {"id":"REC-000001", "day_of_month":25, "type":"income",
         "amount":2500000, "category":"수입", "memo":"월급", "tags":["급여"]}
```

### 1.3.3 파일이 없으면 어떻게 되는가? (초기 실행)

프로그램을 **처음** 실행하면 `data/` 폴더도, 파일도 아무것도 없습니다.
이때 프로그램이 자동으로 해주는 것들이 있습니다:

1. `data/` 폴더가 없으면 → **자동 생성** (repository.py L30)
2. `transactions.jsonl`이 없으면 → **빈 파일 자동 생성** (repository.py L33-35)
3. `categories.jsonl`이 비어있으면 → **기본 카테고리 5개 자동 등록** (repository.py L155-162)

이 부분의 **실제 코드**(repository.py)를 보면:

```python
# BaseRepository.__init__ (repository.py 24~35번째 줄)
def __init__(self, data_dir: str = "data", filename: str = ""):
    self.data_dir = data_dir
    self.filename = filename
    self.file_path = os.path.join(data_dir, filename)
    
    # ① 폴더가 없으면 만든다
    os.makedirs(self.data_dir, exist_ok=True)
    
    # ② 파일이 없으면 빈 파일을 만든다
    if not os.path.exists(self.file_path):
        with open(self.file_path, "w", encoding="utf-8") as f:
            pass  # 아무것도 안 쓰고 그냥 닫는다 = 빈 파일 생성
```

```python
# CategoryRepository._ensure_initial_categories (repository.py 155~162번째 줄)
def _ensure_initial_categories(self) -> None:
    # 카테고리 파일이 완전히 비어있으면 (크기 0바이트)
    if os.path.getsize(self.file_path) == 0:
        # 5개의 기본 카테고리를 자동으로 넣어준다
        default_categories = ["식비", "교통", "주거", "수입", "기타"]
        for cat_name in default_categories:
            self.save(Category(name=cat_name))
```

**정합성 확인 ✅**: 실제 코드와 설명이 정확히 일치합니다. `os.makedirs`에 `exist_ok=True`가 있으므로 폴더가 이미 있어도 에러 없이 넘어갑니다.

---

## 1.4 프로그램 실행 흐름 — 처음부터 끝까지

사용자가 `python -m budget_app add`를 쳤다고 합시다. 이때 프로그램 내부에서 어떤 일이 벌어지는지 **처음부터 끝까지** 추적해 봅시다.

### 1.4.1 전체 흐름도

```
사용자 입력
  │  python -m budget_app add
  ▼
[__main__.py]  ← "진입점"
  │  from budget_app.cli import run_cli
  │  run_cli()  ← 이 함수를 호출!
  ▼
[cli.py의 run_cli()]  ← "사용자와 대화"
  │  ① @handle_errors_gracefully 데코레이터가 전체를 감싼다
  │  ② BudgetService() 객체를 만든다
  │  ③ argparse로 "add"라는 명령어를 파싱한다
  │  ④ args.command == "add"이므로 대화형 입력 시작
  │  ⑤ 사용자에게 날짜, 타입, 카테고리, 금액, 메모, 태그를 물어본다
  │  ⑥ service.add_transaction(...)을 호출한다
  ▼
[service.py의 add_transaction()]  ← "비즈니스 판단"
  │  ① @log_activity() 데코레이터가 로그를 남길 준비를 한다
  │  ② 카테고리가 실제로 존재하는지 cat_repo.exists()로 검증
  │  ③ 고유 ID를 생성한다 (TX-000001 → TX-000002 → ...)
  │  ④ Transaction 객체를 만든다
  │  ⑤ tx_repo.save(tx)로 저장을 요청한다
  ▼
[repository.py의 save()]  ← "파일에 기록"
  │  ① Transaction 객체를 JSON 문자열로 변환 (to_dict → json.dumps)
  │  ② transactions.jsonl 파일 끝에 한 줄 추가 (append 모드)
  ▼
[다시 cli.py로 돌아옴]
  │  "저장 완료! ID = TX-000003" 출력
  ▼
프로그램 종료 (exit code = 0)
```

### 1.4.2 핵심 통찰: "데이터는 항상 아래로 흐르고, 결과는 위로 올라온다"

```
cli.py (사용자 입력 받음)
  │
  ├─→ service.py (판단하고 처리)
  │     │
  │     ├─→ repository.py (파일에 쓰기)
  │     │     │
  │     │     └─→ models.py (데이터 형태 정의)
  │     │
  │     └─← 결과 반환 (성공/실패, ID 등)
  │
  └─← 사용자에게 결과 출력
```

이것이 **"레이어드 아키텍처"**입니다:
- **위쪽 계층**은 아래쪽 계층을 호출할 수 있지만
- **아래쪽 계층**은 위쪽 계층의 존재를 모릅니다
- `repository.py`는 `cli.py`가 존재하는지도 모르고, 관심도 없습니다
- `models.py`는 그 누구의 존재도 모릅니다. 그저 "데이터가 이렇게 생겼다"만 정의합니다

---

## 1.5 이 단계의 핵심 정리

```
✅ 이 프로그램은 "콘솔 가계부"이다.
✅ 단순한 가계부가 아니라, "안전하고 구조적인" 가계부이다.
✅ 8개 파이썬 파일이 각자 역할을 나눠서 협력한다.
✅ 데이터는 JSONL 형식으로 data/ 폴더에 영구 저장된다.
✅ 사용자의 요청은 cli → service → repository → 파일 순으로 흘러간다.
✅ 결과는 파일 → repository → service → cli → 사용자 순으로 올라온다.
✅ 평가는 "동작 확인" + "구조 설명" + "이유 설명" + "심화 사고"로 구성된다.
```

---
---

# 📘 2단계: 파이썬 패키지 시스템과 프로그램 진입점

> **이 단계의 목표**: `python -m budget_app`이라는 명령어가 **정확히 무슨 의미인지**, 왜 `python budget_app`으로는 실행할 수 없는지, `__init__.py`와 `__main__.py`가 각각 무슨 역할을 하는지 완벽히 이해합니다.

---

## 2.1 "파이썬 패키지"란 무엇인가?

### 2.1.1 파일 vs 모듈 vs 패키지

파이썬에서는 코드를 담는 단위가 세 가지 있습니다:

```
파일(File)     → 물리적인 .py 파일 하나
모듈(Module)   → 파이썬이 import할 수 있는 .py 파일 하나
패키지(Package) → 여러 모듈을 묶은 폴더 (반드시 __init__.py 포함)
```

비유하면:
- **파일** = 종이 한 장
- **모듈** = 한 챕터가 적힌 종이 한 장 (다른 챕터에서 참조 가능)
- **패키지** = 여러 챕터를 묶은 책 한 권

### 2.1.2 우리 프로그램의 패키지 구조

```
budget_app/              ← 이 폴더 자체가 "패키지"
├── __init__.py          ← "이 폴더는 패키지입니다" 증명서
├── __main__.py          ← "이 패키지를 직접 실행하면 여기부터 시작"
├── cli.py               ← 모듈 1
├── service.py           ← 모듈 2
├── repository.py        ← 모듈 3
├── models.py            ← 모듈 4
├── decorators.py        ← 모듈 5
└── utils.py             ← 모듈 6
```

`budget_app` 폴더 안에 `__init__.py`가 있으므로, 파이썬은 이 폴더를 "아, 이건 그냥 폴더가 아니라 파이썬 패키지구나!"라고 인식합니다.

---

## 2.2 `__init__.py` — 패키지의 신분증

### 2.2.1 실제 코드 (전문)

우리 프로그램의 `__init__.py`는 매우 간결합니다:

```python
# budget_app/__init__.py (전체 9줄)

"""
__init__.py
이 파일은 budget_app 디렉토리가 파이썬 '패키지(Package)'임을 알리는 역할을 합니다.
동시에 패키지가 처음 로드될 때 필요한 초기화 설정이나 간단한 버전을 명시할 수 있습니다.
"""

__version__ = "1.0.0"
__author__ = "Antigravity Pair Programmer"
```

### 2.2.2 이 파일이 하는 일

1. **존재 자체가 의미**: 이 파일이 `budget_app/` 폴더 안에 있다는 것만으로 파이썬은 "이 폴더는 패키지다"라고 인식합니다
2. **버전 정보 저장**: `__version__`과 `__author__` 변수로 패키지의 메타 정보를 기록합니다
3. **초기화 코드 실행**: 패키지가 처음 임포트될 때 이 파일의 코드가 실행됩니다 (여기서는 변수 대입뿐)

### 2.2.3 만약 `__init__.py`가 없다면?

```python
# 이 import가 실패합니다!
from budget_app.models import Transaction
#  → ModuleNotFoundError: No module named 'budget_app'
```

파이썬이 `budget_app`을 "그냥 폴더"로 취급하기 때문에 패키지로서의 임포트가 불가능해집니다.

> **참고**: Python 3.3 이후에는 `__init__.py` 없이도 "네임스페이스 패키지"로 동작하는 경우가 있지만, 명시적으로 두는 것이 표준이며 우리 프로그램도 이 표준을 따릅니다.

---

## 2.3 `__main__.py` — 프로그램의 정문

### 2.3.1 실제 코드 (전문)

```python
# budget_app/__main__.py (전체 13줄)

"""
__main__.py
이 모듈은 가계부 애플리케이션의 '실행 진입점(Entry Point)'입니다.
터미널에서 `python -m budget_app` 명령을 입력하면,
파이썬 엔진이 패키지 내부에서 이 __main__.py 파일을 찾아 가장 먼저 실행하게 됩니다.
"""

from budget_app.cli import run_cli

if __name__ == "__main__":
    # cli.py 모듈에 작성해 둔 run_cli 함수를 기동하여 가계부 콘솔 프로그램을 시작합니다.
    run_cli()
```

### 2.3.2 한 줄씩 완벽 해부

#### 줄 8: `from budget_app.cli import run_cli`

```python
from budget_app.cli import run_cli
```

이 한 줄의 의미를 풀면:

```
from budget_app.cli  →  budget_app 패키지 안의 cli.py 모듈에서
import run_cli       →  run_cli라는 이름(함수)을 가져와라
```

**왜 `from cli import run_cli`가 아닌가요?**

이것은 **상대 경로 vs 절대 경로** 문제입니다:
- `from cli import run_cli` → "cli.py가 어디 있는지 모르겠는데?" (에러 발생 가능)
- `from budget_app.cli import run_cli` → "budget_app 패키지 안의 cli.py에서!" (명확!)

`-m` 옵션으로 실행하면 파이썬이 `budget_app`을 패키지로 인식하기 때문에 이 절대 경로 임포트가 정상 작동합니다.

#### 줄 10-12: `if __name__ == "__main__":`

```python
if __name__ == "__main__":
    run_cli()
```

이것은 파이썬의 **가장 유명한 관용구(idiom)** 중 하나입니다.

**`__name__`이란?**

모든 파이썬 파일은 실행될 때 `__name__`이라는 특수 변수를 자동으로 갖습니다:
- 파일이 **직접 실행**되면 → `__name__`의 값은 `"__main__"`
- 파일이 **다른 파일에서 임포트**되면 → `__name__`의 값은 `"budget_app.__main__"`

따라서 이 조건문의 의미는:
```
"이 파일이 직접 실행되었을 때만 run_cli()를 호출해라"
"다른 파일이 이 파일을 import하는 경우에는 run_cli()를 호출하지 마라"
```

### 2.3.3 `__main__.py`가 없다면?

```bash
$ python -m budget_app add
# → 에러: No module named budget_app.__main__; 
#         'budget_app' is a package and cannot be directly executed
```

패키지를 실행하려면 "어디서부터 시작할지" 알려주는 `__main__.py`가 반드시 필요합니다.

---

## 2.4 `-m` 옵션의 비밀 — 왜 반드시 이렇게 실행해야 하는가?

### 2.4.1 두 가지 실행 방법 비교

```bash
# 방법 A: 직접 실행 (❌ 문제 발생!)
$ python budget_app/__main__.py add

# 방법 B: -m 모듈 모드 실행 (✅ 정상 동작!)
$ python -m budget_app add
```

### 2.4.2 방법 A가 실패하는 이유

방법 A로 실행하면 파이썬은 이렇게 동작합니다:

```
1. budget_app/__main__.py 파일을 "독립적인 스크립트"로 취급
2. sys.path[0]에 budget_app/ 디렉토리를 등록
3. __main__.py 안의 코드를 실행
4. "from budget_app.cli import run_cli" 실행
5. 💥 에러! "budget_app"이라는 패키지를 찾을 수 없음
```

왜 못 찾을까요? `sys.path[0]`이 `budget_app/` 폴더로 설정되었기 때문에, 파이썬은 `budget_app/budget_app/cli.py`를 찾으려고 합니다. 당연히 그런 경로는 없습니다!

### 2.4.3 방법 B가 성공하는 이유

방법 B로 실행하면 파이썬은 이렇게 동작합니다:

```
1. "budget_app"을 패키지로 인식
2. sys.path[0]에 현재 디렉토리(glad/)를 등록
3. budget_app/__init__.py를 먼저 실행 (패키지 초기화)
4. budget_app/__main__.py를 실행
5. "from budget_app.cli import run_cli" 실행
6. ✅ glad/budget_app/cli.py를 정확히 찾음!
```

### 2.4.4 그림으로 비교

```
[방법 A: python budget_app/__main__.py]
sys.path[0] = glad/budget_app/
찾는 경로:    glad/budget_app/budget_app/cli.py  ← 이런 경로 없음! ❌

[방법 B: python -m budget_app]
sys.path[0] = glad/
찾는 경로:    glad/budget_app/cli.py             ← 정확히 존재! ✅
```

### 2.4.5 실행 명령어의 전체 구조

```bash
python -m budget_app add --옵션들
│      │  │           │   │
│      │  │           │   └─ 선택적 옵션 (--limit, --id 등)
│      │  │           └─ 서브커맨드 (add, list, search, ...)
│      │  └─ 패키지 이름 (budget_app 폴더)
│      └─ "모듈 모드로 실행" 플래그
└─ 파이썬 인터프리터
```

---

## 2.5 프로그램 시작 순서 — 코드 레벨에서의 완전한 추적

`python -m budget_app add`를 치는 순간부터 코드가 실행되는 정확한 순서:

```
[시스템]
① 파이썬 인터프리터가 기동됨
② sys.path에 현재 디렉토리(glad/)가 추가됨
③ budget_app 패키지를 찾음

[__init__.py 실행]  (budget_app/__init__.py)
④ __version__ = "1.0.0" 변수 설정
⑤ __author__ = "Antigravity Pair Programmer" 변수 설정

[__main__.py 실행]  (budget_app/__main__.py)
⑥ from budget_app.cli import run_cli 
   → cli.py 모듈이 로드됨
   → cli.py 안의 import들도 연쇄적으로 실행:
     → from budget_app.models import Transaction
     → from budget_app.service import BudgetService
       → service.py 안의 import들도 연쇄적으로 실행:
         → from budget_app.repository import TransactionRepository, ...
           → repository.py 안의 import들도 실행:
             → from budget_app.models import Transaction, Category, ...
     → from budget_app.utils import validate_date, ...
     → from budget_app.decorators import handle_errors_gracefully
⑦ if __name__ == "__main__": → True (직접 실행이므로)
⑧ run_cli() 호출!

[cli.py의 run_cli() 실행]
⑨ @handle_errors_gracefully 데코레이터가 먼저 작동
   → try: 블록 안에서 run_cli의 본문 코드가 실행됨
⑩ service = BudgetService() 
   → BudgetService.__init__ 실행
   → 내부에서 4개의 Repository 객체 생성
   → 각 Repository의 __init__에서:
     → data/ 폴더 존재 확인/생성
     → .jsonl 파일 존재 확인/생성
     → CategoryRepository는 추가로 기본 카테고리 확인/생성
⑪ parser = argparse.ArgumentParser(...) 
   → 명령어 파서 설정 시작
⑫ args = parser.parse_args()
   → 사용자가 입력한 "add"를 파싱
   → args.command = "add"
⑬ if args.command == "add": → True!
   → 대화형 입력 시작...
```

### 2.5.1 연쇄 임포트(Chain Import)의 핵심

위 순서에서 ⑥번이 가장 복잡합니다. `from budget_app.cli import run_cli` 한 줄만 실행해도, 파이썬은 cli.py → service.py → repository.py → models.py 순서로 줄줄이 모듈을 불러옵니다.

이것은 마치 **도미노**와 같습니다:

```
cli.py를 로드하려면
  → cli.py가 import하는 service.py를 먼저 로드해야 하고
    → service.py가 import하는 repository.py를 먼저 로드해야 하고
      → repository.py가 import하는 models.py를 먼저 로드해야 한다
```

하지만 이 모든 과정은 **파이썬이 자동으로** 처리합니다. 우리가 신경 쓸 필요는 없습니다.

---

## 2.6 이 단계의 핵심 정리

```
✅ budget_app/ 폴더는 "파이썬 패키지"이다 (__init__.py가 증명)
✅ __init__.py는 패키지의 신분증이자 초기화 파일이다
✅ __main__.py는 패키지를 직접 실행할 때의 진입점이다
✅ python -m budget_app은 "budget_app 패키지를 모듈 모드로 실행"한다는 뜻이다
✅ -m 없이 실행하면 sys.path 문제로 import가 깨진다
✅ __name__ == "__main__"은 "직접 실행일 때만 동작"하는 조건문이다
✅ 하나의 import 문이 연쇄적으로 여러 모듈을 불러올 수 있다 (도미노)
```

### 2.6.1 다른 사람에게 설명하는 연습

> **질문**: "왜 `python -m budget_app`으로 실행해야 하나요?"
>
> **답변 예시**: "budget_app은 폴더(패키지)이기 때문에, `-m` 옵션을 붙여야 파이썬이 이 폴더를 패키지로 인식하고, 현재 디렉토리를 기준으로 import 경로를 잡아줍니다. `-m` 없이 실행하면 파이썬이 경로를 잘못 잡아서 `from budget_app.cli import run_cli` 같은 import가 깨집니다. `-m`을 붙이면 파이썬은 먼저 `__init__.py`로 패키지를 초기화하고, `__main__.py`에서 프로그램을 시작합니다."

---
---

# 📘 3단계: 데이터 모델(models.py) — dataclass와 직렬화

> **이 단계의 목표**: 프로그램이 다루는 데이터가 **어떤 형태(Shape)**인지, 왜 `dataclass`를 쓰는지, `to_dict()`와 `from_dict()`가 왜 필요한지, 타입 힌트가 무엇이고 왜 중요한지 완벽히 이해합니다.

---

## 3.1 "데이터 모델"이란 무엇인가?

### 3.1.1 일상생활 비유

은행에서 "계좌 개설 신청서"를 작성한다고 생각해 봅시다:

```
┌─────────────────────────────────┐
│     계좌 개설 신청서             │
│                                  │
│  이름: _______________           │
│  주민번호: _______________       │
│  전화번호: _______________       │
│  주소: _______________           │
│  개설 유형: □ 보통예금  □ 적금   │
└─────────────────────────────────┘
```

이 신청서 양식 자체가 **"모델(Model)"**입니다. 양식은 다음을 정의합니다:

1. **어떤 정보가 필요한지** (이름, 주민번호, ...)
2. **각 정보의 형태는 무엇인지** (이름=문자열, 주민번호=숫자 등)
3. **필수 항목과 선택 항목** (이름=필수, 전화번호=선택)

우리 프로그램도 똑같습니다. "거래 내역"이라는 데이터가 어떤 형태여야 하는지를 `models.py`에서 정의합니다.

### 3.1.2 왜 모델을 따로 정의해야 하는가?

모델 없이 코드를 짜면 이런 일이 벌어집니다:

```python
# ❌ 모델 없이 딕셔너리로 막 쓰는 경우
transaction = {
    "id": "TX-001",
    "amount": 15000,
    # "date"는 넣었나? 까먹었는데?
    # "category"의 키 이름이 "cat"이었나 "category"였나?
    # "amount"가 문자열이었나 숫자였나?
}
```

모델이 있으면:
```python
# ✅ 모델이 있으면 정확히 무엇이 필요한지 명확
tx = Transaction(
    id="TX-001",
    type="expense",
    date="2026-05-25",
    amount=15000,
    category="식비",
    memo="점심",       # 선택 (기본값 "")
    tags=["외식"]      # 선택 (기본값 [])
)
```

---

## 3.2 `@dataclass`란 무엇인가?

### 3.2.1 일반 클래스 vs dataclass

파이썬에서 데이터를 담는 클래스를 만드는 방법은 두 가지입니다:

#### 방법 1: 일반 클래스 (장황하고 반복적)

```python
class Transaction:
    def __init__(self, id, type, date, amount, category, memo="", tags=None):
        self.id = id
        self.type = type
        self.date = date
        self.amount = amount
        self.category = category
        self.memo = memo
        self.tags = tags if tags is not None else []
    
    def __repr__(self):
        return f"Transaction(id={self.id}, type={self.type}, ...)"
    
    def __eq__(self, other):
        return (self.id == other.id and self.type == other.type 
                and self.date == other.date and ...)
```

→ 필드가 7개인데 `__init__`에서 7줄, `__repr__`에서 또 7줄... 반복 지옥!

#### 방법 2: dataclass (깔끔하고 자동)

```python
from dataclasses import dataclass, field
from typing import List

@dataclass
class Transaction:
    id: str
    type: str
    date: str
    amount: int
    category: str
    memo: str = ""
    tags: List[str] = field(default_factory=list)
```

→ 끝! `__init__`, `__repr__`, `__eq__` 등이 **자동으로 생성**됩니다!

### 3.2.2 `@dataclass`가 자동으로 해주는 것들

`@dataclass` 데코레이터를 붙이면 파이썬이 자동으로 만들어주는 메소드:

```
1. __init__()  → Transaction(id="TX-001", type="expense", ...) 으로 객체 생성 가능
2. __repr__()  → print(tx) 했을 때 보기 좋게 출력됨
3. __eq__()    → tx1 == tx2로 두 객체가 같은지 비교 가능
```

직접 쓴 것처럼 동작하지만, 코드량은 1/3 이하입니다!

---

## 3.3 Transaction 클래스 — 코드 완전 해부

### 3.3.1 실제 코드 (models.py 12~52번째 줄)

```python
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
```

### 3.3.2 필드별 완전 해설

#### `id: str` — 거래 고유 식별자

```python
id: str    # 예: "TX-000001", "TX-000002", ...
```

- **역할**: 모든 거래를 **유일하게 구분**하는 번호표
- **형식**: `"TX-"` + 6자리 숫자 (예: TX-000001)
- **왜 필요한가?**: "TX-000003번 거래를 삭제해줘"처럼 **특정 거래를 지목**할 때 사용
- **누가 만드는가?**: `service.py`의 `_generate_new_id()` 함수가 자동 발급

```python
# service.py 41~56번째 줄 — ID 자동 발급 로직
def _generate_new_id(self) -> str:
    max_num = 0
    for tx in self.tx_repo.find_all_stream():    # 모든 거래를 읽으면서
        if tx.id.startswith("TX-"):              # TX-로 시작하는 ID를 찾아
            try:
                num = int(tx.id.split("-")[1])    # 숫자 부분만 추출
                if num > max_num:                 # 가장 큰 숫자를 기억
                    max_num = num
            except (ValueError, IndexError):
                pass
    return f"TX-{max_num + 1:06d}"               # 가장 큰 숫자 + 1로 새 ID
```

**동작 예시**:
```
현재 거래: TX-000001, TX-000002, TX-000003
→ max_num = 3
→ 새 ID = TX-000004
```

#### `type: str` — 거래 종류

```python
type: str    # "income" (수입) 또는 "expense" (지출)
```

- 반드시 `"income"` 또는 `"expense"` 중 하나여야 합니다
- 입력 검증은 `utils.py`의 `validate_type()` 함수가 담당합니다

```python
# utils.py 149~157번째 줄
def validate_type(type_str: str) -> str:
    clean_type = type_str.strip().lower()              # 공백 제거 + 소문자 변환
    if clean_type not in ("income", "expense"):        # 허용된 값이 아니면
        raise ValueError(f"거래 타입 '{type_str}'은(는) 허용되지 않습니다. ...")
    return clean_type                                   # 소문자로 정규화해서 반환
```

**정합성 확인 ✅**: `validate_type`은 `strip().lower()`로 처리하므로 `" Income "`을 넣어도 `"income"`으로 정리됩니다.

#### `date: str` — 거래 일자

```python
date: str    # "2026-05-25" 형식 (YYYY-MM-DD)
```

- **왜 `str`이지 `datetime`이 아닌가?**: JSONL 파일에 바로 쓸 수 있도록 문자열로 관리합니다. 날짜 비교(`"2026-05-10" < "2026-05-20"`)는 문자열 비교만으로도 정확히 동작합니다 (YYYY-MM-DD 형식의 특성)
- **입력 검증**: `utils.py`의 `validate_date()` 함수가 "2026-13-40" 같은 불가능한 날짜를 차단합니다

```python
# utils.py 122~132번째 줄
def validate_date(date_str: str) -> str:
    try:
        parsed_date = datetime.strptime(date_str, "%Y-%m-%d")  # 파싱 시도
        return parsed_date.strftime("%Y-%m-%d")                 # 정규화된 형태로 반환
    except ValueError:
        raise ValueError(f"날짜 '{date_str}'는 올바른 날짜 형식이 아니거나 ...")
```

**`strptime`이 하는 일**: "2026-02-30"처럼 실제로 존재하지 않는 날짜를 넣으면 `ValueError`가 발생합니다. 단순한 정규식보다 훨씬 정확합니다.

#### `amount: int` — 금액

```python
amount: int    # 반드시 0보다 큰 양수 정수 (예: 15000)
```

- **왜 `int`인가?**: 원(₩) 단위로 관리하므로 소수점이 필요 없습니다
- **왜 항상 양수인가?**: 수입/지출의 구분은 `type` 필드가 담당합니다. 금액 자체는 항상 양수입니다

```python
# utils.py 135~146번째 줄
def validate_amount(amount_str: str) -> int:
    try:
        amount = int(amount_str)      # 문자열을 정수로 변환 시도
        if amount <= 0:               # 0 이하면 거부
            raise ValueError()
        return amount
    except ValueError:
        raise ValueError(f"금액 '{amount_str}'은(는) 0보다 큰 양의 정수여야 합니다. ...")
```

#### `category: str` — 카테고리

```python
category: str    # 예: "식비", "교통", "주거", "수입", "기타"
```

- 반드시 `categories.jsonl`에 **미리 등록된** 카테고리여야 합니다
- 등록되지 않은 카테고리를 쓰면 `service.py`에서 거부합니다

#### `memo: str = ""` — 메모 (선택)

```python
memo: str = ""    # 기본값: 빈 문자열 (안 적어도 됨)
```

- `= ""`는 **기본값(default value)**입니다
- 거래를 만들 때 memo를 안 주면 자동으로 빈 문자열이 들어갑니다:
  ```python
  tx = Transaction(id="TX-001", type="expense", date="2026-05-25",
                   amount=15000, category="식비")
  # → tx.memo는 "" (빈 문자열)
  ```

#### `tags: List[str] = field(default_factory=list)` — 태그 목록 (선택)

```python
tags: List[str] = field(default_factory=list)    # 기본값: 빈 리스트 []
```

이 부분이 초심자에게 **가장 헷갈리는** 부분입니다. 차근차근 설명합니다:

**왜 `tags: List[str] = []`가 아닌가?**

파이썬에는 **"가변 기본값의 함정(Mutable Default Argument Trap)"**이라는 유명한 버그가 있습니다:

```python
# ❌ 위험한 코드
@dataclass
class Transaction:
    tags: List[str] = []    # 이러면 모든 Transaction이 같은 리스트를 공유!

tx1 = Transaction(...)
tx2 = Transaction(...)
tx1.tags.append("음식")
print(tx2.tags)  # → ["음식"] ← tx2에도 영향이?! 버그!
```

`field(default_factory=list)`는 "새 Transaction을 만들 때마다 **새로운 빈 리스트**를 만들어라"라는 뜻입니다:

```python
# ✅ 안전한 코드
@dataclass
class Transaction:
    tags: List[str] = field(default_factory=list)    # 매번 새 리스트 생성

tx1 = Transaction(...)
tx2 = Transaction(...)
tx1.tags.append("음식")
print(tx2.tags)  # → [] ← tx2는 영향 없음! 안전!
```

---

## 3.4 직렬화(Serialization) — `to_dict()`와 `from_dict()`

### 3.4.1 직렬화란?

**직렬화(Serialization)**: 프로그램 내부의 객체(Object)를 → 저장/전송 가능한 형태로 변환
**역직렬화(Deserialization)**: 저장/전송된 데이터를 → 다시 프로그램 내부 객체로 복원

비유하면:
- **직렬화** = 3D 입체 레고 조립물을 → 설명서(2D 텍스트)로 변환
- **역직렬화** = 설명서를 보고 → 다시 3D 레고를 조립

### 3.4.2 우리 프로그램의 직렬화 흐름

```
Transaction 객체 (메모리 안)
     │
     │ to_dict()         ← 직렬화 1단계: 객체 → 딕셔너리
     ▼
Python dict
     │
     │ json.dumps()      ← 직렬화 2단계: 딕셔너리 → JSON 문자열
     ▼
JSON 문자열 (파일에 쓸 수 있음)
     │
     │ 파일에 쓰기       ← 저장
     ▼
transactions.jsonl 파일
```

읽을 때는 정확히 **역순**:

```
transactions.jsonl 파일
     │
     │ 파일에서 한 줄 읽기   ← 로딩
     ▼
JSON 문자열
     │
     │ json.loads()          ← 역직렬화 1단계: JSON 문자열 → 딕셔너리
     ▼
Python dict
     │
     │ from_dict()           ← 역직렬화 2단계: 딕셔너리 → 객체
     ▼
Transaction 객체 (메모리 안)
```

### 3.4.3 `to_dict()` 실제 코드

```python
# models.py 25~37번째 줄
def to_dict(self) -> dict:
    """
    데이터 저장 및 가공을 위해 객체를 파이썬 기본 딕셔너리 형식으로 변환합니다.
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
```

**실행 예시**:
```python
tx = Transaction(id="TX-000001", type="expense", date="2026-05-25",
                 amount=15000, category="식비", memo="점심", tags=["외식"])
                 
print(tx.to_dict())
# → {"id": "TX-000001", "type": "expense", "date": "2026-05-25",
#     "amount": 15000, "category": "식비", "memo": "점심", "tags": ["외식"]}
```

### 3.4.4 `from_dict()` 실제 코드

```python
# models.py 39~52번째 줄
@classmethod
def from_dict(cls, data: dict) -> "Transaction":
    """
    저장 파일에서 읽어온 딕셔너리를 활용해 Transaction 객체를 새로 생성합니다.
    """
    return cls(
        id=data["id"],
        type=data["type"],
        date=data["date"],
        amount=int(data["amount"]),      # ← 혹시 문자열로 저장됐을 수도 있으니 int 변환
        category=data["category"],
        memo=data.get("memo", ""),       # ← "memo" 키가 없으면 기본값 "" 사용
        tags=data.get("tags", [])        # ← "tags" 키가 없으면 기본값 [] 사용
    )
```

#### `@classmethod`란?

```python
@classmethod
def from_dict(cls, data: dict) -> "Transaction":
```

- 일반 메소드: `self`(이미 만들어진 객체)를 첫 인자로 받음
- 클래스 메소드: `cls`(클래스 자체)를 첫 인자로 받음

`from_dict`는 **이미 있는 객체를 수정하는 게 아니라**, 딕셔너리로부터 **새 객체를 만드는** 역할이므로 클래스 메소드가 적합합니다.

```python
# cls는 Transaction 클래스 자체
# cls(...)는 Transaction(...)과 동일
```

사용법:
```python
data = {"id": "TX-000001", "type": "expense", "date": "2026-05-25",
        "amount": 15000, "category": "식비"}

tx = Transaction.from_dict(data)    # ← 클래스 이름으로 직접 호출
print(tx.id)      # → "TX-000001"
print(tx.amount)  # → 15000
print(tx.memo)    # → "" (키가 없어서 기본값 적용)
print(tx.tags)    # → [] (키가 없어서 기본값 적용)
```

#### `data.get("memo", "")` vs `data["memo"]`

```python
# data.get("키이름", 기본값)
data.get("memo", "")     # "memo" 키가 없으면 "" 반환 (에러 안 남)
data["memo"]              # "memo" 키가 없으면 KeyError 에러 발생!
```

`get()`을 쓰는 이유: 초기 버전의 JSONL 파일에 `memo`나 `tags` 필드가 없을 수 있기 때문입니다. 이런 **방어적 프로그래밍**은 실무에서 매우 중요합니다.

---

## 3.5 나머지 3개 모델 클래스

### 3.5.1 Category — 카테고리 (models.py 55~67번째 줄)

```python
@dataclass
class Category:
    """
    거래에 할당될 수 있는 카테고리(분류)를 정의하는 클래스입니다.
    """
    name: str    # 카테고리명 (예: 식비, 교통, 주거, 수입, 기타 등)

    def to_dict(self) -> dict:
        return {"name": self.name}

    @classmethod
    def from_dict(cls, data: dict) -> "Category":
        return cls(name=data["name"])
```

**가장 단순한 모델**입니다. 필드가 `name` 하나뿐입니다.

저장되는 형태:
```json
{"name": "식비"}
{"name": "교통"}
```

### 3.5.2 Budget — 월별 예산 (models.py 70~89번째 줄)

```python
@dataclass
class Budget:
    """
    특정 월의 한도 예산을 정의하는 클래스입니다.
    """
    month: str     # 대상 년월 (형식: YYYY-MM), 예: "2026-05"
    amount: int    # 예산 설정 금액 (양수 정수), 예: 1000000

    def to_dict(self) -> dict:
        return {
            "month": self.month,
            "amount": self.amount
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Budget":
        return cls(
            month=data["month"],
            amount=int(data["amount"])    # ← int() 변환으로 안전하게
        )
```

저장되는 형태:
```json
{"month": "2026-05", "amount": 1000000}
```

**Budget이 하는 일**: "2026년 5월에는 100만원까지만 쓰겠다"를 기록합니다. `summary` 명령어에서 이 예산과 실제 지출을 비교하여 사용률과 초과 경고를 보여줍니다.

### 3.5.3 RecurringRule — 반복 거래 규칙 (models.py 92~127번째 줄)

```python
@dataclass
class RecurringRule:
    """
    [보너스 과제 5.2]
    매달 고정적으로 발생하는 반복 거래의 생성 규칙을 정의합니다.
    """
    id: str                  # 반복 규칙 고유 ID (예: REC-000001)
    day_of_month: int        # 매달 며칠에 발생할 것인지 (1~31)
    type: str                # 거래 종류 ('income' 또는 'expense')
    amount: int              # 반복 발생할 금액
    category: str            # 카테고리 이름
    memo: str = ""           # 자동 입력될 메모
    tags: List[str] = field(default_factory=list)  # 자동 입력될 태그 목록
```

**RecurringRule이 하는 일**: "매달 25일에 월급 250만원이 들어온다"를 규칙으로 등록해두면, `recurring generate --month 2026-05` 명령어로 해당 월의 거래를 자동 생성합니다.

저장되는 형태:
```json
{"id": "REC-000001", "day_of_month": 25, "type": "income", "amount": 2500000, "category": "수입", "memo": "월급", "tags": ["급여", "고정"]}
```

---

## 3.6 타입 힌트(Type Hints) — 코드의 계약서

### 3.6.1 타입 힌트란?

```python
# 타입 힌트 없는 코드
def add_transaction(self, date, type_str, category, amount, memo, tags):
    # date가 문자열인지 datetime인지? amount가 int인지 float인지?
    # 전혀 알 수 없음! 코드를 전부 읽어봐야 파악 가능!
    pass

# 타입 힌트 있는 코드
def add_transaction(self, date: str, type_str: str, category: str, 
                    amount: int, memo: str = "", 
                    tags: List[str] = None) -> str:
    # date는 문자열, amount는 정수, 반환값은 문자열(ID)
    # 한눈에 파악 가능!
    pass
```

### 3.6.2 타입 힌트의 3가지 이점

#### 이점 1: 문서 역할 — "이 함수가 뭘 받고 뭘 돌려주는지" 즉시 파악

```python
# service.py의 실제 코드
def search_transactions(
    self,
    from_date: Optional[str] = None,    # 시작일 (없을 수도 있음)
    to_date: Optional[str] = None,      # 종료일 (없을 수도 있음)
    category: Optional[str] = None,     # 카테고리 (없을 수도 있음)
    type_str: Optional[str] = None,     # 타입 (없을 수도 있음)
    keyword: Optional[str] = None,      # 키워드 (없을 수도 있음)
    tag: Optional[str] = None           # 태그 (없을 수도 있음)
) -> Generator[Transaction, None, None]:  # Transaction을 하나씩 yield하는 제너레이터 반환
```

이 선언만 봐도 알 수 있는 것들:
1. 모든 검색 조건은 **선택적(Optional)**이다
2. 검색 조건은 **문자열(str)**로 전달한다
3. 반환값은 **Transaction 객체들의 제너레이터**이다

#### 이점 2: IDE 자동완성 — 코딩 속도 2배

타입 힌트가 있으면 IDE(예: VS Code, PyCharm)가:
- `tx.` 찍으면 → `id`, `type`, `date`, `amount`, `category`, `memo`, `tags` 자동 제안
- 잘못된 타입을 넣으면 → 빨간 줄로 경고

#### 이점 3: 정적 분석 — 배포 전 버그 발견

```bash
# mypy를 사용한 타입 체크
$ mypy budget_app/
# → service.py:102: error: Argument 1 has incompatible type "int"; expected "str"
```

코드를 실행하기 전에도 타입 불일치 버그를 잡아낼 수 있습니다.

### 3.6.3 자주 쓰이는 타입 힌트 해석표

우리 프로그램에서 자주 등장하는 타입 힌트들의 의미:

```python
str                          # 문자열
int                          # 정수
bool                         # 참/거짓
dict                         # 딕셔너리

List[str]                    # 문자열들의 리스트, 예: ["식비", "교통"]
List[Category]               # Category 객체들의 리스트

Optional[str]                # str 또는 None (값이 없을 수도 있음)
Optional[int]                # int 또는 None

Tuple[bool, str]             # (참/거짓, 문자열) 쌍, 예: (True, "성공")
Tuple[int, int, List[str]]   # (정수, 정수, 문자열리스트) 세쌍둥이

Dict[str, Any]               # 키가 문자열이고 값이 아무거나인 딕셔너리

Generator[Transaction, None, None]  
# Transaction을 하나씩 yield하는 제너레이터
# [yield 타입, send 타입, return 타입]

Callable[..., Any]           # 호출 가능한 것 (함수, 메소드)
```

---

## 3.7 4개 모델의 관계도

```
┌─────────────────────────┐
│     Transaction         │ ← 거래 내역 (핵심)
│  id, type, date,        │
│  amount, category,      │
│  memo, tags             │
│                         │
│  category ──참조──┐     │
└─────────────────────┼───┘
                      │
                      ▼
┌─────────────────────────┐
│     Category            │ ← 카테고리 사전
│  name                   │
└─────────────────────────┘

┌─────────────────────────┐
│     Budget              │ ← 월별 예산
│  month, amount          │
│                         │
│  summary 명령어에서     │
│  Transaction의 지출     │
│  합계와 비교하여        │
│  사용률을 계산함         │
└─────────────────────────┘

┌─────────────────────────┐
│     RecurringRule        │ ← 반복 거래 규칙 (보너스)
│  id, day_of_month,      │
│  type, amount, category,│
│  memo, tags             │
│                         │
│  generate 시            │
│  Transaction을 자동 생성 │
└─────────────────────────┘
```

**관계 설명**:
- Transaction의 `category` 필드 값은 반드시 Category에 등록된 `name` 중 하나여야 합니다
- Budget의 `month`와 Transaction의 `date`(앞 7글자)를 비교하여 예산 분석을 합니다
- RecurringRule의 규칙에 따라 Transaction이 자동 생성될 수 있습니다

---

## 3.8 models.py가 다른 모듈에서 어떻게 사용되는가?

### 3.8.1 repository.py에서의 사용

```python
# repository.py — 파일에서 읽어올 때
data_dict = json.loads(stripped_line)           # JSON 문자열 → 딕셔너리
yield Transaction.from_dict(data_dict)          # 딕셔너리 → Transaction 객체

# repository.py — 파일에 저장할 때
json_line = json.dumps(transaction.to_dict(), ensure_ascii=False)  # 객체 → 딕셔너리 → JSON 문자열
f.write(json_line + "\n")                       # JSON 문자열 → 파일에 쓰기
```

### 3.8.2 service.py에서의 사용

```python
# service.py — 새 거래 생성할 때
tx = Transaction(                               # Transaction 객체 직접 생성
    id=tx_id,
    type=type_str,
    date=date,
    amount=amount,
    category=category,
    memo=memo,
    tags=tags
)
self.tx_repo.save(tx)                           # 저장소에 저장 요청
```

### 3.8.3 cli.py에서의 사용

```python
# cli.py — 거래 목록을 표로 출력할 때
for tx in tx_generator:                          # 제너레이터로부터 하나씩 받음
    rows.append([
        tx.id,                                   # Transaction 객체의 필드에 접근
        tx.date,
        "수입" if tx.type == "income" else "지출",
        tx.category,
        f"{tx.amount:,}원",                      # 천단위 쉼표 포맷
        tx.memo,
        ", ".join(tx.tags)                       # 리스트 → 쉼표 구분 문자열
    ])
```

---

## 3.9 이 단계의 핵심 정리

```
✅ models.py는 데이터의 "양식(Form)"을 정의하는 곳이다
✅ @dataclass는 __init__, __repr__ 등을 자동 생성해주는 편리한 도구이다
✅ Transaction은 7개 필드(id, type, date, amount, category, memo, tags)를 가진다
✅ to_dict()는 객체→딕셔너리 변환(직렬화), from_dict()는 딕셔너리→객체 변환(역직렬화)
✅ field(default_factory=list)는 "가변 기본값의 함정"을 방지하는 안전장치이다
✅ 타입 힌트는 문서 역할 + IDE 자동완성 + 정적 분석 세 가지 이점을 제공한다
✅ Optional[str]은 "str 또는 None", List[str]은 "문자열 리스트"를 의미한다
✅ 4개 모델(Transaction, Category, Budget, RecurringRule) 모두 동일한 to_dict/from_dict 패턴을 따른다
```

### 3.9.1 다른 사람에게 설명하는 연습

> **질문**: "Transaction 클래스의 to_dict()와 from_dict()는 왜 필요한가요?"
>
> **답변 예시**: "프로그램이 돌아가는 동안 거래 데이터는 Transaction 객체(파이썬 메모리 안의 형태)로 존재합니다. 하지만 파일에 저장하려면 JSON 문자열로 변환해야 합니다. to_dict()는 객체를 딕셔너리로 바꿔주는 중간 단계이고, json.dumps()와 합쳐져서 파일에 쓸 수 있는 문자열이 됩니다. from_dict()는 그 반대로, 파일에서 읽어온 딕셔너리를 다시 Transaction 객체로 복원합니다. 이 과정을 직렬화/역직렬화라고 부릅니다."

> **질문**: "field(default_factory=list)를 왜 쓰나요? 그냥 `tags = []` 하면 안 되나요?"
>
> **답변 예시**: "파이썬에서 기본값으로 리스트 같은 '변경 가능한(mutable)' 객체를 직접 쓰면, 모든 인스턴스가 같은 리스트 객체를 공유하는 버그가 발생합니다. field(default_factory=list)를 쓰면 새 객체를 만들 때마다 독립적인 빈 리스트가 생성되어 이 문제를 방지합니다."

---
---

# 📘 4단계: 저장소 계층(repository.py) — 파일 I/O의 모든 것

> **이 단계의 목표**: repository.py가 **어떻게 데이터를 파일에 저장(Save)하고 읽어오는지(Load)**, 클래스 상속이 왜 쓰였는지, 파일을 여는 모드(`"w"`, `"a"`, `"r"`)의 차이를 완벽히 이해합니다.

---

## 4.1 Repository(저장소)란 무엇인가?

### 4.1.1 일상생활 비유

도서관을 떠올려 봅시다:

```
┌───────────────────────────────────────────┐
│  📚 도서관                                 │
│                                            │
│  사서(Librarian) = Repository               │
│                                            │
│  사서가 하는 일:                             │
│  ① 새 책을 서가에 꽂는다        → save()    │
│  ② 책 한 권씩 넘겨보며 찾는다   → find_all_stream() │
│  ③ 모든 책을 한꺼번에 테이블로   → find_all() │
│  ④ 특정 책의 내용을 교체한다    → update()   │
│  ⑤ 특정 책을 서가에서 빼낸다    → delete()   │
│                                            │
│  서가(Bookshelf) = .jsonl 파일              │
│  책 한 권 = JSON 한 줄                      │
└───────────────────────────────────────────┘
```

Repository는 **사서**입니다. 비즈니스 로직(service.py)이 "이 거래를 저장해줘"라고 요청하면, Repository가 알아서 파일을 열고, JSON으로 변환하고, 파일에 쓰고, 파일을 닫습니다.

### 4.1.2 왜 Repository를 분리하는가?

만약 `service.py`에서 직접 파일을 읽고 쓴다면:

```python
# ❌ 나쁜 예: service.py에서 파일 I/O를 직접 처리
class BudgetService:
    def add_transaction(self, ...):
        # 비즈니스 로직과 파일 I/O가 뒤섞임!
        if not self.cat_repo.exists(category):
            raise ValueError(...)
        tx_id = self._generate_new_id()
        json_line = json.dumps(tx.to_dict(), ensure_ascii=False)
        with open("data/transactions.jsonl", "a", encoding="utf-8") as f:
            f.write(json_line + "\n")
```

문제점:
- 나중에 저장 형식을 JSONL → SQLite로 바꾸려면? → `service.py` **전체를 수정**해야 함
- 파일 경로가 여기저기 하드코딩되어 있으면? → 하나 빼먹으면 버그

```python
# ✅ 좋은 예: Repository로 분리
class BudgetService:
    def add_transaction(self, ...):
        # 비즈니스 로직만 집중!
        if not self.cat_repo.exists(category):
            raise ValueError(...)
        tx_id = self._generate_new_id()
        tx = Transaction(...)
        self.tx_repo.save(tx)     # "저장해줘" 한 마디면 끝!
```

분리의 장점:
- 저장 방식을 바꿔도 `service.py`는 **수정 불필요**
- `self.tx_repo.save(tx)` 한 줄이면 되므로 **코드가 깔끔**

---

## 4.2 BaseRepository — 모든 저장소의 부모 클래스

### 4.2.1 "상속(Inheritance)"이란?

```
부모 클래스 (BaseRepository)
    ├── 자식 클래스 1 (TransactionRepository)
    ├── 자식 클래스 2 (CategoryRepository)
    ├── 자식 클래스 3 (BudgetRepository)
    └── 자식 클래스 4 (RecurringRepository)
```

상속의 핵심 개념: **"공통된 기능은 부모에게 한 번만 작성하고, 자식들이 물려받아 쓴다."**

비유: 스마트폰(부모)의 기본 기능(전화, 문자, 인터넷)을 물려받아서, 각 제조사(자식)가 고유 기능(카메라, 디자인)만 추가하는 것과 같습니다.

### 4.2.2 BaseRepository 코드 완전 해부 (repository.py 20~61번째 줄)

```python
class BaseRepository:
    """
    모든 저장소 클래스가 공통으로 사용하는 원자적 쓰기 및 기본 경로 관리 로직을 품은 부모 클래스입니다.
    """
    def __init__(self, data_dir: str = "data", filename: str = ""):
        self.data_dir = data_dir          # 데이터 폴더 경로 (기본: "data")
        self.filename = filename          # 파일 이름 (예: "transactions.jsonl")
        self.file_path = os.path.join(data_dir, filename)
        # ↑ 경로 결합: "data" + "transactions.jsonl" = "data/transactions.jsonl"
        
        os.makedirs(self.data_dir, exist_ok=True)
        # ↑ "data" 폴더가 없으면 만든다. exist_ok=True이므로 이미 있어도 에러 안 남
        
        if not os.path.exists(self.file_path):
            with open(self.file_path, "w", encoding="utf-8") as f:
                pass
        # ↑ 파일이 없으면 빈 파일을 만든다
        # "w" 모드: 쓰기 모드로 파일을 열되, 아무것도 안 쓰고 그냥 닫으면 = 빈 파일 생성
```

#### `os.path.join()`의 역할

```python
os.path.join("data", "transactions.jsonl")
# Windows → "data\\transactions.jsonl"
# Mac/Linux → "data/transactions.jsonl"
```

운영체제마다 경로 구분자가 다른데(`\` vs `/`), `os.path.join`이 자동으로 맞춰줍니다.

#### `with open(...) as f:` 구문의 의미

```python
# ❌ 위험한 방법
f = open("파일.txt", "w")
f.write("데이터")
f.close()    # 까먹으면? 파일이 안 닫힘! → 데이터 유실 위험!

# ✅ 안전한 방법 (with 문)
with open("파일.txt", "w") as f:
    f.write("데이터")
# ← with 블록을 벗어나면 자동으로 f.close()가 호출됨!
# 에러가 나도 자동으로 닫힘!
```

`with` 문은 **"이 블록이 끝나면 반드시 파일을 닫아라"**를 보장합니다. 이것을 **컨텍스트 매니저(Context Manager)**라고 부릅니다.

---

## 4.3 파일 열기 모드 — `"r"`, `"w"`, `"a"`의 차이

우리 프로그램에서 3가지 모드를 모두 사용합니다:

### 4.3.1 `"r"` — 읽기 모드 (Read)

```python
# repository.py 90~97번째 줄 (find_all_stream)
with open(self.file_path, "r", encoding="utf-8") as f:
    for line in f:
        # 한 줄씩 읽기
```

- 파일의 내용을 **읽기만** 합니다
- 파일이 없으면 `FileNotFoundError` 에러 발생
- 파일 내용을 변경하지 않습니다

### 4.3.2 `"w"` — 쓰기 모드 (Write)

```python
# repository.py 34번째 줄 (빈 파일 생성)
with open(self.file_path, "w", encoding="utf-8") as f:
    pass  # 아무것도 안 씀

# repository.py 50~52번째 줄 (_atomic_write_lines의 임시 파일 쓰기)
with open(tmp_file_path, "w", encoding="utf-8") as tmp_file:
    for line in lines:
        tmp_file.write(line + "\n")
```

- 파일이 없으면 **새로 생성**
- 파일이 이미 있으면 **기존 내용을 전부 지우고** 새로 씀 ⚠️
- 주의: 기존 데이터가 날아가므로 원본 파일에 직접 사용하면 위험!

### 4.3.3 `"a"` — 추가 모드 (Append)

```python
# repository.py 78~79번째 줄 (save — 새 거래 추가)
with open(self.file_path, "a", encoding="utf-8") as f:
    f.write(json_line + "\n")
```

- 파일이 없으면 **새로 생성**
- 파일이 이미 있으면 기존 내용을 **보존하고 맨 끝에 추가**
- 가장 안전! 기존 데이터를 건드리지 않음

### 4.3.4 우리 프로그램의 모드 사용 전략

```
새 거래 추가(save)     → "a" 모드 (기존 유지 + 끝에 추가)
파일 전체 읽기         → "r" 모드 (읽기만)
수정/삭제 후 전체 교체 → "w" 모드 (임시 파일에만! 원본은 건드리지 않음)
```

**핵심 통찰**: `"w"` 모드는 **절대로 원본 파일에 직접 사용하지 않습니다**. 항상 임시 파일(`.tmp`)에만 사용하고, 완성되면 `os.replace()`로 교체합니다. 이것이 원자적 쓰기의 핵심입니다 (6단계에서 상세 설명).

---

## 4.4 TransactionRepository — 거래 저장소 완전 해부

### 4.4.1 클래스 선언과 상속 (repository.py 63~68번째 줄)

```python
class TransactionRepository(BaseRepository):
    def __init__(self, data_dir: str = "data"):
        super().__init__(data_dir=data_dir, filename="transactions.jsonl")
```

#### `class TransactionRepository(BaseRepository):` — 상속 선언

괄호 안의 `BaseRepository`는 "이 클래스는 BaseRepository를 **상속**한다"는 뜻입니다.

상속하면 무엇을 얻나?
- `self.data_dir` → BaseRepository에서 물려받음
- `self.filename` → BaseRepository에서 물려받음
- `self.file_path` → BaseRepository에서 물려받음
- `_atomic_write_lines()` 메소드 → BaseRepository에서 물려받음
- 폴더/파일 자동 생성 → BaseRepository에서 물려받음

#### `super().__init__(...)` — 부모의 초기화 호출

```python
super().__init__(data_dir=data_dir, filename="transactions.jsonl")
```

`super()`는 **부모 클래스(BaseRepository)**를 가리킵니다.

이 한 줄이 실행되면:
1. BaseRepository의 `__init__`이 호출됨
2. `self.data_dir = "data"` 설정
3. `self.filename = "transactions.jsonl"` 설정
4. `self.file_path = "data/transactions.jsonl"` 설정
5. `data/` 폴더 존재 확인/생성
6. `data/transactions.jsonl` 파일 존재 확인/생성

**다른 Repository들도 같은 패턴:**
```python
# CategoryRepository
super().__init__(data_dir=data_dir, filename="categories.jsonl")

# BudgetRepository
super().__init__(data_dir=data_dir, filename="budgets.jsonl")

# RecurringRepository
super().__init__(data_dir=data_dir, filename="recurring.jsonl")
```

→ filename만 다르고 나머지 초기화 로직은 **BaseRepository에서 100% 재사용**!

### 4.4.2 save() — 새 거래를 파일에 저장 (repository.py 70~79번째 줄)

```python
def save(self, transaction: Transaction) -> None:
    # ① Transaction 객체 → 딕셔너리 → JSON 문자열 변환
    json_line = json.dumps(transaction.to_dict(), ensure_ascii=False)
    
    # ② "a"(append) 모드로 파일을 열어 끝에 한 줄 추가
    with open(self.file_path, "a", encoding="utf-8") as f:
        f.write(json_line + "\n")
```

**실행 과정을 단계별로:**

```
Transaction 객체
  id="TX-000003", type="expense", date="2026-05-25",
  amount=18000, category="식비", memo="야식", tags=["야식","피자"]
    │
    │ transaction.to_dict()  ← 3단계에서 배운 직렬화!
    ▼
Python 딕셔너리
  {"id":"TX-000003", "type":"expense", "date":"2026-05-25",
   "amount":18000, "category":"식비", "memo":"야식", "tags":["야식","피자"]}
    │
    │ json.dumps(..., ensure_ascii=False)
    ▼
JSON 문자열 (한 줄)
  '{"id":"TX-000003","type":"expense","date":"2026-05-25","amount":18000,"category":"식비","memo":"야식","tags":["야식","피자"]}'
    │
    │ f.write(json_line + "\n")  ← 줄바꿈을 추가해서 파일 끝에 붙임
    ▼
transactions.jsonl 파일 (맨 끝에 새 줄 추가됨)
```

#### `ensure_ascii=False`의 의미

```python
# ensure_ascii=True (기본값) → 한글이 유니코드 이스케이프로 변환됨
json.dumps({"memo": "점심"})
# → '{"memo": "\\uc810\\uc2ec"}'  ← 사람이 읽을 수 없음!

# ensure_ascii=False → 한글이 그대로 저장됨
json.dumps({"memo": "점심"}, ensure_ascii=False)
# → '{"memo": "점심"}'  ← 사람이 읽을 수 있음!
```

한글 데이터를 파일에서 바로 읽을 수 있게 하기 위해 `ensure_ascii=False`를 씁니다.

### 4.4.3 find_all() — 전체 목록 리스트로 반환 (repository.py 99~103번째 줄)

```python
def find_all(self) -> List[Transaction]:
    return list(self.find_all_stream())
```

이 한 줄은 **5단계에서 배울 제너레이터를 리스트로 변환**합니다:
- `find_all_stream()` → 한 줄씩 yield하는 제너레이터
- `list(...)` → 제너레이터가 yield하는 모든 것을 모아서 리스트로 만듦

**언제 사용하나?**: 정렬이나 전체 수정처럼 **모든 데이터를 한꺼번에 봐야 하는 경우**에 사용합니다.

---

## 4.5 다른 3개 Repository 클래스

### 4.5.1 CategoryRepository (repository.py 147~211번째 줄)

특별한 점: **초기 카테고리 자동 생성** + **중복 방지**

```python
class CategoryRepository(BaseRepository):
    def __init__(self, data_dir: str = "data"):
        super().__init__(data_dir=data_dir, filename="categories.jsonl")
        self._ensure_initial_categories()    # ← 추가 초기화!

    def _ensure_initial_categories(self) -> None:
        # 파일 크기가 0바이트(=완전히 비어있음)이면
        if os.path.getsize(self.file_path) == 0:
            default_categories = ["식비", "교통", "주거", "수입", "기타"]
            for cat_name in default_categories:
                self.save(Category(name=cat_name))

    def save(self, category: Category) -> None:
        # 중복 체크: 이미 존재하면 저장하지 않음
        if self.exists(category.name):
            return                       # ← 조용히 무시 (에러 안 남)
        json_line = json.dumps(category.to_dict(), ensure_ascii=False)
        with open(self.file_path, "a", encoding="utf-8") as f:
            f.write(json_line + "\n")

    def exists(self, category_name: str) -> bool:
        for cat in self.find_all():
            if cat.name == category_name:
                return True
        return False
```

**정합성 확인 ✅**: 
- `_ensure_initial_categories`는 `__init__` 안에서 `super().__init__()` 다음에 호출됩니다
- `os.path.getsize()`는 파일이 이미 존재해야 작동하는데, `super().__init__()`에서 빈 파일을 이미 만들어줬으므로 안전합니다

### 4.5.2 BudgetRepository (repository.py 214~260번째 줄)

특별한 점: **save_or_update** — 같은 월이면 수정, 없으면 추가

```python
def save_or_update(self, budget: Budget) -> None:
    found = False
    new_lines = []
    for bg in self.find_all():
        if bg.month == budget.month:        # 같은 달의 예산이 이미 있으면
            new_lines.append(json.dumps(budget.to_dict(), ensure_ascii=False))
            found = True                     # → 새 값으로 교체
        else:
            new_lines.append(json.dumps(bg.to_dict(), ensure_ascii=False))
            
    if not found:
        # 기존에 없던 달이면 파일 끝에 추가
        json_line = json.dumps(budget.to_dict(), ensure_ascii=False)
        with open(self.file_path, "a", encoding="utf-8") as f:
            f.write(json_line + "\n")
    else:
        # 기존 예산을 수정한 경우 → 원자적 쓰기로 전체 교체
        self._atomic_write_lines(new_lines)
```

**왜 이런 방식인가?**: 예산은 "한 달에 하나"만 있어야 합니다. 2026-05 예산이 이미 있는데 또 만들면 안 되니까, 기존 값을 업데이트하는 것입니다.

### 4.5.3 RecurringRepository (repository.py 263~296번째 줄)

TransactionRepository와 거의 동일한 패턴입니다. `save`, `find_all`, `delete` 세 메소드를 가집니다.

---

## 4.6 4개 Repository 클래스의 상속 관계 정리

```
        BaseRepository (부모)
        ┌─────────────────────────────┐
        │ __init__(): 폴더/파일 생성   │
        │ _atomic_write_lines(): 원자적│
        │   쓰기 (공통 안전 장치)       │
        └──────────┬──────────────────┘
                   │ 상속
    ┌──────────────┼──────────────────────┐
    │              │                      │
    ▼              ▼                      ▼
TransactionRepo  CategoryRepo         BudgetRepo      RecurringRepo
 save()           save() +중복방지     save_or_update()  save()
 find_all_stream() find_all()          find_all()       find_all()
 find_all()       exists()            find_by_month()   delete()
 update()         delete()
 delete()         _ensure_initial_
                   categories()
```

**핵심**: 4개 클래스 모두 `_atomic_write_lines()`를 물려받아 사용하므로, 안전한 파일 쓰기 로직을 **한 번만 작성**하면 됩니다.

---

## 4.7 이 단계의 핵심 정리

```
✅ Repository는 파일 I/O만 전담하는 "사서" 역할이다
✅ BaseRepository가 공통 기능(폴더 생성, 파일 생성, 원자적 쓰기)을 제공한다
✅ 4개 자식 Repository가 각각 다른 파일을 담당한다
✅ "a" 모드는 기존 내용 보존+끝에 추가, "w" 모드는 전체 덮어쓰기, "r" 모드는 읽기
✅ 원본 파일에는 절대 "w" 모드를 직접 사용하지 않는다 (임시 파일에만!)
✅ json.dumps(ensure_ascii=False)로 한글을 그대로 저장한다
✅ with 문으로 파일을 열면 블록 끝에서 자동으로 닫힌다
✅ super().__init__()으로 부모의 초기화를 호출한다
```

---
---

# 📘 5단계: 제너레이터와 yield — 스트리밍의 원리

> **이 단계의 목표**: `yield`가 정확히 무엇이고, 일반 함수와 어떻게 다르며, 왜 10만 건의 데이터를 다룰 때 제너레이터가 필수인지를 **완벽히** 이해합니다.

---

## 5.1 제너레이터 이전의 문제 — "한 번에 다 읽기"의 한계

### 5.1.1 일상생활 비유

**식당 뷔페 vs 코스 요리**를 비유해 봅시다.

```
[뷔페 방식] = 일반 함수 (return)
  → 주방에서 100가지 요리를 전부 만들어서 테이블에 한꺼번에 깔아놓음
  → 100인분 접시가 필요 → 테이블(=메모리)이 남아나질 않음!
  → 손님이 3접시만 먹고 가면? 97접시 낭비!

[코스 요리 방식] = 제너레이터 (yield)
  → 주방에서 한 접시씩 만들어서 내보냄
  → 접시 1개분 공간만 있으면 됨
  → 손님이 "더 주세요" 할 때만 다음 접시를 만듦
  → 손님이 3접시 먹고 "그만!" 하면? 주방도 즉시 멈춤!
```

### 5.1.2 프로그래밍에서의 문제

만약 거래가 10만 건이라면:

```python
# ❌ 일반 함수 방식: 전부 메모리에 올림
def find_all_normal():
    result = []    # ← 10만 개를 담을 리스트
    with open("transactions.jsonl", "r") as f:
        for line in f:
            data = json.loads(line.strip())
            tx = Transaction.from_dict(data)
            result.append(tx)    # ← 10만 번 추가
    return result    # ← 10만 개를 한 번에 반환

all_transactions = find_all_normal()
# → 메모리에 Transaction 객체 10만 개가 동시에 존재!
# → 각 객체가 약 200바이트라면 ≈ 20MB 메모리 점유
# → 100만 건이면? ≈ 200MB!
# → 1000만 건이면? ≈ 2GB! 💥 메모리 부족!
```

```python
# ✅ 제너레이터 방식: 한 건씩만 메모리에 올림
def find_all_stream():
    with open("transactions.jsonl", "r") as f:
        for line in f:
            data = json.loads(line.strip())
            tx = Transaction.from_dict(data)
            yield tx    # ← "여기 한 건이요!" 하고 멈춤
                        #    다음 요청이 올 때까지 대기

for tx in find_all_stream():
    # tx는 매 반복마다 딱 1건만 메모리에 존재
    # 이전 tx는 가비지 컬렉터가 회수
    print(tx.id)
# → 10만 건이든 1000만 건이든 메모리 사용량은 일정!
# → 약 200바이트 (1건분)만 사용!
```

---

## 5.2 `yield`의 동작 원리 — 일시정지와 재개

### 5.2.1 `return` vs `yield` 핵심 차이

```python
# return이 있는 일반 함수
def normal_function():
    print("A")
    return 1        # ← 여기서 함수가 완전히 종료됨
    print("B")      # ← 절대 실행되지 않음 (dead code)

# yield가 있는 제너레이터 함수
def generator_function():
    print("A")
    yield 1          # ← 값을 보내고 "일시정지" (함수가 종료되지 않음!)
    print("B")       # ← 다음에 호출하면 여기서부터 이어서 실행됨
    yield 2          # ← 또 일시정지
    print("C")
    yield 3
```

**`yield`는 `return`과 다르게 함수를 "죽이지 않습니다"!**

함수의 상태(지역 변수, 실행 위치)를 **얼려두고(freeze)** 잠시 멈추는 것입니다.

### 5.2.2 단계별 실행 시뮬레이션

```python
gen = generator_function()   # ① 제너레이터 객체 생성 (아직 아무것도 실행 안 됨!)

val1 = next(gen)             # ② 첫 번째 호출
# 출력: "A"                  
# yield 1에서 멈춤           
# val1 = 1                  

val2 = next(gen)             # ③ 두 번째 호출
# "yield 1" 다음부터 이어서 실행!
# 출력: "B"                  
# yield 2에서 멈춤           
# val2 = 2                  

val3 = next(gen)             # ④ 세 번째 호출
# "yield 2" 다음부터 이어서 실행!
# 출력: "C"                  
# yield 3에서 멈춤           
# val3 = 3                  

next(gen)                    # ⑤ 네 번째 호출
# yield 3 다음에 아무것도 없으므로 함수 종료
# StopIteration 예외 발생! (for문이 자동으로 처리)
```

### 5.2.3 for 문과 제너레이터의 관계

```python
for val in generator_function():
    print(val)
```

이 for 문은 내부적으로 이렇게 동작합니다:

```python
gen = generator_function()     # 제너레이터 객체 생성
while True:
    try:
        val = next(gen)        # 다음 yield까지 실행
        print(val)             # yield된 값 사용
    except StopIteration:      # 더 이상 yield가 없으면
        break                  # for 루프 종료
```

결과:
```
A
1
B
2
C
3
```

---

## 5.3 실제 코드의 제너레이터 — `find_all_stream()`

### 5.3.1 코드 완전 해부 (repository.py 81~97번째 줄)

```python
def find_all_stream(self) -> Generator[Transaction, None, None]:
    # ① 파일이 존재하지 않으면 아무것도 yield하지 않고 끝남
    if not os.path.exists(self.file_path):
        return    # ← 제너레이터에서 return은 "더 이상 줄 게 없다"는 의미
        
    # ② 파일을 읽기 모드로 연다
    with open(self.file_path, "r", encoding="utf-8") as f:
        # ③ 파일의 각 줄을 하나씩 순회
        for line in f:
            stripped_line = line.strip()     # ④ 줄바꿈(\n) 제거
            if not stripped_line:            # ⑤ 빈 줄이면 건너뜀
                continue
            # ⑥ JSON 문자열 → 딕셔너리 → Transaction 객체로 변환
            data_dict = json.loads(stripped_line)
            # ⑦ yield! 이 객체를 호출자에게 보내고 일시정지
            yield Transaction.from_dict(data_dict)
```

### 5.3.2 `for line in f:` — 파이썬의 숨은 제너레이터

사실 파일 객체(`f`) 자체도 **제너레이터처럼 동작**합니다!

```python
with open("파일.txt", "r") as f:
    for line in f:     # ← f는 한 줄씩 읽어서 제공하는 이터레이터
        print(line)
```

`f.readlines()`(전체를 리스트로 읽기)와 달리, `for line in f`는 디스크에서 **한 줄씩만** 읽어옵니다. 이것 자체가 이미 메모리 효율적인 스트리밍입니다.

우리의 `find_all_stream()`은 이 **이중 스트리밍**을 구현합니다:

```
[디스크]  ──한 줄씩──→  [for line in f]  ──한 객체씩──→  [yield]  ──한 건씩──→  [호출자]
          파이썬 내장       1차 스트리밍      우리 코드       2차 스트리밍
```

### 5.3.3 반환 타입: `Generator[Transaction, None, None]`

```python
def find_all_stream(self) -> Generator[Transaction, None, None]:
```

`Generator[YieldType, SendType, ReturnType]`:
- `YieldType = Transaction` → yield로 보내는 값의 타입
- `SendType = None` → send()로 받는 값의 타입 (우리는 사용 안 함)
- `ReturnType = None` → 제너레이터가 끝나면 반환하는 값 (없음)

### 5.3.4 `find_all_stream()`이 사용되는 모든 곳

우리 프로그램에서 이 제너레이터가 호출되는 곳들:

```python
# 1. 검색 (service.py 114번째 줄)
for tx in self.tx_repo.find_all_stream():
    if from_date and tx.date < from_date:
        continue
    ...

# 2. 카테고리 삭제 시 영향받는 거래 수 세기 (service.py 248번째 줄)
for tx in self.tx_repo.find_all_stream():
    if tx.category == name:
        affected_count += 1

# 3. 월별 요약 계산 (service.py 175번째 줄)
for tx in self.tx_repo.find_all_stream():
    if tx.date.startswith(month):
        ...

# 4. ID 자동 발급 시 최대 번호 찾기 (service.py 47번째 줄)
for tx in self.tx_repo.find_all_stream():
    if tx.id.startswith("TX-"):
        ...

# 5. 반복 거래 중복 확인 (service.py 371번째 줄)
for tx in self.tx_repo.find_all_stream():
    if tx.date.startswith(month):
        ...

# 6. 수정/삭제 시 전체 스캔 (repository.py 113, 134번째 줄)
for tx in self.find_all_stream():
    if tx.id == updated_tx.id:
        ...
```

**정합성 확인 ✅**: 위의 모든 줄 번호가 실제 코드와 일치합니다.

---

## 5.4 `find_all()` vs `find_all_stream()` — 언제 뭘 쓰는가?

### 5.4.1 두 함수의 차이

```python
# 제너레이터 버전 — O(1) 메모리
def find_all_stream(self) -> Generator[Transaction, None, None]:
    ...
    yield Transaction.from_dict(data_dict)

# 리스트 버전 — O(N) 메모리
def find_all(self) -> List[Transaction]:
    return list(self.find_all_stream())
```

| | `find_all_stream()` | `find_all()` |
|:---|:---|:---|
| **메모리** | O(1) — 1건분만 | O(N) — 전체를 메모리에 올림 |
| **용도** | 한 번 순회하며 필터링/집계 | 정렬, 전체 수정, 전체 삭제 |
| **제약** | 정렬 불가 (정렬은 전체를 알아야 가능) | 대용량 시 메모리 부담 |

### 5.4.2 실제 코드에서의 사용 패턴

```python
# ✅ find_all_stream() 사용 — 정렬 불필요한 경우
#    (service.py 175번째 줄 — 월별 합계 계산)
for tx in self.tx_repo.find_all_stream():
    if tx.date.startswith(month):
        total_income += tx.amount   # 합산만 하면 되므로 정렬 불필요

# ✅ find_all() 사용 — 정렬이 필요한 경우
#    (service.py 88번째 줄 — 최신순 목록)
all_tx = self.tx_repo.find_all()        # 전체를 리스트로 가져옴
all_tx.sort(key=lambda tx: (tx.date, tx.id), reverse=True)  # 정렬!
```

**핵심 통찰**: 정렬(`sort`)은 **모든 요소를 비교**해야 하므로, 제너레이터로는 불가능합니다. 정렬이 필요할 때만 `find_all()`을 쓰고, 나머지 경우에는 `find_all_stream()`을 씁니다.

---

## 5.5 메모리 사용량 비교 — 왜 중요한가?

### 5.5.1 구체적인 수치 비교

Transaction 객체 1개의 대략적인 메모리 크기:
- 파이썬 객체 오버헤드: ~56바이트
- 문자열 필드 7개 평균: ~40바이트 × 7 = ~280바이트
- 리스트(tags) 오버헤드: ~56바이트
- **합계**: 약 400바이트/건

```
┌────────────────────────────────────────────────────┐
│  거래 건수      find_all() 메모리    find_all_stream()│
│                                     메모리            │
│  100건          40 KB               400 B (0.4KB)    │
│  1,000건        400 KB              400 B            │
│  10,000건       4 MB                400 B            │
│  100,000건      40 MB               400 B            │
│  1,000,000건    400 MB ⚠️           400 B            │
│  10,000,000건   4 GB 💥            400 B            │
└────────────────────────────────────────────────────┘
```

1천만 건이 되면 `find_all()`은 4GB 메모리를 잡아먹지만, `find_all_stream()`은 여전히 400바이트만 씁니다. 이것이 **O(N) vs O(1)의 위력**입니다.

### 5.5.2 공간 복잡도 개념

- **O(1)**: "데이터가 아무리 많아도 사용하는 메모리는 일정" (상수)
- **O(N)**: "데이터가 N개면 메모리도 N에 비례해서 증가"

제너레이터의 공간 복잡도가 O(1)인 이유:
- 한 번에 딱 1건만 메모리에 올림
- 이전 건은 `yield` 후 가비지 컬렉터가 회수
- 다음 건을 요청받으면 그때서야 파일에서 읽어옴

---

## 5.6 `list_transactions()`의 제너레이터 활용 (service.py)

### 5.6.1 코드 분석 (service.py 83~99번째 줄)

```python
def list_transactions(self, limit: Optional[int] = None) -> Generator[Transaction, None, None]:
    all_tx = self.tx_repo.find_all()    # ← 여기서 전체를 리스트로 받음
    
    # 최신순 정렬 (날짜 역순, 같으면 ID 역순)
    all_tx.sort(key=lambda tx: (tx.date, tx.id), reverse=True)
    
    count = 0
    for tx in all_tx:
        if limit is not None and count >= limit:
            break            # ← limit 건수에 도달하면 더 이상 yield 안 함
        yield tx             # ← 정렬된 결과를 한 건씩 yield
        count += 1
```

**이 함수의 설계 의도**:
1. 정렬이 필요하므로 `find_all()`로 전체를 가져옴 (어쩔 수 없음)
2. 정렬 후에는 다시 `yield`로 한 건씩 내보냄
3. `limit`이 지정되면 그 수만큼만 yield하고 멈춤

**왜 정렬 후에도 yield를 쓰는가?**: `limit=3`이면 3건만 yield하고 멈추므로, 나머지 997건은 cli.py까지 전달되지 않습니다. 약간의 메모리 절약 효과가 있습니다.

---

## 5.7 `search_transactions()`의 제너레이터 활용 (service.py)

### 5.7.1 코드 분석 (service.py 101~140번째 줄)

```python
def search_transactions(self, from_date=None, to_date=None, 
                         category=None, type_str=None,
                         keyword=None, tag=None) -> Generator[Transaction, None, None]:
    filtered = []
    for tx in self.tx_repo.find_all_stream():    # ← 스트리밍으로 읽음!
        # 6가지 필터 조건 확인
        if from_date and tx.date < from_date: continue
        if to_date and tx.date > to_date: continue
        if category and tx.category != category: continue
        if type_str and tx.type != type_str: continue
        if keyword and keyword.lower() not in tx.memo.lower(): continue
        if tag and tag not in tx.tags: continue
        
        filtered.append(tx)    # 조건을 모두 통과한 건만 수집
    
    # 최신순 정렬
    filtered.sort(key=lambda tx: (tx.date, tx.id), reverse=True)
    
    for tx in filtered:
        yield tx    # 정렬된 결과를 한 건씩 yield
```

**이 함수의 메모리 전략**:
1. **읽기**: `find_all_stream()`으로 한 건씩 스트리밍 → 조건 불일치하면 즉시 `continue`로 버림
2. **수집**: 조건 통과한 건만 `filtered` 리스트에 모음 → 10만 건 중 100건만 통과하면 100건만 메모리에!
3. **출력**: 정렬 후 `yield`로 한 건씩 전달

```
10만 건 파일
    │
    │ find_all_stream() → 한 건씩 읽기
    ▼
6가지 필터 → 99,900건 탈락 → continue로 즉시 버림
    │
    │ 100건만 filtered에 추가
    ▼
100건 정렬
    │
    │ yield로 한 건씩 전달
    ▼
화면 출력
```

---

## 5.8 이 단계의 핵심 정리

```
✅ yield는 값을 반환하되 함수를 "일시정지"시킨다 (return은 "종료")
✅ 제너레이터는 "요청받을 때마다 한 건씩 생산"하는 코스 요리 방식이다
✅ find_all_stream()은 파일을 한 줄씩 읽어 Transaction을 yield한다
✅ find_all()은 find_all_stream()의 모든 결과를 리스트로 모은 것이다
✅ 정렬이 필요하면 find_all(), 순회만 하면 find_all_stream() 사용
✅ 메모리 사용량: find_all()=O(N), find_all_stream()=O(1)
✅ for line in f: 자체가 디스크에서 한 줄씩 읽는 스트리밍이다
✅ Generator[Transaction, None, None]은 "Transaction을 yield하는 제너레이터" 타입이다
```

### 5.8.1 다른 사람에게 설명하는 연습

> **질문**: "제너레이터를 왜 사용했고, 어떻게 구현했나요?"
>
> **답변 예시**: "가계부 데이터가 10만 건, 100만 건으로 늘어나면 전체를 메모리에 올리는 것은 비효율적이고 위험합니다. 그래서 repository.py의 find_all_stream() 함수에서 yield 키워드를 사용해 파일을 한 줄씩 읽고, 각 줄을 Transaction 객체로 변환한 뒤 즉시 호출자에게 전달합니다. 이렇게 하면 동시에 메모리에 올라가는 데이터는 항상 1건뿐이므로 공간 복잡도가 O(1)이 됩니다. 검색이나 집계 같은 한 번 순회 작업에서는 이 스트리밍 방식을 쓰고, 정렬이 필요한 경우에만 find_all()로 전체를 리스트로 가져옵니다."

---
---

# 📘 6단계: 원자적 쓰기(Atomic Write) — 데이터 안전의 핵심

> **이 단계의 목표**: 거래를 수정(update)하거나 삭제(delete)할 때 **왜 원본 파일에 직접 쓰면 위험한지**, 임시 파일 + `os.replace()`가 어떻게 이 문제를 해결하는지, 에러 발생 시 복구 메커니즘까지 완벽히 이해합니다.

---

## 6.1 문제 상황 — "직접 쓰기"가 위험한 이유

### 6.1.1 일상생활 비유

**시험지 수정**을 비유해 봅시다:

```
[위험한 방법 ❌]
시험지 원본에 직접 지우개로 지우고 다시 씀
→ 지우개가 닳아서 구멍이 뚫림 → 원본 망가짐!
→ 지우다가 전기가 나감 → 반만 지워진 상태!

[안전한 방법 ✅]
① 빈 시험지를 새로 가져옴 (임시 파일)
② 수정할 내용을 새 시험지에 깨끗하게 다시 씀
③ 다 쓰고 나서, 원본과 새 시험지를 한 번에 바꿔치기
→ 실패해도 원본은 그대로 있음!
```

### 6.1.2 프로그래밍에서의 구체적 위험

가계부에 5건의 거래가 있고, 3번째 거래를 삭제한다고 합시다:

```
[원본 파일: transactions.jsonl]
TX-000001 ... ← 1번째 줄
TX-000002 ... ← 2번째 줄
TX-000003 ... ← 3번째 줄 (삭제 대상!)
TX-000004 ... ← 4번째 줄
TX-000005 ... ← 5번째 줄
```

#### 위험한 방식: 원본 파일에 직접 "w" 모드로 쓰기

```python
# ❌ 이렇게 하면 안 됩니다!
with open("transactions.jsonl", "w") as f:    # "w" = 기존 내용 전부 삭제!
    f.write(line1)    # 1번 ✅
    f.write(line2)    # 2번 ✅
    # ← 여기서 정전! 또는 디스크 꽉 참! 또는 프로그램 크래시!
    # f.write(line4)  # 실행 안 됨
    # f.write(line5)  # 실행 안 됨
```

결과:
```
[파일 상태 — 복구 불가능!]
TX-000001 ...
TX-000002 ...
(여기서 끝 — TX-000004, TX-000005 데이터 영원히 증발! 💀)
```

**"w" 모드가 파일을 여는 순간 기존 내용이 전부 삭제**되기 때문에, 쓰다가 에러가 나면 원본 데이터도 없고 새 데이터도 불완전합니다. 최악의 상황!

### 6.1.3 추가 위험: "append 한 줄 삭제"가 불가능

JSONL 파일에서 3번째 줄만 깔끔하게 삭제하는 것은 **물리적으로 불가능**합니다.

```
파일은 "종이 두루마리"와 같습니다.
두루마리 중간의 글자를 지우면? → 빈 공간이 남거나 뒤가 밀려야 함
텍스트 파일에서는 "중간 삭제"라는 연산이 존재하지 않습니다!
```

따라서 "삭제"를 구현하려면 반드시 **전체를 다시 써야** 합니다:
1. 모든 줄을 읽는다
2. 삭제할 줄만 제외하고 나머지를 모은다
3. 새 파일에 다시 쓴다

이 "전체 다시 쓰기"를 안전하게 하는 것이 바로 **원자적 쓰기**입니다.

---

## 6.2 원자적 쓰기의 원리 — 3단계 메커니즘

### 6.2.1 전체 흐름도

```
[1단계: 임시 파일 생성 및 쓰기]
원본: transactions.jsonl (안전하게 보존됨)
임시: transactions.jsonl.tmp (여기에 새 내용을 씀)

    transactions.jsonl          transactions.jsonl.tmp
    ┌──────────────┐            ┌──────────────┐
    │ TX-000001    │            │ TX-000001    │ ← 복사
    │ TX-000002    │            │ TX-000002    │ ← 복사
    │ TX-000003    │            │              │ ← 건너뜀! (삭제 대상)
    │ TX-000004    │            │ TX-000004    │ ← 복사
    │ TX-000005    │            │ TX-000005    │ ← 복사
    └──────────────┘            └──────────────┘

[2단계: 쓰기 성공 확인]
.tmp 파일이 정상적으로 닫혔는가? → YES → 다음 단계로

[3단계: 원자적 교체]
os.replace("transactions.jsonl.tmp", "transactions.jsonl")
→ OS 커널이 파일 이름을 한순간에 바꿈 (원자적!)
→ "transactions.jsonl.tmp"이 "transactions.jsonl"이 됨
→ 기존 "transactions.jsonl"은 자동으로 사라짐

    transactions.jsonl (교체 완료!)
    ┌──────────────┐
    │ TX-000001    │
    │ TX-000002    │
    │ TX-000004    │
    │ TX-000005    │
    └──────────────┘
```

### 6.2.2 "원자적(Atomic)"이란?

원자(Atom)는 "더 이상 쪼갤 수 없는 것"이라는 뜻입니다.

`os.replace()`는 **"파일 이름 변경"을 단 하나의 동작으로** 수행합니다:
- 절반만 교체되는 일이 없습니다
- 교체 중에 정전이 나도 **교체 전(구 파일)** 또는 **교체 후(신 파일)** 중 하나만 존재합니다
- "교체 도중 반쯤 바뀐 상태"는 OS 커널이 허용하지 않습니다

이것은 OS(운영체제) 수준에서 보장하는 것이므로, 파이썬이 아닌 **OS가 안전성을 지켜주는** 것입니다.

---

## 6.3 실제 코드 완전 해부 — `_atomic_write_lines()`

### 6.3.1 코드 (repository.py 37~60번째 줄)

```python
def _atomic_write_lines(self, lines: List[str]) -> None:
    # ① 임시 파일 경로 생성
    tmp_file_path = self.file_path + ".tmp"
    # 예: "data/transactions.jsonl" + ".tmp" = "data/transactions.jsonl.tmp"
    
    try:
        # ② 임시 파일에 데이터 쓰기 ("w" 모드 = 새로 만들기)
        with open(tmp_file_path, "w", encoding="utf-8") as tmp_file:
            for line in lines:
                tmp_file.write(line + "\n")
        # ← with 블록 끝 = 파일이 확실히 닫힘 = 모든 데이터가 디스크에 기록됨
        
        # ③ 임시 파일 → 원본 파일로 원자적 교체
        os.replace(tmp_file_path, self.file_path)
        # ← 이 한 줄이 실행되는 순간, 교체 완료!
        
    except Exception as e:
        # ④ 쓰기 도중 에러 발생 시: 임시 파일만 정리하고 에러 전파
        if os.path.exists(tmp_file_path):
            os.remove(tmp_file_path)    # 불완전한 임시 파일 삭제
        raise IOError(f"파일을 안전하게 쓰는 도중 오류가 발생했습니다: {e}")
```

### 6.3.2 각 시나리오별 동작

#### 시나리오 1: 정상 완료 ✅

```
① tmp 파일 생성 → ✅
② tmp 파일에 쓰기 → ✅
③ os.replace() → ✅
결과: 원본 파일이 새 내용으로 완벽하게 교체됨
```

#### 시나리오 2: 쓰기 도중 에러 (디스크 꽉 참) ⚠️

```
① tmp 파일 생성 → ✅
② tmp 파일에 쓰기 → 3줄째에서 💥 디스크 꽉 참!
   → except 블록 진입
③ tmp 파일 삭제 → ✅ (불완전한 tmp 정리)
④ IOError 발생 → 상위(데코레이터)에서 처리
결과: 원본 파일은 전혀 손대지 않았으므로 완벽하게 안전!
```

#### 시나리오 3: os.replace() 직전에 정전 ⚡

```
① tmp 파일 생성 → ✅
② tmp 파일에 쓰기 → ✅ (완벽하게 씀)
③ os.replace() 전에 ⚡ 정전!
결과: 원본 파일은 그대로, .tmp 파일이 남아있음
→ 다음 실행 시 .tmp 파일은 그냥 무시됨 (프로그램은 .jsonl만 읽음)
→ 데이터 안전!
```

#### 시나리오 4: os.replace() 도중 정전 ⚡

```
① tmp 파일 생성 → ✅
② tmp 파일에 쓰기 → ✅
③ os.replace() 도중 ⚡ 정전!
결과: OS가 원자성을 보장하므로, 교체 전 또는 교체 후 중 하나만 존재
→ 어느 쪽이든 데이터는 완전한 상태!
```

**결론: 어떤 시나리오에서도 데이터가 "반쯤 쓰인 불완전한 상태"로 남지 않습니다!**

---

## 6.4 update()와 delete()의 원자적 구현

### 6.4.1 delete() 코드 분석 (repository.py 126~144번째 줄)

```python
def delete(self, tx_id: str) -> bool:
    found = False
    new_lines = []
    
    # ① 모든 거래를 스트리밍으로 읽으면서
    for tx in self.find_all_stream():
        if tx.id == tx_id:
            found = True           # 삭제 대상을 발견! (리스트에 안 넣음)
        else:
            # 삭제 대상이 아닌 건들만 모음
            new_lines.append(json.dumps(tx.to_dict(), ensure_ascii=False))
    
    # ② 삭제 대상을 찾았으면 → 나머지만으로 파일을 교체
    if found:
        self._atomic_write_lines(new_lines)
    
    return found    # True=삭제 성공, False=해당 ID 없음
```

**동작을 도식으로 표현:**

```
원본 파일:                  new_lines 리스트:
TX-000001  ──복사──→        TX-000001
TX-000002  ──복사──→        TX-000002
TX-000003  ──건너뜀!──→     (없음)         ← 삭제!
TX-000004  ──복사──→        TX-000004
TX-000005  ──복사──→        TX-000005

new_lines = [TX-001, TX-002, TX-004, TX-005]
    │
    │ _atomic_write_lines(new_lines)
    ▼
.tmp 파일에 쓰기 → 성공 → os.replace() → 원본 교체 완료!
```

### 6.4.2 update() 코드 분석 (repository.py 105~124번째 줄)

```python
def update(self, updated_tx: Transaction) -> bool:
    found = False
    new_lines = []
    
    for tx in self.find_all_stream():
        if tx.id == updated_tx.id:
            # 수정 대상 → 새 데이터로 교체
            new_lines.append(json.dumps(updated_tx.to_dict(), ensure_ascii=False))
            found = True
        else:
            # 나머지 → 원래 데이터 그대로
            new_lines.append(json.dumps(tx.to_dict(), ensure_ascii=False))
    
    if found:
        self._atomic_write_lines(new_lines)
    
    return found
```

**delete()와 update()의 차이:**

```
delete(): 삭제 대상 → 리스트에 안 넣음 (건너뜀)
update(): 수정 대상 → 새 데이터로 바꿔서 리스트에 넣음

나머지 로직은 100% 동일!
```

### 6.4.3 두 함수의 공통 패턴 (필터-재구성-교체)

```
[1] 필터(Filter): find_all_stream()으로 모든 데이터를 순회
[2] 재구성(Reconstruct): 조건에 따라 데이터를 모음 (삭제면 제외, 수정이면 교체)
[3] 교체(Replace): _atomic_write_lines()로 안전하게 파일 교체
```

이 패턴은 `CategoryRepository.delete()`와 `BudgetRepository.save_or_update()`에서도 동일하게 사용됩니다.

**정합성 확인 ✅**: CategoryRepository.delete() (197~211번째 줄), BudgetRepository.save_or_update() (221~242번째 줄) 모두 같은 `_atomic_write_lines()` 호출 패턴을 따릅니다.

---

## 6.5 원자적 쓰기의 한계와 대용량 병목

### 6.5.1 현재 방식의 시간 복잡도

```python
# delete 또는 update 시:
for tx in self.find_all_stream():    # O(N) — 전체 파일을 한 번 읽음
    new_lines.append(...)            # O(N) — 전체를 메모리에 보관
self._atomic_write_lines(new_lines)  # O(N) — 전체를 다시 씀

# 총 시간 복잡도: O(N)
# 총 공간 복잡도: O(N) (new_lines 리스트)
```

### 6.5.2 10만 건일 때의 현실적 문제

```
거래 1건 삭제를 위해:
① 10만 줄 읽기 → 약 0.5초
② 9만 9999줄을 메모리에 보관 → 약 40MB
③ 9만 9999줄을 .tmp 파일에 쓰기 → 약 0.5초
④ os.replace() → 거의 즉시

총 소요: 약 1초, 메모리 40MB
```

1초는 가계부 수준에서는 문제없지만, 실시간 시스템이라면 병목이 됩니다.

### 6.5.3 개선 방안 (10단계 평가 대비에서 상세 설명)

| 방안 | 원리 | 효과 |
|:---|:---|:---|
| 바이트 오프셋 인덱싱 | ID별 파일 위치를 기억 | 검색 O(1) |
| 월별 파일 분할 | `transactions_2026-05.jsonl` | I/O 대상 축소 |
| Append-Only 로그 | 삭제/수정을 로그만 남김 | 쓰기 O(1) |
| 페이지네이션 | 필요한 범위만 로드 | 메모리 절약 |

---

## 6.6 이 단계의 핵심 정리

```
✅ 원본 파일에 "w" 모드로 직접 쓰면 에러 시 데이터가 날아간다
✅ 원자적 쓰기 = ①.tmp에 쓰기 → ②정상 확인 → ③os.replace()로 교체
✅ os.replace()는 OS 커널이 원자성을 보장한다 (절반만 교체 불가능)
✅ 에러 시 .tmp만 삭제하면 원본은 완벽하게 안전하다
✅ delete()는 "삭제 대상 제외하고 나머지만 모아서 교체"
✅ update()는 "수정 대상을 새 데이터로 바꿔서 모아서 교체"
✅ 시간/공간 복잡도는 O(N)이며, 대용량 시 병목이 될 수 있다
✅ _atomic_write_lines()는 BaseRepository에 한 번만 구현하고 4개 자식이 재사용한다
```

### 6.6.1 다른 사람에게 설명하는 연습

> **질문**: "파일 기반 update/delete를 어떻게 안전하게 처리했나요?"
>
> **답변 예시**: "JSONL 파일은 중간 줄만 삭제하거나 수정하는 것이 물리적으로 불가능합니다. 그래서 전체 내용을 읽으면서 삭제할 건은 제외하고(또는 수정할 건은 교체하고), 나머지를 새 리스트로 모읍니다. 그런데 이 리스트를 원본 파일에 바로 'w' 모드로 쓰면, 쓰다가 에러가 나면 원본 데이터까지 날아갑니다. 그래서 '원자적 쓰기'를 구현했습니다. 먼저 임시 파일(.tmp)에 새 내용을 완전히 쓰고, 정상적으로 닫힌 것을 확인한 후, os.replace()로 한순간에 원본 파일명으로 교체합니다. os.replace()는 OS 커널이 원자성을 보장하므로, 정전이 나더라도 파일이 반쯤 교체된 상태가 되지 않습니다. 만약 .tmp 쓰기 도중 에러가 나면, .tmp만 삭제하고 원본은 그대로 두어 데이터를 안전하게 보호합니다."

---

---
---

# 📘 7단계: 비즈니스 서비스(service.py) — 두뇌의 로직

> **이 단계의 목표**: 데이터 검증, ID 자동 발급, 카테고리 삭제 무결성, CSV 가져오기/내보내기 등 가계부의 "두뇌" 역할을 하는 `service.py`의 핵심 비즈니스 로직을 완벽히 이해합니다.

---

## 7.1 Service 계층이란 무엇인가?

### 7.1.1 3계층 아키텍처(3-Layer Architecture)의 완성

우리는 지금까지 데이터 정의(`models.py`)와 파일 입출력(`repository.py`)을 배웠습니다. 이제 퍼즐의 마지막 조각인 `service.py`를 맞출 차례입니다.

```
[CLI 계층] cli.py
  "사용자님, 날짜를 입력하세요!" → (2026-05-15)
       │
       ▼
[Service 계층] service.py (★★★★★ 여기가 두뇌!)
  "음, 이 날짜는 올바르군. 카테고리도 존재하는군.
   ID를 새로 발급해서 저장소에 넘겨야겠다!"
       │
       ▼
[Repository 계층] repository.py
  "파일 열고 한 줄 추가완료!"
```

### 7.1.2 Service가 하는 5가지 핵심 역할

1. **무결성 검증**: 등록되지 않은 카테고리를 쓰려는지 감시
2. **비즈니스 규칙 적용**: 카테고리를 지우면 그 카테고리를 쓰던 거래들은 어떻게 할 것인가?
3. **복잡한 계산**: 월별 수입/지출/예산 사용률 계산
4. **외부 연동**: CSV 파일 읽고 쓰기, ZIP 백업
5. **ID 발급**: 고유한 식별자 자동 생성

---

## 7.2 무결성과 의존성 관리 — "그냥 삭제하면 안 되나요?"

### 7.2.1 카테고리 삭제의 딜레마

`CategoryRepository.delete()`는 단순히 `categories.jsonl` 파일에서 그 줄을 지우는 역할만 합니다.
하지만 비즈니스 로직 관점에서 보면 **치명적인 문제**가 생깁니다.

**상황**: "식비" 카테고리를 삭제하려고 합니다. 그런데 과거 거래 중에 "식비"로 등록된 거래가 100건 있습니다.
- 만약 카테고리만 지워버리면? → 과거 거래 100건은 "존재하지 않는 유령 카테고리"를 가리키게 됩니다 (데이터 무결성 파괴!)

### 7.2.2 service.py의 해결책 (service.py 241~263번째 줄)

```python
def remove_category(self, name: str, fallback_category: str = "기타") -> Tuple[int, bool]:
    # ① 카테고리 삭제 시도
    success = self.cat_repo.delete(name)
    if not success:
        return 0, False    # 삭제 실패 (카테고리 없음)
        
    # ② fallback_category("기타")가 없다면 생성
    if not self.cat_repo.exists(fallback_category):
        self.cat_repo.save(Category(name=fallback_category))
        
    affected_count = 0
    
    # ③ 삭제된 카테고리를 쓰고 있던 거래들을 찾아서 "기타"로 변경!
    for tx in self.tx_repo.find_all_stream():
        if tx.category == name:
            tx.category = fallback_category    # 카테고리 이관
            self.tx_repo.update(tx)            # 업데이트
            affected_count += 1
            
    return affected_count, True    # 몇 건이 이관되었는지 반환
```

**이것이 비즈니스 로직입니다!** 
"삭제해라"라는 단순한 명령 이면에, 데이터의 일관성을 유지하기 위한 **규칙(Rule)**이 숨어있는 곳이 바로 서비스 계층입니다.

---

## 7.3 월별 요약과 예산 분석 (service.py 166~215번째 줄)

`summary` 명령어는 단순히 합계만 구하는 것이 아니라, 예산(Budget)과 비교하여 "얼마나 초과했는지"까지 계산합니다.

### 7.3.1 제너레이터를 활용한 합산 로직

```python
def get_monthly_summary(self, month: str) -> Dict[str, Any]:
    total_income = 0
    total_expense = 0
    
    # 제너레이터로 전체 데이터를 훑으면서 해당 월(month)의 거래만 합산! (O(1) 메모리)
    for tx in self.tx_repo.find_all_stream():
        if tx.date.startswith(month):    # 예: "2026-05-15".startswith("2026-05") -> True
            if tx.type == "income":
                total_income += tx.amount
            elif tx.type == "expense":
                total_expense += tx.amount
                
    balance = total_income - total_expense
```

**핵심 통찰**: 날짜 문자열 비교! `datetime` 객체로 바꾸지 않고 단순히 `startswith()` 문자열 검사만으로 월(month) 필터링을 아주 빠르게 처리합니다.

### 7.3.2 예산(Budget)과의 결합

```python
    budget_limit = 0
    usage_percent = 0.0
    over_budget = False
    
    # 해당 월의 예산(Budget) 정보 조회
    budget_obj = self.budget_repo.find_by_month(month)
    if budget_obj:
        budget_limit = budget_obj.amount
        if budget_limit > 0:
            # 사용률 = (지출 합계 / 예산) * 100
            usage_percent = (total_expense / budget_limit) * 100
            if total_expense > budget_limit:
                over_budget = True    # 예산 초과!
```

이 계산 결과를 딕셔너리로 포장해서 `cli.py`로 넘겨주면, `cli.py`가 화면에 예쁘게 표로 그려줍니다.

---

## 7.4 외부 연동: CSV 가져오기와 내보내기

미션에서 요구하는 엑셀 호환 CSV 포맷:
`ID,Type,Date,Amount,Category,Memo,Tags`

### 7.4.1 내보내기 (Export) (service.py 289~309번째 줄)

```python
@log_execution_time
def export_csv(self, filepath: str) -> int:
    count = 0
    
    # "w" 모드로 새 CSV 파일 열기. newline=""는 CSV 표준 모범 사례
    with open(filepath, "w", encoding="utf-8", newline="") as csvfile:
        writer = csv.writer(csvfile)
        
        # 1. 헤더(첫 줄) 쓰기
        writer.writerow(["ID", "Type", "Date", "Amount", "Category", "Memo", "Tags"])
        
        # 2. 거래 데이터를 한 건씩 스트리밍으로 읽어와서 쓰기
        for tx in self.tx_repo.find_all_stream():
            writer.writerow([
                tx.id,
                tx.type,
                tx.date,
                tx.amount,
                tx.category,
                tx.memo,
                ",".join(tx.tags)  # ["식비", "야식"] → "식비,야식" 문자열로 변환
            ])
            count += 1
    return count
```

**데코레이터 활용**: 이 작업은 파일이 10만 건이면 오래 걸리므로, 위에 `@log_execution_time`을 붙여서 몇 초 걸렸는지 측정합니다! (8단계에서 상세 설명)

### 7.4.2 가져오기 (Import) — 깨진 행 방어 메커니즘 (service.py 312~351번째 줄)

초심자가 가장 많이 실수하는 부분: "CSV 100줄 가져오다가 50번째 줄에서 에러 나면 어떡하지?"

```python
@log_execution_time
def import_csv(self, filepath: str) -> Tuple[int, int]:
    success_count = 0
    fail_count = 0
    
    with open(filepath, "r", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)    # 첫 줄을 헤더(Key)로 인식해서 딕셔너리로 읽음!
        
        for row in reader:
            try:
                # CSV에서 읽은 문자열 데이터를 검증하면서 타입 변환
                date_val = validate_date(row["Date"])
                type_val = validate_type(row["Type"])
                amt_val = validate_amount(row["Amount"])
                cat_val = row["Category"].strip()
                memo_val = row.get("Memo", "").strip()
                
                # Tags가 비어있지 않으면 쉼표로 분리하여 리스트로 만듦
                raw_tags = row.get("Tags", "")
                tags_val = [t.strip() for t in raw_tags.split(",")] if raw_tags else []
                
                # 검증에 통과하면 거래 추가 (save)
                self.add_transaction(
                    date=date_val, type_str=type_val, category=cat_val,
                    amount=amt_val, memo=memo_val, tags=tags_val
                )
                success_count += 1
                
            except Exception as e:
                # 어떤 한 줄에서 에러가 발생하더라도 멈추지 않고, 실패 카운트만 올리고 다음 줄로 넘어감!
                fail_count += 1
                
    return success_count, fail_count
```

**이것이 "부분 성공(Partial Success)" 전략입니다!** 
만약 에러가 났다고 프로그램을 종료해버리면, 사용자는 깨진 1줄 때문에 99줄의 정상 데이터도 가져올 수 없게 됩니다.

---

## 7.5 [보너스] 백업 기능과 ZIP 압축 (service.py 416~435번째 줄)

미션 5.1의 요구사항인 "모든 데이터를 하나의 파일로 묶어서 저장하기"를 구현합니다.

```python
@log_execution_time
def backup_data(self, backup_dir: str = "backups") -> str:
    # 백업 폴더가 없으면 생성
    os.makedirs(backup_dir, exist_ok=True)
    
    # 백업 파일명 생성: "backup_20260530_092000.zip"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"backup_{timestamp}.zip"
    backup_path = os.path.join(backup_dir, backup_filename)
    
    # 백업 대상 4개 파일 목록
    target_files = [
        "transactions.jsonl", "categories.jsonl", 
        "budgets.jsonl", "recurring.jsonl", "activity.log"
    ]
    
    # zipfile 라이브러리를 사용해 압축! (ZIP_DEFLATED 옵션으로 용량 최소화)
    with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for fname in target_files:
            file_to_zip = os.path.join(self.data_dir, fname)
            if os.path.exists(file_to_zip):
                # 파일의 실제 경로와 ZIP 내부에서 보일 이름(아크이름)을 지정
                zipf.write(file_to_zip, arcname=fname)
                
    return backup_path
```

**`arcname`의 중요성**: `arcname=fname`을 안 주면, ZIP 파일을 풀었을 때 `Users/사용자/Desktop/glad/data/transactions.jsonl`처럼 전체 절대 경로 폴더 트리가 함께 압축되는 대참사가 발생합니다.

---

## 7.6 이 단계의 핵심 정리

```
✅ Service는 비즈니스 규칙(도메인 지식)이 담겨 있는 "두뇌" 계층이다
✅ ID는 기존 데이터를 읽어서 가장 큰 번호 + 1로 자동 발급된다
✅ 카테고리를 삭제하면, 그 카테고리를 쓰던 과거 거래는 "기타"로 자동 이관된다
✅ 월별 조회는 startswith() 문자열 비교로 초고속 처리된다
✅ CSV 가져오기(Import)는 에러가 난 줄은 건너뛰고 정상인 줄만 넣는 "부분 성공"을 택한다
✅ 백업은 zipfile 표준 라이브러리로 전체 data 파일을 한 번에 압축한다
```

### 7.6.1 다른 사람에게 설명하는 연습

> **질문**: "import CSV에 일부 깨진 행이 섞이면 어떻게 처리하나요?"
>
> **답변 예시**: "파일을 한꺼번에 처리하면 중간에 깨진 데이터 1건 때문에 전체 작업이 롤백되거나 크래시 날 수 있습니다. 그래서 service.py의 import_csv 함수에서는 CSV의 매 행(row)을 순회할 때 try-except 블록으로 감쌉니다. 정상 행은 성공적으로 저장(success_count 증가)하고, 날짜 포맷이 틀렸거나 금액이 문자로 적힌 깨진 행을 만나면 예외를 무시하고 fail_count만 증가시킨 뒤 바로 다음 행으로 넘어갑니다. 작업이 끝나면 사용자에게 'N건 성공, M건 실패' 리포트를 출력하여 사용자의 신뢰를 지킵니다."

---
---

# 📘 8단계: 데코레이터 — 관심사 분리의 기술

> **이 단계의 목표**: `@` 기호로 시작하는 파이썬 데코레이터의 완벽한 원리, `functools.wraps`의 역할, 그리고 예외 처리/로깅/시간 측정을 데코레이터로 분리하는 이유(관심사 분리)를 이해합니다.

---

## 8.1 데코레이터란 무엇인가? — "포장지" 비유

### 8.1.1 일상생활 비유

선물을 준다고 가정해 봅시다:
- **핵심 로직 (함수)** = "스마트폰" (선물 내용물)
- **데코레이터** = "예쁜 포장지와 리본"

우리는 스마트폰 자체(핵심 로직)를 분해해서 포장지를 집어넣지 않습니다. 스마트폰은 그대로 둔 채, 그 겉을 예쁜 상자로 감쌉니다.

프로그래밍에서도 마찬가지입니다:
```python
# ❌ 포장지가 내용물과 섞인 경우 (데코레이터 없음)
def add_transaction():
    start_time = time.time()       # ──┐
    print("로그 기록 시작")        #   │ ← 포장지 (부가 기능)
    try:                           # ──┘
        
        # [핵심 비즈니스 로직]
        tx = Transaction(...)
        save(tx)
        
    except Exception as e:         # ──┐
        print("에러 발생!")        #   │ ← 포장지 (부가 기능)
    end_time = time.time()         #   │
    print("소요 시간:", end_time)  # ──┘
```

코드의 절반 이상이 비즈니스 로직과 무관한 "시간 측정", "예외 처리", "로깅"입니다. 이걸 100개의 함수에 다 복붙해야 할까요?

### 8.1.2 데코레이터를 쓰면 어떻게 바뀌는가?

```python
# ✅ 포장지를 분리한 경우 (데코레이터 사용)
@log_time        # 시간 측정 포장지
@handle_error    # 예외 처리 포장지
def add_transaction():
    # [오직 핵심 로직만 존재!]
    tx = Transaction(...)
    save(tx)
```

이것을 **"관심사 분리(Separation of Concerns, SoC)"** 또는 **"관점 지향 프로그래밍(AOP)"**이라고 부릅니다. 핵심 비즈니스 로직은 핵심만 남기고, 공통 기능(시간 측정, 오류 처리)은 데코레이터로 분리하는 기술입니다.

---

## 8.2 데코레이터 1: `@handle_errors_gracefully`

미션 요구사항: "잘못된 입력이나 파일 입출력 오류 상황에서 스택트레이스를 노출하지 않고 에러 메시지와 힌트를 제공할 것."

### 8.2.1 코드 완전 해부 (decorators.py 16~50번째 줄)

```python
def handle_errors_gracefully(func: Callable[..., Any]) -> Callable[..., Any]:
    
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            # ① 원래 실행하려던 함수를 여기서 실행!
            return func(*args, **kwargs)
            
        except FileNotFoundError as e:
            # ② 파일 관련 에러가 터지면 가로채서 한글로 예쁘게 출력
            print(f"\n[오류] 데이터를 보관할 파일을 찾을 수 없습니다.")
            print(f"[상세] {e.filename}")
            print("[힌트] 저장 폴더 경로와 권한을 확인하세요.")
            sys.exit(1)    # 비정상 종료 (에러 코드 1)
            
        except ValueError as e:
            # ③ 입력값 오류 가로채기
            print(f"\n[오류] 입력값 또는 데이터 형식이 올바르지 않습니다.")
            print(f"[원인] {e}")
            sys.exit(1)
            
        except Exception as e:
            # ④ 나머지 모든 종류의 예상치 못한 시스템 에러 가로채기
            print(f"\n[오류] 예상치 못한 시스템 문제가 발생했습니다: {e}")
            sys.exit(1)

    return wrapper    # 포장된 새 함수(wrapper)를 반환
```

### 8.2.2 `*args`, `**kwargs`란 무엇인가?

데코레이터는 "어떤 함수"에 붙을지 모릅니다:
- 인자가 없는 함수 `run_cli()`에 붙을 수도 있고
- 인자가 3개인 함수 `add(a, b, c)`에 붙을 수도 있습니다.

`*args`(위치 인자 전부 모음)와 `**kwargs`(키워드 인자 전부 모음)를 쓰면 **어떤 인자가 몇 개 들어오든 그대로 받아서 원본 함수에 전달**할 수 있습니다. 즉, **"만능 전달자"**입니다.

### 8.2.3 `@functools.wraps(func)`는 왜 필요한가?

파이썬에서 함수를 다른 함수(`wrapper`)로 덮어씌우면, 원본 함수의 "이름(`__name__`)"과 "도움말(`__doc__`)"이 모두 `wrapper`라는 이름으로 바뀌어 버리는 버그가 생깁니다.

이 데코레이터를 붙여주면 **"비록 껍데기는 wrapper지만, 내 이름표와 명찰은 원래 함수(func)의 것을 그대로 유지해라!"**라고 파이썬에게 알려줍니다.

---

## 8.3 데코레이터 2: `@log_execution_time`

미션 밖의 추가 기능이지만, 실무에서 가장 많이 쓰는 성능 측정 데코레이터입니다.

### 8.3.1 코드 해부 (decorators.py 53~73번째 줄)

```python
def log_execution_time(func: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        # 1. 시작 버튼 누르기
        start_time = time.perf_counter()
        
        # 2. 본래 작업 수행
        result = func(*args, **kwargs)
        
        # 3. 종료 버튼 누르고 시간 계산
        end_time = time.perf_counter()
        elapsed = end_time - start_time
        
        # 4. 결과 출력
        print(f"[성능 로그] '{func.__name__}' 작업 소요 시간: {elapsed:.4f}초")
        
        # 5. 원래 반환해야 할 결과값 돌려주기
        return result

    return wrapper
```

**`time.time()` 대신 `time.perf_counter()`를 쓰는 이유**:
`time.time()`은 시스템 시계(운영체제의 현재 시각)를 기준하므로 누군가 중간에 윈도우 시계를 1시간 뒤로 돌리면 소요 시간이 -1시간이 되는 버그가 납니다. 반면 `perf_counter()`는 무조건 "컴퓨터가 켜진 이후의 절대적인 틱(Tick)"을 세므로 성능 측정에 완벽합니다.

**어디에 쓰였나?**: (service.py) `export_csv`, `import_csv`, `backup_data`, `generate_recurring` 등 무겁고 오래 걸리는 파일 I/O 작업들에 붙어 있습니다.

---

## 8.4 데코레이터 3: `@log_activity()` (팩토리 패턴)

이것이 가장 복잡한 구조입니다. 왜냐하면 데코레이터가 **매개변수**를 받기 때문입니다.

### 8.4.1 왜 3중 중첩인가?

```python
# 보통의 데코레이터 (2중)
@log_execution_time
def func(): pass

# 매개변수를 받는 데코레이터 (3중)
@log_activity(log_filepath="data/activity.log")
def func(): pass
```

위의 `@log_activity(...)`는 사실 데코레이터 자체가 아닙니다! **"데코레이터를 만들어내는 공장(Factory)"**입니다.

### 8.4.2 코드 해부 (decorators.py 76~106번째 줄)

```python
# 1층: 데코레이터 팩토리 (매개변수 log_filepath를 받음)
def log_activity(log_filepath: str = "data/activity.log") -> Callable[..., Any]:
    
    # 2층: 진짜 데코레이터 (함수를 받음)
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        
        # 3층: 실행되는 래퍼 (인자를 받음)
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            
            # ① 일단 본 작업(수정, 추가 등) 먼저 실행
            result = func(*args, **kwargs)
            
            # ② 로깅 시도 (실패해도 본 작업 결과는 건드리지 않음)
            try:
                os.makedirs(os.path.dirname(log_filepath), exist_ok=True)
                with open(log_filepath, "a", encoding="utf-8") as log_file:
                    now_str = time.strftime("%Y-%m-%d %H:%M:%S")
                    # 함수 이름과 매개변수를 파일에 쓴다
                    log_file.write(f"[{now_str}] '{func.__name__}' 기능 호출. 매개변수: {args[1:]}\n")
            except Exception:
                pass    # 로깅 실패는 조용히 무시 (본 작업이 더 중요하므로)
                
            # ③ 원래 결과 반환
            return result
            
        return wrapper
    return decorator
```

이 데코레이터는 (service.py) `add_transaction`, `update_transaction`, `remove_category` 등 중요한 데이터를 **"변경"**하는 핵심 함수들에 붙어 있어서, 무슨 일이 일어났는지 나중에 감사(Audit)할 수 있게 증거를 남깁니다.

---

## 8.5 이 단계의 핵심 정리

```
✅ 데코레이터는 기존 코드를 수정하지 않고 부가 기능을 덧붙이는 "포장지" 기술이다
✅ 이를 통해 핵심 비즈니스 로직과 공통 관심사(오류 처리, 시간 측정)를 분리한다 (관심사 분리)
✅ *args, **kwargs는 어떤 인자가 몇 개 들어오든 원본 함수로 안전하게 전달하는 만능 전달자다
✅ @functools.wraps(func)는 원본 함수의 이름과 도움말을 잃어버리지 않게 지켜준다
✅ @handle_errors_gracefully는 시스템 에러를 잡아 사용자 친화적 힌트로 바꿔준다
✅ 데코레이터에 매개변수를 넘기려면 3중 중첩 함수(팩토리 패턴)를 만들어야 한다
```

### 8.5.1 다른 사람에게 설명하는 연습

> **질문**: "데코레이터로 분리한 공통 기능이 무엇이며, 왜 분리가 필요한가요?"
>
> **답변 예시**: "우리 가계부 프로그램에는 모든 명령어의 에러를 잡아서 한글 힌트로 보여주는 기능(handle_errors_gracefully)과, 무거운 작업의 실행 시간을 재는 기능(log_execution_time)이 있습니다. 만약 이 기능들을 데코레이터로 분리하지 않으면, try-except 블록과 시작/종료 시간 측정 코드를 모든 함수(add, list, search, import 등) 내부에 일일이 복사+붙여넣기 해야 합니다. 이러면 코드가 뚱뚱해지고 진짜 비즈니스 로직이 파묻혀 읽기 힘들어집니다. 데코레이터로 분리하면 핵심 로직은 본연의 임무에만 집중할 수 있고, 공통 기능은 함수 위에 '@' 기호 하나만 붙여서 깔끔하게 재사용할 수 있습니다. 이를 객체지향 설계에서 '관심사 분리(Separation of Concerns)'라고 부릅니다."

---
---

# 📘 9단계: CLI 표현 계층 — 사용자와의 대화

> **이 단계의 목표**: 사용자의 입력을 파싱하는 `argparse`의 원리, 튕기지 않고 무한 반복해서 입력을 받아내는 대화형 프롬프트 로직, 그리고 한글/영문 길이를 정확히 맞춰 터미널 표(Table)를 예쁘게 그리는 `utils.py`의 동아시아 폭 계산 원리를 완벽히 이해합니다.

---

## 9.1 `argparse` — 명령어 파싱의 마법사

`cli.py`에서 가장 먼저 만나는 것은 `argparse` 라이브러리입니다.

### 9.1.1 파싱(Parsing)이란?

사용자가 터미널에 이렇게 입력했습니다:
`python -m budget_app search --type income --category 식비`

이 긴 문자열을 컴퓨터는 어떻게 이해할까요?
`argparse`가 이 문자열을 쪼개고 분석해서 **"파이썬 딕셔너리 같은 객체(Namespace)"**로 예쁘게 정리해 줍니다.

### 9.1.2 코드 분석 (cli.py 71~124번째 줄)

```python
# 1. 메인 파서 정의 (전체 프로그램의 도움말)
parser = argparse.ArgumentParser(
    prog="python -m budget_app",
    description="★ 스마트 가계부 콘솔 서비스 ★",
)

# 2. 서브커맨드(add, list, search 등)를 담을 공간 생성
subparsers = parser.add_subparsers(dest="command", help="실행할 명령어를 선택해 주세요.")

# 3. 'list' 서브커맨드 정의
list_parser = subparsers.add_parser("list", help="최신순 거래 리스트 조회")
list_parser.add_argument("--limit", type=int, default=None)

# 4. 'search' 서브커맨드 정의
search_parser = subparsers.add_parser("search", help="정밀 검색")
search_parser.add_argument("--from", dest="from_date", help="시작 날짜")
# (생략)
```

**`dest="command"`의 의미**:
사용자가 입력한 명령어(add, list 등)가 파싱된 결과 객체(`args`)의 `command`라는 변수에 저장되도록 합니다.
즉, `args.command == "add"` 형태로 조건을 체크할 수 있게 됩니다.

**`add_argument("--limit", type=int)`의 의미**:
사용자가 `--limit 10`이라고 치면, "10"이라는 문자열을 자동으로 정수(`int`)로 변환해서 `args.limit`에 넣어줍니다!

---

## 9.2 대화형 입력 루프 (Interactive Prompt)

미션의 숨겨진 난관: "사용자가 날짜를 잘못 입력했다고 해서 프로그램이 꺼지고 다시 `python -m ...`부터 시작하게 하면 안 됩니다!"

### 9.2.1 만능 입력기 `prompt_interactive` (cli.py 28~61번째 줄)

```python
def prompt_interactive(
    prompt_text: str,                 # 화면에 띄울 질문 (예: "날짜를 입력하세요: ")
    validator: Callable[[str], Any],  # 입력값을 검사할 함수 (예: validate_date)
    optional: bool = False,           # 엔터(빈 값) 허용 여부
    default_val: str = ""             # 빈 값일 때 대신 쓸 기본값
) -> Any:
    
    # 무한 루프 시작! 통과할 때까지 나가지 못합니다.
    while True:
        try:
            # 1. 사용자 입력 받기
            user_input = input(prompt_text).strip()
            
            # 2. 필수값인데 비웠을 경우
            if not user_input and not optional:
                raise ValueError("이 항목은 비워둘 수 없는 필수 항목입니다.")
                
            # 3. 선택값인데 비웠을 경우
            if not user_input and optional:
                return validator(default_val) if default_val else ""
                
            # 4. 입력값이 있으면 검증기에 통과시키기
            return validator(user_input)
            
        except ValueError as e:
            # 5. 검증기에서 에러 발생! (프로그램 끄지 않고 안내문 출력 후 재시작)
            print(f"  └ [오류] {e}")
            print("  └ [힌트] 입력 형식을 다시 확인하시고 올바른 값을 적어주세요.\n")
```

### 9.2.2 `add` 명령어에서의 활용 (cli.py 134~152번째 줄)

이 만능 함수를 사용하면 `add` 로직이 믿을 수 없을 만큼 깔끔해집니다:

```python
if args.command == "add":
    print("\n[새로운 거래 내역 추가]")
    # 오늘 날짜를 기본값으로 제공!
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    date_val = prompt_interactive(
        f"1. 날짜 (YYYY-MM-DD) [엔터시 오늘날짜 {today_str}]: ", 
        validate_date, optional=True, default_val=today_str)
        
    type_val = prompt_interactive("2. 분류 (income / expense): ", validate_type)
    
    cat_val = prompt_interactive("3. 카테고리 (예: 식비, 수입): ", lambda x: x)
    
    amt_val = prompt_interactive("4. 금액 (0보다 큰 양수): ", validate_amount)
    
    memo_val = prompt_interactive("5. 메모 (선택사항, 엔터시 생략): ", lambda x: x, optional=True)
```

**`lambda x: x`의 의미**: 
카테고리나 메모는 문자열 그 자체이므로 특별한 형식 검사나 형변환이 필요 없습니다. "입력받은 것(`x`)을 그대로 반환(`x`)해라"라는 가장 단순한 익명 함수입니다.

---

## 9.3 `utils.py` — 터미널 표(Table) 정렬의 비밀

가계부 데이터를 터미널에 예쁘게 표로 그리려면 엄청난 난관이 하나 있습니다. 바로 **"한글"**입니다.

### 9.3.1 동아시아 글자 폭(East Asian Width)의 딜레마

파이썬의 `len("가")`와 `len("A")`는 둘 다 결과가 `1`입니다.
하지만 터미널에서 출력해보면:
- `A`는 가로로 1칸을 차지합니다 (반각, Half-width)
- `가`는 가로로 2칸을 차지합니다 (전각, Full-width)

따라서 `len()`을 믿고 20칸짜리 표를 그리면:
```
[len() 기준으로 정렬한 경우 - 삐뚤빼뚤 💥]
식비                  | 12,000원
서브웨이 샌드위치     | 8,000원
ABC 마트              | 50,000원
```
한글이 섞이는 순간 표가 완전히 붕괴됩니다!

### 9.3.2 해결책: `get_display_width` (utils.py 20~35번째 줄)

우리는 외부 라이브러리(`tabulate`, `rich` 등)를 쓸 수 없으므로, 문자열의 시각적 길이를 직접 계산해야 합니다. `unicodedata`라는 파이썬 기본 라이브러리를 사용합니다.

```python
import unicodedata

def get_display_width(text: str) -> int:
    width = 0
    for char in text:
        # unicodedata.east_asian_width(char)는 글자의 종류를 반환합니다.
        # 'W' (Wide) = 한글, 한자, 일본어 등 → 화면에서 2칸 차지
        # 'F' (Fullwidth) = 전각 영문/기호 → 화면에서 2칸 차지
        if unicodedata.east_asian_width(char) in ('W', 'F'):
            width += 2
        else:
            # 영문, 숫자, 일반 기호 등은 1칸 차지
            width += 1
    return width
```

이제 "가A"를 넣으면 `len()`은 2를 반환하지만, `get_display_width()`는 3 (2+1)을 반환합니다. 정확히 화면에 보이는 칸 수와 일치하게 됩니다!

### 9.3.3 공백 채우기 로직: `pad_string` (utils.py 38~53번째 줄)

원하는 칸 수(예: 20칸)만큼 왼쪽/오른쪽으로 공백을 채워 넣는 함수입니다.

```python
def pad_string(text: str, total_width: int, align: str = 'left') -> str:
    # 1. 이 글씨가 화면에서 몇 칸을 차지하는지 계산
    current_width = get_display_width(text)
    
    # 2. 채워 넣어야 할 빈칸(스페이스) 갯수 계산
    padding_size = total_width - current_width
    if padding_size <= 0:
        return text    # 이미 꽉 찼으면 그냥 반환
        
    # 3. 정렬 방향에 따라 빈칸 붙이기
    padding = " " * padding_size
    if align == 'right':
        return padding + text
    elif align == 'center':
        left_pad = " " * (padding_size // 2)
        right_pad = " " * (padding_size - len(left_pad))
        return left_pad + text + right_pad
    else: # 기본값은 왼쪽 정렬
        return text + padding
```

### 9.3.4 `print_table` — 모든 것을 합치기 (utils.py 56~97번째 줄)

이 두 함수를 결합하면 터미널에 아름다운 표를 그릴 수 있습니다.

```python
def print_table(headers: List[str], rows: List[List[Any]], col_widths: List[int], aligns: List[str] = None):
    # (예시 데이터)
    # headers = ["ID", "Category", "Amount"]
    # col_widths = [12, 15, 12]
    # aligns = ['left', 'center', 'right']
    
    # 1. 헤더 그리기
    header_str = " | ".join(pad_string(h, w, a) for h, w, a in zip(headers, col_widths, aligns))
    print(header_str)
    
    # 2. 구분선 긋기 (총 길이에 맞춰서 '-', '+' 기호 배치)
    separator_str = "-+-".join("-" * w for w in col_widths)
    print(separator_str)
    
    # 3. 데이터 행 그리기
    for row in rows:
        row_str_list = [str(item) for item in row]    # 모두 문자열로 변환 (숫자 포함)
        row_str = " | ".join(pad_string(item, w, a) for item, w, a in zip(row_str_list, col_widths, aligns))
        print(row_str)
```

이 덕분에 우리 가계부는 `list`나 `search`를 쳤을 때 외부 라이브러리 없이도 완벽한 좌/우 정렬 표를 보여줄 수 있습니다.

---

## 9.4 이 단계의 핵심 정리

```
✅ argparse를 통해 복잡한 터미널 인자를 딕셔너리(Namespace)로 쉽게 파싱한다
✅ while True 루프와 try-except를 결합하여 "성공할 때까지 무한 질문하는" 대화형 프롬프트를 만들었다
✅ lambda x: x는 아무런 검증/변환 없이 입력값을 그대로 통과시키는 익명 함수다
✅ 한글은 영문 2글자 폭을 차지하므로 len()으로는 표 정렬이 불가능하다
✅ unicodedata.east_asian_width()를 활용해 시각적 렌더링 길이를 직접 계산하여 표를 그렸다
```

---

---
---

# 🏆 10단계 (최종): 평가 대비 — 16가지 기준 완전 정복

---

## 💡 [항목 1] 필수 기능 및 동작 검증 (8개)

이 항목들은 "프로그램이 스펙대로 정상 작동하는가?"를 묻는 팩트(Fact) 체크입니다. 프로그램 시연을 통해 쉽게 증명할 수 있습니다.

**1. add/list/search/summary/export/import/update/delete가 요구사항대로 동작하는가?**
> **답변**: "네, CLI의 argparse와 대화형 프롬프트를 통해 8가지 핵심 기능이 모두 완벽하게 동작합니다. 특히 update는 대화형(안 B)으로 구현하여 사용자가 편리하게 수정할 수 있습니다."

**2. 프로그램 재실행 후에도 거래/카테고리/예산 데이터가 유지되는가?**
> **답변**: "네, 메모리가 아닌 `data/` 폴더 하위의 파일들(`transactions.jsonl`, `categories.jsonl`, `budgets.jsonl`, `recurring.jsonl`)에 영구 저장되므로 재실행해도 데이터가 완벽히 유지됩니다."

**3. category add/list/remove가 정상 동작하는가? (삭제 시 사용 중인 카테고리 처리 포함)**
> **답변**: "네, 단순히 카테고리만 지우는 것이 아니라, `BudgetService.remove_category()`에서 해당 카테고리를 쓰던 과거 거래들을 찾아서 자동으로 '기타' 카테고리로 이관(Fallback)하여 데이터 무결성을 지켰습니다."

**4. budget set이 저장되며, summary에서 예산 사용률/초과 여부가 출력되는가?**
> **답변**: "네, `budgets.jsonl`에 월별 예산이 저장되며, `summary` 명령어를 칠 때 제너레이터로 지출 합계를 구한 뒤 예산과 나누어 사용률(%)을 계산하고, 초과 시 터미널에 [예산 초과!] 경고가 예쁘게 출력됩니다."

**5. import/export가 명시된 CSV 스키마(UTF-8, 헤더, 컬럼)로 동작하는가?**
> **답변**: "네, 파이썬 내장 `csv` 모듈을 사용하여 UTF-8 인코딩으로 `ID,Type,Date,Amount,Category,Memo,Tags` 헤더 순서에 맞춰 정확히 내보내고 읽어옵니다."

**6. 잘못된 입력/파일 오류에서 스택트레이스 없이 오류 메시지와 해결 힌트를 출력하는가?**
> **답변**: "네, `decorators.py`에 구현한 `@handle_errors_gracefully` 데코레이터를 최상단 CLI 진입점에 붙여서, ValueError나 FileNotFoundError를 가로채어 원인과 한글 힌트로 번역해서 출력합니다."

**7. 오류 상황에서 종료 코드가 0이 아님을 확인할 수 있는가?**
> **답변**: "네, 데코레이터에서 에러를 낚아챘을 때 `sys.exit(1)`을 호출하여 비정상 종료(0이 아님)임을 OS에 확실히 알립니다."

---

## 🧠 [항목 2] 아키텍처 및 설계 원리 (3개)

여기서부터는 "코드를 직접 설계하고 이해했는가?"를 묻는 심층 질문입니다.

**8. 코드가 3개 이상 모듈로 분리되어 있고, 각 모듈의 책임을 “어떻게” 나눴는지 설명할 수 있는가?**
> **모범 답안**: "네, 저는 3계층 아키텍처(3-Tier) 패턴을 따라 모듈을 5개로 분리했습니다.
> 1) **models.py**: 데이터의 생김새(Transaction 등)를 정의하는 뼈대입니다.
> 2) **repository.py**: 파일 I/O를 전담하는 '사서'입니다. 파일에 쓰고 읽는 역할만 합니다.
> 3) **service.py**: 카테고리 무결성이나 예산 계산 등 비즈니스 규칙을 집행하는 '두뇌'입니다.
> 4) **cli.py**: 사용자의 입력을 받고 결과를 보여주는 '얼굴'입니다.
> 5) **decorators.py/utils.py**: 에러 처리나 표 그리기 같은 공통 도구를 모아둔 공구상자입니다.
> 이렇게 나누니 파일 입출력 로직을 고칠 때 CLI나 모델 코드를 건드릴 필요가 없어 유지보수가 매우 쉬워졌습니다."

**9. 최소 2개 이상의 클래스에 부여한 책임 경계를 “어떻게” 정했는지 설명할 수 있는가?**
> **모범 답안**: "저장소 계층에서 `BaseRepository`와 `TransactionRepository` 클래스로 경계를 나누었습니다. 
> `BaseRepository`는 '어느 파일이든 JSONL을 한 줄씩 읽고 쓰는 기본 공통 로직(원자적 쓰기 등)'이라는 책임을 가집니다. 반면 자식인 `TransactionRepository`는 파일 경로를 알려주고, 딕셔너리를 Transaction 객체로 변환하는 '거래 데이터 특화 로직'에만 책임을 집니다. 이렇게 부모-자식으로 책임을 나누니 코드 중복이 완벽히 사라졌습니다."

**10. 파일 기반 update/delete를 “어떻게” 안전하게 처리했는지 설명할 수 있는가?**
> **모범 답안**: "JSONL은 중간 줄만 수정하는 게 불가능해서 전체 파일을 덮어써야 합니다. 이때 'w' 모드로 덮어쓰다 에러가 나면 원본이 날아가므로 **'원자적 쓰기(Atomic Write)'**를 도입했습니다. 먼저 `.tmp` 임시 파일에 수정된 전체 데이터를 쓴 다음, 쓰기가 정상적으로 끝나면 `os.replace()`를 통해 OS 커널 레벨에서 원본 파일과 한순간에 교체합니다. 도중에 에러가 나면 임시 파일만 삭제하면 되므로 원본 데이터가 완벽하게 보호됩니다."

---

## 🚀 [항목 3] 파이썬 고급 문법 및 이점 (3개)

파이썬의 철학을 잘 이해하고 활용했는지 묻는 질문입니다.

**11. list/search를 제너레이터로 스트리밍 처리한 방식을 “어떻게” 구현했고, “왜” 유리한지 설명할 수 있는가?**
> **모범 답안**: "`find_all_stream()`이라는 함수 안에서 파일의 줄을 한 줄씩 읽으면서 `yield`를 사용해 데이터를 뱉어내도록 구현했습니다. 만약 파일에 거래 데이터가 10만 건이 있을 때 `return [리스트]` 방식을 쓰면 10만 건을 모두 메모리(RAM)에 올려야 해서 컴퓨터가 다운될 수 있습니다. 반면 제너레이터를 쓰면 한 줄 읽고 버리고, 한 줄 읽고 버리는 식이라 데이터가 100만 건이어도 메모리 사용량(공간 복잡도)이 언제나 O(1)로 일정하게 유지되는 엄청난 이점이 있습니다."

**12. 데코레이터로 분리한 공통 기능이 무엇이며, “왜” 분리가 필요했는지 설명할 수 있는가?**
> **모범 답안**: "예외 처리 힌트(`@handle_errors_gracefully`), 로깅(`@log_activity`), 실행 시간 측정(`@log_execution_time`)을 데코레이터로 분리했습니다. 만약 이걸 분리하지 않았다면 모든 비즈니스 함수 안에 `try-except` 블록과 `start_time`, `end_time` 코드를 수십 번 복붙해야 했을 겁니다. 데코레이터로 빼냄으로써 핵심 비즈니스 로직(내용물)과 공통 부가 기능(포장지)을 완벽히 분리하는 '관심사 분리'를 달성했고, 코드가 훨씬 깔끔해졌습니다."

**13. 타입 힌트를 적용해 얻는 이점을 실제 코드 예로 “어떻게” 확인했고 “왜” 도움이 되는지 설명할 수 있는가?**
> **모범 답안**: "모든 함수에 `def func(date: str) -> bool:` 형태로 타입 힌트를 달았습니다. 코딩할 때 `tx.d`까지만 쳐도 IDE가 `tx.date`를 자동 완성해 주어 오타를 극적으로 줄였습니다. 특히 `List[Transaction]`처럼 복잡한 반환 타입을 적어두니, 이 함수가 문자열 리스트를 주는지 객체 리스트를 주는지 문서를 보지 않아도 바로 알 수 있어 협업과 디버깅 속도가 엄청나게 빨라졌습니다."

---

## 🔮 [항목 4] 기술적 한계 및 미래 확장성 (3개)

"단순히 돌아가는 코드를 짠 게 아니라, 문제점을 인식하고 발전시킬 수 있는가?"를 묻는 킬러 문항입니다.

**14. JSONL과 CSV 중 선택한 저장 포맷의 장단점을 비교하고, “왜” 그 포맷을 택했는지 근거를 말할 수 있는가?**
> **모범 답안**: "기본 저장소로 CSV 대신 JSONL을 선택했습니다. CSV는 사람이 엑셀로 읽기는 편하지만, `tags`처럼 리스트 데이터(배열)나 줄바꿈이 들어간 다차원 데이터를 저장할 때 포맷이 깨지기 쉽습니다. 반면 JSONL은 한 줄마다 완벽한 JSON 객체를 담으므로 리스트나 딕셔너리를 직렬화/역직렬화하기 훨씬 안전하고 빠릅니다. 게다가 줄바꿈으로 데이터가 구분되므로 제너레이터 스트리밍 방식과 찰떡궁합이어서 선택했습니다."

**15. 거래가 10만 건으로 늘어난다면, 현재 구조에서 병목이 어디이며 “어떻게” 개선할지 설명할 수 있는가?**
> **모범 답안**: "현재의 병목은 `update`와 `delete`입니다. 1건만 수정하더라도 10만 건을 다 읽어서 임시 파일에 다시 쓴 후 교체해야 하므로(O(N)의 시간 복잡도) 굉장히 느려질 것입니다. 이를 개선하려면, ① 매번 파일 전체를 덮어쓰지 않아도 되는 SQLite 같은 진짜 관계형 데이터베이스(RDBMS)를 도입하거나, ② 메모리에 인덱스(B-Tree)를 캐싱해 두고 수정된 부분만 디스크 블록 단위로 덮어쓰는 별도의 커스텀 스토리지를 구현해야 합니다."

**16. import CSV에 일부 깨진 행이 섞이면, “어떻게” 처리해 사용자 신뢰를 지킬지(부분 성공/롤백/리포트) 설명할 수 있는가?**
> **모범 답안**: "저는 '부분 성공(Partial Success)' 방식을 채택했습니다. `service.py`의 `import_csv()` 안에서 CSV 행을 하나씩 돌 때 `try-except`로 감싸두었습니다. 날짜나 금액이 깨진 쓰레기 행을 만나면 에러를 내서 프로그램을 폭파시키는 게 아니라, 조용히 `fail_count`만 1 증가시키고 다음 정상 행을 계속 저장합니다. 마지막에 '90건 성공, 10건 실패'라고 정확한 리포트를 띄워줌으로써, 사용자가 살릴 수 있는 데이터는 다 살리게 하여 신뢰를 지켰습니다."

---
---

# 🎉 대단원의 막을 내리며

수고하셨습니다! 당신은 이제 이 3,500줄에 달하는 거대한 `budget_app` 코드의 모든 구석구석을 뼛속까지 이해하게 되었습니다. 

단순히 "코드가 이렇게 짜여 있네"가 아니라:
- **왜** 3개의 폴더(계층)로 나눴는지
- **왜** 그냥 쓰지 않고 원자적 쓰기(.tmp)를 했는지
- **왜** `return list` 대신 `yield`를 썼는지
- **왜** 데코레이터로 포장했는지

그 **"이유(Why)"**를 스스로 남에게 설명할 수 있다면, 당신은 이미 초보자를 벗어나 **주니어 백엔드 개발자**의 사고방식을 갖춘 것입니다.

이 가이드를 소리 내어 읽어보시고, 궁금한 코드는 직접 지워보거나 프린트(`print()`)를 찍어보며 실험해 보세요. 당신의 성장을 진심으로 응원합니다! 🚀


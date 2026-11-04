# AI Agent Coding Harness & Implementation Guide

본 문서는 AI 에이전트(Antigravity 등)가 파이썬 소프트웨어 프로젝트의 코드를 작성, 리팩토링, 검증할 때 엄격히 준수해야 하는 **하네스 프롬프트(Harness Prompt) 가이드라인**입니다. 본 가이드는 범용 소프트웨어 공학 원칙을 다루는 **Part 1**과 대상 프로젝트의 특화 제약을 다루는 **Part 2**로 구성됩니다.

---

# Part 1. General AI Agent Harness Guidelines (범용 규칙)

## 1. Core Philosophy (핵심 철학)
- **Code as Documentation (명세서 같은 코드)**: 코드는 기계뿐만 아니라 '사람'이 읽었을 때 도메인 명세서처럼 명확하고 자연스럽게 이해되어야 합니다.
- **명시성(Explicitness) 우대**: 암묵적이거나 짧은 함축적 구문보다, 길더라도 의도가 명확히 드러나고 추적하기 쉬운 코드를 지향합니다.

---

## 2. Architecture & Design Principles (설계 원칙)

### 2.1 단일 책임 원칙 (Single Responsibility Principle - SRP)
모든 함수, 클래스, 모듈은 오직 하나의 변경 이유와 책임만 가져야 합니다. 데이터 변환, 유효성 검사, 비즈니스 처리, I/O 등이 섞여 있다면 기능별로 분리하세요.

### 2.2 적극적인 객체지향/클래스 활용 (OOP & Modularization)
상태와 행위를 묶는 것이 효과적이거나 객체 생성을 캡슐화해야 할 때 적극적으로 클래스를 활용하세요. 단순 딕셔너리나 튜플 대신 명시적인 데이터 클래스나 객체를 사용합니다.

### 2.3 표준 패키지 구조화 및 실행 진입점 (`python3 -m <pkg>`)
단일 파일 형태의 스크립트가 아닌 2개 이상의 모듈로 구성된 프로젝트는 **반드시 패키지 디렉터리(`pkg_name/`) 구조로 격리**하고, `__main__.py`를 작성하여 `python3 -m <pkg_name>` 형태로 일관되게 실행할 수 있어야 합니다.

```text
my_project/
├── my_package/
│   ├── __init__.py
│   ├── __main__.py      # python3 -m my_package 실행 진입점
│   ├── core.py
│   └── utils.py
├── tests/
└── README.md
```

### 2.4 사이드 이펙트 최소화 (No Side Effects)
가능한 한 순수 함수(Pure Function) 형태로 작성하고, 전역 상태(Global State) 참조 및 변경을 극도로 지양하세요.

---

## 3. Data Flow & Pipeline (데이터 처리 흐름)
모든 주요 메서드 및 함수는 다음 3단계 파이프라인 흐름을 명확히 분리하여 구현해야 합니다.

```text
[ 1. Data Refinement ] -> [ 2. Validation ] -> [ 3. Logic Execution ]
```

1. **Data Refinement (데이터 정제)**: 입력 데이터의 공백 제거, 타입 변환, 바이트 계산 등 처리하기 적합한 표준 형태로 가공합니다.
2. **Validation (유효성 검사)**: 정제된 데이터의 범위, 널(Null) 여부, 도메인 제약조건을 검증합니다.
3. **Logic Execution (비즈니스 로직 실행)**: 유효성 검사를 완전히 통과한 데이터로만 실제 상태 변경 및 핵심 로직을 수행합니다.

---

## 4. Coding Standard & Syntax Constraints (엄격한 코딩 컨벤션)

### 4.1 타입 힌트 필수 (Type Hinting)
Python `typing` 모듈을 사용하여 모든 함수 파라미터, 반환값, 주요 클래스 변수에 명시적인 타입 힌트를 작성하세요.

```python
# DON'T
def process_user(user, age):
    return {"name": user, "age": age}

# DO
from typing import Dict, Any

def process_user(user_name: str, age: int) -> Dict[str, Any]:
    return {"name": user_name, "age": age}
```

### 4.2 Guard Clauses / Early Return (보호 구문)
예외 조건 및 비정상 상태는 함수의 **최상단에 Guard Clause로 배치**하여 즉시 리턴하거나 예외를 발생시킴으로써 들여쓰기 깊이(Nesting Depth)를 최소화하세요.

```python
# DON'T
def calculate_discount(price: int, is_member: bool) -> float:
    if price > 0:
        if is_member:
            return price * 0.8
        else:
            return price * 0.95
    else:
        raise ValueError("Invalid price")

# DO
def calculate_discount(price: int, is_member: bool) -> float:
    if price <= 0:
        raise ValueError("Price must be greater than zero.")
        
    if is_member:
        return price * 0.8
    return price * 0.95
```

### 4.3 의도가 드러나는 명확한 네이밍 (Intention-Revealing Names)
`data`, `res`, `tmp`, `val`, `i` 같은 모호한 변수명은 엄격히 금지합니다.
- 변수/속성: 명사형 (예: `user_session_token`, `expiration_timestamp`)
- 함수/메서드: 동사형 (예: `validate_user_credentials()`, `calculate_memory_bytes()`)

### 4.4 상대 임포트(Relative Import) 사용
패키지 내부 모듈 간 참조 시 모듈 이름 충돌 방지 및 패키지 독립성을 위해 상대 임포트(`from .core import ...`)를 사용하세요.

---

## 5. Anti-Patterns & Syntax Constraints (절대 금지 사항)

### 5.1 매직 스트링 / 매직 넘버 금지 (`Enum` 및 Text Class 활용)
코드 내 문자열 리터럴이나 수치 리터럴을 직접 하드코딩하는 것은 금지됩니다. 반드시 `Enum`이나 전용 Constant Class(Text Class)로 분리하세요.

```python
# DON'T
if status == "PENDING" or count > 5:
    return "ERR memory limit"

# DO
from enum import Enum

class SystemStatus(Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"

class ConfigLimits:
    MAX_RETRY_COUNT: int = 5

class ErrorMessages:
    MEMORY_LIMIT_EXCEEDED: str = "ERR memory limit"

if status == SystemStatus.PENDING.value or count > ConfigLimits.MAX_RETRY_COUNT:
    return ErrorMessages.MEMORY_LIMIT_EXCEEDED
```

### 5.2 삼항 연산자(Ternary Operator) 최소화
가독성을 해치는 복잡한 삼항 연산자(`a if cond else b`) 대신 명시적인 `if-else` 구문이나 Guard Clause를 사용하세요.

### 5.3 복잡한 리스트 컴프리헨션(List Comprehension) 지양
단순 데이터 맵핑을 제외하고, 조건문이나 부수 효과가 포함된 복잡한 컴프리헨션은 가독성을 저해하므로 명시적인 `for` 루프를 사용하세요.

### 5.4 포괄적 예외 처리 금지
`except Exception:` 또는 bare `except:`와 같이 뭉뚱그려 예외를 포획하지 마세요. 반드시 `except ValueError:`, `except KeyError:` 처럼 구체적인 예외 타입을 명시해야 합니다.

---

## 6. Verification & Test Protocol (검증 및 테스트 규정)
- AI 에이전트는 코드 리팩토링이나 기능 추가 작업 후, **반드시 자동화된 단위 테스트(Unit Tests)를 수행**해야 합니다.
- 수정 사항이 기존 기능을 파손하지 않는지 회귀 테스트(Regression Test)를 수행하고, 모든 테스트가 100% 통과(Pass)한 것을 직접 확인한 뒤 작업을 완료해야 합니다.

---

# Part 2. Project-Specific Guidelines (Mini-Redis)

본 섹션은 현재 워크스페이스의 **Mini-Redis 프로젝트** 리팩토링 및 패키징 시 적용되는 특화 제약조건입니다.

## 1. Package Directory & Executable Module
- 모든 소스 코드는 `mini_redis/` 패키지 폴더 내부에 위치해야 하며, `python3 -m mini_redis`로 CLI 인터랙티브 셀을 시작할 수 있는 `mini_redis/__main__.py` 진입점을 갖추어야 합니다.

## 2. Custom Data Structure Enforcement (내장 자료형 사용 엄격 배제)
- Redis 엔진 내부 데이터 저장, LRU 추적, TTL 추적 로직에는 파이썬 내장 `dict`, `set`, `collections` 모듈 사용을 **엄격히 배제**해야 합니다.
- 대신 밑바닥부터 작성된 커스텀 자료구조인 `HashMap`, `DoublyLinkedList`, `MinHeap`, `DynamicArray`를 조합하여 알고리즘을 구현하세요.

## 3. Memory & TTL Engine Constraints
- **메모리 계산**: `used_memory = len(key.encode('utf-8')) + len(str(value).encode('utf-8'))` 표준 방식을 준수하세요.
- **Eviction & Expiration**: 모든 읽기/쓰기 명령 수행 전 `_cleanup_expired()` (Lazy Deletion)가 선행되어야 하며, 메모리 초과 시 LRU 규칙에 따라 `_evict_lru()`가 정확히 호출되어야 합니다.

## 4. Redis Constants & Response Standards
- `SET`, `GET`, `DEL`, `EXPIRE`, `TTL`, `CONFIG`, `INFO` 등의 명령어 및 `OK`, `(nil)`, `(integer)` 등 Redis 반환 규격은 `mini_redis/constants.py`의 `RedisCommands`, `RedisResponses`, `ErrorMessages` 클래스에 집약하여 관리해야 합니다.
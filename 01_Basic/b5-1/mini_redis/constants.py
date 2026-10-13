"""
[Mini-Redis 모듈 상수 정의 파일]

1. 어떤 로직인가:
   - Redis 프로토콜 명령어 문자열, 표준 응답 포맷, 에러 메시지, 기본 메모리/버킷 상수를 한데 집약 관리하는 텍스트 상수 모듈입니다.

2. 왜 존재하는가 (존재 이유 및 목적):
   - 코드 여러 곳에 "OK", "(nil)", "SET" 같은 리터럴 문자열을 하드코딩하면 타이핑 오타 버그가 발생하기 쉽고 변경 시 수정 범위가 커집니다.
   - 단일 진실 출처(Single Source of Truth) 원칙을 적용하여 중앙에서 일관되게 상수를 관리하기 위해 존재합니다.

3. 소프트웨어 설계 원칙:
   - Python `typing.Final` 속성을 사용하여 상수가 중간에 재할당되지 않도록 정적 분석기 레벨에서 보호합니다.
"""

from typing import Final


class RedisCommands:
    """
    [Redis CLI 명령어 집합]
    1. 어떤 로직인가: 사용자가 입력하는 커맨드 명칭(SET, GET, EXPIRE 등)의 상수 집합입니다.
    2. 왜 존재하는가: 오타를 방지하고 명령어 추가/수정 시 안전하게 리팩토링하기 위해 존재합니다.
    """
    SET: Final[str] = "SET"
    GET: Final[str] = "GET"
    DEL: Final[str] = "DEL"
    EXISTS: Final[str] = "EXISTS"
    DBSIZE: Final[str] = "DBSIZE"
    EXPIRE: Final[str] = "EXPIRE"
    TTL: Final[str] = "TTL"
    CONFIG: Final[str] = "CONFIG"
    INFO: Final[str] = "INFO"
    PING: Final[str] = "PING"
    KEYS: Final[str] = "KEYS"
    PUSH: Final[str] = "PUSH"
    POP: Final[str] = "POP"
    PUBLISH: Final[str] = "PUBLISH"
    SUBSCRIBE: Final[str] = "SUBSCRIBE"
    POLL: Final[str] = "POLL"
    EXIT: Final[str] = "EXIT"
    QUIT: Final[str] = "QUIT"


class RedisResponses:
    """
    [Redis 프로토콜 규격 응답 포맷]
    1. 어떤 로직인가: Redis 엔진 처리 결과로 터미널에 반환되는 표준 출력 텍스트 양식입니다.
    2. 왜 존재하는가: Redis 클라이언트 표준 호환성(OK, (nil), (integer) N)을 100% 보장하기 위해 존재합니다.
    """
    OK: Final[str] = "OK"
    NIL: Final[str] = "(nil)"
    PONG: Final[str] = "PONG"

    @staticmethod
    def format_integer(val: int) -> str:
        """무엇: format_integer 연산을 수행합니다.
        상태: 필요한 값, 연결, 또는 크기만 갱신하고 자료구조 불변식을 유지합니다.
        이유: 상위 Redis 명령이 예측 가능한 결과와 일관된 상태를 전제로 이 연산을 조합합니다.
        복잡도: 직접 접근은 O(1), 순회나 재배치가 있으면 O(N)."""
        return f"(integer) {val}"


class ErrorMessages:
    """
    [에러 메시지 집합]
    1. 어떤 로직인가: 인자 오류, 메모리 초과(OOM), 존재하지 않는 명령어 등 에러 발생 시 반환할 표준 텍스트입니다.
    2. 왜 존재하는가: 에러 포맷 규격화 및 메시지 수정 편의성을 높이기 위해 존재합니다.
    """
    ERR_UNKNOWN_COMMAND: Final[str] = "ERR unknown command"
    ERR_WRONG_ARGUMENTS: Final[str] = "ERR wrong number of arguments"
    ERR_VALUE_NOT_INT: Final[str] = "ERR value is not an integer or out of range"
    ERR_MEMORY_LIMIT: Final[str] = "OOM command not allowed when used memory > 'maxmemory'"
    ERR_SYNTAX_ERROR: Final[str] = "ERR syntax error: unbalanced quotes"


class ConfigDefaults:
    """
    [엔진 기본 구성값]
    1. 어떤 로직인가: 초기 버킷 크기(8개), 로드 팩터(0.75), 기본 메모리(0=무제한) 기본값입니다.
    2. 왜 존재하는가: 자료구조 튜닝 포인트를 한곳에서 제어하기 위해 존재합니다.
    """
    DEFAULT_MAX_MEMORY: Final[int] = 0        # 0: 무제한 메모리 설정
    INITIAL_CAPACITY: Final[int] = 8          # 해시맵 및 동적 배열의 최초 상자 개수
    DEFAULT_LOAD_FACTOR: Final[float] = 0.75  # 해시맵 버킷 충돌 임계점 (75% 차면 2배 확장)

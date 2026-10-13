"""
[Mini-Redis 패키지 초기화 파일]

1. 어떤 로직인가:
   - 외부에서 `from mini_redis import MiniRedis, PubSub` 형태로 패키지를 가져올 때
     주요 핵심 클래스와 상수를 직접 노출(Export)하는 패키지 진입점 설정 모듈입니다.

2. 왜 존재하는가 (존재 이유 및 목적):
   - 이 파일이 없으면 사용자는 `from mini_redis.mini_redis_core import MiniRedis`처럼
     내부 구현 파일의 깊은 경로를 전부 기억해야 해서 모듈 캡슐화가 깨집니다.
   - `__all__` 리스트를 명시하여 패키지의 공개 API 명세를 단정하게 관리하기 위해 존재합니다.

3. 알고리즘 및 구조 원리:
   - Python의 패키지 네임스페이스 기법을 활용하여 내부 모듈 구조 변경 시에도 외부 호출부 코드가 깨지지 않도록 보호합니다.
"""

# 패키지 경계: 내부 파일 배치를 숨기고 핵심 엔진을 한 import 경로로 제공한다.

from .mini_redis_core import MiniRedis
from .pub_sub import PubSub
from .constants import RedisCommands, RedisResponses, ErrorMessages

__all__ = ["MiniRedis", "PubSub", "RedisCommands", "RedisResponses", "ErrorMessages"]

"""
[MiniRedis Core Engine Integration Test Suite]

1. 어떤 로직인가:
   - MiniRedis 엔진의 SET/GET/DEL 기본 명령어, maxmemory 초과 시 LRU 캐시 Eviction, EXPIRE/TTL 지연 삭제(Lazy Deletion) 동작을 검증하는 통합 테스트 모듈입니다.

2. 왜 존재하는가 (존재 이유 및 목적):
   - 4대 자료구조가 통합 결합되어 오케스트레이션되는 Redis 서버 기능이 요구사항 명세대로 정상 작동하는지 자동 보장하기 위해 존재합니다.
"""

import time
import io
import sys
import unittest
from mini_redis.mini_redis_core import MiniRedis
from mini_redis.pub_sub import PubSub
from mini_redis.cli import handle_command
from mini_redis.constants import RedisResponses, ErrorMessages


class TestMiniRedisCore(unittest.TestCase):

    def test_mini_redis_basic_set_get_del(self):
        """
        1. 어떤 검증인가: SET, GET, DEL 기본 동작 및 (nil), (integer) N 표준 프로토콜 반환 검증.
        2. 왜 검증하는가: 기본 Key-Value CRUD 명세가 지켜지는지 보장하기 위함입니다.
        """
        redis = MiniRedis()

        self.assertEqual(redis.set("user:1", "Alice"), RedisResponses.OK)
        self.assertEqual(redis.get("user:1"), "Alice")
        self.assertEqual(redis.get("user:2"), RedisResponses.NIL)

        self.assertEqual(redis.delete("user:1"), RedisResponses.format_integer(1))
        self.assertEqual(redis.get("user:1"), RedisResponses.NIL)
        self.assertEqual(redis.delete("user:1"), RedisResponses.format_integer(0))

    def test_mini_redis_lru_eviction(self):
        """
        1. 어떤 검증인가: maxmemory 10바이트 제한 상황에서 k1, k2 저장 후 k1을 읽어서 최신(MRU)으로 만든 뒤 k3 저장 시 LRU인 k2가 쫓겨나는지 검증.
        2. 왜 검증하는가: HashMap과 DoublyLinkedList의 결합을 통한 O(1) LRU Eviction 알고리즘이 미션 명세대로 동작하는지 보장하기 위함입니다.
        """
        redis = MiniRedis()
        redis.config_set_maxmemory(10)

        redis.set("k1", "v1")  # 4 bytes (used_memory = 4)
        redis.set("k2", "v2")  # 4 bytes (used_memory = 8)

        redis.get("k1")        # k1을 읽어 Head 직후로 이동시켜 k2를 LRU 상태로 만듦

        redis.set("k3", "v3")  # 4 bytes -> 총 12 bytes > 10 bytes -> k2 Eviction 발생!

        self.assertEqual(redis.get("k2"), RedisResponses.NIL)  # k2는 쫓겨남
        self.assertEqual(redis.get("k1"), "v1")                 # k1은 살아남음
        self.assertEqual(redis.get("k3"), "v3")                 # k3 저장됨

    def test_mini_redis_ttl_expiration(self):
        """
        1. 어떤 검증인가: EXPIRE 설정 후 TTL 시간 조회 및 지정 시간 경과 후 GET 시 (nil) 반환 및 지연 삭제(Lazy Deletion) 검증.
        2. 왜 검증하는가: MinHeap 기반 TTL 관리 및 Lazy Deletion 알고리즘의 유효성을 보장하기 위함입니다.
        """
        redis = MiniRedis()

        redis.set("temp", "val")
        res = redis.expire("temp", 1)
        self.assertEqual(res, RedisResponses.format_integer(1))

        ttl = redis.ttl("temp")
        self.assertIn("(integer)", ttl)

        # 1초 경과 대기
        time.sleep(1.1)

        # 1.1초 경과 후 GET 호출 시 _cleanup_expired에 의해 지연 삭제되고 (nil) 리턴
        self.assertEqual(redis.get("temp"), RedisResponses.NIL)
        self.assertEqual(redis.ttl("temp"), RedisResponses.format_integer(-2))

    def test_cli_unbalanced_quotes(self):
        """
        1. 어떤 검증인가: cli handle_command에서 닫히지 않은 따옴표 입력 시 ValueError 예외 발생으로 인한 프로그램 종료 없이 에러 메시지를 출력하고 루프를 유지하는지 검증.
        2. 왜 검증하는가: 사용자 입력을 안전하게 파싱하여 CLI 안정성을 보장하기 위함입니다.
        """
        db = MiniRedis()
        pubsub = PubSub()
        captured_output = io.StringIO()
        sys.stdout = captured_output
        try:
            should_continue = handle_command('SET k "unclosed', db, pubsub)
            sys.stdout = sys.__stdout__
            self.assertTrue(should_continue)
            self.assertIn(ErrorMessages.ERR_SYNTAX_ERROR, captured_output.getvalue())
        finally:
            sys.stdout = sys.__stdout__


if __name__ == "__main__":
    unittest.main()

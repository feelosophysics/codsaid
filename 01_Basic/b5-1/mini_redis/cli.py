"""
[CLI: 사용자 인터랙티브 REPL 커맨드 인터페이스 모듈]

1. 어떤 로직인가:
   - 사용자가 터미널에서 입력한 텍스트를 `shlex.split`으로 파싱하여 인자 개수를 검증하고,
     `MiniRedis` 코어 엔진 메서드를 실행한 뒤 결과를 Redis 프로토콜로 출력하는 REPL 모듈입니다.

2. 왜 존재하는가 (존재 이유 및 목적):
   - 대화형 쉘 환경(`mini-redis> `)을 제공하여 사용자가 직접 명령어를 입력하고 즉시 결과를 확인하게 위해 존재합니다.
   - `shlex` 파싱을 통해 `"Alice Bob"` 처럼 공백이 포함된 인자를 안전하게 다룹니다.
"""

import sys
import shlex
from typing import List

from .mini_redis_core import MiniRedis
from .pub_sub import PubSub
from .constants import RedisCommands, RedisResponses, ErrorMessages


def print_error(msg: str) -> None:
    """무엇: print_error 연산을 수행합니다.
    상태: 필요한 값, 연결, 또는 크기만 갱신하고 자료구조 불변식을 유지합니다.
    이유: 상위 Redis 명령이 예측 가능한 결과와 일관된 상태를 전제로 이 연산을 조합합니다.
    복잡도: 직접 접근은 O(1), 순회나 재배치가 있으면 O(N)."""
    print(f"(error) {msg}")


def handle_command(line: str, db: MiniRedis, pubsub: PubSub) -> bool:
    """무엇: REPL 입력을 파싱해 저장 명령과 메시지 명령으로 분기합니다.
    상태: CLI는 상태를 직접 보유하지 않고 db 또는 pubsub 객체만 변경합니다.
    이유: 입출력 어댑터와 엔진을 분리해야 터미널 없이도 엔진을 테스트할 수 있습니다.
    복잡도: 명령별 엔진 연산에 따름."""
    # 1. Data Refinement & Parsing
    stripped_line: str = line.strip()
    if not stripped_line:
        return True

    # 2. Command Parsing & Execution
    try:
        try:
            args: List[str] = shlex.split(stripped_line)
        except ValueError:
            print_error(ErrorMessages.ERR_SYNTAX_ERROR)
            return True
        if not args:
            return True

        cmd: str = args[0].upper()

        # Early Return: exit / quit 시 즉시 루프 종료
        if cmd in (RedisCommands.EXIT, RedisCommands.QUIT):
            return False

        if cmd == RedisCommands.SET:
            if len(args) != 3:
                print_error(f"{ErrorMessages.ERR_WRONG_ARGUMENTS} for '{RedisCommands.SET}' command")
                return True
            result = db.set(args[1], args[2])
            print(result)

        elif cmd == RedisCommands.GET:
            if len(args) != 2:
                print_error(f"{ErrorMessages.ERR_WRONG_ARGUMENTS} for '{RedisCommands.GET}' command")
                return True
            found, val = db.get_with_status(args[1])
            if not found:
                print(RedisResponses.NIL)
            else:
                print(f'"{val}"')

        elif cmd == RedisCommands.DEL:
            if len(args) != 2:
                print_error(f"{ErrorMessages.ERR_WRONG_ARGUMENTS} for '{RedisCommands.DEL}' command")
                return True
            print(db.delete(args[1]))

        elif cmd == RedisCommands.EXISTS:
            if len(args) != 2:
                print_error(f"{ErrorMessages.ERR_WRONG_ARGUMENTS} for '{RedisCommands.EXISTS}' command")
                return True
            print(db.exists(args[1]))

        elif cmd == RedisCommands.DBSIZE:
            if len(args) != 1:
                print_error(f"{ErrorMessages.ERR_WRONG_ARGUMENTS} for '{RedisCommands.DBSIZE}' command")
                return True
            print(db.dbsize())

        elif cmd == RedisCommands.KEYS:
            if len(args) != 1:
                print_error(f"{ErrorMessages.ERR_WRONG_ARGUMENTS} for '{RedisCommands.KEYS}' command")
                return True
            keys = db.keys()
            if not keys:
                print("(empty array)")
            else:
                for i, k in enumerate(keys):
                    print(f'{i+1}. "{k}"')

        elif cmd == RedisCommands.EXPIRE:
            if len(args) != 3:
                print_error(f"{ErrorMessages.ERR_WRONG_ARGUMENTS} for '{RedisCommands.EXPIRE}' command")
                return True
            try:
                seconds = int(args[2])
                print(db.expire(args[1], seconds))
            except ValueError:
                print_error(ErrorMessages.ERR_VALUE_NOT_INT)

        elif cmd == RedisCommands.TTL:
            if len(args) != 2:
                print_error(f"{ErrorMessages.ERR_WRONG_ARGUMENTS} for '{RedisCommands.TTL}' command")
                return True
            print(db.ttl(args[1]))

        elif cmd == RedisCommands.CONFIG:
            if len(args) != 4 or args[1].upper() != "SET" or args[2].lower() != "maxmemory":
                print_error("ERR unknown or malformed 'CONFIG' command")
                return True
            try:
                limit = int(args[3])
                print(db.config_set_maxmemory(limit))
            except ValueError:
                print_error(ErrorMessages.ERR_VALUE_NOT_INT)

        elif cmd == RedisCommands.INFO:
            if len(args) != 2 or args[1].lower() != "memory":
                print_error("ERR unknown or malformed 'INFO' command")
                return True
            print(db.info_memory())

        elif cmd == RedisCommands.SUBSCRIBE:
            if len(args) != 2:
                print_error(f"{ErrorMessages.ERR_WRONG_ARGUMENTS} for '{RedisCommands.SUBSCRIBE}' command")
                return True
            pubsub.subscribe(args[1])
            print(f"Subscribed to channel '{args[1]}'. Use POLL to read messages.")

        elif cmd == RedisCommands.PUBLISH:
            if len(args) != 3:
                print_error(f"{ErrorMessages.ERR_WRONG_ARGUMENTS} for '{RedisCommands.PUBLISH}' command")
                return True
            receivers = pubsub.publish(args[1], args[2])
            print(RedisResponses.format_integer(receivers))

        elif cmd == RedisCommands.POLL:
            if len(args) != 2:
                print_error(f"{ErrorMessages.ERR_WRONG_ARGUMENTS} for '{RedisCommands.POLL}' command")
                return True
            msgs = pubsub.poll(args[1])
            if not msgs:
                print("(empty queue)")
            else:
                for i, msg in enumerate(msgs):
                    print(f'{i+1}) "{msg}"')

        else:
            print_error(f"{ErrorMessages.ERR_UNKNOWN_COMMAND} '{args[0]}'")

    except MemoryError as e:
        print_error(str(e))
    except Exception as e:
        print_error(f"Internal error: {str(e)}")

    return True


def main() -> None:
    """무엇: main 연산을 수행합니다.
    상태: 필요한 값, 연결, 또는 크기만 갱신하고 자료구조 불변식을 유지합니다.
    이유: 상위 Redis 명령이 예측 가능한 결과와 일관된 상태를 전제로 이 연산을 조합합니다.
    복잡도: 직접 접근은 O(1), 순회나 재배치가 있으면 O(N)."""
    db = MiniRedis()
    pubsub = PubSub()

    print("Welcome to Mini Redis CLI.")
    print("Type 'exit' or 'quit' to terminate.")

    while True:
        try:
            line = input("mini-redis> ")
            should_continue = handle_command(line, db, pubsub)
            if not should_continue:
                break
        except (EOFError, KeyboardInterrupt):
            print("\nType 'exit' to terminate.")
            break


if __name__ == "__main__":
    main()

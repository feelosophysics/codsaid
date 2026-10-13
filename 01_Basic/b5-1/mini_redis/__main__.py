"""
[Mini-Redis 패키지 전용 실행 진입점 모듈]

1. 어떤 로직인가:
   - 터미널에서 `python3 -m mini_redis` 명령어를 입력했을 때 CLI 인터랙티브 REPL 셀을 자동으로 시작시키는 모듈입니다.

2. 왜 존재하는가 (존재 이유 및 목적):
   - 파이썬 표준 라이브러리 규격(`__main__.py`)을 준수하여, 사용자가 패키지 내부 경로(`mini_redis/cli.py`)를 몰라도
     `python3 -m <패키지명>` 키워드 하나로 즉시 애플리케이션을 실행할 수 있게 만들기 위해 존재합니다.
   - 단일 스크립트 실행 방식에서 발생할 수 있는 상대 임포트 에러(`ImportError: attempted relative import`)를 방지합니다.

3. 알고리즘 및 실행 원리:
   - 파이썬 인터프리터가 모듈로 패키지를 실행할 때 최상단에서 `__main__.py`를 자동 탐색하여 실행하며, `cli.main()`을 호출하여 REPL 루프를 작동시킵니다.
"""

# 패키지 실행 경로는 CLI 진입만 담당한다. 저장과 명령 규칙은 cli와 core에 남긴다.

import sys
from .cli import main

if __name__ == "__main__":
    main()

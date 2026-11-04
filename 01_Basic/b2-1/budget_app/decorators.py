"""
decorators.py
이 모듈은 파이썬의 핵심 고급 문법인 '데코레이터(Decorator)'를 정의하는 곳입니다.
데코레이터는 기존 함수의 코드를 직접 수정하지 않고도, 그 함수가 실행되기 전이나 후에 공통 기능
(예: 예외 처리, 실행 시간 측정, 로깅 등)을 덧붙여 실행할 수 있게 해주는 아주 유용한 기능입니다.

사용자님의 학습을 돕기 위해 데코레이터의 원리를 각 코드마다 상세히 설명해 두었습니다.
"""

import sys
import time
import functools
from typing import Callable, Any


def handle_errors_gracefully(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    [데코레이터 1: 예외 안전 처리]
    함수 실행 중 예기치 못한 에러가 발생했을 때, 무시무시한 시스템 스택트레이스(Stack Trace, 영어 에러 로그)를
    사용자에게 노출하는 대신, 에러 원인과 친절한 해결 힌트(Hint)를 한글로 출력하고
    비정상 종료 코드(exit code = 1)를 반환하며 종료되도록 합니다.
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            # 원래 실행하려고 했던 함수를 실행합니다.
            return func(*args, **kwargs)
        except KeyboardInterrupt:
            # 사용자가 Ctrl+C를 눌러 강제 종료할 때의 예외 처리입니다.
            print("\n\n[알림] 사용자가 프로그램 실행을 중단했습니다.")
            sys.exit(0)
        except FileNotFoundError as e:
            print(f"\n[오류] 데이터를 보관할 파일을 찾을 수 없습니다.")
            print(f"[상세] {e.filename} 파일이 존재하지 않거나 읽기 권한이 없습니다.")
            print("[힌트] 프로그램을 처음 실행하는 경우라면, 먼저 데이터 저장 폴더의 경로와 생성 권한을 확인하세요.")
            sys.exit(1)
        except ValueError as e:
            # 입력값 검증 오류 등 사용자가 값을 잘못 넣었을 때의 예외 처리입니다.
            print(f"\n[오류] 입력값 또는 데이터 형식이 올바르지 않습니다.")
            print(f"[원인] {e}")
            print("[힌트] 입력 형식을 다시 확인해 주시기 바랍니다. 예) 날짜: YYYY-MM-DD, 금액: 양수 정수")
            sys.exit(1)
        except Exception as e:
            # 그 외의 예상치 못한 시스템 모든 에러를 안전하게 가로챕니다.
            print(f"\n[오류] 프로그램 실행 중 예상치 못한 문제가 발생했습니다.")
            print(f"[상세 에러 내용] {e}")
            print("[힌트] 파일 저장 폴더의 권한을 확인하거나, 데이터 파일이 깨지지 않았는지 확인하세요.")
            sys.exit(1)

    return wrapper


def log_execution_time(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    [데코레이터 2: 실행 시간 측정]
    어떤 함수가 실행되기 시작한 시간과 완료된 시간을 측정하여,
    이 함수를 처리하는 데 총 몇 초가 소요되었는지 터미널에 표시해 줍니다.
    대용량 CSV 가져오기/내보내기나 백업 같은 무거운 작업을 분석할 때 매우 유용합니다.
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = time.perf_counter() # 초정밀 시작 타이머 작동
        
        # 실제 함수를 실행하고 결과값을 담아둡니다.
        result = func(*args, **kwargs)
        
        end_time = time.perf_counter() # 완료 타이머 작동
        elapsed = end_time - start_time # 소요 시간 계산
        
        print(f"[성능 로그] '{func.__name__}' 작업 소요 시간: {elapsed:.4f}초")
        return result

    return wrapper


def log_activity(log_filepath: str = "data/activity.log") -> Callable[..., Any]:
    """
    [데코레이터 3: 활동 로깅 (팩토리 데코레이터)]
    이 데코레이터는 가계부의 주요 변경 이벤트(거래 생성, 수정, 삭제)가 수행될 때,
    어떤 행위가 언제 완료되었는지를 텍스트 파일(activity.log)에 영구 기록하는 감사(Audit) 로그 기능입니다.
    매개변수를 전달받기 위해 데코레이터를 리턴하는 3중 중첩 함수 구조를 지니고 있습니다.
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # 먼저 원본 함수를 실행시킵니다.
            result = func(*args, **kwargs)
            
            # 로그 기록을 시도합니다. (로깅 중 실패가 전체 기능 실패를 만들지 않도록 예외 처리)
            try:
                import os
                # 로그 파일이 위치할 폴더가 없으면 자동 생성합니다.
                os.makedirs(os.path.dirname(log_filepath), exist_ok=True)
                
                # 파일의 끝에 로그를 추가(append, 'a') 모드로 엽니다.
                with open(log_filepath, "a", encoding="utf-8") as log_file:
                    now_str = time.strftime("%Y-%m-%d %H:%M:%S")
                    log_file.write(f"[{now_str}] '{func.__name__}' 기능이 호출되었습니다. (매개변수: {args[1:] if len(args) > 1 else ''})\n")
            except Exception:
                # 로깅 실패는 화면에 출력하지 않고 조용히 넘어갑니다.
                pass
                
            return result
        return wrapper
    return decorator

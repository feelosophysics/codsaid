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

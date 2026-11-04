#!/usr/bin/env python3
"""개발용 서버를 실행하고 외부 공개 도구의 사용 예를 출력하는 예전 보조 스크립트입니다.
현재 EC2의 systemd+Caddy 배포 과정에서는 사용하지 않습니다. Popen은 별도 프로그램을 시작하고 wait는
종료를 기다립니다.
파일을 읽거나 주석을 붙이는 것만으로 서버가 실행되지는 않습니다. 이 스크립트를 직접 실행해야 main이 호출됩니다.
"""

import subprocess
import sys
import time
import os

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def main():
    """개발 서버를 시작하고 공개 접속 도구 안내를 출력합니다. 현재 운영 배포 절차에서는 실행하지 않습니다.
    """
    print("=" * 65)
    print("[AI 챗봇 서비스] 외부 공개 네트워크 실행 스크립트")
    print("=" * 65)
    print("1. 로컬 FastAPI 서버 (http://127.0.0.1:8000)를 기동합니다.")
    print("2. 평가자가 접속할 수 있는 공인 HTTPS URL을 제공합니다.\n")

    port = 8000

    # 개발용 FastAPI 프로세스를 시작합니다. 현재 EC2 배포 경로는 이 도구를 사용하지 않습니다.
    print(f"FastAPI 서버 기동 중... (Port: {port})")
    # 별도 Python 프로세스를 시작합니다. 현재 EC2의 systemd 서비스와는 다른 개발용 실행 경로입니다.
    server_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", str(port), "--reload"],
        stdout=sys.stdout,
        stderr=sys.stderr
    )

    time.sleep(2)

    print("\n" + "-" * 65)
    print("[평가자 및 외부 네트워크 접속 방법 안내]")
    print("=" * 65)
    print("▶ 로컬 접속:   http://127.0.0.1:8000")
    print("▶ 대화 로그:   http://127.0.0.1:8000/logs")
    print("▶ API 명세서:  http://127.0.0.1:8000/docs")
    print("-" * 65)
    print("외부 네트워크 공개(평가용 URL 생성) 옵션:")
    print("   옵션 1 (Node.js npx):  npx localtunnel --port 8000")
    print("   옵션 2 (ngrok):         ngrok http 8000")
    print("   옵션 3 (Cloudflare):    cloudflared tunnel --url http://localhost:8000")
    print("=" * 65)
    print("종료하려면 Ctrl + C를 누르세요.\n")

    try:
        server_process.wait()
    except KeyboardInterrupt:
        print("\n서버를 종료합니다...")
        server_process.terminate()

if __name__ == "__main__":
    main()

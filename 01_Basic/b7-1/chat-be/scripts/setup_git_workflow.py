#!/usr/bin/env python3
"""초기 Git 브랜치·커밋을 만드는 예전 보조 스크립트입니다. 현재 배포와 팀 리뷰 작업에는 사용하지 않습니다.
실행하면 저장소 설정·커밋·브랜치를 바꾸므로 주석 점검 중에는 실행하지 않습니다.
if __name__ == "__main__"은 다른 파일에서 가져오기만 했을 때 main을 자동 실행하지 않게 하는
조건입니다.
"""

import subprocess
import os
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def run_cmd(cmd):
    """문자열 명령을 셸에 전달하고 출력 결과를 받습니다. 이 보조 도구는 Git 변경을 수행하므로 현재 검증에서는
    실행하지 않습니다.
    """
    print(f"  [RUN] {cmd}")
    # 셸 문자열을 실행하는 실제 변경 작업입니다. 주석 추가/문법 확인 중 이 함수를 호출하지 않습니다.
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if res.returncode != 0 and "already exists" not in res.stderr and "fatal" not in res.stderr:
        print(f"  [WARN] {res.stderr.strip()}")
    return res.stdout.strip()

def main():
    """Git 설정과 초기 브랜치/커밋을 만듭니다. 현재 저장소의 이력을 바꾸므로 학습 주석 확인을 위해 실행하지
    않습니다.
    """
    print("=" * 60)
    print("[Git 브랜치 전략 및 협업 이력 자동화 셋업]")
    print("=" * 60)

    # 1. 초기 Git 설정을 시작합니다. 현재 작업에서는 이 변경 도구를 실행하지 않습니다.
    run_cmd("git init")
    run_cmd('git config user.name "AI Chatbot Team"')
    run_cmd('git config user.email "team@feelosophysics.org"')

    # 2. 이 예전 초기화 도구의 초기 커밋 단계입니다. 현재 작업에서는 실행하지 않습니다.
    run_cmd("git add .gitignore requirements.txt README.md docs/ .agents/")
    run_cmd('git commit -m "chore: initial project documentation, ADR, and requirements setup"')

    # 3. 이 예전 도구의 develop 생성/전환 단계입니다. 현재 작업에서는 실행하지 않습니다.
    run_cmd("git checkout -b develop")

    # 4. 이 예전 도구가 역할별 초기 브랜치를 만드는 단계입니다.
    branches = [
        ("dev/auth", "Role 1: 인증 및 보안 모듈 (Bcrypt, JWT, 건설 도메인)"),
        ("dev/log", "Role 2: 데이터 및 로깅 모듈 (SQLite ORM, 지연시간 적재, 4대 표준 로거)"),
        ("dev/chat", "Role 3: AI 파이프라인 & SSE 스트리밍 모듈 (Gemma 4 26B, 타임아웃 방어)")
    ]

    for branch_name, desc in branches:
        print(f"\n* 기능 브랜치 생성: {branch_name} ({desc})")
        run_cmd(f"git branch {branch_name}")

    # 이 예전 초기화 도구의 마지막 브랜치 전환 단계입니다. 현재 작업에서는 실행하지 않습니다.
    run_cmd("git checkout develop")
    
    print("\n" + "=" * 60)
    print("[SUCCESS] Git 협업 브랜치 셋업 완료!")
    print("현재 브랜치 목록:")
    print(run_cmd("git branch -a"))
    print("=" * 60)
    print("팀원들과 작업할 때는 각자의 feature 브랜치로 전환 후 커밋하고 develop으로 PR 머지하시면 됩니다.")

if __name__ == "__main__":
    main()

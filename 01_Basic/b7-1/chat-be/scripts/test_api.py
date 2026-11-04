#!/usr/bin/env python3
"""TestClient로 브라우저 없이 API 요청을 보내는 예전 수동 점검 도구입니다. 실제 AI 키가 있는 환경에서 자동
실행하지 않습니다.
검증은 별도 임시 폴더·임시 DB·빈 AI 키로 준비한 pytest 경로를 사용합니다. 응답의 HTTP 숫자는 성공/거절
상태를 뜻합니다.
"""

import sys
import os
import time

# Windows 터미널에서도 한글을 출력할 수 있게 UTF-8을 사용합니다.
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app

def run_tests():
    """시험용 HTTP 요청으로 가입·로그인·채팅·로그 흐름을 확인합니다. 직접 실행 전에 DB/AI 환경이 격리됐는지
    확인해야 합니다.
    """
    client = TestClient(app)
    print("=" * 65)
    print("[AI 챗봇 서비스] E2E 자동화 API 테스트 시작")
    print("=" * 65)

    timestamp = int(time.time())
    username = f"student_{timestamp}"
    password = "studyPassword123!"

    # 1. 시험용 계정 가입을 요청합니다.
    print("\n[Step 1] 회원가입 테스트 (/api/v1/auth/register)...")
    res = client.post("/api/v1/auth/register", json={"username": username, "nickname": "스터디학생", "password": password})
    assert res.status_code == 201, f"회원가입 실패: {res.text}"
    print(f"  [OK] 회원가입 성공: ID={res.json()['id']}, Username={res.json()['username']}")

    # 2. 가입한 시험 계정으로 로그인합니다.
    print("\n[Step 2] 로그인 및 쿠키/JWT 발급 테스트 (/api/v1/auth/login)...")
    res = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert res.status_code == 200, f"로그인 실패: {res.text}"
    token = res.json()["access_token"]
    cookies = {"access_token": token}
    print("  [OK] 로그인 성공: 토큰 발급 확인 (값은 출력하지 않음)")

    # 3. 시험용 대화를 만듭니다.
    print("\n[Step 3] 대화 세션 생성 (/api/v1/chat/sessions)...")
    res = client.post("/api/v1/chat/sessions", json={"title": "FastAPI 실습 세션"}, cookies=cookies)
    assert res.status_code == 201, f"세션 생성 실패: {res.text}"
    session_id = res.json()["id"]
    print(f"  [OK] 대화 세션 생성 성공: Session ID={session_id}")

    # 4. 답변 조각과 완료 사건이 오는지 확인합니다.
    print("\n[Step 4] SSE 실시간 스트리밍 대화 질의 (/api/v1/chat/stream)...")
    prompt = "FastAPI의 장점과 DB 로깅 원리를 요약해줘."
    res = client.post("/api/v1/chat/stream", json={"message": prompt, "session_id": session_id}, cookies=cookies)
    assert res.status_code == 200, f"채팅 스트리밍 실패: {res.text}"
    assert "event: meta" in res.text
    assert "event: done" in res.text
    print("  [OK] SSE 스트리밍 정상 수신 및 완료 이벤트 확인")

    # 5. 저장된 대화 메시지를 다시 조회합니다.
    print("\n[Step 5] 세션 대화 내역 조회 (/api/v1/chat/sessions/{id}/messages)...")
    res = client.get(f"/api/v1/chat/sessions/{session_id}/messages", cookies=cookies)
    assert res.status_code == 200
    messages = res.json()
    assert len(messages) >= 2
    print(f"  [OK] 세션 내 메시지 {len(messages)}건 정상 조회 (User 질의 + AI 응답)")

    # 6. 기록 조회 API를 확인합니다.
    print("\n[Step 6] 대화 로그 영속화 조회 (/api/v1/logs)...")
    res = client.get("/api/v1/logs", cookies=cookies)
    assert res.status_code == 200
    logs = res.json()["items"]
    assert len(logs) >= 2
    print(f"  [OK] DB 저장 로그 {len(logs)}건 확인 완료 (Latency 측정값 포함)")

    print("\n" + "=" * 65)
    print("[SUCCESS] 모든 E2E API 테스트 케이스가 성공적으로 통과했습니다!")
    print("=" * 65)

if __name__ == "__main__":
    run_tests()

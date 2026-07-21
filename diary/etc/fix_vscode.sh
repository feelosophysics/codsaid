#!/bin/bash

echo "=== VS Code 충돌 및 프로세스 꼬임 해결 스크립트 ==="

echo "1. 현재 남아있는 VS Code 프로세스 확인 및 강제 종료..."
# VS Code 관련 프로세스 목록
pkill -9 -f "Visual Studio Code"
killall -9 "Code Helper" 2>/dev/null
killall -9 "Visual Studio Code" 2>/dev/null
killall -9 Code 2>/dev/null

echo "2. VS Code 락(lock) 및 소켓 파일 제거..."
rm -f "$HOME/Library/Application Support/Code/code.lock"
rm -f "$HOME/Library/Application Support/Code/"*.sock

echo "3. VS Code 정상 실행 시도..."
code .

echo "=== 프로세스 정리 및 재실행 완료! ==="

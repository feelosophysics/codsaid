#!/bin/bash
# Finder에서 열거나 `bash run_mac_demo.command`로 실행한다.
set -eu
cd -- "$(dirname -- "$0")"

finish() {
    status=$?
    trap - EXIT
    if [ "$status" -ne 0 ]; then
        printf '\n실행에 실패했습니다. 위 오류 내용을 확인해 주세요.\n'
    fi
    if [ -t 0 ]; then
        printf '\nEnter를 누르면 창을 닫습니다. '
        read -r answer || true
    fi
    exit "$status"
}
trap finish EXIT

if [ "$(uname -s)" != Darwin ]; then
    printf '이 실행 파일은 macOS 전용입니다.\n'
    exit 1
fi

# Finder가 연 터미널에서도 사용자 경로의 uv를 찾는다.
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:/usr/local/bin:/opt/homebrew/bin:$PATH"
if ! command -v uv >/dev/null 2>&1; then
    printf 'uv를 찾지 못했습니다. uv가 설치된 터미널에서 이 파일을 실행해 주세요.\n'
    exit 1
fi

printf 'A5-1 Mac 시연: 기존 잠금 파일로 환경을 준비합니다.\n'
uv sync --locked
# uv를 다시 거치지 않고 이 환경의 Python에 검색 경로를 전달한다.
.venv/bin/python tools/mac_demo.py "$@"

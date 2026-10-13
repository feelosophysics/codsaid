#!/bin/bash

# 에러 발생 시 스크립트 실행 즉각 중단
set -e

echo "[INFO] 가상환경 자동 빌드 및 셋팅을 시작합니다..."

# 1. .venv 가상환경 생성 여부 확인 및 생성
if [ ! -d ".venv" ]; then
    echo "[INFO] .venv 가상환경이 존재하지 않습니다. 새로 생성하는 중..."
    
    # Python 3.10 이상 버전 검사 및 탐색
    PYTHON_BIN=""
    for cmd in python3.13 python3.12 python3.11 python3.10 python3; do
        if command -v "$cmd" >/dev/null 2>&1; then
            # 버전 정보 추출 (예: 3.12)
            ver=$("$cmd" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
            major=$(echo "$ver" | cut -d. -f1)
            minor=$(echo "$ver" | cut -d. -f2)
            if [ "$major" -eq 3 ] && [ "$minor" -ge 10 ]; then
                PYTHON_BIN="$cmd"
                break
            fi
        fi
    done

    if [ -z "$PYTHON_BIN" ]; then
        echo "[ERROR] Python 3.10 이상 버전이 시스템에 설치되어 있지 않거나 PATH에 없습니다."
        echo "        (기본 python3 버전: $(python3 --version 2>&1))"
        echo "        Python 3.10 이상 버전을 설치한 후 다시 시도해 주세요."
        exit 1
    fi

    echo "[INFO] 검증된 파이썬 인터프리터($PYTHON_BIN, 버전: $($PYTHON_BIN -c 'import sys; print(sys.version)'))로 가상환경을 생성합니다..."
    $PYTHON_BIN -m venv .venv
    
    echo "[INFO] 가상환경 활성화 스크립트(.venv/bin/activate)를 커스텀 버전(alias 우회 및 한글 주석)으로 패치합니다..."
    cat << 'EOF' > .venv/bin/activate
# 이 파일은 bash 또는 zsh 환경에서 "source bin/activate" 명령어로 실행되어야 합니다.
# 셸 스크립트를 직접 실행(./activate)하면 가상환경이 현재 터미널 세션에 적용되지 않습니다.

# deactivate 함수: 가상환경을 비활성화하고 원래 터미널 환경으로 복원하는 함수입니다.
deactivate () {
    # 기존에 백업해 두었던 PATH 환경 변수가 있다면 이를 원래대로 복구합니다.
    if [ -n "${_OLD_VIRTUAL_PATH:-}" ] ; then
        PATH="${_OLD_VIRTUAL_PATH:-}"
        export PATH
        unset _OLD_VIRTUAL_PATH
    fi
    # 기존에 백업해 두었던 PYTHONHOME 환경 변수가 있다면 복구합니다.
    if [ -n "${_OLD_VIRTUAL_PYTHONHOME:-}" ] ; then
        PYTHONHOME="${_OLD_VIRTUAL_PYTHONHOME:-}"
        export PYTHONHOME
        unset _OLD_VIRTUAL_PYTHONHOME
    fi

    # 셸의 커맨드 해시 테이블을 초기화합니다.
    # 이전 PATH의 명령어가 계속 실행되는 것을 방지합니다.
    hash -r 2> /dev/null

    # 기존에 백업해 두었던 PS1(터미널 프롬프트) 환경 변수를 복구합니다.
    if [ -n "${_OLD_VIRTUAL_PS1:-}" ] ; then
        PS1="${_OLD_VIRTUAL_PS1:-}"
        export PS1
        unset _OLD_VIRTUAL_PS1
    fi

    # 가상환경 변수들을 삭제합니다.
    unset VIRTUAL_ENV
    unset VIRTUAL_ENV_PROMPT

    # 가상환경 활성화 시 비활성화했던 python/pip alias를 원래대로 다시 등록합니다.
    if [ -n "${_OLD_VIRTUAL_ALIAS_PYTHON:-}" ] ; then
        case "$_OLD_VIRTUAL_ALIAS_PYTHON" in
            alias\ *)
                eval "$_OLD_VIRTUAL_ALIAS_PYTHON"
                ;;
            *)
                eval "alias $_OLD_VIRTUAL_ALIAS_PYTHON"
                ;;
        esac
        unset _OLD_VIRTUAL_ALIAS_PYTHON
    fi
    if [ -n "${_OLD_VIRTUAL_ALIAS_PIP:-}" ] ; then
        case "$_OLD_VIRTUAL_ALIAS_PIP" in
            alias\ *)
                eval "$_OLD_VIRTUAL_ALIAS_PIP"
                ;;
            *)
                eval "alias $_OLD_VIRTUAL_ALIAS_PIP"
                ;;
        esac
        unset _OLD_VIRTUAL_ALIAS_PIP
    fi

    # nondestructive 옵션이 인자로 오지 않았다면 이 deactivate 함수 자체를 메모리에서 제거합니다.
    if [ ! "${1:-}" = "nondestructive" ] ; then
        unset -f deactivate
    fi
}

# 기존 활성화되어 있던 다른 가상환경이 있다면 비활성화(nondestructive 모드)합니다.
deactivate nondestructive

# 운영체제 종류(OS)에 맞춰 가상환경 루트 디렉토리 경로(VIRTUAL_ENV)를 설정합니다.
# 하드코딩 대신 스크립트 파일의 실제 위치를 동적으로 감지하여 이식성을 높입니다.
if [ -n "${BASH_SOURCE:-}" ]; then
    _ACTIVATE_PATH="${BASH_SOURCE[0]}"
elif [ -n "${ZSH_VERSION:-}" ]; then
    _ACTIVATE_PATH="${(%):-%x}"
else
    _ACTIVATE_PATH="$0"
fi
_VENV_DIR=$(cd "$(dirname "${_ACTIVATE_PATH}")/.." && pwd)

case "$(uname)" in
    CYGWIN*|MSYS*|MINGW*)
        # Windows의 cygwin, msys, mingw 환경에 맞춰 경로를 윈도우 스타일에서 POSIX 스타일로 변환합니다.
        VIRTUAL_ENV=$(cygpath "$_VENV_DIR")
        export VIRTUAL_ENV
        ;;
    *)
        # macOS 및 Linux 환경에서는 디렉토리 경로를 그대로 사용합니다.
        export VIRTUAL_ENV="$_VENV_DIR"
        ;;
esac
unset _ACTIVATE_PATH
unset _VENV_DIR

# 현재 PATH를 백업하고, 가상환경의 bin 디렉토리를 PATH 맨 앞에 추가합니다.
# 이로 인해 가상환경 내의 python, pip 등이 우선적으로 실행됩니다.
_OLD_VIRTUAL_PATH="$PATH"
PATH="$VIRTUAL_ENV/"bin":$PATH"
export PATH

# 가상환경 활성화 시 글로벌 alias(python, pip 등) 때문에 가상환경 바이너리가 무시되는 현상을 막기 위해,
# 현재 등록된 alias를 임시 백업해두고 해제(unalias)합니다.
_OLD_VIRTUAL_ALIAS_PYTHON=""
_OLD_VIRTUAL_ALIAS_PIP=""

if alias python >/dev/null 2>&1; then
    _OLD_VIRTUAL_ALIAS_PYTHON=$(alias python)
    unalias python
fi

if alias pip >/dev/null 2>&1; then
    _OLD_VIRTUAL_ALIAS_PIP=$(alias pip)
    unalias pip
fi

# 프롬프트에 표시될 가상환경 이름 접두어입니다.
VIRTUAL_ENV_PROMPT='(.venv) '
export VIRTUAL_ENV_PROMPT

# PYTHONHOME 환경 변수가 설정되어 있다면 백업 후 일시적으로 해제합니다.
# (전역 파이썬 라이브러리 경로가 참조되어 충돌하는 것을 방지)
if [ -n "${PYTHONHOME:-}" ] ; then
    _OLD_VIRTUAL_PYTHONHOME="${PYTHONHOME:-}"
    unset PYTHONHOME
fi

# 프롬프트 비활성화 옵션이 켜져 있지 않다면 터미널 프롬프트(PS1) 앞에 (.venv)를 추가합니다.
if [ -z "${VIRTUAL_ENV_DISABLE_PROMPT:-}" ] ; then
    _OLD_VIRTUAL_PS1="${PS1:-}"
    PS1="(.venv) ${PS1:-}"
    export PS1
fi

# 다시 한 번 명령 해시 테이블을 비워 바뀐 PATH가 정상 적용되도록 합니다.
hash -r 2> /dev/null
EOF
else
    echo "[INFO] .venv 가상환경이 이미 존재합니다."
fi

# 2. 가상환경 활성화
echo "[INFO] 가상환경(.venv)을 활성화합니다..."
source .venv/bin/activate

# 3. pip 최신화
echo "[INFO] pip를 최신 버전으로 업그레이드합니다..."
pip install --upgrade pip

# 4. req.txt의 의존성 라이브러리 설치
if [ -f "requirements.txt" ]; then
    echo "[INFO] requirements.txt 의존성 파일을 바탕으로 라이브러리를 설치합니다..."
    pip install -r requirements.txt
else
    echo "[WARN] requirements.txt 파일이 발견되지 않았습니다. 기본 필요한 라이브러리를 직접 설치합니다..."
    pip install python-dotenv PyYAML
fi

echo "[SUCCESS] 가상환경 자동 빌드 및 의존성 패키지 설치가 완료되었습니다!"
echo "[TIP] 가상환경을 수동으로 전환하여 사용하려면 아래 명령을 사용하세요:"
echo "      source .venv/bin/activate"

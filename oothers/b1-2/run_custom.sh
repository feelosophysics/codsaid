#!/usr/bin/env bash

# ==============================================================================
# [run_custom.sh] 사용자 정의 옵션 기반 실시간 장애 분석 애플리케이션 기동 스크립트
# ==============================================================================
# 이 스크립트는 초심자 개발자가 다른 동료나 친구에게 쉘 스크립트 작동 구조와 리눅스 
# 프로세스 제어 원리를 "완벽히 강의할 수 있을 정도"로 친절하고 상세한 교육용 한글 주석을
# 한 줄 한 줄 정밀 부착한 최종 마스터피스 학습 교안 버전입니다.
# ==============================================================================

# 1. 공통 환경 변수 및 설정 정의 (경로 동적 탐지 및 내보내기)
# ------------------------------------------------------------------------------
# [교육 꿀팁 - 쉘의 절대 경로 실시간 자동 탐지]
# - BASH_SOURCE[0]는 현재 실행 중인 스크립트의 파일명을 정확히 가리키는 내장 배열입니다.
# - dirname 명령어는 파일명 앞의 폴더 경로만 쏙 잘라내 줍니다.
# - cd와 pwd를 &&(AND)로 엮어 실행하면, 어떤 위치에서 실행하든 이 파일이 위치한 실제 절대 경로가 탐지됩니다.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# [교육 꿀팁 - ${변수:-기본값} 방어적 치환 문법]
# - AGENT_HOME 변수가 쉘 환경에 이미 존재하면 그 값을 쓰고, 비어 있으면 DEFAULT_HOME을 대입합니다.
DEFAULT_HOME="$SCRIPT_DIR/agent_home"
export AGENT_HOME="${AGENT_HOME:-$DEFAULT_HOME}"

# 애플리케이션 바인딩 포트(15034)와 서브 폴더 경로 정의 및 export(자식 프로세스로 환경 상속)
export AGENT_PORT=15034
export AGENT_UPLOAD_DIR="$AGENT_HOME/upload_files"
export AGENT_KEY_PATH="$AGENT_HOME/api_keys"
export AGENT_LOG_DIR="$AGENT_HOME/logs"

# 실행 파일(바이너리)의 로컬 상대 경로
APP_BIN="./agent-app-leak"

# 2. 도움말 출력 함수 (Usage Guide)
# ------------------------------------------------------------------------------
# - echo -e 옵션은 이스케이프 문자(\033 등)를 해석하여 터미널에 알록달록한 ANSI 색상을 입혀줍니다.
show_help() {
    echo -e "\033[1;34m======================================================================\033[0m"
    echo -e "💡 \033[1;36m[run_custom.sh] 사용 가이드 - 직접 제어하는 리소스 실습 환경\033[0m"
    echo -e "\033[1;34m======================================================================\033[0m"
    echo "사용법: $0 [옵션]"
    echo ""
    echo "지원하는 옵션:"
    echo "  -m, --memory <MB>      메모리 제한 설정 (정수, 범위: 50 ~ 512 MB)"
    echo "  -c, --cpu <%>          CPU 최대 허용률 설정 (정수, 범위: 10 ~ 100 %)"
    echo "  -t, --thread <bool>    멀티스레드 활성화 여부 (true / false)"
    echo "  -d, --daemon           백그라운드(Daemon) 모드로 실행 (실습 추적 모드)"
    echo "  -h, --help             이 도움말을 화면에 출력합니다."
    echo ""
    echo "예시:"
    echo "  ./run_custom.sh -m 128 -c 50 -t false"
    echo "  ./run_custom.sh --memory 256 --cpu 80 --thread true --daemon"
    echo "  (아무 인자 없이 실행 시 대화식 터미널 프롬프트 모드로 진입합니다.)"
    echo -e "\033[1;34m======================================================================\033[0m"
}

# 3. 명령줄 인수 파싱 루프 (Arguments Parsing Engine)
# ------------------------------------------------------------------------------
# - $#는 쉘에 전달된 전체 매개변수(인자)의 개수입니다.
# - -gt 0은 '0보다 크다(Greater Than)'를 뜻하므로, 인자가 남아있는 동안 계속 루프를 돕니다.
DAEMON_MODE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        -m|--memory)
            # $1은 첫 번째 매개변수(--memory), $2는 그 바로 뒤의 매개변수 값(예: 128)입니다.
            MEMORY_LIMIT="$2"
            # shift 2 명령어는 매개변수 큐를 왼쪽으로 2칸 강제로 당깁니다. ($3이 $1이 됨)
            shift 2
            ;;
        -c|--cpu)
            CPU_MAX_OCCUPY="$2"
            shift 2
            ;;
        -t|--thread)
            MULTI_THREAD_ENABLE="$2"
            shift 2
            ;;
        -d|--daemon)
            DAEMON_MODE=true
            # 데몬 모드는 뒤에 따라오는 인자 값이 없으므로 1칸만 shift 합니다.
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            # 등록되지 않은 엉뚱한 옵션 유입 시 즉각 에러 처리 후 도움말 제공
            echo -e "\033[1;31m❌ [오류] 알 수 없는 인수입니다: $1\033[0m"
            show_help
            exit 1
            ;;
    esac
done

# 4. 입력 부재 시 대화식 입력 프롬프트 제공 (Interactive Fallback & Input Validation)
# ------------------------------------------------------------------------------
echo -e "\033[1;35m======================================================================\033[0m"
echo -e "🚀 \033[1;35m[옵션 빌딩] 리소스 분석용 커스텀 환경 구성을 빌드합니다.\033[0m"
echo -e "\033[1;35m======================================================================\033[0m"

# 4.1 MEMORY_LIMIT 입력 유도 및 정규식 검증
# - -z "$변수" 문법은 변수가 Null(텅 빈 상태)인지 검사합니다.
if [ -z "$MEMORY_LIMIT" ]; then
    # read -p 명령은 터미널 화면에 프롬프트 안내를 띄우고 사용자 입력을 USER_MEM 변수에 곧바로 담아줍니다.
    read -p "👉 MEMORY_LIMIT 설정 (50~512 MB) [기본값: 256]: " USER_MEM
    MEMORY_LIMIT="${USER_MEM:-256}"
fi

# [교육 꿀팁 - 정규식을 활용한 정수 검증 문법]
# - =~ 정규식 매칭 연산자와 ^[0-9]+$ 정규 표현식을 사용해, 입력값이 순수 정수 숫자인지 1차 가려내고,
# - -lt(Less Than, 미만) 연산자와 -gt(Greater Than, 초과) 연산자로 미션 허용 범위를 정밀 필터링합니다.
if ! [[ "$MEMORY_LIMIT" =~ ^[0-9]+$ ]] || [ "$MEMORY_LIMIT" -lt 50 ] || [ "$MEMORY_LIMIT" -gt 512 ]; then
    echo -e "\033[1;31m❌ [오류] MEMORY_LIMIT는 50에서 512 사이의 정수여야 합니다. (입력값: $MEMORY_LIMIT)\033[0m"
    exit 1
fi

# 4.2 CPU_MAX_OCCUPY 입력 유도 및 검증
if [ -z "$CPU_MAX_OCCUPY" ]; then
    read -p "👉 CPU_MAX_OCCUPY 설정 (10~100 %) [기본값: 80]: " USER_CPU
    CPU_MAX_OCCUPY="${USER_CPU:-80}"
fi

if ! [[ "$CPU_MAX_OCCUPY" =~ ^[0-9]+$ ]] || [ "$CPU_MAX_OCCUPY" -lt 10 ] || [ "$CPU_MAX_OCCUPY" -gt 100 ]; then
    echo -e "\033[1;31m❌ [오류] CPU_MAX_OCCUPY는 10에서 100 사이의 정수여야 합니다. (입력값: $CPU_MAX_OCCUPY)\033[0m"
    exit 1
fi

# 4.3 MULTI_THREAD_ENABLE 입력 유도 및 불리언 형식 대조
if [ -z "$MULTI_THREAD_ENABLE" ]; then
    read -p "👉 MULTI_THREAD_ENABLE 여부 (true/false) [기본값: false]: " USER_THREAD
    MULTI_THREAD_ENABLE="${USER_THREAD:-false}"
fi

# [교육 꿀팁 - 대소문자 방어적 tr 치환]
# - tr '[:upper:]' '[:lower:]' 파이핑은 사용자가 TRUE, True, False 등으로 마구 입력해도
# - 전부 강제로 소문자(true/false)로 변환해 쉘의 변수 매칭 실패를 철저하게 무력화합니다.
MULTI_THREAD_ENABLE=$(echo "$MULTI_THREAD_ENABLE" | tr '[:upper:]' '[:lower:]')
if [ "$MULTI_THREAD_ENABLE" != "true" ] && [ "$MULTI_THREAD_ENABLE" != "false" ]; then
    echo -e "\033[1;31m❌ [오류] MULTI_THREAD_ENABLE은 'true' 또는 'false' 여야 합니다. (입력값: $MULTI_THREAD_ENABLE)\033[0m"
    exit 1
fi

# 외부 프로세스(애플리케이션 바이너리)가 이 환경변수를 온전히 물고 갈 수 있게 export 처리
export MEMORY_LIMIT
export CPU_MAX_OCCUPY
export MULTI_THREAD_ENABLE

# 5. 실행 권한 자가 진단 및 초기 환경 검증
# ------------------------------------------------------------------------------
# - ! -x 옵션은 파일에 '실행 권한(eXecute)'이 없는 상태를 논리 부정(!) 연산자로 걸러냅니다.
if [ ! -x "$APP_BIN" ]; then
    echo -e "\033[1;33m[안내] $APP_BIN 바이너리에 실행 권한이 부여되지 않았습니다. 권한을 부여합니다 (chmod +x).\033[0m"
    chmod +x "$APP_BIN"
fi

# [교육 꿀팁 - source 명령어와 Sub-shell의 원리]
# - ./setup_env.sh 처럼 단순 실행하면 서브 쉘(새 자식 프로세스)이 뜨며 부모 쉘의 환경변수 영역에 도달하지 못하지만,
# - 'source' 혹은 '.' 명령어를 붙여 가져오면 현재 이 스크립트가 실행되고 있는 '동일 쉘 메모리 공간' 위에 
#   setup_env.sh가 정의해놓은 디렉토리 권한과 변수 설정들을 그대로 복사 이식받게 됩니다.
if [ -f "./setup_env.sh" ]; then
    source ./setup_env.sh
else
    echo -e "\033[1;33m[경고] setup_env.sh가 존재하지 않아 기본 구성 요소를 자동 생성합니다.\033[0m"
    mkdir -p "$AGENT_UPLOAD_DIR" "$AGENT_KEY_PATH" "$AGENT_LOG_DIR"
    echo -n "agent_api_key_test" > "$AGENT_KEY_PATH/secret.key"
fi

# 6. 프로세스 초기화 및 관제 스크립트와의 아름다운 공존 (Coexistence Architecture)
# ------------------------------------------------------------------------------

# [핵심 학습 포인트 - 포트 충돌 방지 및 안전 청소]
# - pgrep 명령어는 실행 중인 프로세스 이름 전체를 대상으로 필터링 검색하여 매칭되는 PID만 뽑아냅니다.
# - 기존에 기동해 둔 앱이 있으면 포트 15034 바인딩 충돌이 백 퍼센트 나기 때문에 기동 전 무조건 안전 사멸해야 합니다.
# - 교착 상태(Deadlock)에 빠진 스레드는 일반 종료 신호에 불응하므로 강제 사멸 시그널(-9, SIGKILL)을 명시 주입합니다.
cleanup_previous_app() {
    echo "----------------------------------------------------------------------"
    echo -e "\033[1;36m🧹 [애플리케이션 초기화] 포트 충돌 방지를 위해 기존 agent-app-leak 인스턴스를 찾아 종료합니다.\033[0m"
    
    APP_PIDS=$(pgrep -f "agent-app-leak")
    if [ -n "$APP_PIDS" ]; then
        kill -9 $APP_PIDS 2>/dev/null
        echo "✔ 기존에 실행 중이던 백그라운드 애플리케이션(agent-app-leak, PID: $APP_PIDS)을 강제 종료했습니다."
    else
        echo "✔ 충돌되는 기존 애플리케이션 프로세스가 없습니다. 깨끗한 상태입니다."
    fi
    echo "----------------------------------------------------------------------"
}

# [핵심 학습 포인트 - monitor.sh 프로세스의 생존 보장!]
# - 기존 run_scenario.sh는 monitor.sh 마저 강제 종료 시켜서 초심자가 다른 창에서 로그를 띄워두고 실습하는 흐름을 방해했습니다.
# - 본 스크립트는 monitor.sh를 절대 죽이지 않고, 현재 켜져 있는지가 확인되면 친절한 tail -f 조회 법을 안내하고,
#   켜져 있지 않을 때만 따로 구동해달라는 스마트 경고 지침을 화면에 피드백합니다.
check_monitor_status() {
    # grep -v grep은 pgrep 검색 쉘 자체가 필터 결과 목록에 꼬여 들어오는 부작용을 원천 배제시킵니다.
    MON_PIDS=$(pgrep -f "monitor.sh" | grep -v grep)
    if [ -z "$MON_PIDS" ]; then
        echo -e "\033[1;33m💡 [안내] 현재 관제 스크립트(monitor.sh)가 실행되고 있지 않습니다!\033[0m"
        echo "   실시간 관제 분석 실습을 위해, 다른 터미널 창을 열고 아래 명령어로 관제를 먼저 실행해 주세요:"
        echo -e "   \033[1;36m./monitor.sh\033[0m"
    else
        echo -e "\033[1;32m✔ [안내] 관제 스크립트(monitor.sh)가 이미 동작 중입니다!\033[0m (PID: $MON_PIDS)"
        echo "   다른 터미널 창에서 실시간 관제 로그 스트리밍을 볼 수 있습니다:"
        echo -e "   \033[1;36mtail -f \"$AGENT_LOG_DIR/monitor.log\"\033[0m"
    fi
    echo "----------------------------------------------------------------------"
}

cleanup_previous_app
check_monitor_status

# 7. 애플리케이션 기동 연산 및 모드 분기 (Foreground vs Daemon Mode)
# ------------------------------------------------------------------------------
echo -e "\033[1;32m⚙ [기동 구성 요약]"
echo "   - MEMORY_LIMIT        : $MEMORY_LIMIT MB"
echo "   - CPU_MAX_OCCUPY      : $CPU_MAX_OCCUPY %"
echo "   - MULTI_THREAD_ENABLE : $MULTI_THREAD_ENABLE"
echo -e "   - RUN_MODE            : $( [ "$DAEMON_MODE" = true ] && echo "Background (Daemon)" || echo "Foreground (Live Console)" )\033[0m"
echo "----------------------------------------------------------------------"

# 이전 잔존 로그 잔상을 지우기 위해 리디렉션 덮어쓰기(>) 기호로 로그 파일 초기 비우기
> "$AGENT_LOG_DIR/app.log"

if [ "$DAEMON_MODE" = true ]; then
    # 7.1 [백그라운드(Daemon) 실행 모드]
    echo -e "\033[1;32m🚀 애플리케이션을 백그라운드 모드로 구동합니다.\033[0m"
    
    # [교육 꿀팁 - nohup과 백그라운드 기호 &의 공학적 의미]
    # - nohup은 'No Hang Up'의 약자로, 사용자가 터미널 창을 닫아 세션이 끊어져도(SIGHUP 시그널이 발생해도)
    #   커널이 이 자식 프로세스를 고아 프로세스로 이관하여 끝까지 영구히 존속시키는 보호막입니다.
    # - 뒤에 붙는 '2>&1'은 표준 에러(2) 출력 스트림을 표준 출력(1)이 가리키는 파일 경로(app.log)로 합수시켜 병합하라는 고도의 스트림 리디렉션이며,
    # - 맨 끝의 '&'는 이 무거운 바이너리를 실행하는 주도권을 백그라운드로 던져 쉘의 제어권을 사용자 프롬프트로 즉각 복귀시키는 마법의 특수기호입니다.
    nohup "$APP_BIN" > "$AGENT_LOG_DIR/app.log" 2>&1 &
    
    # 찰나의 기동 물리 할당 대기 시간 부여
    sleep 0.3
    NEW_APP_PID=$(pgrep -f "agent-app-leak" | sort -n | tail -n 1)
    
    if [ -n "$NEW_APP_PID" ]; then
        echo -e "  - 애플리케이션 PID   : \033[1;36m$NEW_APP_PID\033[0m"
        echo "  - 애플리케이션 로그  : $AGENT_LOG_DIR/app.log"
        echo ""
        echo -e "\033[1;33m📚 [학습 미션 - 다음 명령어들을 다른 터미널에서 입력하여 직접 상태를 진단해 보세요!]\033[0m"
        echo "  1. 프로세스가 가상 메모리 테이블에 살아있는지 증명하기:"
        echo -e "     \033[1;36mps -ef | grep agent-app-leak\033[0m"
        echo "  2. 실시간 CPU 및 메모리 소모 수치 개별 필터링 조회하기 (헤더 생략 옵션):"
        echo -e "     \033[1;36mps -p $NEW_APP_PID -o %cpu=,%mem=\033[0m"
        echo "  3. 애플리케이션 내부 실행 스레드(LWP) 테이블 전개 관측하기 (데드락 진단 필수):"
        echo -e "     \033[1;36mps -L -p $NEW_APP_PID\033[0m"
        echo "  4. 실시간으로 수집되는 monitor.sh 관제 데이터 로그 스트리밍하기:"
        echo -e "     \033[1;36mtail -f \"$AGENT_LOG_DIR/monitor.log\"\033[0m"
        echo "  5. 프로세스를 직접 강제 사멸시키는 시그널 실험해보기:"
        echo -e "     \033[1;36mkill -9 $NEW_APP_PID\033[0m"
    else
        echo -e "\033[1;31m❌ [오류] 백그라운드 애플리케이션 기동에 실패했습니다. 로그를 점검하세요 ($AGENT_LOG_DIR/app.log).\033[0m"
        exit 1
    fi
else
    # 7.2 [포그라운드(Live Console) 실행 모드]
    echo -e "\033[1;32m🚀 애플리케이션을 포그라운드 모드로 구동합니다. 콘솔 로그가 스트리밍됩니다.\033[0m"
    echo -e "\033[1;33m👉 실행을 중단하고 프로세스를 종료하려면 터미널에서 [Ctrl + C]를 누르세요.\033[0m"
    echo "----------------------------------------------------------------------"
    
    # [교육 꿀팁 - tee 명령의 위대함]
    # - 일반 파이프 리디렉션은 화면을 묵묵부답으로 막아버려 콘솔 실시간 보기가 안 됩니다.
    # - 'tee' 명령어는 수도관의 T자형 분기점처럼 작동하여, 흘러나오는 표준 출력 물줄기를
    #   1번 스트림(사용자 눈에 보이는 화면 터미널)과 2번 스트림(실제 파일 app.log 기록) 양쪽으로 동시에 쏘아 보내 줍니다.
    "$APP_BIN" 2>&1 | tee "$AGENT_LOG_DIR/app.log"
fi

echo -e "\033[1;34m======================================================================\033[0m"

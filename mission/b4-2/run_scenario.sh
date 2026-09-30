#!/usr/bin/env bash

# ==============================================================================
# [run_scenario.sh] 장애 재현 및 교육용 실시간 명령어 검증 CLI 튜터 컨트롤러
# ==============================================================================
# 이 스크립트는 리눅스 초심자가 메모리 누수(OOM), CPU Spike, Deadlock 장애를 분석하고
# 상황에 맞는 실전 관제 명령어(ps, top, pstack 등)를 직접 손으로 입력하여 숙달할 수 있게 돕는
# "인터랙티브 교육형 CLI 시뮬레이터 튜터"입니다.
# 
# 다른 초심자에게 이 장애 환경과 명령어의 기저 원리를 "완벽히 강의할 수 있을 정도"의
# 최고 밀도 해설 한글 주석을 한 줄 한 줄 친절하게 부착했습니다.
# ==============================================================================

# 1. 공통 환경 변수 및 설정 정의 (동적화)
# ------------------------------------------------------------------------------
# [교육적 경로 동적화 기법]
# 하드코딩된 경로는 환경 이식성을 해칩니다. SCRIPT_DIR를 통해 이 스크립트가 실행된 
# 실제 폴더 위치를 실시간 탐지하여 agent_home 디렉토리 절대 경로를 동적으로 수립합니다.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_HOME="$SCRIPT_DIR/agent_home"
export AGENT_HOME="${AGENT_HOME:-$DEFAULT_HOME}"
export AGENT_PORT=15034
export AGENT_UPLOAD_DIR="$AGENT_HOME/upload_files"
export AGENT_KEY_PATH="$AGENT_HOME/api_keys"
export AGENT_LOG_DIR="$AGENT_HOME/logs"

# 앱 실행 바이너리의 로컬 경로 지정
APP_BIN="./agent-app-leak"

# 2. 실행 권한 및 초기 환경 검증
# ------------------------------------------------------------------------------
if [ ! -x "$APP_BIN" ]; then
    echo -e "\033[1;33m[안내] $APP_BIN 바이너리에 실행 권한이 부여되지 않았습니다. 권한을 부여합니다 (chmod +x).\033[0m"
    chmod +x "$APP_BIN"
fi

if [ -f "./monitor.sh" ] && [ ! -x "./monitor.sh" ]; then
    chmod +x "./monitor.sh"
fi

# setup_env.sh를 활용해 기초 폴더 구성과 secret.key 검증을 선제적으로 완수합니다.
if [ -f "./setup_env.sh" ]; then
    # 'source' 명령어는 서브 쉘을 띄우지 않고 현재 쉘의 메모리 공간에 환경 구성을 로드합니다.
    source ./setup_env.sh
else
    echo -e "\033[1;31m[경고] setup_env.sh가 존재하지 않아 기본 구성 요소를 자동 생성합니다.\033[0m"
    mkdir -p "$AGENT_UPLOAD_DIR" "$AGENT_KEY_PATH" "$AGENT_LOG_DIR"
    echo -n "agent_api_key_test" > "$AGENT_KEY_PATH/secret.key"
fi

# 3. 헬퍼 기능: 실행 중인 프로세스 안전 청소 (Cleanup)
# ------------------------------------------------------------------------------
cleanup_processes() {
    echo "----------------------------------------------------------------------"
    echo -e "\033[1;36m🧹 [프로세스 초기화] 잔존 프로세스(앱 및 관제 툴)가 있는지 조회하고 종료합니다.\033[0m"
    
    MON_PIDS=$(pgrep -f "monitor.sh")
    if [ -n "$MON_PIDS" ]; then
        kill $MON_PIDS 2>/dev/null
        echo "✔ 백그라운드 관제 스크립트(monitor.sh)를 안전하게 종료했습니다."
    fi

    APP_PIDS=$(pgrep -f "agent-app-leak")
    if [ -n "$APP_PIDS" ]; then
        # 교착상태(Deadlock)에 빠진 스레드는 일반 SIGTERM(15) 시그널에 무응답할 수 있으므로,
        # 확실한 자원 해제를 위해 강제 종료 시그널인 SIGKILL(-9)을 동시 주입합니다.
        kill -9 $APP_PIDS 2>/dev/null
        echo "✔ 백그라운드 애플리케이션(agent-app-leak)을 강제 종료(-9) 처리했습니다."
    fi
    echo "----------------------------------------------------------------------"
}

# 4. 헬퍼 기능: 시나리오 기동기 (Launcher)
# ------------------------------------------------------------------------------
launch_scenario() {
    cleanup_processes

    echo -e "\033[1;35m======================================================================"
    echo "🚀 [시나리오 기동] 프로세스를 백그라운드 모드로 가동합니다."
    echo "   - MEMORY_LIMIT        : $MEMORY_LIMIT MB"
    echo "   - CPU_MAX_OCCUPY      : $CPU_MAX_OCCUPY %"
    echo "   - MULTI_THREAD_ENABLE : $MULTI_THREAD_ENABLE"
    echo -e "======================================================================\033[0m"

    export MEMORY_LIMIT
    export CPU_MAX_OCCUPY
    export MULTI_THREAD_ENABLE

    # 백그라운드 로그 파일 초기화
    > "$AGENT_LOG_DIR/app.log"
    > "$AGENT_LOG_DIR/monitor.log"

    # 관제 및 앱 백그라운드 기동
    # - nohup은 터미널이 닫혀도 자식 프로세스의 생존을 방어하며, 끝의 &는 백그라운드 전송 기호입니다.
    nohup ./monitor.sh > /dev/null 2>&1 &
    nohup "$APP_BIN" > "$AGENT_LOG_DIR/app.log" 2>&1 &

    sleep 0.5
    NEW_APP_PID=$(pgrep -f "agent-app-leak" | head -n 1)
    NEW_MON_PID=$(pgrep -f "monitor.sh" | head -n 1)

    echo -e "\033[1;32m✔ 기동 성공!\033[0m"
    echo "  - 애플리케이션 PID   : $NEW_APP_PID"
    echo "  - 관제 스크립트 PID  : $NEW_MON_PID"
    echo "----------------------------------------------------------------------"
}

# 5. 실습 명령어 안내판 (Tutorial Print Helper)
# ------------------------------------------------------------------------------
print_tutorial_guide() {
    local SCENARIO_TYPE="$1"
    echo -e "\n\033[1;33m💡 [초심자 실습 미션 가이드라인 - 직접 타이핑하여 실습해 보세요!]\033[0m"
    case "$SCENARIO_TYPE" in
        "OOM")
            echo "1. 새 터미널을 열고 실시간 관제 로그를 스트리밍해 봅니다:"
            echo -e "   \033[1;36mtail -f $AGENT_LOG_DIR/monitor.log\033[0m"
            echo "2. OOM Crash가 터진 후, 애플리케이션 로그의 마지막 부분을 분석하세요:"
            echo -e "   \033[1;36mtail -n 20 $AGENT_LOG_DIR/app.log\033[0m"
            echo "3. [실습 핵심] 아래 문구를 확인하고, 메모리 제한이 도달한 정확한 시점을 증명하세요:"
            echo "   'Memory limit exceeded...' 및 'SELF-TERMINATED...'"
            ;;
        "CPU")
            echo "1. 새 터미널을 열고 특정 프로세스의 CPU 사용률을 실시간 조회합니다:"
            echo -e "   \033[1;36mtop -p \$(pgrep -f agent-app-leak)\033[0m"
            echo "2. CPU 사용률이 치솟은 직후 내장 Watchdog 정책에 의해 프로세스가 사멸되는 로그를 확인하세요:"
            echo -e "   \033[1;36mtail -f $AGENT_LOG_DIR/app.log\033[0m"
            echo "   'WATCHDOG: INITIATING EMERGENCY ABORT (SIGTERM)' 로그가 핵심 증거입니다."
            ;;
        "DEADLOCK")
            echo "1. 프로세스가 종료되지 않고 멈춰 있는지 PID 생존을 증명합니다:"
            echo -e "   \033[1;36mps -ef | grep agent-app-leak\033[0m"
            echo "2. 스레드 자원 점유가 완전히 멎은 상태(0% CPU, 메모리 정체)인지 스레드 단위로 감시합니다:"
            echo -e "   \033[1;36mps -L -p \$(pgrep -f agent-app-leak) -o pid,tid,%cpu,%mem,comm,state\033[0m"
            echo "3. 로그 출력 자체가 영구히 멎은 마지막 지점을 조사하세요:"
            echo -e "   \033[1;36mtail -n 10 $AGENT_LOG_DIR/app.log\033[0m"
            echo "   'WAITING... BLOCKED' 상태에서 멈춘 두 스레드의 이름 and 자원 락 관계를 메모해 두세요."
            ;;
    esac
    echo "======================================================================"
}

# 6. 초심자용 플레이북 출력 도우미 (Playbook Print Helper)
# ------------------------------------------------------------------------------
print_system_playbook() {
    echo -e "\n\033[1;34m======================================================================"
    echo "         📘 [초심자를 위한 리눅스 트러블슈팅 실습 플레이북]"
    echo "======================================================================"
    echo "  1단계: [환경 셋업] ./setup_env.sh 를 실행해 필수 인증키와 경로를 구성합니다."
    echo "  2단계: [제어기 기동] ./run_scenario.sh 로 대화식 제어 패널을 실행합니다."
    echo "  3단계: [장애 재현] 1번(OOM), 3번(CPU Spike), 5번(Deadlock) 메뉴를 구동해"
    echo "         앱을 백그라운드로 띄우고 실시간 미션 가이드를 숙독합니다."
    echo "  4단계: [실시간 관제] 튜터가 추천하는 명령어를 다른 터미널에 쳐 보며 데이터를 수집합니다."
    echo "  5단계: [조치 및 검증] 2번, 4번, 6번 조치 메뉴로 환경변수를 고쳐 Before & After를 증명합니다."
    echo "  6단계: [대화식 학습] 9번 메뉴를 켜서 튜터와 함께 '왜', '어떻게' 명령어를"
    echo "         옵션 한 칸씩 조립(Building Block)하며 실질적인 관제 역량을 마스터합니다!"
    echo -e "======================================================================\033[0m"
}

# 7. 인터랙티브 명령어 빌딩 튜터 엔진 (★ 대화식 빌딩-블록 패러다임 전면 개편 ★)
# ------------------------------------------------------------------------------
run_command_tutor() {
    local ACTUAL_PID=$(pgrep -f "agent-app-leak" | head -n 1)
    
    echo -e "\n\033[1;35m======================================================================"
    echo "  🎓 [대화식 관제 명령어 빌딩 블록 튜터에 오신 것을 환영합니다!]"
    echo "  - 이 시뮬레이터는 '애초에 모르는 상태'에서 출발해 생각의 흐름을 훈련합니다."
    echo "  - 튜터가 관제 목적과 필요한 명령어 조각들을 차근차근 설명해 드릴 것입니다."
    echo "  - 설명을 토대로 조각들을 퍼즐처럼 하나로 이어붙여 명령어를 완성해 보세요!"
    echo "  - (실제 구동 중인 앱의 PID는 '$ACTUAL_PID'입니다. 입력 시 사용해 보세요.)"
    echo -e "======================================================================\033[0m"

    # [Step 1: 프로세스 탐색 - PID 생존 증명]
    # --------------------------------------------------------------------------
    while true; do
        echo -e "\n\033[1;33m[Step 1] 탐정의 첫 걸음: 프로세스 생존 여부 확인하기\033[0m"
        echo "  - **상황 맥락**: '프로세스가 갑자기 프리징되었습니다. 완전히 죽은 크래시인가요? 살아만 있는 먹통인가요?'"
        echo "  - **관제 목적**: 프로세스가 커널 메모리에 로드되어 PID(Process ID)를 꿋꿋하게 갖고 있는지 먼저 조회해야 합니다."
        echo "  - **명령어 조각 설명**:"
        echo "    * 조각 A: 'ps -ef' (시스템 내 실행 중인 전체 프로세스 목록을 표 형태로 깔끔하게 리포트)"
        echo "    * 조각 B: 'grep agent' (너무 방대한 목록에서 오직 'agent'가 포함된 한 행만 콕 집어 필터링)"
        echo "    * 연결 고리: '|' (파이프 기호 - 앞 명령어의 결과를 뒤 명령어의 입력으로 수혈)"
        echo "----------------------------------------------------------------------"
        echo "  ✍ [미션]: 조각 A와 조각 B를 파이프(|)로 연결해 'agent 프로세스를 탐색하는 한 줄의 명령어'를 조립해 보세요!"
        read -p "▶ 조립된 명령어 입력: " USER_INPUT
        USER_INPUT=$(echo "$USER_INPUT" | xargs)

        if [[ "$USER_INPUT" =~ ^ps[[:space:]]+-[A-Za-z]*e[A-Za-z]*f[A-Za-z]*[[:space:]]*\|[[:space:]]*grep[[:space:]]+agent[[:space:]]*$ ]] || \
           [[ "$USER_INPUT" =~ ^ps[[:space:]]+aux[[:space:]]*\|[[:space:]]*grep[[:space:]]+agent[[:space:]]*$ ]]; then
            
            echo -e "\n\033[1;32m✔ [정답입니다!] 아주 훌륭한 첫 조립입니다.\033[0m"
            echo "----------------------------------------------------------------------"
            echo -e "\033[1;36m🔬 [ubu27 가상머신 라이브 연동 출력]\033[0m"
            eval "$USER_INPUT" | grep -v grep
            echo "----------------------------------------------------------------------"
            echo -e "\033[1;34m📖 [튜터의 생각 흐름 강의]\033[0m"
            echo "  - 'ps -ef'로 프로세스 리스트를 출력하고, 이를 'grep agent'로 조여 현재 프로세스가"
            echo "    정확히 몇 번 PID로 구동 중인지 파악했습니다. PID가 잡힌다면 프로세스는 '살아 있는' 상태입니다."
            echo "======================================================================"
            break
        else
            echo -e "\033[1;31m❌ [오답입니다!] 아하, 조각들의 조립이 조금 엇갈렸습니다.\033[0m"
            echo "💡 힌트: 'ps -ef'를 먼저 치고, 한 칸 띄우고 파이프('|') 기호를 넣은 뒤, 'grep agent'를 이어 붙이세요."
            echo "   (작성 예시: ps -ef | grep agent)"
        fi
    done

    # [Step 2: 물리 메모리 점유율 관제 - OOM 탐지]
    # --------------------------------------------------------------------------
    local Q2_PID=${ACTUAL_PID:-55432}
    while true; do
        echo -e "\n\033[1;33m[Step 2] 힙 누수 추적: 물리 메모리 RSS 비율 추출하기\033[0m"
        echo "  - **상황 맥락**: '프로세스가 약 10분 후 예고 없이 꺼집니다. 메모리 증가 패턴이 선형적으로 우상향하나요?'"
        echo "  - **관제 목적**: 가상 메모리(VSZ)는 빈 선언 주소까지 더해져 뻥튀기되므로, '실제 가용 물리 RAM에 할당된 RSS(Resident Set Size) 사용 백분율'만 순수하게 가로채어 기울기를 감시해야 합니다."
        echo "  - **명령어 조각 설명**:"
        echo "    * 조각 A: 'ps' (프로세스 상태 조회 기본문)"
        echo "    * 조각 B: '-p $Q2_PID' (방금 찾은 특정 프로세스 ID를 타겟팅)"
        echo "    * 조각 C: '-o %mem=' (원하는 컬럼인 '%mem(물리메모리 비율)'을 선택하고, 등호`=`를 끝에 달아 칼럼명 헤더를 강제 제거!)"
        echo "----------------------------------------------------------------------"
        echo "  ✍ [미션]: 조각 A, B, C를 모두 빈칸으로 분리하여 순서대로 이어붙이고, 특정 PID(예: $Q2_PID)의 물리 메모리 점유율을 헤더 없이 숫자만 깔끔하게 출력하는 완전한 단일 명령어를 조립해 보세요!"
        read -p "▶ 조립된 명령어 입력: " USER_INPUT
        USER_INPUT=$(echo "$USER_INPUT" | xargs)

        if [[ "$USER_INPUT" =~ ^ps[[:space:]]+(-p|--pid)[[:space:]]+([0-9]+|\$[A-Za-z0-9_]+)[[:space:]]+-o[[:space:]]+%mem=[[:space:]]*$ ]] || \
           [[ "$USER_INPUT" =~ ^ps[[:space:]]+-o[[:space:]]+%mem=[[:space:]]+(-p|--pid)[[:space:]]+([0-9]+|\$[A-Za-z0-9_]+)[[:space:]]*$ ]]; then
            
            local CMD_TO_RUN=$(echo "$USER_INPUT" | sed "s/\$PID/$ACTUAL_PID/g")
            
            echo -e "\n\033[1;32m✔ [정답입니다!] 완벽하게 옵션을 빌딩하셨습니다.\033[0m"
            echo "----------------------------------------------------------------------"
            echo -e "\033[1;36m🔬 [ubu27 가상머신 라이브 연동 출력]\033[0m"
            if [ -n "$ACTUAL_PID" ]; then
                echo "💻 실행 명령어: $CMD_TO_RUN"
                echo -n "📊 라이브 메모리 점유율: "
                eval "$CMD_TO_RUN"
            else
                echo -e "💻 실행 명령어: ps -p 55432 -o %mem=\n📊 가상 출력:  12.8%"
                echo "*(현재 백그라운드 프로세스가 실행 중이지 않아 시뮬레이션 데이터를 표시합니다)*"
            fi
            echo "----------------------------------------------------------------------"
            echo -e "\033[1;34m📖 [튜터의 생각 흐름 강의]\033[0m"
            echo "  - '-o %mem='의 기적: 컬럼을 직접 지정하는 Custom Format 옵션(-o) 뒤에 등호(=)를 명시적으로"
            echo "    붙여주는 이 사소한 세부 행동이, 쓸데없는 텍스트 헤더('%MEM')를 제거해 쉘 스크립트가 데이터 가공 없이"
            echo "    순수 숫자 백분율만 변수에 담을 수 있게 해주는 결정적 실무 꿀팁입니다."
            echo "======================================================================"
            break
        else
            echo -e "\033[1;31m❌ [오답입니다!] 아하, 조립 중에 옵션이나 부호가 빠진 것 같습니다.\033[0m"
            echo "💡 힌트: 'ps'를 적고, 특정 PID 지칭 옵션 '-p $Q2_PID'를 한 칸 띄워 적고, 헤더 제거 옵션 '-o %mem='을 이어 붙이세요."
            echo "   (작성 예시: ps -p $Q2_PID -o %mem=)"
        fi
    done

    # [Step 3: CPU 과점유 식별 - CPU Spike]
    # --------------------------------------------------------------------------
    local Q3_PID=${ACTUAL_PID:-55432}
    while true; do
        echo -e "\n\033[1;33m[Step 3] 연산 부하 추적: CPU 사용률 추출하기\033[0m"
        echo "  - **상황 맥락**: '특정 구간에서 시스템이 극도로 지연됩니다. 특정 프로세스가 CPU를 과독점하는지 증거를 잡으세요!'"
        echo "  - **관제 목적**: 대화식으로 화면을 실시간 그리는 top 명령어 대신, 시스템 오버헤드 없이 깔끔하게 특정 PID의 CPU 점유 % 수치만 낚아채어 Watchdog 보호 정책의 임계치와 실시간 비교 대조해야 합니다."
        echo "  - **명령어 조각 설명**:"
        echo "    * 조각 A: 'ps -p $Q3_PID'"
        echo "    * 조각 B: '-o %cpu=' (원하는 칼럼인 '%cpu(CPU 사용율)'을 커스텀 출력하며, 등호`=`를 끝에 붙여 헤더 제거!)"
        echo "----------------------------------------------------------------------"
        echo "  ✍ [미션]: 조각 A와 조각 B를 결합하여 특정 PID(예: $Q3_PID)의 CPU 사용률을 헤더 없이 단번에 구하는 명령어를 완성해 보세요!"
        read -p "▶ 조립된 명령어 입력: " USER_INPUT
        USER_INPUT=$(echo "$USER_INPUT" | xargs)

        if [[ "$USER_INPUT" =~ ^ps[[:space:]]+(-p|--pid)[[:space:]]+([0-9]+|\$[A-Za-z0-9_]+)[[:space:]]+-o[[:space:]]+%cpu=[[:space:]]*$ ]] || \
           [[ "$USER_INPUT" =~ ^ps[[:space:]]+-o[[:space:]]+%cpu=[[:space:]]+(-p|--pid)[[:space:]]+([0-9]+|\$[A-Za-z0-9_]+)[[:space:]]*$ ]]; then
            
            local CMD_TO_RUN=$(echo "$USER_INPUT" | sed "s/\$PID/$ACTUAL_PID/g")
            
            echo -e "\n\033[1;32m✔ [정답입니다!] CPU 점유율 빌딩을 성공리에 완수했습니다.\033[0m"
            echo "----------------------------------------------------------------------"
            echo -e "\033[1;36m🔬 [ubu27 가상머신 라이브 연동 출력]\033[0m"
            if [ -n "$ACTUAL_PID" ]; then
                echo "💻 실행 명령어: $CMD_TO_RUN"
                echo -n "📊 라이브 CPU 사용률: "
                eval "$CMD_TO_RUN"
            else
                echo -e "💻 실행 명령어: ps -p 55432 -o %cpu=\n📊 가상 출력:  48.5%"
                echo "*(현재 백그라운드 프로세스가 실행 중이지 않아 시뮬레이션 데이터를 표시합니다)*"
            fi
            echo "----------------------------------------------------------------------"
            echo -e "\033[1;34m📖 [튜터의 생각 흐름 강의]\033[0m"
            echo "  - 이처럼 'ps -p PID -o %mem='과 'ps -p PID -o %cpu='의 일관된 원리를 꿰뚫음으로써,"
            echo "    우리는 쉘 스크립트(monitor.sh) 내에서 가벼운 시스템 콜 조회를 기반으로"
            echo "    리소스 과점유 장애 증거 데이터를 아주 정교하게 누적 수집할 수 있게 되었습니다."
            echo "======================================================================"
            break
        else
            echo -e "\033[1;31m❌ [오답입니다!] 옵션 문자나 등호(=)를 다시 한번 체크해 보세요.\033[0m"
            echo "💡 힌트: 'ps -p $Q3_PID -o %cpu=' 형태로 구성되었는지 철자와 부호를 엄밀히 확인하세요."
        fi
    done

    # [Step 4: 스레드 상태 진단 - Deadlock 프리징 감지]
    # --------------------------------------------------------------------------
    local Q4_PID=${ACTUAL_PID:-55432}
    while true; do
        echo -e "\n\033[1;33m[Step 4] 스레드 수면 분석: 내부 경량 스레드(LWP) 전개하기\033[0m"
        echo "  - **상황 맥락**: '프로세스는 꿋꿋하게 살아 있는데(PID 생존), CPU도 0%로 머물고 아무 로그도 안 나옵니다. 스레드들이 락 경쟁을 하다가 기절해 버린 것 아닐까요?'"
        echo "  - **관제 목적**: 프로세스 내부의 모든 개별 실행 스레드(Light-Weight Process, LWP) 목록을 펼쳐, 걔네들이 실제로 시간을 소비하며 연산을 하고 있는지(TIME 필드 감시) 정체 상태를 감시합니다."
        echo "  - **명령어 조각 설명**:"
        echo "    * 조각 A: 'ps -p $Q4_PID' (대상 PID 타겟팅)"
        echo "    * 조각 B: '-L' (LWP - 스레드 테이블을 촤르륵 펼쳐서 시각화하라는 핵심 지시자)"
        echo "----------------------------------------------------------------------"
        echo "  ✍ [미션]: 조각 A와 조각 B를 스페이스로 결합하여 프로세스(PID: $Q4_PID) 내부의 모든 스레드 상태를 상세 전개하여 보여주는 명령어를 조립해 보세요!"
        read -p "▶ 조립된 명령어 입력: " USER_INPUT
        USER_INPUT=$(echo "$USER_INPUT" | xargs)

        if [[ "$USER_INPUT" =~ ^ps[[:space:]]+.*-L.* ]] && [[ "$USER_INPUT" =~ -p[[:space:]]+([0-9]+|\$[A-Za-z0-9_]+) ]]; then
            
            local CMD_TO_RUN=$(echo "$USER_INPUT" | sed "s/\$PID/$ACTUAL_PID/g")
            
            echo -e "\n\033[1;32m✔ [정답입니다!] 스레드 전개 핵심 원리를 완전히 포착하셨습니다.\033[0m"
            echo "----------------------------------------------------------------------"
            echo -e "\033[1;36m🔬 [ubu27 가상머신 라이브 연동 출력]\033[0m"
            if [ -n "$ACTUAL_PID" ]; then
                echo "💻 실행 명령어: $CMD_TO_RUN | head -n 8"
                echo "📊 라이브 출력: "
                eval "$CMD_TO_RUN" | head -n 8
            else
                echo "💻 실행 명령어: ps -L -p 55432"
                echo -e "📊 가상 출력  :"
                echo -e "    PID   LWP TTY          TIME CMD"
                echo -e "  55432 55432 pts/0    00:00:01 agent-app-leak"
                echo -e "  55432 55433 pts/0    00:00:00 worker_thread_A"
                echo -e "  55432 55434 pts/0    00:00:00 worker_thread_B"
                echo "*(현재 백그라운드 프로세스가 실행 중이지 않아 시뮬레이션 데이터를 표시합니다)*"
            fi
            echo "----------------------------------------------------------------------"
            echo -e "\033[1;34m📖 [튜터의 생각 흐름 강의]\033[0m"
            echo "  - **데드락 증거 수집의 백미**: 이 명령어 실행 결과의 'TIME' 컬럼은 스레드가 점유한"
            echo "    순수 CPU 타임 누적치입니다. 데드락에 빠지면 수십 분이 흘러도 TIME 수치가 소수점 끝자리조차"
            echo "    단 1밀리초도 늘어나지 않고 영구 프리징됩니다. CPU가 0%이면서 TIME이 얼어붙었다는 물증을 100% 획득하는 것입니다."
            echo "======================================================================"
            break
        else
            echo -e "\033[1;31m❌ [오답입니다!] 스레드 전개 옵션(-L)과 PID 지칭 옵션(-p)의 조합을 확인하세요.\033[0m"
            echo "💡 힌트: 'ps -L -p $Q4_PID' 또는 'ps -p $Q4_PID -L' 형태가 바른 문법입니다."
        fi
    done

    # [Step 5: 콜스택 분석 - 데드락 락 대기 입증]
    # --------------------------------------------------------------------------
    local Q5_PID=${ACTUAL_PID:-55432}
    while true; do
        echo -e "\n\033[1;33m[Step 5] 락 대기 코드 검증: 콜스택 덤프 뽑아내기\033[0m"
        echo "  - **상황 맥락**: '스레드가 멈춰 있는 것까진 알았습니다. 대체 소스 코드 몇 번째 행에서 어떤 자원 락을 달라고 조르고 있기에 멈춘 건가요?'"
        echo "  - **관제 목적**: 실행 중인 각 스레드의 함수 호출 단계를 밑바닥부터 역추적하여, 스레드들이 '__lll_lock_wait' 또는 'pthread_mutex_lock' 등 동기화 락 함수 호출 지점에 포박당해 있음을 증명합니다."
        echo "  - **명령어 조각 설명**:"
        echo "    * 조각 A: 'pstack' (프로세스 내 모든 스레드의 콜 스택 트레이스를 일괄 덤프해 주는 마법사)"
        echo "    * 조각 B: '$Q5_PID' (대상 프로세스 ID)"
        echo "----------------------------------------------------------------------"
        echo "  ✍ [미션]: 조각 A와 조각 B를 한 칸 띄우고 순서대로 결합하여 특정 PID(예: $Q5_PID)의 전체 스레드 스택 프레임을 한눈에 보여주는 명령어를 조립해 보세요!"
        read -p "▶ 조립된 명령어 입력: " USER_INPUT
        USER_INPUT=$(echo "$USER_INPUT" | xargs)

        if [[ "$USER_INPUT" =~ ^pstack[[:space:]]+([0-9]+|\$[A-Za-z0-9_]+)[[:space:]]*$ ]] || \
           [[ "$USER_INPUT" =~ ^gdb[[:space:]]+.*-p[[:space:]]+([0-9]+|\$[A-Za-z0-9_]+).* ]]; then
            
            local CMD_TO_RUN=$(echo "$USER_INPUT" | sed "s/\$PID/$ACTUAL_PID/g")
            
            echo -e "\n\033[1;32m✔ [정답입니다!] 최종 분석에 완벽히 마침표를 찍으셨습니다!\033[0m"
            echo "----------------------------------------------------------------------"
            echo -e "\033[1;36m🔬 [ubu27 가상머신 라이브 연동 출력]\033[0m"
            if [ -n "$ACTUAL_PID" ] && command -v pstack &>/dev/null; then
                echo "💻 실행 명령어: $CMD_TO_RUN"
                echo "📊 라이브 출력: "
                eval "$CMD_TO_RUN"
            else
                echo "💻 실행 명령어: pstack 55432"
                echo -e "📊 가상 출력  :"
                echo -e "  Thread 2 (LWP 55433):"
                echo -e "  #0  __lll_lock_wait () at ../sysdeps/unix/sysv/linux/x86_64/lowlevellock.S:135"
                echo -e "  #1  __GI___pthread_mutex_lock (mutex=0x7ffd01b2) at ../nptl/pthread_mutex_lock.c:80"
                echo -e "  #2  acquire_resource_A () at agent-app.c:45"
                echo -e "  Thread 1 (LWP 55432):"
                echo -e "  #0  __lll_lock_wait () at ../sysdeps/unix/sysv/linux/x86_64/lowlevellock.S:135"
                echo -e "  #1  __GI___pthread_mutex_lock (mutex=0x7ffd01b6) at ../nptl/pthread_mutex_lock.c:80"
                echo -e "  #2  acquire_resource_B () at agent-app.c:60"
                echo "*(현재 백그라운드 프로세스가 실행 중이지 않거나 시스템에 pstack이 없어 시뮬레이션 데이터를 표시합니다)*"
            fi
            echo "----------------------------------------------------------------------"
            echo -e "\033[1;34m📖 [튜터의 생각 흐름 강의]\033[0m"
            echo "  - **데드락 입증의 스모킹 건**: 덤프 결과 상 Thread 1이 'Resource B'를 쥔 채 'Resource A'를 취득하려 대기하고,"
            echo "    Thread 2는 'Resource A'를 쥔 채 'Resource B'를 취득하려 '__lll_lock_wait'에 머문 것이 보인다면,"
            echo "    우리는 스레드 간 교차/순환 락 경합 구조를 100% 규명한 것입니다. 이 스택 로그가 기술 이슈 문서의 가장 강력한 증거가 됩니다."
            echo "======================================================================"
            break
        else
            echo -e "\033[1;31m❌ [오답입니다!] 간결하게 pstack과 대상 PID를 결합해 보세요.\033[0m"
            echo "💡 힌트: 'pstack $Q5_PID' 형태로 작성하시면 통과됩니다."
        fi
    done

    # [9대 트러블슈팅 질문 이론 마스터 세션]
    # --------------------------------------------------------------------------
    echo -e "\n\033[1;32m🎉 완벽합니다! 5단계의 대화식 명령어 빌딩 블록 훈련을 모두 정복하셨습니다!\033[0m"
    echo -e "\033[1;36m💡 이제 스스로와 다른 동료를 완벽히 이해시킬 수 있는 '9대 트러블슈팅 핵심 이론집'을 학습합니다.\033[0m"
    read -p "▶ 이론 교안을 펼치려면 [Enter] 키를 누르세요..."
    
    echo -e "\n\033[1;33m======================================================================"
    echo "       📚 [초심자를 위한 9대 장애 분석 & 트러블슈팅 완벽 가이드북]"
    echo -e "======================================================================\033[0m"
    
    echo -e "\n\033[1;37m[1] 데드락(Deadlock)의 발생 원리: '상호 배제'와 '순환 대기'\033[0m"
    echo "  - **상호 배제 (Mutual Exclusion)**: 한 번에 하나의 스레드만 공유 자원을 가질 수 있습니다."
    echo "    어떤 스레드가 자원을 쓰면 다른 스레드는 절대 동시에 들어올 수 없어 차단됩니다."
    echo "  - **순환 대기 (Circular Wait)**: 스레드 A가 자원 1을 점유한 채 자원 2를 대기하고,"
    echo "    스레드 B가 자원 2를 점유한 채 자원 1을 대기하면서 서로 꼬리를 물고 무한정 기다리는 닫힌 루프(A -> B -> A)를 형성합니다."
    echo "  - [해결책]: 락을 거는 순서를 모든 스레드에서 완전히 동일하게 일치시키거나(Lock Ordering),"
    echo "    락 획득 시 타임아웃을 부여(try_lock)하여 무한 대기를 깨뜨려야 합니다."

    echo -e "\n\033[1;37m[2] OOM과 Deadlock이 동시 발생했다면? 트러블슈팅 우선순위와 근거\033[0m"
    echo "  - **우선순위 1위: OOM(Out of Memory) Crash 해결 및 메모리 복구**"
    echo "    * 근거 1 (파급력): OOM은 커널이 시스템 폭주를 막기 위해 OOM Killer를 동작시켜 서비스를 즉시 사멸(Crash)시킵니다."
    echo "      반면 데드락은 프로세스는 조용히 살아 있어 서비스에 장애를 일으키지만 시스템 전체를 폭파하진 않습니다."
    echo "    * 근거 2 (인과 관계): 시스템 메모리가 고갈(OOM 직전)되면, 락 자원을 안전하게 할당/해제해야 할"
    echo "      메모리 공간마저 부족해져 정상적인 동기화 처리가 꼬여 2차적으로 데드락(Deadlock)이 유발되는 경우가 빈번합니다."
    echo "      따라서 가용 자원 확보(OOM 해결)를 우선 조치하여 실서버 서비스 생존율을 극대화해야 합니다."

    echo -e "\n\033[1;37m[3] 실제 운영 서버 환경에서 메모리 누수 사전 탐지 및 monitor.sh 개선안\033[0m"
    echo "  - 현행 monitor.sh는 화면에 텍스트만 찍을 뿐 능동적 대처가 불가능합니다."
    echo "  - **운영 환경 적용을 위한 3대 개선 방안**:"
    echo "    1. 임계치 경보 알림 (Threshold Alerting): 물리 메모리(MEM) 점유율이 80%를 초과할 시,"
    echo "       사내 Slack API Webhook이나 E-mail API를 호출해 인프라 담당자에게 실시간 경고를 전송합니다."
    echo "    2. 메모리 증가 기울기 분석 (Slope Trend Analysis): 단순히 현재 사용량이 아닌,"
    echo "       최근 5분간의 메모리 상승 속도(기울기)를 미분/추적하여 '선형적으로 우상향'하는 패턴 검출 시"
    echo "       메모리 누수 확정 경고를 발송합니다."
    echo "    3. 자동 덤프 및 로그 로테이션 (Auto-dumping): 장애 발생 임계 도달 직전,"
    echo "       스레드 덤프나 메모리 힙 덤프를 디스크에 자동 영구 백업한 후 정상 재기동 프로세스로 연계합니다."

    echo -e "\n\033[1;37m[4] 소스 코드 레벨에서의 근본적 트러블슈팅 개선 제안\033[0m"
    echo "  - **메모리 누수 개선**: 주기적으로 객체를 저장하는 컬렉션(List, Map 등)이 있다면, 작업 종료 즉시"
    echo "    'clear()', 'pop()', 'del' 등을 명시하여 참조 관계를 해제하고, 가비지 컬렉터(GC)가 수거하도록 돕습니다."
    echo "  - **CPU 과점유 개선**: 무한 루프(while true) 내에 반드시 양보(sleep 혹은 yield) 구문을 심어"
    echo "    커널의 CPU 스케줄러가 다른 유익한 프로세스에 실행 타임 슬라이스를 골고루 할당하도록 배려합니다."
    echo "  - **교착 상태(Deadlock) 개선**: 스레드들이 락을 취득할 때 항상 정해진 순서(예: 언제나 Resource A 취득 후 Resource B 취득)로만"
    echo "    락을 얻게 유도하고, 'try_lock(timeout)'을 사용해 락을 즉시 취득하지 못하면 즉시 자원을 포기하고 양보하게 설계합니다."

    echo -e "\n\033[1;37m[5] 다시 이 미션을 처음부터 수행한다면? 트러블슈팅의 바람직한 흐름\033[0m"
    echo "  - 무작정 프로그램 재부팅을 하거나 소스코드를 파헤치는 주먹구구식 접근을 지양하겠습니다."
    echo "  - **계통적 탑다운 트러블슈팅 프로토콜 확립**:"
    echo "    1. 관제 로그(monitor.log) 데이터 수집 ➔ 2. 현상 분류(OOM Crash / CPU Latency / Deadlock 프리징)"
    echo "    ➔ 3. 리눅스 표준 분석 도구(ps, top, pstack, lsof)를 통한 객체 증거 확보"
    echo "    ➔ 4. 환경변수를 조정한 Before & After 한계 임계 실험 검증 ➔ 5. 소스 코드 레벨 개선 제안"
    echo "  - 이 정교한 로직을 철저히 따라 장애 대응력을 기술 문서(GitHub Issue Report)로 정밀하게 작성하겠습니다."
    echo "======================================================================"
    echo -e "\033[1;32m🎓 축하합니다! 리눅스 장애 트러블슈팅 미션의 모든 본질과 해설을 완벽하게 체득하셨습니다.\033[0m"
}

# 8. 인터랙티브 대화형 메뉴 루프
# ------------------------------------------------------------------------------
# 플레이북 가이드를 시작할 때 선제 인쇄하여 사용자에게 방향성을 제시합니다.
print_system_playbook

while true; do
    echo ""
    echo -e "\033[1;34m======================================================================"
    echo "   🚨 리눅스 리소스 장애 분석 및 트러블슈팅 컨트롤러 (Interactive CLI Tutor)"
    echo "======================================================================"
    echo " [1] OOM Crash 재현 (Before: MEMORY_LIMIT=50MB)"
    echo " [2] OOM Crash 조치 & 검증 (After: MEMORY_LIMIT=256MB)"
    echo "----------------------------------------------------------------------"
    echo " [3] CPU Spike & Watchdog 재현 (Before: CPU_MAX_OCCUPY=15%)"
    echo " [4] CPU Spike 조치 & 검증 (After: CPU_MAX_OCCUPY=90%)"
    echo "----------------------------------------------------------------------"
    echo " [5] Deadlock 재현 (Before: MULTI_THREAD_ENABLE=true)"
    echo " [6] Deadlock 회피 & 검증 (After: MULTI_THREAD_ENABLE=false)"
    echo "----------------------------------------------------------------------"
    echo " [7] 현재 실행 중인 모든 백그라운드 프로세스 강제 종료 및 청소"
    echo " [8] 컨트롤러 종료"
    echo -e "\033[1;35m [9] ★ 리눅스 관제 명령어 실전 연습 시뮬레이터 & 9대 핵심 교안 학습 ★\033[0m"
    echo -e "\033[1;34m======================================================================\033[0m"
    read -p "▶ 실행할 시나리오 번호를 입력하세요 (1-9): " CHOICE

    case "$CHOICE" in
        1)
            MEMORY_LIMIT=50
            CPU_MAX_OCCUPY=100
            MULTI_THREAD_ENABLE="false"
            launch_scenario
            print_tutorial_guide "OOM"
            ;;
        2)
            MEMORY_LIMIT=256
            CPU_MAX_OCCUPY=100
            MULTI_THREAD_ENABLE="false"
            launch_scenario
            print_tutorial_guide "OOM"
            ;;
        3)
            MEMORY_LIMIT=512
            CPU_MAX_OCCUPY=15
            MULTI_THREAD_ENABLE="false"
            launch_scenario
            print_tutorial_guide "CPU"
            ;;
        4)
            MEMORY_LIMIT=512
            CPU_MAX_OCCUPY=90
            MULTI_THREAD_ENABLE="false"
            launch_scenario
            print_tutorial_guide "CPU"
            ;;
        5)
            MEMORY_LIMIT=512
            CPU_MAX_OCCUPY=100
            MULTI_THREAD_ENABLE="true"
            launch_scenario
            print_tutorial_guide "DEADLOCK"
            ;;
        6)
            MEMORY_LIMIT=512
            CPU_MAX_OCCUPY=100
            MULTI_THREAD_ENABLE="false"
            launch_scenario
            print_tutorial_guide "DEADLOCK"
            ;;
        7)
            cleanup_processes
            ;;
        8)
            echo "👋 컨트롤러를 종료합니다. 백그라운드 모니터링은 별도 종료 처리까지 계속될 수 있습니다."
            exit 0
            ;;
        9)
            run_command_tutor
            ;;
        *)
            echo -e "\033[1;31m[경고] 잘못된 선택입니다. 1번부터 9번 사이의 숫자를 입력해 주십시오.\033[0m"
            ;;
    esac
done

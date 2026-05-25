#!/usr/bin/env bash
# ==============================================================================
# 🖥️ Linux Process & System Resource Troubleshooting Helper (diagnose.sh)
# ==============================================================================
# 이 스크립트는 b1-2_mission 학습을 돕기 위해 시나리오별 장애 상황을 한눈에 구동하고
# 모니터링 결과를 바로 확인해볼 수 있는 대화형 진단 도구입니다.
#
# 작성일: 2026-05-24
# ==============================================================================

set -eu
IFS=$'\n\t'

# 색상 및 스타일 정의 (Premium UX)
readonly BOLD='\033[1m'
readonly GREEN='\033[1;32m'
readonly YELLOW='\033[1;33m'
readonly RED='\033[1;31m'
readonly BLUE='\033[1;36m'
readonly RESET='\033[0m'

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP="$ROOT_DIR/evidence/run_workspace/agent-app-leak"
RUN_CASE_SCRIPT="$ROOT_DIR/scripts/run_agent_case.sh"

# 사전 부트 환경 및 바이너리 검증
check_prerequisites() {
  if [[ ! -f "$APP" ]]; then
    echo -e "${RED}${BOLD}❌ 에러: 애플리케이션 바이너리가 유실되었습니다!${RESET}"
    echo -e "경로를 확인해 주세요: $APP"
    exit 1
  fi

  if [[ ! -f "$RUN_CASE_SCRIPT" ]]; then
    echo -e "${RED}${BOLD}❌ 에러: 실행 헬퍼 스크립트가 유실되었습니다!${RESET}"
    echo -e "경로를 확인해 주세요: $RUN_CASE_SCRIPT"
    exit 1
  fi
}

# 로고 출력
print_logo() {
  clear
  echo -e "${BLUE}${BOLD}======================================================================${RESET}"
  echo -e "${BLUE}${BOLD}   🖥️  Linux Process & System Resource Troubleshooting Companion      ${RESET}"
  echo -e "${BLUE}${BOLD}   [ Mission: b1-2 ] - Linux Process Metrics Analysis & Diagnostic   ${RESET}"
  echo -e "${BLUE}${BOLD}======================================================================${RESET}"
  echo -e "이 도구는 Memory Leak, CPU Spike, Deadlock 시나리오를 원클릭으로 가동하고"
  echo -e "OS 수준의 관제 메트릭과 애플리케이션 로그의 변화를 실시간 진단하도록 돕습니다."
  echo -e "----------------------------------------------------------------------"
}

# 결과 상세 요약 리포트 출력
analyze_result() {
  local case_name="$1"
  local log_file="$ROOT_DIR/evidence/raw/${case_name}.app.log"
  local monitor_file="$ROOT_DIR/evidence/raw/${case_name}.monitor.log"
  local exit_file="$ROOT_DIR/evidence/raw/${case_name}.exit.txt"

  echo -e "\n${YELLOW}${BOLD}📊 [실행 완료 결과 분석 요약]${RESET}"
  echo -e "----------------------------------------------------------------------"
  
  if [[ -f "$exit_file" ]]; then
    echo -e "${BOLD}🔑 종료 정보:${RESET}"
    cat "$exit_file" | grep -E "pid|cleanup|exit_code" | sed 's/^/  /g'
  fi

  echo -e "\n${BOLD}📝 수집된 로그 및 관제 데이터 파일 위치:${RESET}"
  echo -e "  - 앱 실행 로그: ${GREEN}evidence/raw/${case_name}.app.log${RESET}"
  echo -e "  - monitor.sh 관제 로그: ${GREEN}evidence/raw/${case_name}.monitor.log${RESET}"
  echo -e "  - 시스템 스냅샷 로그: ${GREEN}evidence/raw/${case_name}.ps.log${RESET} / ${GREEN}top.log${RESET}"

  if [[ -f "$log_file" ]]; then
    echo -e "\n${BOLD}📌 마지막 5줄 앱 로그 스냅샷:${RESET}"
    echo -e "${BLUE}--------------------------------------------------${RESET}"
    tail -n 5 "$log_file" | sed 's/^/  /g'
    echo -e "${BLUE}--------------------------------------------------${RESET}"
  fi

  echo -e "----------------------------------------------------------------------"
  echo -e "💡 ${YELLOW}분석 팁:${RESET} 위 로그 파일들을 열어 ${BOLD}README.md${RESET}의 분석 내용과 직접 대조해보세요!"
  read -n 1 -s -r -p "계속하려면 아무 키나 누르세요..."
}

# 시나리오 실행 핸들러
run_scenario() {
  local num="$1"
  local case_name=""
  local mem_lim=""
  local cpu_occ=""
  local thread_en=""
  local samples="20"

  case "$num" in
    1)
      case_name="oom-low"
      mem_lim="50"
      cpu_occ="100"
      thread_en="false"
      samples="10"
      echo -e "\n${RED}${BOLD}🚀 [시나리오 1] Memory Leak & OOM - 가용 한계: 50MB (Before) 실행${RESET}"
      ;;
    2)
      case_name="oom-high"
      mem_lim="100"
      cpu_occ="100"
      thread_en="false"
      samples="16"
      echo -e "\n${GREEN}${BOLD}🚀 [시나리오 2] Memory Leak & OOM - 가용 한계: 100MB (After) 실행${RESET}"
      ;;
    3)
      case_name="cpu-low"
      mem_lim="512"
      cpu_occ="10"
      thread_en="false"
      samples="25"
      echo -e "\n${GREEN}${BOLD}🚀 [시나리오 3] CPU Spike & Latency - 제한 10% (After/안전 모드) 실행${RESET}"
      ;;
    4)
      case_name="cpu-high"
      mem_lim="512"
      cpu_occ="100"
      thread_en="false"
      samples="35"
      echo -e "\n${RED}${BOLD}🚀 [시나리오 4] CPU Spike & Latency - 제한 100% (Before/폭주 모드) 실행${RESET}"
      ;;
    5)
      case_name="deadlock-on"
      mem_lim="512"
      cpu_occ="10"
      thread_en="true"
      samples="25"
      echo -e "\n${RED}${BOLD}🚀 [시나리오 5] Thread Deadlock - 멀티스레드 교착 재현 (Before) 실행${RESET}"
      ;;
    6)
      case_name="deadlock-off"
      mem_lim="512"
      cpu_occ="10"
      thread_en="false"
      samples="20"
      echo -e "\n${GREEN}${BOLD}🚀 [시나리오 6] Thread Deadlock - 싱글스레드 데드락 회피 (After) 실행${RESET}"
      ;;
    *)
      return
      ;;
  esac

  echo -e "설정 변수: MEMORY_LIMIT=${mem_lim}MB, CPU_MAX_OCCUPY=${cpu_occ}%, MULTI_THREAD_ENABLE=${thread_en}"
  echo -e "백그라운드로 프로그램을 구동하며 시스템 메트릭을 수집하는 중입니다..."
  echo -e "잠시만 기다려 주세요 (수집 샘플: ${samples}회)..."
  
  # 스크립트 실행 호출
  bash "$RUN_CASE_SCRIPT" "$case_name" "$mem_lim" "$cpu_occ" "$thread_en" "$samples"

  echo -e "${GREEN}${BOLD}✔ 시나리오 수집이 성공적으로 끝났습니다!${RESET}"
  analyze_result "$case_name"
}

# 메인 메뉴 루프
main_menu() {
  check_prerequisites
  
  while true; do
    print_logo
    echo -e "${BOLD}1.${RESET} ${RED}Memory Leak & OOM - 50MB 임계치 폭사 시나리오 (Before)${RESET}"
    echo -e "${BOLD}2.${RESET} ${GREEN}Memory Leak & OOM - 100MB 상향 생존 시간 증가 시나리오 (After)${RESET}"
    echo -e "${BOLD}3.${RESET} ${GREEN}CPU 과점유 - 10% Cooldown 억제 장치 정상 작동 시나리오 (After)${RESET}"
    echo -e "${BOLD}4.${RESET} ${RED}CPU 과점유 - 100% 개방 Watchdog 강제 SIGTERM 차단 시나리오 (Before)${RESET}"
    echo -e "${BOLD}5.${RESET} ${RED}Deadlock - 멀티스레드 락 꼬임 영구 멈춤 시나리오 (Before)${RESET}"
    echo -e "${BOLD}6.${RESET} ${GREEN}Deadlock - 싱글스레드 동시성 경합 제거로 데드락 회피 시나리오 (After)${RESET}"
    echo -e "${BOLD}7. 종료${RESET}"
    echo -e "----------------------------------------------------------------------"
    read -p "가동 및 진단할 시나리오 번호를 선택하세요 (1-7): " choice

    if [[ "$choice" == "7" ]]; then
      echo -e "\n${BLUE}${BOLD}👋 트러블슈팅 도우미를 종료합니다. 학습 화이팅입니다!${RESET}\n"
      break
    fi

    if [[ "$choice" =~ ^[1-6]$ ]]; then
      run_scenario "$choice"
    else
      echo -e "${RED}⚠ 올바른 번호를 선택해 주세요 (1-7)${RESET}"
      sleep 1
    fi
  done
}

main_menu

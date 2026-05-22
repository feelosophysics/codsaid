#!/bin/bash
# =============================================================================
# report.sh - monitor.log 관제 이력 데이터 통계 분석기 (보너스 1 스크립트)
# 물리적 위치: $AGENT_HOME/bin/report.sh
# 소유 권한 구조: 소유자: agent-dev / 소유 그룹: agent-core / 허용 권한: 750 (rwxr-x---)
# 구동 사용법:
#   1. 시간 지정 검색: ./report.sh "시작시점" "종료시점"
#      - 예시: ./report.sh "2026-02-25 13:00:00" "2026-02-25 14:00:00"
#   2. 전체 기간 검색: ./report.sh (인자 없이 실행 시 누적된 전체 이력 스캔)
# =============================================================================

# 환경변수로부터 로그 경로를 유연하게 획득하고, 미지정 시 시스템 디렉토리를 바라보도록 백업 처리
LOG_FILE="${AGENT_LOG_DIR:-/var/log/agent-app}/monitor.log"

# ── [인자 처리 및 시간 매개변수 바인딩] ────────────────────────────────────────
# $1(첫 번째 인자)은 조사 범위 시작 타임스탬프, $2(두 번째 인자)는 종료 타임스탬프입니다.
START_TIME="$1"
END_TIME="$2"

# 멱등 에러 핸들링: 관제 로그 파일 자체가 물리적으로 부재하다면 즉각 실패 처리
if [ ! -f "$LOG_FILE" ]; then
    echo "[오류] 로그 파일을 찾을 수 없습니다: $LOG_FILE"
    exit 1
fi

# ── [데이터 슬라이싱 및 시간대 필터링] ──────────────────────────────────────────
if [ -n "$START_TIME" ] && [ -n "$END_TIME" ]; then
    # -n 옵션은 문자열의 크기가 0이 아닐 경우(즉, 인자가 둘 다 실존할 때) 참으로 인식합니다.
    echo "[정보] '$START_TIME'부터 '$END_TIME'까지의 로그를 분석 중..."
    
    # 💡 [awk 기반의 지능형 타임스탬프 어휘적 비교(Lexical Comparison) 기술]
    # awk에 -v 옵션으로 외부 쉘 변수(START/END_TIME)를 내부 변수 s와 e로 매핑시킵니다.
    FILTERED=$(awk -v s="$START_TIME" -v e="$END_TIME" '{
        # 로그 포맷의 맨 처음에 항상 고정으로 들어오는 [YYYY-MM-DD HH:MM:SS] 시간 정보를 획득합니다.
        # substr을 이용하면 gawk(GNU awk) 전용인 match 3인자 확장 기능에 의존하지 않으므로
        # mawk, bsd awk 등 모든 리눅스/Unix 계열 awk 엔진과 완벽히 100% 호환됩니다.
        ts = substr($0, 2, 19)
        if (ts >= s && ts <= e) print
    }' "$LOG_FILE")
else
    # 인자가 생략되었을 때는 전체 로그 적재 내역을 통계 범위로 할당
    echo "[정보] 누적된 전체 로그를 분석 중..."
    FILTERED=$(cat "$LOG_FILE")
fi

# ── [데이터 정규화 검증 및 무결성 필터] ────────────────────────────────────────
# 로그 내에 수동으로 기록한 임의 텍스트나 깨진 오류 줄이 통계 연산에 침투해
# 계산 에러(크래시)를 유발하지 않도록, grep -E(정규식 확장)를 사용하여 정상 관제 포맷만 안전하게 발라냅니다.
# 기대 검출 포맷: [YYYY-MM-DD HH:MM:SS] PID:48291 CPU:25.3% MEM:9.8% DISK_USED:23%
VALID=$(echo "$FILTERED" | grep -E '\[.*\] PID:[0-9]+ CPU:[0-9.]+% MEM:[0-9.]+% DISK_USED:[0-9]+%')

# wc -l 명령어로 최종 계산 대상이 될 유효 샘플 수(행 개수)를 셉니다.
# grep -v "^$" 를 추가하여 빈 줄(Empty Line)을 확실히 걷어냅니다.
SAMPLE_COUNT=$(echo "$VALID" | grep -v "^$" | wc -l)

# 멱등 방어: 분석 가능한 유효 행이 0개라면 경고를 뿜고 안전하게 종료 코드를 리턴합니다.
if [ "$SAMPLE_COUNT" -eq 0 ]; then
    echo "[경고] 분석할 유효한 로그 항목을 찾을 수 없습니다."
    exit 0
fi

# ── [수치 계산 코어 엔진 함수 정의] ────────────────────────────────────────────

# calc_stats: 특정 자원 컬럼을 기계적으로 읽어 평균(Average), 최댓값(Max), 최솟값(Min)을 정밀 계산
# 인자: $1 -> 자원 키값(CPU/MEM/DISK_USED), $2 -> 출력 단위(%)
calc_stats() {
    local field="$1"   # 계측 대상 필드 식별자
    local unit="$2"    # 화면에 덧붙일 접미사

    local values
    # 💡 [펄 호환 정규식(PCRE)의 메타문자 \K 활용 기법]
    # grep -oP 옵션: -o(일치하는 텍스트만 출력) + -P(Perl 호환 정규식 활성화)
    # 정규식 패턴 'CPU:\K[0-9.]+'의 동작 방식:
    #   1. 파일에서 'CPU:'를 탐색 매칭합니다.
    #   2. '\K' 기호가 작동하여 그 앞의 매칭('CPU:') 정보를 매칭 기록에서 깨끗하게 지우고 포인터를 전방 이동시킵니다.
    #   3. 결과적으로 뒤에 오는 '순수 숫자/소수점([0-9.]+)'만을 완벽히 분리해 내어 변수에 담습니다. (예: 25.3)
    values=$(echo "$VALID" | grep -oP "${field}:\K[0-9.]+")

    if [ -z "$values" ]; then
        echo "    평균 : N/A"
        echo "    최댓값 : N/A"
        echo "    최솟값 : N/A"
        return
    fi

    # 💡 [awk 기반의 일괄 실수 산술 통계 알고리즘]
    # awk 내부에서 변수를 초기화하고 실수 연산을 통해 최종 통계값을 누적해 나갑니다.
    echo "$values" | awk -v unit="$unit" '
    BEGIN { 
        # 초기치 할당: 최대는 가장 낮게(-1), 최소는 극단적으로 높게(999999) 셋업
        max=-1; min=999999; sum=0; count=0 
    }
    {
        # 읽어 들인 문자열 값에 0을 더해 기계가 강제로 실수 타입(Float)으로 캐스팅하게 유도합니다.
        val = $1 + 0
        sum += val
        count++
        # 실시간 순회 비교를 통해 최대/최소 변수 갱신 (시뮬레이션 비교)
        if (val > max) { max = val }
        if (val < min) { min = val }
    }
    END {
        # 누적 연산 결과를 바탕으로 부동 소수점 1자리(%.1f) 정밀 연산 및 출력 포맷 수행
        printf "    평균 : %.1f%s\n", sum/count, unit
        printf "    최댓값 : %.1f%s\n", max, unit
        printf "    최솟값 : %.1f%s\n", min, unit
    }'
}

# calc_max_time: 특정 자원의 최대 부하가 발생했던 '역사적 골든 타임'을 역추적해 출력하는 함수
calc_max_time() {
    local field="$1"
    echo "$VALID" | awk -v f="$field" '
    BEGIN { max=-1; maxline="" }
    {
        # 호환성 있는 substr 및 RSTART/RLENGTH를 이용한 자원 수치 파싱 기법 적용
        ts = substr($0, 2, 19)
        if (match($0, f ":[0-9.]+")) {
            str = substr($0, RSTART, RLENGTH)
            val = substr(str, length(f) + 2) + 0
            if (val > max) { 
                max = val
                maxline = ts 
            }
        }
    }
    END { printf "    최대 발생 시각 : %s\n", maxline }'
}

# calc_min_time: 특정 자원의 최소 부하(가장 평온했던 시각)를 역추적해 출력하는 함수
calc_min_time() {
    local field="$1"
    echo "$VALID" | awk -v f="$field" '
    BEGIN { min=999999; minline="" }
    {
        ts = substr($0, 2, 19)
        if (match($0, f ":[0-9.]+")) {
            str = substr($0, RSTART, RLENGTH)
            val = substr(str, length(f) + 2) + 0
            if (val < min) { 
                min = val
                minline = ts 
            }
        }
    }
    END { printf "    최소 발생 시각 : %s\n", minline }'
}

# ── [리포트 출력 UI 렌더러] ───────────────────────────────────────────────────
echo ""
echo "====== 통계 분석 리포트 ======"
echo ""

# 1. CPU 종합 리포트
echo "[CPU]"
calc_stats "CPU" "%"
calc_max_time "CPU"
calc_min_time "CPU"
echo ""

# 2. 메모리 종합 리포트
echo "[메모리]"
calc_stats "MEM" "%"
calc_max_time "MEM"
calc_min_time "MEM"
echo ""

# 3. 디스크 종합 리포트 (디스크는 점진적으로 차오르는 누적 자원이므로 발생 시각 추적 제외)
echo "[디스크]"
calc_stats "DISK_USED" "%"
echo ""

# 4. 전체 조사 대상 모수 통계
echo "[표본 데이터]"
echo "    데이터 수집 지점: $SAMPLE_COUNT 개 표본"
echo ""
echo "=================================="

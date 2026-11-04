#!/bin/bash
# =============================================================================
# archive.sh - 시간 기반 시계열 로그 보존 정책 (보너스 2 스크립트)
# 물리적 위치: $AGENT_HOME/bin/archive.sh
# 소유 권한 구조: 소유자: agent-dev / 소유 그룹: agent-core / 허용 권한: 750 (rwxr-x---)
# 관리 규칙:
#   - 1단계: 7일 경과 *.log 파일 → gzip으로 자동 압축
#   - 2단계: 압축 완료된 *.log.gz 아카이브 파일들 → 외부 안전 보존소로 강제 대피 이동
#   - 3단계: 30일 경과한 오래된 .gz 아카이브 파일들 → 파일 시스템 고갈을 막기 위해 영구 자동 삭제
# =============================================================================

# 환경변수가 지정되어 있으면 로그 디렉토리로 쓰고, 없으면 /var/log/agent-app 기본값 주입
LOG_DIR="${AGENT_LOG_DIR:-/var/log/agent-app}"
# 안전 대피 보관용 영구 아카이브 저장소 디렉토리 정의
ARCHIVE_DIR="/var/log/monitor/agent-app/archive"
COMPRESS_DAYS=7   # 압축을 단행할 시효 기준점 (7일 경과)
DELETE_DAYS=30     # 영구 영멸 삭제를 단행할 시효 기준점 (30일 경과)

# 크론 배치 작동 증적을 남기기 위해 작동 시작 타임스탬프 로깅 출력
echo "[$(date '+%Y-%m-%d %H:%M:%S')] archive.sh 실행 시작"

# ── [준비 단계 ①] 아카이브 대피소 디렉토리 무결성 확인 및 자동 복구 ────────
if [ ! -d "$ARCHIVE_DIR" ]; then
    # -p 옵션으로 중간 부모 디렉토리까지 안전하게 동시 자동 빌드
    mkdir -p "$ARCHIVE_DIR" 2>/dev/null
    
    # 디렉토리 생성 명령의 성공 여부 ($? != 0) 검증하여 권한 누락 예외 처리
    if [ $? -ne 0 ]; then
        echo "[오류] 아카이브 디렉토리를 생성할 수 없습니다: $ARCHIVE_DIR (권한이 없습니까?)"
        exit 1
    fi
    echo "[정보] 아카이브 디렉토리를 생성했습니다: $ARCHIVE_DIR"
fi

# ── [준비 단계 ②] 관제 로그 원본 디렉토리 실존 여부 감사 ────────────────────
if [ ! -d "$LOG_DIR" ]; then
    # 로그 보관 폴더 자체가 없다면 대상이 없는 상태이므로 에러가 아닌 경고를 뿜고 유연하게 자동 성공 종료 처리
    echo "[경고] 로그 디렉토리를 찾을 수 없습니다: $LOG_DIR — 아카이브할 대상이 없습니다."
    exit 0
fi

# ── [1단계] 7일이 경과한 원본 로그 파일 선별 및 자동 압축 ────────────────────
echo ""
echo "[1단계] ${COMPRESS_DAYS}일 이상 된 로그 파일 압축 중..."

# 💡 [리눅스 find 기반의 시간 필터 마이닝 명령어 해부]
#   -maxdepth 1: 하위 디렉토리를 깊숙이 파고들지 않고 딱 지정 디렉토리 바로 하위의 1차 자식들만 탐색
#   -name "*.log": 파일 이름 패턴이 확장자 .log로 끝나는 자원만 검출
#   -mtime +7: 파일의 '수정 시각(mtime)' 정보가 현 시점 대비 정확히 7일(7 * 24시간)보다 더 이전(즉, 과거)인 객체만 매칭
COMPRESS_TARGETS=$(find "$LOG_DIR" -maxdepth 1 -name "*.log" -mtime "+${COMPRESS_DAYS}" 2>/dev/null)

if [ -z "$COMPRESS_TARGETS" ]; then
    # -z 옵션: 탐색된 7일 경과 대상 문자열이 텅 비어 있는 경우
    echo "[정보] ${COMPRESS_DAYS}일 이상 된 로그 파일이 없습니다. 압축을 건너뜁니다."
else
    COMPRESS_COUNT=0
    
    # 💡 [IFS를 초기화한 while read -r 파이프 안전 루프 기법]
    # IFS(Internal Field Separator)를 텅 비워두어 공백이나 띄어쓰기가 들어간 파일명이 분할되어 유실되는 참사를 차단합니다.
    # read -r 옵션은 백슬래시(\) 이스케이프가 파일명 내에서 변조를 일으키는 현상을 기계적으로 막아 무결성을 보장합니다.
    # <<< "$COMPRESS_TARGETS" (Here-String 기법)을 사용해 변수 데이터를 루프로 안전하게 밀어넣습니다.
    while IFS= read -r logfile; do
        # 방어적 보안 코딩: 해당 파일이 현재 스크립트 실행자 계정에서 읽을 수 있는지 권한 점검 (-r)
        if [ ! -r "$logfile" ]; then
            echo "[경고] '$logfile' 파일을 읽을 수 없습니다 — 건너뜁니다 (권한이 없습니까?)"
            continue
        fi
        echo "  압축 중: $logfile"
        
        # gzip 명령어로 대상 파일 압축 집행
        # 성공 시 원본 monitor.log.X는 사라지고 자동으로 압축 확장자가 붙은 monitor.log.X.gz 파일이 제자리에 생성됩니다.
        gzip "$logfile" 2>/dev/null
        if [ $? -eq 0 ]; then
            COMPRESS_COUNT=$((COMPRESS_COUNT + 1))
        else
            echo "[경고] 압축 실패: $logfile"
        fi
    done <<< "$COMPRESS_TARGETS"
    echo "[정보] ${COMPRESS_COUNT}개의 파일을 압축했습니다."
fi

# ── [2단계] 생성된 압축 아카이브 파일들을 대피소 디렉토리로 이동 ──────────────
echo ""
echo "[2단계] 압축된 파일을 아카이브 보관소로 이동 중: $ARCHIVE_DIR"

# 7일 경과 필터로 압축되어 제자리에 남아있는 모든 .log.gz 파일 리스트 수집
MOVE_TARGETS=$(find "$LOG_DIR" -maxdepth 1 -name "*.log.gz" 2>/dev/null)

if [ -z "$MOVE_TARGETS" ]; then
    echo "[정보] 이동할 압축 파일이 없습니다. 건너뜁니다."
else
    MOVE_COUNT=0
    while IFS= read -r gzfile; do
        echo "  이동 중: $gzfile → $ARCHIVE_DIR/"
        
        # mv 명령어로 압축 본을 안전 보관소(/var/log/monitor/agent-app/archive/)로 이동 배치
        mv "$gzfile" "$ARCHIVE_DIR/" 2>/dev/null
        if [ $? -eq 0 ]; then
            MOVE_COUNT=$((MOVE_COUNT + 1))
        else
            echo "[경고] 이동 실패: $gzfile (권한이 없습니까?)"
        fi
    done <<< "$MOVE_TARGETS"
    echo "[정보] ${MOVE_COUNT}개의 파일을 아카이브 보관소로 이동했습니다."
fi

# ── [3단계] 30일이 경과한 아카이브 파일 영구 제거 (용량 고갈 방지) ──────────
echo ""
echo "[3단계] ${DELETE_DAYS}일 이상 된 아카이브 파일 삭제 중..."

# 아카이브 보존소 내부에서 30일(-mtime +30)이 경과하여 완전히 노후화된 .gz 파일 리스트 수집
DELETE_TARGETS=$(find "$ARCHIVE_DIR" -maxdepth 1 -name "*.gz" -mtime "+${DELETE_DAYS}" 2>/dev/null)

if [ -z "$DELETE_TARGETS" ]; then
    echo "[정보] ${DELETE_DAYS}일 이상 된 아카이브 파일이 없습니다. 삭제를 건너뜁니다."
else
    DELETE_COUNT=0
    while IFS= read -r gzfile; do
        echo "  삭제 중: $gzfile"
        
        # rm -f (force) 옵션으로 사용자 확인창 없이 즉시 영구 파괴 집행
        rm -f "$gzfile" 2>/dev/null
        if [ $? -eq 0 ]; then
            DELETE_COUNT=$((DELETE_COUNT + 1))
        else
            echo "[경고] 삭제 실패: $gzfile (권한이 없습니까?)"
        fi
    done <<< "$DELETE_TARGETS"
    echo "[정보] ${DELETE_COUNT}개의 아카이브 파일을 삭제했습니다."
fi

echo ""
echo "[$(date '+%Y-%m-%d %H:%M:%S')] archive.sh 실행 완료."

#!/bin/bash

# 에러 발생 시 즉시 중단
set -e

# 스크립트 파일이 위치한 디렉토리를 기준으로 작업 디렉토리 설정
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

DB_DIR="query"
DB_FILE="$DB_DIR/library.db"
SCHEMA_FILE="$DB_DIR/schema.sql"
DATA_FILE="$DB_DIR/data.sql"
QUERIES_FILE="$DB_DIR/queries.sql"
RESULTS_FILE="$DB_DIR/query_results.txt"

echo "=================================================="
echo "📚 도서 대여 데이터베이스 자동 구축 및 검증 시작"
echo "=================================================="

# 1. 기존 데이터베이스 파일 초기화
if [ -f "$DB_FILE" ]; then
    echo "🔄 1. 기존 데이터베이스 파일($DB_FILE)을 초기화합니다..."
    rm -f "$DB_FILE"
else
    echo "🔄 1. 신규 데이터베이스 파일을 생성합니다..."
fi

# 2. DDL 스크립트 실행 (외래키 제약조건 활성화 및 스키마 생성)
echo "🏗️  2. 데이터베이스 스키마 생성 중 ($SCHEMA_FILE)..."
sqlite3 "$DB_FILE" < "$SCHEMA_FILE"

# 3. 샘플 데이터(DML) 삽입
echo "📥 3. 샘플 데이터 적재 중 ($DATA_FILE)..."
sqlite3 "$DB_FILE" < "$DATA_FILE"

# 4. 핵심 및 보너스 쿼리 일괄 실행 및 결과 추출
echo "📊 4. 핵심 쿼리 실행 및 결과 보고서 갱신 중 ($RESULTS_FILE)..."
sqlite3 "$DB_FILE" < "$QUERIES_FILE" > "$RESULTS_FILE"

echo "=================================================="
echo "✅ 모든 작업이 성공적으로 완료되었습니다!"
echo "📍 생성된 데이터베이스: $DB_FILE"
echo "📍 쿼리 실행 결과 보고서: $RESULTS_FILE"
echo "=================================================="

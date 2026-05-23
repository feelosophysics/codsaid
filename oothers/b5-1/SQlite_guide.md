# 🏁 Phase 1 SQL 데이터베이스 미션 완료 보고서 (Walkthrough)

이 보고서는 학습자의 요구사항을 반영하여 구현한 SQLite 기반 도서 대여 데이터베이스의 작업 내역과 검증 결과를 서술합니다. 

---

## 📂 최종 생성된 결과물 및 구조

모든 결과물은 작업 공간 내에 유기적으로 배치되었습니다.

1. **스키마 정의서**: [schema.sql](file:///Users/f22losophysics1091/Desktop/260524work/schema.sql)
   - `CATEGORY`, `MEMBER`, `BOOK`, `RENTAL` 테이블 설계
   - PK/FK 선언, `ON DELETE CASCADE / RESTRICT` 무결성 검증, `CHECK` 제약조건 설정
2. **샘플 데이터**: [data.sql](file:///Users/f22losophysics1091/Desktop/260524work/data.sql)
   - 테이블별 10개 행 이상의 유의미한 시나리오 데이터 삽입
   - 서브쿼리 검증을 위해 대여 이력이 없는 휴면 회원(고길동) 추가
3. **핵심 쿼리 및 분석**: [queries.sql](file:///Users/f22losophysics1091/Desktop/260524work/queries.sql)
   - 기본 조회 4개, 조인 4개, 집계 3개, 서브쿼리 2개, 데이터 조작 2개, 인덱스 생성 1개 포함 (총 16개 쿼리)
4. **실행 결과 보고**: [query_results.txt](file:///Users/f22losophysics1091/Desktop/260524work/results/query_results.txt)
   - 실제 SQLite를 구동하여 16개 쿼리를 일괄 수행해 추출한 터미널 데이터 출력 결과본
5. **CS & AI 연계 학습서**: [study_guide.md](file:///Users/f22losophysics1091/Desktop/260524work/study_guide.md)
   - RDBMS 이론, 정규화, SQL 쿼리 논리 처리 순서, B-Tree 인덱스 아키텍처, AI 엔지니어링 접점 기술 정리

---

## 🧪 실행 및 검증 프로세스

### 1. 자동화 스크립트 실행 환경 구축
로컬 터미널 환경에서 다음 명령어를 순차적으로 수행하여 데이터베이스 스키마 구성, 데이터 삽입 및 16개 쿼리 실행을 일괄 검증했습니다.

```bash
# 1. 기존 데이터베이스 파일 초기화
rm -f library.db

# 2. DDL 스크립트 실행 (외래키 제약조건 포함)
sqlite3 library.db < schema.sql

# 3. 샘플 데이터(DML) 삽입
sqlite3 library.db < data.sql

# 4. 핵심 쿼리 일괄 실행 및 파일 추출
sqlite3 -header -column library.db < queries.sql > results/query_results.txt
```

### 2. 수동 무결성 검증 (참조 무결성 테스트)
- **외래키 위반 시나리오**: `data.sql`에 기록된 대로 `PRAGMA foreign_keys = ON;` 활성화 상태에서, `BOOK` 테이블에 존재하지 않는 카테고리 ID($99$)를 가진 책을 삽입하거나, 존재하지 않는 회원 ID로 대여 기록을 삽입하려는 시도는 데이터베이스 엔진 단에서 원천 차단(`FOREIGN KEY constraint failed`)됨을 확인했습니다.
- **ON DELETE CASCADE 정상 동작**: `MEMBER` 테이블에서 회원(홍길동)을 `DELETE` 하였을 때, 그와 연동된 `RENTAL` 테이블의 모든 대여 레코드들이 `ON DELETE CASCADE` 옵션에 의해 동반 삭제됨을 `queries.sql` Query 15의 실행 결과를 통해 입증하였습니다.

---

## 📊 핵심 쿼리 실행 결과 (요약)

실제 실행 결과에서 추출한 주요 통계 요약본입니다.

### 1. [Query 5] 현재 대여 및 연체 중인 현황 (INNER JOIN)
```
rental_id  member_name  book_title          rental_date  status 
---------  -----------  ------------------  -----------  -------
3          김철수          코스모스                2026-04-10   OVERDUE
7          강동원          사피엔스                2026-04-25   OVERDUE
5          최지우          부의 시나리오             2026-05-20   RENTED 
10         아이유          원씽 (The One Thing)  2026-05-21   RENTED 
8          한소희          총, 균, 쇠             2026-05-22   RENTED 
11         아이유          밑바닥부터 시작하는 딥러닝      2026-05-22   RENTED 
15         박민수          클린 코드               2026-05-23   RENTED 
```

### 2. [Query 11] 대여 상태별 거시적 수치 집계 (GROUP BY + COUNT)
```
status    count
--------  -----
RETURNED  8    
RENTED    5    
OVERDUE   2    
```

### 3. [Query 13] 대여 이력이 없는 휴면 회원 추출 (NOT EXISTS Subquery)
`data.sql`에 추가한 휴면 회원 '고길동'이 정확하게 반환되어 서브쿼리 연산의 정밀함을 입증했습니다.
```
id  name  email                   join_date 
--  ----  ----------------------  ----------
12  고길동   gildong_go@example.com  2025-11-20
```

---

> [!TIP]
> 작업 공간에 생성된 [study_guide.md](file:///Users/f22losophysics1091/Desktop/260524work/study_guide.md) 가이드를 통해 데이터베이스 내부 엔진의 구조와 자료구조(B-Tree) 이론을 함께 학습하면 향후 Phase 2, 3를 진행할 때 강력한 기초 체력이 다져질 것입니다.

.headers on
.mode column

-- 외래키 활성화
PRAGMA foreign_keys = ON;

-- =============================================================================
-- PART A: 기본 조회 쿼리 (4개)
-- =============================================================================

-- [Query 1] 전체 회원 목록 조회 (가입일 순)
.print ""
.print "[Query 1] 전체 회원 목록 조회"
SELECT id, name, email, join_date 
FROM MEMBER 
ORDER BY join_date ASC;

-- [Query 2] 20,000원 이상인 도서 목록 조회 (가격 내림차순 정렬)
.print ""
.print "[Query 2] 20,000원 이상 고가 도서 목록 조회"
SELECT id, title, price 
FROM BOOK 
WHERE price >= 20000 
ORDER BY price DESC;

-- [Query 3] 이메일에 특정 도메인이 포함된 회원 조회 (LIKE 및 LIMIT 사용)
.print ""
.print "[Query 3] 이메일 도메인이 '@example.com'인 회원 중 5명 조회"
SELECT id, name, email 
FROM MEMBER 
WHERE email LIKE '%@example.com' 
LIMIT 5;

-- [Query 4] 도서 카테고리 목록 조회 (이름 사전순)
.print ""
.print "[Query 4] 도서 카테고리 목록 조회"
SELECT id, name 
FROM CATEGORY 
ORDER BY name ASC;


-- =============================================================================
-- PART B: 조인(JOIN) 조회 쿼리 (4개)
-- =============================================================================

-- [Query 5] 대여 기록과 회원 정보 결합 조회 (INNER JOIN)
.print ""
.print "[Query 5] 대여 기록과 회원 정보 결합 조회 (INNER JOIN)"
SELECT r.id AS rental_id, m.name AS member_name, r.rental_date 
FROM RENTAL r 
INNER JOIN MEMBER m ON r.member_id = m.id;

-- [Query 6] 도서와 카테고리 결합 조회 (INNER JOIN)
.print ""
.print "[Query 6] 도서와 카테고리 결합 조회 (INNER JOIN)"
SELECT b.title AS book_title, c.name AS category_name 
FROM BOOK b 
INNER JOIN CATEGORY c ON b.category_id = c.id;

-- [Query 7] 모든 책 목록과 대여 정보 조회 (LEFT JOIN)
.print ""
.print "[Query 7] 모든 책 목록과 대여 정보 조회 (LEFT JOIN)"
SELECT b.title AS book_title, r.rental_date 
FROM BOOK b 
LEFT JOIN RENTAL r ON b.id = r.book_id;

-- [Query 8] 모든 회원 목록과 대여 상태 조회 (LEFT JOIN)
.print ""
.print "[Query 8] 모든 회원 목록과 대여 상태 조회 (LEFT JOIN)"
SELECT m.name AS member_name, r.status 
FROM MEMBER m 
LEFT JOIN RENTAL r ON m.id = r.member_id;


-- =============================================================================
-- PART C: 집계 및 그룹화 쿼리 (3개)
-- =============================================================================

-- [Query 9] 카테고리별 도서 평균 가격 (GROUP BY + AVG)
.print ""
.print "[Query 9] 카테고리별 도서 평균 가격 (GROUP BY + AVG)"
SELECT category_id, AVG(price) AS average_price 
FROM BOOK 
GROUP BY category_id;

-- [Query 10] 회원별 누적 대여 횟수 (GROUP BY + COUNT)
.print ""
.print "[Query 10] 회원별 누적 대여 횟수 (GROUP BY + COUNT)"
SELECT member_id, COUNT(*) AS total_rentals 
FROM RENTAL 
GROUP BY member_id;

-- [Query 11] 카테고리별 도서 총 가격 합산 (GROUP BY + SUM)
.print ""
.print "[Query 11] 카테고리별 도서 총 가격 합산 (GROUP BY + SUM)"
SELECT category_id, SUM(price) AS total_price 
FROM BOOK 
GROUP BY category_id;


-- =============================================================================
-- PART D: 서브쿼리(Subquery) 조회 (2개)
-- =============================================================================

-- [Query 12] 전체 도서 평균 가격보다 비싼 도서 목록 (비교 서브쿼리)
.print ""
.print "[Query 12] 평균 도서 가격보다 비싼 도서 목록"
SELECT id, title, price 
FROM BOOK 
WHERE price > (SELECT AVG(price) FROM BOOK)
ORDER BY price DESC;

-- [Query 13] 도서를 단 한 번도 대여한 적 없는 회원 목록 (NOT IN 서브쿼리)
.print ""
.print "[Query 13] 대여 기록이 없는 회원 목록"
SELECT id, name 
FROM MEMBER 
WHERE id NOT IN (SELECT DISTINCT member_id FROM RENTAL);


-- =============================================================================
-- PART E: 데이터 수정 및 삭제 (2개)
-- =============================================================================

-- [Query 14] 특정 대여 기록을 반납 완료 상태로 변경 (UPDATE)
.print ""
.print "[Query 14] 특정 대여 기록 상태 변경"
UPDATE RENTAL 
SET status = 'RETURNED', return_date = '2026-06-10' 
WHERE id = 1;

-- [Query 15] 특정 회원 정보 삭제 (DELETE)
.print ""
.print "[Query 15] 회원 정보 삭제 (CASCADE 적용 확인)"
DELETE FROM MEMBER 
WHERE id = 10;


-- =============================================================================
-- PART F: 성능 최적화를 위한 인덱스 적용 (1개)
-- =============================================================================

-- [Query 16] RENTAL 테이블의 member_id 컬럼에 인덱스 생성
-- 적용 이유: 회원 ID를 기준으로 대여 기록을 검색하는 쿼리 성능을 높이기 위함
.print ""
.print "[Query 16] RENTAL 테이블의 member_id 인덱스 생성"
CREATE INDEX idx_rental_member ON RENTAL(member_id);


-- =============================================================================
-- PART G: 보너스 과제
-- =============================================================================

-- [보너스 5.1] 조인 1개를 두 방식으로 풀기 (JOIN vs Subquery)
-- 목적: '이영희' 회원의 대여 기록 조회

-- 1. JOIN 방식
.print ""
.print "[보너스 5.1 - JOIN 방식] '이영희' 회원의 대여 기록 조회"
SELECT r.id, r.rental_date, r.status 
FROM RENTAL r 
INNER JOIN MEMBER m ON r.member_id = m.id 
WHERE m.name = '이영희';

-- 2. 서브쿼리 방식
.print ""
.print "[보너스 5.1 - 서브쿼리 방식] '이영희' 회원의 대여 기록 조회"
SELECT id, rental_date, status 
FROM RENTAL 
WHERE member_id = (SELECT id FROM MEMBER WHERE name = '이영희');


-- [보너스 5.2] 데이터 정합성 깨뜨려 보기 (에러 발생 쿼리)
-- 존재하지 않는 카테고리 ID로 도서 등록 시도 (외래키 제약 에러 유도)
-- (실행 시 에러를 방지하기 위해 주석 처리)
-- INSERT INTO BOOK (id, title, category_id, author, price) VALUES (99, '존재할 수 없는 책', 999, '작가', 15000);


-- [보너스 5.3] 미니 리포트 만들기 (핵심 지표 3개)

-- 지표 1: 가장 대여가 많이 된 도서 TOP 3
.print ""
.print "[보너스 5.3 - 지표 1] 가장 대여가 많이 된 도서 TOP 3 (도서 ID 및 횟수)"
SELECT book_id, COUNT(*) AS rental_count 
FROM RENTAL 
GROUP BY book_id 
ORDER BY rental_count DESC 
LIMIT 3;

-- 지표 2: 카테고리별 등록된 도서 개수
.print ""
.print "[보너스 5.3 - 지표 2] 카테고리별 등록된 도서 개수"
SELECT category_id, COUNT(*) AS book_count 
FROM BOOK 
GROUP BY category_id;

-- 지표 3: 현재 대여 중인 도서 건수
.print ""
.print "[보너스 5.3 - 지표 3] 현재 대여 중인 도서 건수"
SELECT COUNT(*) AS rented_count 
FROM RENTAL 
WHERE status = 'RENTED';

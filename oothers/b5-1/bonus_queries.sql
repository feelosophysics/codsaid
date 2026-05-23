-- =============================================================================
-- [Phase 2] SQL 도서 대여 데이터베이스: 보너스 과제 (bonus_queries.sql)
-- =============================================================================

-- 외래키(Foreign Key) 활성화
PRAGMA foreign_keys = ON;

-- =============================================================================
-- [보너스 5.1] 조인 1개를 두 방식으로 풀기 (JOIN vs Subquery)
-- 요구사항: "사피엔스" 도서를 대여한(대여 이력이 있는) 회원 목록 찾기
-- =============================================================================

-- 1. JOIN을 활용한 방식 (INNER JOIN)
-- 옵티마이저 관점: JOIN은 일반적으로 데이터베이스 엔진이 가장 최적화하기 쉬운 표준적인 연결 방식입니다.
-- 인덱스가 잘 타있는 경우, Nested Loop Join이나 Hash Join 등을 통해 매우 빠르게 두 집합을 결합합니다.
SELECT DISTINCT m.id, m.name, m.email
FROM MEMBER m
INNER JOIN RENTAL r ON m.id = r.member_id
INNER JOIN BOOK b ON r.book_id = b.id
WHERE b.title = '사피엔스';

-- 2. 서브쿼리(Subquery)를 활용한 방식 (IN 연산자)
-- 옵티마이저 관점: 논리적으로 안쪽 쿼리(도서 검색 -> 렌탈 검색)를 먼저 수행하고, 
-- 그 결과(member_id 집합)를 바깥 쿼리(MEMBER)에 필터 조건으로 전달합니다.
-- 최신 RDBMS 옵티마이저는 이 서브쿼리 형태를 내부적으로 JOIN 방식(Semi-Join)으로 
-- 풀어서(Unnesting) 실행 계획을 최적화하는 경우가 많습니다.
SELECT id, name, email
FROM MEMBER
WHERE id IN (
    SELECT member_id
    FROM RENTAL
    WHERE book_id = (
        SELECT id
        FROM BOOK
        WHERE title = '사피엔스'
    )
);


-- =============================================================================
-- [보너스 5.2] 데이터 정합성 깨뜨려 보기 (에러 발생 쿼리)
-- 요구사항: 일부러 FK 에러가 나는 입력을 시도하고 원인 분석
-- =============================================================================

-- [에러 시나리오 1] 존재하지 않는 회원의 대여 기록 추가 시도
-- 현상: "FOREIGN KEY constraint failed" 에러가 발생하며 INSERT가 거부(Rollback)됩니다.
-- 원인: RENTAL.member_id는 MEMBER.id를 참조하도록 FK가 걸려 있습니다.
--       하지만 회원 ID '999'는 MEMBER 테이블에 존재하지 않는 유령 회원입니다.
-- 목적: 이 방어막이 없다면, 누가 빌려갔는지 추적할 수 없는 쓰레기 데이터(Orphan Record)가 쌓이게 됩니다.
-- INSERT INTO RENTAL (id, member_id, book_id, rental_date, status) 
-- VALUES (999, 999, 1, '2026-05-24', 'RENTED');

-- [에러 시나리오 2] 존재하지 않는 카테고리에 도서 등록 시도
-- 현상: "FOREIGN KEY constraint failed" 에러가 발생합니다.
-- 원인: BOOK.category_id는 CATEGORY.id를 참조합니다. 
--       카테고리 ID '100'은 사전에 정의된 적이 없습니다.
-- 목적: 분류할 수 없는 외계 카테고리의 책이 도서관 서가에 꽂히는 것을 원천 봉쇄합니다.
-- INSERT INTO BOOK (id, title, category_id, author, price, published_date)
-- VALUES (999, '존재할 수 없는 책', 100, '미상', 15000, '2026-01-01');

-- [에러 시나리오 3] 대여 기록이 존재하는 회원(이영희, ID=1) 강제 삭제 시도
-- 현상: 성공할 수도 있고 실패할 수도 있습니다. 
--       (우리 스키마에서는 ON DELETE CASCADE를 선언했으므로 삭제 자체는 성공하며, 하위 RENTAL 기록이 모두 증발합니다.)
-- 교훈: 만약 ON DELETE RESTRICT를 걸었다면, 이영희 회원 삭제 시 에러가 나면서 방어됩니다. 
--       실무에서는 대여 기록(돈과 얽힌 트랜잭션)이 날아가는 대참사를 막기 위해 회원 탈퇴 시 
--       물리적 삭제(DELETE)가 아닌 논리적 삭제(UPDATE MEMBER SET is_deleted = 1)를 사용하는 것이 안전합니다.

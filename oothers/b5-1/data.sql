-- =============================================================================
-- [Phase 1] SQL로 만드는 도서 대여 데이터베이스: 샘플 데이터 적재 (data.sql)
-- =============================================================================
-- 
-- 본 스크립트는 4개 테이블에 각각 최소 10행 이상의 유의미한 시나리오 데이터를 채워 넣습니다.
-- 무결성 제약조건에 저해되지 않도록 설계된 데이터 삽입 순서와 그 원리에 대해 
-- "교과서적인 깊이 있는 교육적 주석"을 함께 제공합니다.
--
-- -----------------------------------------------------------------------------
-- 💡 데이터 삽입(INSERT)의 순서와 관계 종속성 (Referential Dependency)
--
-- 관계형 데이터베이스에서 외래키(FK)가 선언되어 있다면 아무 순서나 데이터를 밀어 넣을 수 없습니다.
-- 만약 BOOK 테이블을 MEMBER보다 먼저 채우는 것은 괜찮지만, CATEGORY 테이블을 빈 채로 두고
-- BOOK을 먼저 채우려고 하면 어떻게 될까요?
-- 'category_id'가 참조할 부모 키가 존재하지 않으므로 에러(FOREIGN KEY constraint failed)가 발생합니다.
--
-- [올바른 데이터 적재 순서 아키텍처]
-- 1. [독립 테이블] CATEGORY 및 MEMBER (외래키 참조를 받기만 하고, 스스로 다른 테이블을 참조하지 않음)
-- 2. [종속 테이블 1단계] BOOK (CATEGORY를 참조함)
-- 3. [종속 테이블 2단계] RENTAL (MEMBER와 BOOK을 동시에 참조함)
-- =============================================================================

-- 외래키 제약조건 실시간 검사 활성화
PRAGMA foreign_keys = ON;

-- -----------------------------------------------------------------------------
-- 1. CATEGORY 테이블 샘플 데이터 (10개 행)
-- -----------------------------------------------------------------------------
-- 도서의 다양한 장르를 세분화하여 10개 행을 삽입합니다.
-- 중복이 허용되지 않는 UNIQUE 컬럼이므로 고유한 값들로 채워집니다.
INSERT INTO CATEGORY (id, name) VALUES (1, '컴퓨터과학');
INSERT INTO CATEGORY (id, name) VALUES (2, '과학/수학');
INSERT INTO CATEGORY (id, name) VALUES (3, '인문/철학');
INSERT INTO CATEGORY (id, name) VALUES (4, '경제/경영');
INSERT INTO CATEGORY (id, name) VALUES (5, '문학/소설');
INSERT INTO CATEGORY (id, name) VALUES (6, '예술/대중문화');
INSERT INTO CATEGORY (id, name) VALUES (7, '역사');
INSERT INTO CATEGORY (id, name) VALUES (8, '에세이/시');
INSERT INTO CATEGORY (id, name) VALUES (9, '언어/외국어');
INSERT INTO CATEGORY (id, name) VALUES (10, '자기계발');


-- -----------------------------------------------------------------------------
-- 2. MEMBER 테이블 샘플 데이터 (10개 행)
-- -----------------------------------------------------------------------------
-- 회원 정보를 생성합니다. 가입일(join_date)은 과거의 다양한 시점으로 지정하여 
-- 가입 기간별 조회 및 통계 쿼리가 의미 있게 동작하도록 유도합니다.
-- email 컬럼은 UNIQUE 제약조건이 걸려 있으므로 서로 다른 이메일 주소를 할당합니다.
INSERT INTO MEMBER (id, name, email, phone, join_date) VALUES (1, '이영희', 'younghee@example.com', '010-1234-5678', '2025-01-10');
INSERT INTO MEMBER (id, name, email, phone, join_date) VALUES (2, '김철수', 'chulsoo@example.com', '010-2345-6789', '2025-02-15');
INSERT INTO MEMBER (id, name, email, phone, join_date) VALUES (3, '박민수', 'minsoo@example.com', '010-3456-7890', '2025-03-01');
INSERT INTO MEMBER (id, name, email, phone, join_date) VALUES (4, '최지우', 'jiwoo@example.com', '010-4567-8901', '2025-04-12');
INSERT INTO MEMBER (id, name, email, phone, join_date) VALUES (5, '정다은', 'daeun@example.com', '010-5678-9012', '2025-05-20');
INSERT INTO MEMBER (id, name, email, phone, join_date) VALUES (6, '강동원', 'dongwon@example.com', '010-6789-0123', '2025-06-05');
INSERT INTO MEMBER (id, name, email, phone, join_date) VALUES (7, '한소희', 'sohee@example.com', NULL, '2025-07-22'); -- 전화번호가 없는 회원 (NULL 허용 검증)
INSERT INTO MEMBER (id, name, email, phone, join_date) VALUES (8, '송강호', 'kangho@example.com', '010-8901-2345', '2025-08-30');
INSERT INTO MEMBER (id, name, email, phone, join_date) VALUES (9, '아이유', 'iu@example.com', '010-9012-3456', '2025-09-18');
INSERT INTO MEMBER (id, name, email, phone, join_date) VALUES (10, '임영웅', 'hero@example.com', '010-0123-4567', '2025-10-05');
INSERT INTO MEMBER (id, name, email, phone, join_date) VALUES (12, '고길동', 'gildong_go@example.com', '010-7777-7777', '2025-11-20'); -- 도서를 한 번도 대여하지 않은 휴면 회원 (Query 13 검증용)


-- -----------------------------------------------------------------------------
-- 3. BOOK 테이블 샘플 데이터 (10개 행)
-- -----------------------------------------------------------------------------
-- 보유 도서 10권을 등록합니다. 
-- category_id 값은 반드시 상단의 CATEGORY(id) 테이블에 존재하는 1~10 사이의 값이어야 합니다.
-- 만약 category_id에 99를 입력하려 한다면 SQLite는 Referential Integrity 위반으로 차단합니다.
-- 가격(price)은 책마다 고유한 값으로 배정하고, CHECK(price >= 0) 조건에 부합하는 양수입니다.
INSERT INTO BOOK (id, title, category_id, author, price, published_date) VALUES (1, '밑바닥부터 시작하는 딥러닝', 1, '사이토 고키', 28000, '2016-12-01');
INSERT INTO BOOK (id, title, category_id, author, price, published_date) VALUES (2, '클린 코드', 1, '로버트 C. 마틴', 33000, '2013-12-24');
INSERT INTO BOOK (id, title, category_id, author, price, published_date) VALUES (3, '코스모스', 2, '칼 세이건', 19500, '2006-12-20');
INSERT INTO BOOK (id, title, category_id, author, price, published_date) VALUES (4, '정의란 무엇인가', 3, '마이클 샌델', 15000, '2010-05-24');
INSERT INTO BOOK (id, title, category_id, author, price, published_date) VALUES (5, '부의 시나리오', 4, '오건영', 18000, '2021-06-15');
INSERT INTO BOOK (id, title, category_id, author, price, published_date) VALUES (6, '해리 포터와 마법사의 돌', 5, 'J.K. 롤링', 12000, '1997-06-26');
INSERT INTO BOOK (id, title, category_id, author, price, published_date) VALUES (7, '사피엔스', 7, '유발 하라리', 22000, '2015-11-24');
INSERT INTO BOOK (id, title, category_id, author, price, published_date) VALUES (8, '총, 균, 쇠', 7, '재레드 다이아몬드', 28000, '2005-12-19');
INSERT INTO BOOK (id, title, category_id, author, price, published_date) VALUES (9, '데미안', 5, '헤르만 헤세', 10000, '1919-06-01');
INSERT INTO BOOK (id, title, category_id, author, price, published_date) VALUES (10, '원씽 (The One Thing)', 10, '게리 켈러', 14000, '2013-08-30');


-- -----------------------------------------------------------------------------
-- 4. RENTAL 테이블 샘플 데이터 (15개 행)
-- -----------------------------------------------------------------------------
-- 도서 대여 기록 15건을 생성하여 M:N 관계를 구체적으로 표현하고 비즈니스 흐름을 시뮬레이션합니다.
--
-- 💡 시나리오 시점 설정: 현재 시점이 "2026-05-24"라고 가정합니다.
--   - 'RETURNED' (정상 반납 완료): 대여일과 반납일이 모두 과거로 기입됨.
--   - 'RENTED' (정상 대여 중): 대여한 지 얼마 되지 않았고(예: 최근 며칠 이내), 반납일은 NULL.
--   - 'OVERDUE' (연체 중): 대여한 날짜가 오래 지났으나(보통 대여 기간 14일 초과), 반납되지 않아 return_date가 NULL이고 상태는 OVERDUE.
--
-- 💡 데이터 구성:
--   - member_id는 1~10 (MEMBER의 id 참조)
--   - book_id는 1~10 (BOOK의 id 참조)
--   - 이 관계 정보를 통해 "누가 무엇을 언제 빌려서 어떻게 처리했는지" 완벽히 추적할 수 있습니다.
-- -----------------------------------------------------------------------------

-- 건 1: 이영희(1)가 딥러닝 책(1)을 대여하여 정상 반납함.
INSERT INTO RENTAL (id, member_id, book_id, rental_date, return_date, status) 
VALUES (1, 1, 1, '2026-04-01', '2026-04-10', 'RETURNED');

-- 건 2: 이영희(1)가 클린 코드(2)를 대여하여 정상 반납함. (다독 회원 시나리오)
INSERT INTO RENTAL (id, member_id, book_id, rental_date, return_date, status) 
VALUES (2, 1, 2, '2026-04-15', '2026-04-28', 'RETURNED');

-- 건 3: 김철수(2)가 코스모스(3)를 대여했으나 기한이 한참 지나 연체됨. (2026-04-10 대여 후 무소식 -> 연체 시나리오)
INSERT INTO RENTAL (id, member_id, book_id, rental_date, return_date, status) 
VALUES (3, 2, 3, '2026-04-10', NULL, 'OVERDUE');

-- 건 4: 박민수(3)가 정의란 무엇인가(4)를 대여하여 반납함.
INSERT INTO RENTAL (id, member_id, book_id, rental_date, return_date, status) 
VALUES (4, 3, 4, '2026-04-20', '2026-05-02', 'RETURNED');

-- 건 5: 최지우(4)가 부의 시나리오(5)를 최근에 빌려가서 열심히 읽는 중. (정상 대여 시나리오)
INSERT INTO RENTAL (id, member_id, book_id, rental_date, return_date, status) 
VALUES (5, 4, 5, '2026-05-20', NULL, 'RENTED');

-- 건 6: 정다은(5)이 해리 포터(6)를 대여하여 반납함.
INSERT INTO RENTAL (id, member_id, book_id, rental_date, return_date, status) 
VALUES (6, 5, 6, '2026-05-01', '2026-05-12', 'RETURNED');

-- 건 7: 강동원(6)이 사피엔스(7)를 빌려갔으나 반납 기한이 지나 연체됨.
INSERT INTO RENTAL (id, member_id, book_id, rental_date, return_date, status) 
VALUES (7, 6, 7, '2026-04-25', NULL, 'OVERDUE');

-- 건 8: 한소희(7)가 총균쇠(8)를 최근에 빌려감. (정상 대여)
INSERT INTO RENTAL (id, member_id, book_id, rental_date, return_date, status) 
VALUES (8, 7, 8, '2026-05-22', NULL, 'RENTED');

-- 건 9: 송강호(8)가 데미안(9)을 대여하여 반납함.
INSERT INTO RENTAL (id, member_id, book_id, rental_date, return_date, status) 
VALUES (9, 8, 9, '2026-05-05', '2026-05-15', 'RETURNED');

-- 건 10: 아이유(9)가 원씽(10)을 빌려서 현재 읽는 중. (정상 대여)
INSERT INTO RENTAL (id, member_id, book_id, rental_date, return_date, status) 
VALUES (10, 9, 10, '2026-05-21', NULL, 'RENTED');

-- 건 11: 아이유(9)가 딥러닝 책(1)도 함께 대여함. (인기 있는 책의 다회차 대여 검증용)
INSERT INTO RENTAL (id, member_id, book_id, rental_date, return_date, status) 
VALUES (11, 9, 1, '2026-05-22', NULL, 'RENTED');

-- 건 12: 임영웅(10)이 코스모스(3)를 이전에 빌렸다가 정상 반납함.
INSERT INTO RENTAL (id, member_id, book_id, rental_date, return_date, status) 
VALUES (12, 10, 3, '2026-05-01', '2026-05-10', 'RETURNED');

-- 건 13: 이영희(1)가 사피엔스(7)를 이전에 빌렸다가 반납함. (이영희 회원의 3번째 거래)
INSERT INTO RENTAL (id, member_id, book_id, rental_date, return_date, status) 
VALUES (13, 1, 7, '2026-04-20', '2026-05-01', 'RETURNED');

-- 건 14: 김철수(2)가 정의란 무엇인가(4)를 대여했다가 정상 반납함.
INSERT INTO RENTAL (id, member_id, book_id, rental_date, return_date, status) 
VALUES (14, 2, 4, '2026-05-02', '2026-05-14', 'RETURNED');

-- 건 15: 박민수(3)가 클린 코드(2)를 아주 최근에 대여함.
INSERT INTO RENTAL (id, member_id, book_id, rental_date, return_date, status) 
VALUES (15, 3, 2, '2026-05-23', NULL, 'RENTED');

-- =============================================================================
-- [Phase 1] SQL로 만드는 도서 대여 데이터베이스: 스키마 정의서 (schema.sql)
-- =============================================================================
-- 
-- 본 스키마 파일은 관계형 데이터베이스(RDBMS)의 기본 설계 사상과 데이터 무결성(Integrity)을 
-- 밑바닥부터 학습할 수 있도록 "심각할 정도로 상세한 교육적 주석"을 포함하고 있습니다.
-- 
-- -----------------------------------------------------------------------------
-- 💡 핵심 DB 개념 미리보기: 엑셀 vs RDBMS
-- 1. 데이터 중복 방지 (Normalization, 정규화):
--    '소설' 장르의 이름이 백만 번 나온다면, 엑셀은 매 행마다 '소설'이라는 글자를 저장해 메모리를 낭비합니다.
--    RDBMS는 이를 'CATEGORY'라는 독립된 테이블로 분리하고 숫자 키(ID)만 참조(FK)하게 해 공간을 절약하고,
--    장르명이 'SF 소설'로 변경될 때 단 한 군데만 수정하면 되도록 보장합니다 (수정 이상 방지).
--
-- 2. 데이터 무결성 (Data Integrity):
--    "가입하지 않은 회원에게 책을 빌려줄 수 없고", "존재하지 않는 책을 대여할 수 없다"는 비즈니스 규칙을
--    프로그램 코드가 아닌 데이터베이스 엔진 레벨에서 강제하기 위해 PK와 FK라는 안전장치를 사용합니다.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 0. SQLite 외래키(Foreign Key) 활성화 설정
-- -----------------------------------------------------------------------------
-- SQLite는 역사적인 하위 호환성(Backward Compatibility)을 유지하기 위해,
-- 외래키(Foreign Key) 제약조건 검사가 기본적으로 꺼져(OFF) 있습니다.
-- 따라서 데이터베이스 세션을 열 때마다 아래 명령어를 가장 먼저 실행해 주어야만 
-- 외래키 무결성 제약조건이 실시간으로 작동합니다.
PRAGMA foreign_keys = ON;


-- -----------------------------------------------------------------------------
-- 1. CATEGORY 테이블 (도서 장르/카테고리 관리)
-- -----------------------------------------------------------------------------
-- 책의 장르(예: 컴퓨터공학, 소설, 인문학 등)를 관리하는 기준 테이블입니다.
-- 데이터 중복을 없애고 장르 정보의 일관성을 유지하기 위해 독립시켰습니다.
DROP TABLE IF EXISTS CATEGORY;

CREATE TABLE CATEGORY (
    -- [PK - Primary Key (기본키)]
    -- 개념: 테이블 내의 각 행(레코드)을 고유하게 식별할 수 있는 단 하나의 컬럼(또는 컬럼의 조합)입니다.
    -- 특징: 중복값(Duplicate)을 절대 허용하지 않으며, 빈 값(NULL)도 가질 수 없습니다. (Entity Integrity, 개체 무결성)
    -- SQLite 내부: INTEGER PRIMARY KEY는 내부적으로 64비트 부호 있는 정수형(RowID)과 동의어이며,
    --             AUTOINCREMENT를 선언하면 이전에 생성되었다가 삭제된 ID를 재사용하지 않고 계속 증가시킵니다.
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- [NOT NULL / UNIQUE 제약조건]
    -- NOT NULL: 카테고리 이름이 비어 있는(NULL) 데이터는 무의미하므로 반드시 입력되도록 강제합니다.
    -- UNIQUE: 동일한 카테고리 이름(예: '소설')이 두 번 이상 저장되는 것을 방지합니다. 
    --         데이터베이스 엔진은 UNIQUE 제약조건이 걸린 컬럼에 대해 백엔드에서 
    --         자동으로 고유 인덱스(Unique Index)를 생성하여 중복 값 검색 성능을 O(1)에 가깝게 최적화합니다.
    name VARCHAR(50) NOT NULL UNIQUE
);


-- -----------------------------------------------------------------------------
-- 2. MEMBER 테이블 (회원 정보 관리)
-- -----------------------------------------------------------------------------
-- 도서 대여 서비스를 이용하는 회원들을 정의하는 테이블입니다.
DROP TABLE IF EXISTS MEMBER;

CREATE TABLE MEMBER (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- NOT NULL: 회원의 이름은 비즈니스상 필수 정보이므로 누락을 원천 차단합니다.
    name VARCHAR(100) NOT NULL,

    -- UNIQUE: 로그인 ID 또는 연락 목적으로 쓰이는 이메일은 시스템 내에서 유일해야 합니다.
    --         중복 가입 방지 및 특정 이메일로 회원을 조회할 때 인덱싱을 통해 압도적 속도를 냅니다.
    email VARCHAR(100) NOT NULL UNIQUE,

    -- phone: 전화번호는 필수 입력이 아닐 수 있으므로 NOT NULL을 주지 않아 빈 값(NULL)을 허용합니다.
    phone VARCHAR(20),

    -- DEFAULT CURRENT_DATE: 가입 날짜를 명시적으로 넣지 않고 INSERT를 실행할 때,
    --                       데이터베이스 엔진이 자동으로 쿼리가 수행되는 시점의 현재 날짜(YYYY-MM-DD)를 채워 넣습니다.
    join_date DATE DEFAULT CURRENT_DATE
);


-- -----------------------------------------------------------------------------
-- 3. BOOK 테이블 (도서 정보 관리)
-- -----------------------------------------------------------------------------
-- 도서관/서점이 보유하고 있는 책의 메타데이터를 관리하는 테이블입니다.
DROP TABLE IF EXISTS BOOK;

CREATE TABLE BOOK (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    title VARCHAR(200) NOT NULL,

    author VARCHAR(100) NOT NULL,

    -- price: 책의 대여 연체료 계산 기준이나 분실 시 변상 기준이 될 수 있는 도서 가격입니다.
    --        0 이상의 정수만 저장되어야 하므로 CHECK 제약조건을 걸어 음수 입력을 데이터베이스 단에서 불허합니다.
    price INTEGER NOT NULL CHECK (price >= 0),

    published_date DATE,

    -- [FK - Foreign Key (외래키)]
    -- 개념: 다른 테이블의 기본키(PK)를 참조하여 두 테이블 간의 관계(Relation)를 연결하는 연결고리입니다.
    -- 목적: 참조 무결성(Referential Integrity)을 달성합니다. 
    --       즉, BOOK 테이블의 category_id에는 실제로 CATEGORY 테이블에 존재하는 id값만 들어올 수 있습니다.
    category_id INTEGER,
    
    -- [외래키 제약조건 세부 설정]
    -- FOREIGN KEY (이 컬럼) REFERENCES 참조테이블(참조컬럼)
    -- ON DELETE RESTRICT: 참조되는 부모 데이터(CATEGORY)가 삭제될 때의 동작을 정의합니다.
    --   - RESTRICT: 해당 카테고리를 참조하고 있는 책이 하나라도 존재한다면, 부모 카테고리 자체를 삭제하지 못하게 차단합니다.
    --     예를 들어 '컴퓨터공학' 카테고리에 속한 책들이 서가에 있는데 카테고리 자체를 지워버리면,
    --     그 책들은 부모를 잃어버리는 고아 데이터(Orphaned Data)가 되기 때문에 이를 엄격히 보호하는 옵션입니다.
    FOREIGN KEY (category_id) REFERENCES CATEGORY(id) ON DELETE RESTRICT
);


-- -----------------------------------------------------------------------------
-- 4. RENTAL 테이블 (도서 대여 및 반납 거래 기록)
-- -----------------------------------------------------------------------------
-- 누가(MEMBER), 어떤 책을(BOOK), 언제 빌려갔고(rental_date) 언제 반납했는지(return_date)를
-- 기록하는 트랜잭션 성격의 테이블입니다. MEMBER 테이블과 BOOK 테이블 간의 다대다(M:N) 관계를
-- 1:N 관계로 풀어낸 중간 매핑(교차) 테이블이기도 합니다.
DROP TABLE IF EXISTS RENTAL;

CREATE TABLE RENTAL (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- 1:N 관계 매핑을 위한 외래키 컬럼 선언
    member_id INTEGER NOT NULL,
    book_id INTEGER NOT NULL,

    -- DEFAULT CURRENT_DATE: 대여하는 순간의 날짜를 기본값으로 갖습니다.
    rental_date DATE NOT NULL DEFAULT CURRENT_DATE,

    -- return_date: 대여를 처음 시작할 때는 반납하지 않았으므로 NULL 값을 허용합니다.
    --              반납이 완료되는 시점에 UPDATE 문을 통해 실제 반납 날짜를 채워 넣게 됩니다.
    return_date DATE,

    -- status: 대여 상태를 저장합니다.
    --   - 'RENTED': 대여 중
    --   - 'RETURNED': 정상 반납 완료
    --   - 'OVERDUE': 연체 상태
    -- CHECK 제약조건: 정의되지 않은 텍스트(예: 'LOST' 등을 사전에 약속하지 않은 상태)가 임의로 들어오는 것을 
    --                도메인 레벨에서 엄격히 차단하여 데이터 정합성을 유지합니다.
    status VARCHAR(20) NOT NULL DEFAULT 'RENTED' CHECK (status IN ('RENTED', 'RETURNED', 'OVERDUE')),

    -- [참조 무결성 제약조건 정의]
    -- 1. 회원이 탈퇴할 때(MEMBER 삭제 시) 어떻게 할 것인가?
    --    ON DELETE CASCADE: 부모 레코드(MEMBER)가 지워지면, 해당 회원의 과거 모든 대여/반납 기록(RENTAL)도
    --                      종속적으로 함께 자동 삭제되도록 합니다.
    --                      (단, 실제 금융/서비스 실무에서는 데이터 보존을 위해 soft delete를 주로 사용하지만,
    --                       여기서는 CASCADE의 물리적 삭제 전파 작동을 학습하기 위해 선언했습니다.)
    FOREIGN KEY (member_id) REFERENCES MEMBER(id) ON DELETE CASCADE,

    -- 2. 도서 데이터가 지워질 때(BOOK 삭제 시) 어떻게 할 것인가?
    --    ON DELETE RESTRICT: 해당 도서의 대여 기록이 한 건이라도 데이터베이스에 남아 있다면, 
    --                        그 도서 정보 자체를 테이블에서 무단으로 지우는 행위를 차단합니다.
    --                        통계적 분석과 회계 처리를 위해 과거의 거래 이력이 훼손되는 것을 방지합니다.
    FOREIGN KEY (book_id) REFERENCES BOOK(id) ON DELETE RESTRICT
);

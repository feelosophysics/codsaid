# 📚 초보자를 위한 데이터베이스 & SQL 완벽 학습 가이드

안녕하세요! 이 가이드는 **"데이터베이스와 SQL을 처음 접하는 초보자가, 다른 초보자에게 막힘없이 설명할 수 있을 정도로"** 쉽고 상세하게 쓰여진 자습서입니다. 

우리가 정복할 최종 미션은 **"도서 대여 서비스"**의 데이터베이스를 설계하고, 필요한 데이터를 직접 넣은 뒤, 15개의 핵심 쿼리를 통해 원하는 데이터를 마음껏 뽑아보는 것입니다.

천천히 따라오시면, 어느새 누군가에게 "데이터베이스란 말이지~" 하고 자신 있게 설명하고 있는 자신을 발견하게 될 거예요! 😊

---

## 🗺️ 전체 학습 로드맵 (Roadmap)

본 가이드는 총 3단계(Part)로 나누어 진행됩니다. 지금은 **[Part 1]**만 먼저 작성되어 있습니다. 스타일과 분량이 마음에 드시는지 확인해 주신 후, 다음 단계로 함께 나아가요!

*   **Part 1: 기초 다지기 & 환경 설정 (DB & SQL 기초) 👈 [현재 진행 단계]**
    *   1. 엑셀과 DB의 근본적인 차이 (왜 DB를 써야 할까?)
    *   2. 로컬 DB 개발 환경 구축 (SQLite & DBeaver 완전 정복)
    *   3. SQL의 4대 기둥: CRUD 기초 개념과 기본 쿼리
*   **Part 2: 데이터 모델링 & 관계(Relation) 설계 (예정)**
    *   4. Primary Key(PK)와 Foreign Key(FK)의 비밀
    *   5. 1:N(일대다) 관계란 무엇이고 왜 나누어 저장할까?
    *   6. 무결성 제약 조건(Not Null, Unique, FK 제약) 이해하기
    *   7. 도서 대여 도메인 설계 및 테이블 구조도 그리기
*   **Part 3: 실전 SQL 작성 & 고급 조회 패턴 (예정)**
    *   8. 스키마 생성(DDL) 및 샘플 데이터(DML) 스크립트 작성 (순서 제약 해결)
    *   9. 조인(JOIN)과 집계(GROUP BY)로 흩어진 데이터 하나로 모으기
    *   10. 서브쿼리(Subquery)와 검색 최적화를 위한 인덱스(Index) 이해
    *   11. 결과 검증 및 미션 제출물 정리 가이드

---

## 📖 Part 1: 기초 다지기 & 환경 설정

---

### 1. 왜 엑셀이 아니라 데이터베이스(DB)일까?

데이터베이스를 처음 배울 때 가장 많이 하는 질문이 있습니다.
> **"어차피 표 형태로 저장할 거면, 그냥 엑셀(Excel)에 적으면 안 되나요? 엑셀도 필터링 되고, 함수도 쓸 수 있잖아요?"**

아주 합리적인 질문이에요! 하지만 우리가 서비스(웹 앱, 앱 등)를 만들 때 엑셀을 쓰지 않고 굳이 복잡해 보이는 **관계형 데이터베이스(RDBMS)**를 쓰는 데는 아주 결정적인 이유들이 있습니다. 

주변 친구에게 설명해 준다고 생각하고, 아래의 4가지 핵심 차이점을 머릿속에 쏙 넣어봅시다!

#### ① 공유와 동시성 (Concurrency) - "동시에 쓸 때 터지는 엑셀"
*   **엑셀**: 만약 도서 대여점 직원 3명이 동시에 하나의 엑셀 파일을 열고 대여 기록을 적으려고 하면 어떻게 될까요? "이 파일은 다른 사용자가 편집 중입니다. 읽기 전용으로 여시겠습니까?"라는 경고창을 보게 됩니다. 누군가 저장하면 다른 사람의 수정 사항이 덮어씌워지거나 꼬이기 십상이죠.
*   **데이터베이스**: DB는 수천, 수만 명의 사용자가 **동시에** 접속해서 데이터를 읽고 써도, 차례를 안전하게 정리해 주어 데이터가 엉키지 않도록 지켜줍니다.

#### ② 데이터의 정합성과 무결성 (Consistency & Integrity) - "오타를 못 막는 엑셀"
*   **엑셀**: 대여 대장 엑셀 파일의 '대여 회원명' 칸에 누군가 실수로 `'홍길덩'`이라고 오타를 내거나, `'아무개'`라는 가짜 이름을 적어도 엑셀은 눈 하나 깜짝하지 않고 받아들입니다. 심지어 날짜를 적어야 하는 칸에 `'내일모레'`라고 한글을 적어도 막지 못하죠.
*   **데이터베이스**: DB에는 **규칙(제약 조건)**을 미리 걸어둘 수 있습니다. "회원 테이블에 없는 이름은 대여할 수 없어!", "대여일 칸에는 무조건 YYYY-MM-DD 형식의 날짜만 들어와야 해!"라고 규제하는 것이죠. 규칙에 어긋나는 데이터가 들어오려고 하면 DB가 스스로 **"에러!"**를 뿜으며 입력을 거부합니다.

#### ③ 테이블 간의 '관계(Relation)' - "중복이 판치는 엑셀"
이 부분이 가장 중요합니다! 엑셀로 도서 대여 대장을 만들면 보통 아래처럼 적게 됩니다.

| 대여번호 | 회원ID | 회원 이름 | 연락처 | 대여 도서명 | 저자 | 카테고리 | 대여일 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | user01 | 홍길동 | 010-1234-5678 | 어린 왕자 | 생텍쥐페리 | 소설 | 2026-06-09 |
| 2 | user01 | 홍길동 | 010-1234-5678 | 해리 포터 | J.K. 롤링 | 소설 | 2026-06-10 |

보이시나요? `홍길동`이라는 회원이 책을 빌릴 때마다 이름(`홍길동`)과 연락처(`010-1234-5678`)가 **매번 중복해서 저장**됩니다. 
만약 홍길동 회원이 연락처를 `010-9999-9999`로 바꾸면 어떻게 될까요? 엑셀 파일 전체를 뒤져서 홍길동의 연락처를 전부 찾아 고쳐야 합니다. 하나라도 빼먹으면 데이터가 불일치하는 심각한 문제가 생기죠.

반면 **데이터베이스**는 이 정보를 쪼개서 저장합니다.
*   **회원 테이블**에 홍길동의 정보(`ID`, `이름`, `연락처`)를 딱 **한 번만** 저장합니다.
*   **대여 테이블**에는 `회원ID`와 `도서ID`만 연결해 줍니다. 
이렇게 하면 회원의 연락처가 바뀌어도 '회원 테이블'의 단 1행만 수정하면 끝납니다. 대여 테이블은 변경할 필요가 전혀 없죠! 이것이 바로 **관계형 데이터베이스의 핵심 마법**입니다.

---

### 2. 로컬 DB 개발 환경 구축하기 (SQLite & DBeaver)

데이터베이스의 필요성을 이해했으니, 직접 실습해 볼 환경을 만들어봅시다. 
우리는 입문자에게 가장 친절한 **SQLite** 데이터베이스와, DB 안을 시각적으로 쉽게 들여다볼 수 있는 돋보기 도구인 **DBeaver(디비버)**를 사용하겠습니다.

#### 💡 왜 SQLite인가요?
보통 MySQL이나 PostgreSQL 같은 DB는 컴퓨터에 무거운 '서버 프로그램'을 깔고, 백그라운드에서 실행시키고, 포트 번호를 맞추고, 비밀번호를 설정하는 등 입문 단계에서 포기하게 만드는 높은 장벽이 있습니다.
반면 **SQLite**는 **"파일 하나가 곧 데이터베이스"**가 되는 가볍고 단순한 엔진입니다. 별도의 서버 설치가 전혀 필요 없고, 파일 하나만 만들면 준비 끝입니다!

#### 단계 1: DBeaver 설치하기
DBeaver는 메모장이나 엑셀처럼, 데이터베이스 안의 테이블을 보기 좋게 GUI(그래픽 화면)로 보여주고 SQL을 실행할 수 있게 돕는 만능 툴입니다.
1. [DBeaver 공식 다운로드 페이지](https://dbeaver.io/download/)에 접속합니다.
2. 본인의 OS(Windows, macOS)에 맞는 **Community Edition** 설치 파일을 다운로드합니다. (무료입니다!)
3. 설치 프로그램을 실행하여 기본 설정대로 설치를 완료합니다.

#### 단계 2: SQLite 데이터베이스 파일 생성 및 연결하기
설치가 완료되었다면, DBeaver를 켜고 새 데이터베이스를 만들어 연결해 봅시다.

1. **DBeaver 실행**: 설치된 DBeaver를 실행합니다. (처음 실행 시 샘플 데이터베이스를 만들겠냐고 물어볼 수 있는데, '아니오' 혹은 건너뛰기를 누르시면 됩니다.)
2. **새 연결 만들기**: 
   * 왼쪽 위의 플러그 모양 콘센트 아이콘(🔌 `New Database Connection`)을 클릭합니다.
   * 여러 DB 목록이 나오는데, 검색창에 `SQLite`를 검색하고 클릭한 뒤 **[Next]**를 누릅니다.
3. **DB 파일 위치 지정**:
   * 설정 창 중간의 `Path` 입력란 옆에 있는 **[Open]** 혹은 **[Browse]** 버튼을 클릭합니다.
   * 우리 프로젝트 폴더(또는 본인이 편한 위치)를 찾아서 파일 이름을 `library.db`라고 입력하고 [저장]을 누릅니다. (이 파일이 앞으로 모든 도서 대여 데이터가 담길 파일입니다!)
4. **드라이버 다운로드 (최초 1회)**:
   * 연결 설정 창 왼쪽 아래의 **[Test Connection]** 버튼을 누릅니다.
   * 드라이버 파일을 다운로드해야 한다는 팝업창이 뜨면 **[Download]**를 클릭해 줍니다. 잠시 기다리면 연결이 성공했다는 메시지(`Connected`)가 뜹니다!
5. **완료**: **[Finish]**를 누르면 왼쪽 'Database Navigator' 탭에 우리가 만든 SQLite 연결 항목이 나타납니다.

#### 단계 3: SQL 편집기 열기
이제 명령어를 입력할 스케치북을 열 차례입니다.
1. 왼쪽 내비게이터에서 방금 만든 연결 항목(예: `library.db` 혹은 `SQLite ...`)을 마우스 오른쪽 클릭합니다.
2. **[SQL Editor] -> [Open SQL console]** (또는 **[New SQL script]**)을 클릭합니다.
3. 화면 중앙에 하얗고 깨끗한 텍스트 입력창이 나타납니다. 여기에 SQL 명령어를 적고 실행할 수 있습니다.

---

### 3. SQL의 4대 기둥: CRUD 기초 개념과 기본 쿼리

데이터베이스에 말을 걸기 위해 사용하는 언어가 바로 **SQL (Structured Query Language)** 입니다. 
SQL에서 데이터를 다루는 행위는 크게 **4가지(CRUD)**로 나뉩니다. 모든 서비스 개발의 99%는 이 네 가지 작업을 바탕으로 이루어집니다.

*   **C**reate (생성): 데이터를 새롭게 넣기 ➡️ **`INSERT`**
*   **R**ead (조회): 저장된 데이터를 꺼내 보기 ➡️ **`SELECT`**
*   **U**pdate (수정): 기존 데이터를 고치기 ➡️ **`UPDATE`**
*   **D**elete (삭제): 필요 없는 데이터 지우기 ➡️ **`DELETE`**

각각의 문법을 세상에서 가장 쉬운 비유와 예제로 살펴봅시다.

---

#### 🔍 1) SELECT (Read - 조회): "도서관 서가에서 원하는 책 찾아오기"
데이터베이스에 저장된 데이터를 가져오는 명령어입니다. 
우리가 구글이나 네이버에 검색어를 입력하고 결과를 보는 것, 인스타그램 피드를 내려다보는 것 모두 뒤에서는 이 `SELECT` 쿼리가 작동하고 있는 것입니다.

*   **쉽게 설명하기**:
    > "저기요, **[어떤 컬럼]** 정보들을 **[어떤 테이블]**에서 가져다주세요. 참, 조건은 **[이러이러한 것]**만 필터링해서, **[이 순서]**대로 정렬해 주세요!"

*   **기본 문법 구조**:
    ```sql
    SELECT 컬럼명1, 컬럼명2 
    FROM 테이블명 
    WHERE 조건식 
    ORDER BY 정렬기준컬럼 ASC|DESC;
    ```

*   **도서 대여 실전 예제**:
    *   **요구사항**: "도서 테이블(`book`)에서 가격(`price`)이 15,000원 이상인 책들의 제목(`title`)과 저자(`author`)를 찾고, 제목 순서대로 정렬해 줘!"
    ```sql
    SELECT title, author 
    FROM book 
    WHERE price >= 15000 
    ORDER BY title ASC;
    ```
    *   *꿀팁*: 만약 테이블의 모든 컬럼을 다 가져오고 싶다면 별(`*`)을 사용합니다: `SELECT * FROM book;`

---

#### ✍️ 2) INSERT (Create - 생성): "도서관 신간 도서 대장에 등록하기"
테이블에 새로운 데이터를 한 행(Row) 추가할 때 사용하는 명령어입니다. 
웹사이트에서 회원가입을 하거나, 게시판에 새 글을 써서 등록 버튼을 누를 때 실행됩니다.

*   **쉽게 설명하기**:
    > "**[이 테이블]**의 **[이 컬럼들]** 자리에 각각 **[이 값들]**을 쏙쏙 집어넣어 주세요!"

*   **기본 문법 구조**:
    ```sql
    INSERT INTO 테이블명 (컬럼1, 컬럼2, 컬럼3) 
    VALUES (값1, 값2, 값3);
    ```

*   **도서 대여 실전 예제**:
    *   **요구사항**: "도서 테이블(`book`)에 제목이 '어린 왕자', 저자가 '생텍쥐페리', 가격이 12000원인 새로운 책 데이터를 추가해 줘!"
    ```sql
    INSERT INTO book (title, author, price) 
    VALUES ('어린 왕자', '생텍쥐페리', 12000);
    ```
    *   *주의할 점*: 문자를 넣을 때는 작은따옴표(`'`)로 감싸주어야 하며, 숫자는 그냥 적습니다. 지정한 컬럼의 순서와 `VALUES` 뒤의 값의 순서가 정확히 일치해야 합니다!

---

#### ✏️ 3) UPDATE (Update - 수정): "도서 가격 인상 반영하기"
이미 들어있는 데이터의 특정 컬럼 값을 바꿀 때 사용합니다. 
내 프로필 정보를 수정하거나, 비밀번호를 변경할 때 작동합니다.

*   **쉽게 설명하기**:
    > "**[이 테이블]**에서 **[이 조건에 맞는 행]**을 찾아서, 값을 **[이렇게 수정]**해 주세요!"

*   **기본 문법 구조**:
    ```sql
    UPDATE 테이블명 
    SET 변경할컬럼 = 새로운값 
    WHERE 수정할행을찾을조건;
    ```

*   **도서 대여 실전 예제**:
    *   **요구사항**: "ID가 5번인 도서의 가격을 14,000원으로 변경해 줘!"
    ```sql
    UPDATE book 
    SET price = 14000 
    WHERE id = 5;
    ```
    *   *⚠️경고 (매우 중요)*: **WHERE 절을 빼먹으면 절대 안 됩니다!** 
        만약 `WHERE id = 5`를 적지 않고 `UPDATE book SET price = 14000;`이라고만 실행하면, 도서관에 있는 **모든 책의 가격이 14,000원으로 바뀌어버리는** 대참사가 일어납니다! 실무에서도 가장 사고가 많이 나는 쿼리이니 항상 주의하세요!

---

#### 🗑️ 4) DELETE (Delete - 삭제): "폐기 도서 목록에서 제외하기"
테이블에서 기존 데이터를 지울 때 사용합니다. 
회원 탈퇴를 하거나, 작성했던 댓글을 삭제할 때 실행됩니다.

*   **쉽게 설명하기**:
    > "**[이 테이블]**에서 **[이 조건에 맞는 행]**만 완전히 지워주세요!"

*   **기본 문법 구조**:
    ```sql
    DELETE FROM 테이블명 
    WHERE 삭제할행을찾을조건;
    ```

*   **도서 대여 실전 예제**:
    *   **요구사항**: "ID가 3번인 회원의 대여 기록을 삭제해 줘!"
    ```sql
    DELETE FROM rental 
    WHERE member_id = 3;
    ```
    *   *⚠️경고 (매우 중요)*: `DELETE` 또한 **WHERE 절을 절대 빼먹으면 안 됩니다!** 
        `DELETE FROM rental;`이라고만 쓰면 대여 테이블의 **모든 대여 내역이 흔적도 없이 사라져버립니다.** 데이터베이스의 세상에서는 Ctrl + Z(되돌리기)가 되지 않으므로, 지우기 전에는 항상 내가 지우려는 데이터가 맞는지 `SELECT`로 먼저 확인하는 습관을 들이는 것이 좋습니다.

---

### 💡 초보자들을 위한 Part 1 핵심 요약 및 복습 퀴즈!
앞으로 친구에게 아래 3가지 질문을 받았을 때, 자신 있게 답변해 보세요.

1. **"엑셀이랑 DB는 뭐가 달라?"**
   * 🗣️ *"엑셀은 동시 편집이 안 되고 오타 입력도 막기 힘들지만, DB는 강력한 규칙(제약)을 걸어 동시에 다수가 다뤄도 깨지지 않게 해줘. 특히 정보를 쪼개서 '관계'로 연결해 주니까 중복을 막을 수 있어."*
2. **"SQLite는 다른 DB랑 뭐가 달라?"**
   * 🗣️ *"컴퓨터에 별도의 복잡한 서버 프로그램을 실행할 필요 없이, 그냥 `.db` 파일 하나만 만들면 작동하는 가볍고 쓰기 편한 데이터베이스야!"*
3. **"SQL에서 데이터를 다룰 때 꼭 외워야 하는 4대 천왕이 뭐야?"**
   * 🗣️ *"가져올 땐 `SELECT`, 집어넣을 땐 `INSERT`, 고칠 땐 `UPDATE`, 지울 땐 `DELETE`! 그리고 `UPDATE`와 `DELETE`를 쓸 때는 필터링할 `WHERE` 조건절을 반드시 붙여야 대참사를 막을 수 있어!"*

---

## 📖 Part 2: 데이터 모델링 & 관계(Relation) 설계

데이터베이스를 구축하기 전에 가장 먼저 해야 하는 일은 **"설계도 그리기"**입니다. 이 과정을 **데이터 모델링**이라고 합니다. 
테이블을 어떻게 쪼개고 어떻게 연결할지 설계가 잘되어 있어야 나중에 SQL을 짤 때 고생하지 않습니다.

---

### 4. Primary Key(PK)와 Foreign Key(FK)의 비밀

데이터 모델링의 가장 기본이 되는 두 가지 열쇠(Key)가 있습니다. 바로 **기본키(PK)**와 **외래키(FK)**입니다.

#### 🔑 ① 기본키(Primary Key, PK) : "테이블 내의 주민등록번호"
테이블에 들어있는 수많은 데이터(행, Row) 중에서 **"특정 한 행을 절대 헷갈리지 않고 유일하게 식별할 수 있는 열(Column)"**을 뜻합니다.

*   **실생활 비유**: 학교의 **'학번'**, 회사의 **'사번'**, 대한민국의 **'주민등록번호'**, 쇼핑몰의 **'주문번호'**가 모두 PK입니다. 동명이인이 있어도 학번이 다르면 서로 다른 학생이듯, PK는 행들을 구별하는 유일한 단서입니다.
*   **PK가 지켜야 할 두 가지 절대 규칙**:
    1.  **중복되면 안 된다 (Unique)**: 같은 PK를 가진 행이 존재할 수 없습니다.
    2.  **비어있으면 안 된다 (Not Null)**: PK 값은 결코 빈 칸(`NULL`)이 될 수 없습니다. 주민등록번호가 없는 국민은 존재할 수 없는 것과 같습니다.
*   *꿀팁*: 실무에서는 보통 `id`라는 컬럼을 만들고, 데이터가 추가될 때마다 1, 2, 3, 4... 순서대로 자동으로 증가하는 숫자를 PK로 많이 지정합니다. (이를 자동 증가 키, Auto-Increment라고 합니다.)

#### 🔗 ② 외래키(Foreign Key, FK) : "다른 테이블을 가리키는 지시선"
외래키는 **"다른 테이블의 기본키(PK)를 참조하여 연결고리를 만드는 열"**입니다. 테이블과 테이블을 이어주는 강력한 끈이라고 보면 됩니다.

*   **쉽게 설명하기**:
    > "우리 대여 테이블에 있는 `member_id`는 그냥 아무 숫자가 아니야. 저쪽 **회원 테이블의 PK인 `id`**를 가리키는 지시선이야!"
*   **실생활 비유**: 대여 대장에 회원 정보를 매번 다 적기 귀찮아서 회원들의 정보가 적힌 주소록의 번호(회원 ID)만 적어 두는 것입니다. 대여 대장의 `회원ID`가 바로 회원 테이블의 `PK`를 바라보고 있는 외래키(`FK`)입니다.

---

### 5. 1:N (일대다) 관계란 무엇이고 왜 나누어 저장할까?

데이터베이스 설계에서 가장 흔하게 만나는 관계가 바로 **1:N (일대다) 관계**입니다.

#### 👪 1:N 관계의 정의
*   **1**에 해당하는 테이블의 데이터 한 행이, **N**에 해당하는 테이블의 데이터 여러 행과 연결될 수 있는 구조입니다.
*   **도서 대여점 예시**:
    *   **회원(1) : 대여 대장(N)** ➡️ 회원 한 명(`1`)은 책을 여러 번(`N`) 빌릴 수 있습니다. 반대로 대여 대장의 한 줄은 무조건 한 명의 회원에게만 해당합니다.
    *   **카테고리(1) : 도서(N)** ➡️ 소설이라는 카테고리 하나(`1`)에는 소설책 여러 권(`N`)이 속할 수 있습니다.
    *   **도서(1) : 대여 대장(N)** ➡️ 책 한 권(`1`)은 시간이 흐르며 여러 번(`N`) 대여될 수 있습니다.

#### ❓ 왜 귀찮게 테이블을 쪼개서 1:N으로 연결하나요?
앞서 1편에서 설명해 드린 대로, 한 테이블에 다 집어넣으면 **데이터의 중복**이 발생하기 때문입니다. 

| 대여ID | 회원 이름 | 도서명 | 저자 |
| :--- | :--- | :--- | :--- |
| 1 | 홍길동 | 어린 왕자 | 생텍쥐페리 |
| 2 | 홍길동 | 해리 포터 | J.K. 롤링 |

홍길동이 책을 100권 빌리면 홍길동의 이름이 100번 적힙니다. 만약 홍길동이 이름을 '홍길서'로 개명하면 100군데를 모두 수정해야 합니다. 
하지만 테이블을 **회원(1)**과 **대여(N)**로 쪼개면 다음과 같습니다.

*   **회원 테이블(1)**: `1 | 홍길동 | 010-1234-5678` (단 한 줄만 존재)
*   **대여 테이블(N)**:
    *   `대여ID 1 | 회원ID 1(FK) | 도서 ID 10`
    *   `대여ID 2 | 회원ID 1(FK) | 도서 ID 12`

이름이 바뀌면 **회원 테이블의 딱 한 줄**만 바꾸면 끝납니다. 대여 테이블은 회원ID `1`을 가리키고 있으므로 자동으로 연동됩니다.

#### ⚠️ 핵심 규칙: 외래키(FK)는 무조건 'N' 쪽에 위치한다!
초보자가 가장 많이 하는 실수가 "외래키를 어느 테이블에 두어야 하는가?"입니다.
*   **질문**: "회원 테이블에 대여ID를 넣어야 하나요? 아니면 대여 테이블에 회원ID를 넣어야 하나요?"
*   **답변**: **무조건 'N'의 위치인 대여 테이블에 회원ID(FK)를 넣어야 합니다.**
*   *이유 생각해보기*: 만약 회원 테이블에 대여ID를 넣는다면, 회원 한 명이 책을 2번 빌릴 때 대여ID 칸에 값 두 개(예: `1, 2`)를 쉼표로 구겨 넣거나, 회원 행을 복사해서 여러 개 만들어야 합니다. 이는 PK 규칙(유일성)을 깨뜨리게 됩니다. 따라서 언제나 **여러 개가 발생할 수 있는 쪽(N)이 부모(1)의 ID를 들고 있어야 합니다.**

---

### 6. 무결성 제약 조건(Not Null, Unique, FK 제약) 이해하기

제약 조건(Constraint)은 **"데이터베이스가 데이터를 저장할 때 지켜야 하는 철저한 규칙"**입니다. 이 규칙 덕분에 데이터베이스가 오염되지 않고 깨끗하게 유지됩니다. 미션에 포함해야 하는 필수 제약 조건들을 알아봅시다.

#### ① NOT NULL: "이 칸은 절대 비워둘 수 없어!"
*   **의미**: 해당 컬럼에 데이터를 넣을 때 `NULL`(빈 값) 입력을 금지합니다.
*   **적용 대상**: 회원 이름, 책 제목, 카테고리명처럼 **서비스 운영에 있어 필수적인 값**에 지정합니다. (예: 이름 없는 회원은 가입할 수 없습니다.)

#### ② UNIQUE: "똑같은 값이 또 들어오면 안 돼!"
*   **의미**: 테이블 전체에서 중복된 값이 들어올 수 없게 막습니다. (다만, 비어있는 값(`NULL`)은 중복을 허용하는 경우가 많습니다.)
*   **적용 대상**: 회원 로그인 ID, 이메일 주소, 전화번호처럼 **사용자끼리 겹치면 식별에 문제가 생기는 컬럼**에 적용합니다.

#### ③ FOREIGN KEY 제약 (참조 무결성): "유령 데이터를 만들지 마!"
*   **의미**: 외래키로 지정된 컬럼에는 **부모 테이블에 실제로 존재하는 PK 값**만 들어올 수 있게 강제합니다.
*   **적용 대상**: 대여 테이블의 `member_id`에 존재하지 않는 회원 번호인 `999`를 넣으려고 하면, DB가 "회원 테이블에 999번 회원이 없는데 어떻게 대여를 해줘?"라며 입력을 차단합니다.
*   또한 부모 테이블의 데이터가 삭제될 때 자식 데이터를 어떻게 할지 규칙을 정할 수 있습니다 (예: `ON DELETE CASCADE`를 설정하면 회원이 탈퇴할 때 그 회원의 대여 기록도 함께 자동으로 삭제됩니다).

---

### 7. 도서 대여 도메인 설계 및 테이블 구조도 그리기

우리가 정한 **"도서 대여 서비스"**를 위한 테이블 4개를 설계해 봅시다. 
이 4개 테이블은 서로 1:N 관계로 얽히며 미션 요구사항을 충족합니다.

#### 📝 테이블 목록 및 설계 요약
1.  **category (카테고리 테이블)**: 책의 분류 (예: 소설, 역사, IT 등)
2.  **member (회원 테이블)**: 서비스를 이용하는 회원들의 정보
3.  **book (도서 테이블)**: 도서관이 보유한 책 목록 (카테고리 테이블을 참조하는 FK 포함)
4.  **rental (대여 대장 테이블)**: 누가, 어떤 책을, 언제 빌리고 반납했는지 기록 (회원 테이블과 도서 테이블을 참조하는 FK 2개 포함)

#### 📐 테이블 구조 및 관계도 (Entity Relationship)
우리의 테이블들이 어떻게 얽혀있는지 텍스트 다이어그램으로 시각화해 보겠습니다.

```
+------------------+         +------------------+
|    category      |         |     member       |
|------------------|         |------------------|
| PK : id          |         | PK : id          |
|    : name(UQ)    |         |    : login_id(UQ)|
+--------+---------+         |    : name        |
         |                   |    : phone       |
         | 1                 +--------+---------+
         |                            |
         | N                          | 1
+--------v---------+                  |
|      book        |                  |
|------------------|                  |
| PK : id          |                  |
| FK : category_id |                  |
|    : title       |                  |
|    : author      |                  |
|    : price       |                  |
+--------+---------+                  |
         | 1                          |
         |                            |
         | N                          | N
+--------v----------------------------v---------+
|                    rental                     |
|-----------------------------------------------|
| PK : id                                       |
| FK : member_id                                |
| FK : book_id                                  |
|    : rental_date                              |
|    : return_date                              |
+-----------------------------------------------+
```

*   **관계 분석**:
    *   `category` (1) : `book` (N) ➡️ 한 카테고리에는 여러 책이 등록될 수 있습니다. (`category_id`가 외래키로 작동)
    *   `member` (1) : `rental` (N) ➡️ 한 회원은 여러 번 책을 대여할 수 있습니다. (`member_id`가 외래키로 작동)
    *   `book` (1) : `rental` (N) ➡️ 한 도서는 여러 번 대여될 수 있습니다. (`book_id`가 외래키로 작동)
    *   **요구사항 확인**: 최소 4개 테이블 만족, 1:N 관계가 3개이므로 최소 2개 조건도 거뜬히 만족합니다!

---

## 📖 Part 3: 실전 SQL 작성 & 고급 조회 패턴

이제 설계도를 바탕으로 DBeaver에서 실행할 실제 SQL 스크립트를 작성하고 쿼리를 정복해 볼 차례입니다.

---

### 8. 스키마 생성(DDL) 및 샘플 데이터(DML) 스크립트 작성

#### 🧱 스키마 생성 SQL (DDL - Data Definition Language)
테이블을 생성할 때는 **생성 순서가 아주 중요합니다.** 외래키 제약조건이 걸려있기 때문입니다.
*   **규칙**: 자식 테이블(FK를 가진 테이블)을 만들기 전에, **부모 테이블(참조 대상이 되는 테이블)**을 반드시 먼저 만들어야 합니다.
*   **올바른 순서**: `category`와 `member` 생성 ➡️ `book` 생성 (category 참조) ➡️ `rental` 생성 (member, book 참조)

자, 아래의 코드를 DBeaver의 SQL 편집기에 그대로 복사해서 실행해 보세요!

```sql
-- 1. 카테고리 테이블 생성 (부모)
CREATE TABLE category (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

-- 2. 회원 테이블 생성 (부모)
CREATE TABLE member (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    login_id TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    phone TEXT
);

-- 3. 도서 테이블 생성 (category의 자식이자 rental의 부모)
CREATE TABLE book (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    author TEXT,
    price INTEGER NOT NULL,
    FOREIGN KEY (category_id) REFERENCES category(id)
);

-- 4. 대여 대장 테이블 생성 (member와 book의 자식)
CREATE TABLE rental (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id INTEGER NOT NULL,
    book_id INTEGER NOT NULL,
    rental_date TEXT NOT NULL, -- SQLite는 DATE 타입 대신 TEXT에 'YYYY-MM-DD' 형식으로 저장합니다.
    return_date TEXT,          -- 반납하지 않은 경우 빈 값(NULL)을 허용합니다.
    FOREIGN KEY (member_id) REFERENCES member(id),
    FOREIGN KEY (book_id) REFERENCES book(id)
);
```

#### 🌱 샘플 데이터 입력 SQL (DML - Data Manipulation Language)
데이터를 입력할 때도 **순서의 규칙**이 적용됩니다. 부모 테이블에 데이터가 먼저 있어야 자식 테이블에 값을 채울 수 있습니다.
*   **올바른 입력 순서**: `category`, `member` 데이터 입력 ➡️ `book` 데이터 입력 ➡️ `rental` 데이터 입력
*   각 테이블에 의미 있는 데이터를 **최소 10행씩** 꽉꽉 채워보겠습니다.

```sql
-- 1. 카테고리 데이터 입력 (10개)
INSERT INTO category (name) VALUES ('소설');
INSERT INTO category (name) VALUES ('시/에세이');
INSERT INTO category (name) VALUES ('인문학');
INSERT INTO category (name) VALUES ('역사');
INSERT INTO category (name) VALUES ('과학');
INSERT INTO category (name) VALUES ('자기계발');
INSERT INTO category (name) VALUES ('경제/경영');
INSERT INTO category (name) VALUES ('IT/컴퓨터');
INSERT INTO category (name) VALUES ('예술');
INSERT INTO category (name) VALUES ('어린이');

-- 2. 회원 데이터 입력 (10개)
INSERT INTO member (login_id, name, phone) VALUES ('hong12', '홍길동', '010-1234-5678');
INSERT INTO member (login_id, name, phone) VALUES ('kim99', '김철수', '010-9876-5432');
INSERT INTO member (login_id, name, phone) VALUES ('lee_dev', '이영희', '010-5555-1234');
INSERT INTO member (login_id, name, phone) VALUES ('park_reader', '박민수', '010-2222-8888');
INSERT INTO member (login_id, name, phone) VALUES ('choi_best', '최지우', '010-3333-7777');
INSERT INTO member (login_id, name, phone) VALUES ('jung_science', '정민재', '010-4444-6666');
INSERT INTO member (login_id, name, phone) VALUES ('kang_money', '강하늘', '010-7777-1111');
INSERT INTO member (login_id, name, phone) VALUES ('yoon_art', '윤소희', '010-8888-2222');
INSERT INTO member (login_id, name, phone) VALUES ('lim_history', '임재범', '010-9999-3333');
INSERT INTO member (login_id, name, phone) VALUES ('shin_books', '신지혜', '010-1111-4444');

-- 3. 도서 데이터 입력 (10개)
-- 카테고리 ID 매칭: 1-소설, 2-시, 3-인문, 4-역사, 5-과학, 6-자기계발, 7-경제, 8-IT, 9-예술, 10-어린이
INSERT INTO book (category_id, title, author, price) VALUES (1, '어린 왕자', '생텍쥐페리', 12000);
INSERT INTO book (category_id, title, author, price) VALUES (1, '해리 포터와 마법사의 돌', 'J.K. 롤링', 15000);
INSERT INTO book (category_id, title, author, price) VALUES (3, '사피엔스', '유발 하라리', 22000);
INSERT INTO book (category_id, title, author, price) VALUES (4, '설민석의 조선왕조실록', '설민석', 18000);
INSERT INTO book (category_id, title, author, price) VALUES (5, '코스모스', '칼 세이건', 25000);
INSERT INTO book (category_id, title, author, price) VALUES (6, '데일 카네기 인간관계론', '데일 카네기', 11500);
INSERT INTO book (category_id, title, author, price) VALUES (7, '부의 시나리오', '오건영', 16000);
INSERT INTO book (category_id, title, author, price) VALUES (8, 'Do it! 점프 투 파이썬', '박응용', 18800);
INSERT INTO book (category_id, title, author, price) VALUES (8, '혼자 공부하는 SQL', '우재남', 19500);
INSERT INTO book (category_id, title, author, price) VALUES (10, '만화 그리스 로마 신화', '토마스 불핀치', 13000);

-- 4. 대여 데이터 입력 (10개)
-- 대여일과 반납일(반납 완료 시 작성, 미반납 시 NULL) 입력
INSERT INTO rental (member_id, book_id, rental_date, return_date) VALUES (1, 1, '2026-05-01', '2026-05-08');
INSERT INTO rental (member_id, book_id, rental_date, return_date) VALUES (1, 3, '2026-05-10', '2026-05-17');
INSERT INTO rental (member_id, book_id, rental_date, return_date) VALUES (2, 2, '2026-05-12', '2026-05-19');
INSERT INTO rental (member_id, book_id, rental_date, return_date) VALUES (3, 8, '2026-05-15', '2026-05-22');
INSERT INTO rental (member_id, book_id, rental_date, return_date) VALUES (4, 5, '2026-05-20', NULL); -- 미반납 상태
INSERT INTO rental (member_id, book_id, rental_date, return_date) VALUES (5, 9, '2026-05-22', '2026-05-29');
INSERT INTO rental (member_id, book_id, rental_date, return_date) VALUES (6, 6, '2026-05-25', NULL); -- 미반납 상태
INSERT INTO rental (member_id, book_id, rental_date, return_date) VALUES (1, 2, '2026-06-01', '2026-06-08');
INSERT INTO rental (member_id, book_id, rental_date, return_date) VALUES (7, 7, '2026-06-03', NULL); -- 미반납 상태
INSERT INTO rental (member_id, book_id, rental_date, return_date) VALUES (3, 9, '2026-06-05', NULL); -- 미반납 상태
```

---

### 9. 조인(JOIN)과 집계(GROUP BY)로 흩어진 데이터 하나로 모으기

우리가 미션을 해결할 때 가장 어렵지만 중요한 부분이 바로 **조인(JOIN)**과 **그룹화(GROUP BY)**입니다. 이 장벽만 넘어서면 SQL 실력이 초보에서 중급자로 껑충 올라가게 됩니다!

#### ① 조인(JOIN): "테이블 붙이기"
데이터베이스는 중복을 피하기 위해 데이터를 여러 테이블에 나누어 담아두었습니다. 하지만 화면에 대여 현황을 보여줄 때는 **"이름, 연락처, 빌린 도서명, 대여일"**을 한 번에 보여주어야 하죠. 
나누어져 있는 두 테이블을 공통된 연결고리(PK와 FK)를 기준 삼아 양옆으로 붙이는 것이 **조인(JOIN)**입니다.

##### 🤝 1. INNER JOIN (내부 조인): "교집합"
*   **정의**: 양쪽 테이블 모두에 데이터가 매칭되는 경우에만 합쳐서 출력합니다.
*   **비유**: 대여 대장에 적힌 도서 ID가 도서 테이블의 도서 ID와 **일치하는 조합만** 뽑아서 출력해요. 대여 기록이 없는 책이나, 빌린 사람이 없는 가상의 책은 출력되지 않습니다.
*   **실전 예제**: "누가 어떤 책을 빌려 갔는지 대여 대장 정보와 회원 이름, 도서 제목을 합쳐서 보고 싶어!"
    ```sql
    SELECT r.id AS 대여번호, m.name AS 회원이름, b.title AS 도서제목, r.rental_date AS 대여일
    FROM rental r
    INNER JOIN member m ON r.member_id = m.id
    INNER JOIN book b ON r.book_id = b.id;
    ```
    *   *분석*: `FROM rental r`을 기본으로 삼고, 대여 테이블의 회원 번호(`r.member_id`)와 회원 테이블의 식별자(`m.id`)가 일치하는 회원을 딱 달라붙게(`INNER JOIN member m ON ...`) 조인한 것입니다. 마찬가지로 책도 연결했습니다.

##### 👈 2. LEFT JOIN (외부 조인): "기준 테이블 중심"
*   **정의**: 왼쪽(기준) 테이블의 데이터는 **무조건** 다 보여주고, 오른쪽(대상) 테이블의 매칭되는 데이터가 있으면 보여주고 없으면 **`NULL` (빈칸)**로 남겨서 출력합니다.
*   **비유**: 도서관에 등록된 전체 회원 목록을 뽑으면서 각 회원의 대여 횟수나 기록을 붙이고 싶을 때 사용합니다. 책을 한 번도 안 빌린 회원도 회원 목록에는 나와야 하니까요!
*   **실전 예제**: "전체 회원 목록과 대여한 이력을 함께 뽑아줘. 책을 빌리지 않은 회원도 이름은 꼭 보여줘!"
    ```sql
    SELECT m.name AS 회원이름, r.rental_date AS 대여일, r.book_id AS 대여도서ID
    FROM member m
    LEFT JOIN rental r ON m.id = r.member_id;
    ```
    *   *분석*: 만약 `홍길동` 회원은 여러 번 빌렸다면 대여일과 도서 ID가 다 붙어서 나옵니다. 하지만 책을 한 번도 빌리지 않은 `신지혜` 회원의 경우에는 대여일과 도서 ID 칸이 전부 `NULL`인 상태로 한 줄 출력됩니다.

---

#### 📊 ② GROUP BY와 집계 함수: "동아리별로 모여서 머릿수 세기"
수많은 원시 데이터들을 특정 기준에 따라 **그룹으로 묶어 통계치**를 낼 때 사용합니다.

*   **집계 함수 종류**:
    *   `COUNT()`: 행 개수 세기
    *   `SUM()`: 합계 구하기
    *   `AVG()`: 평균 구하기
    *   `MAX()` / `MIN()`: 최댓값 / 최솟값 구하기
*   **작동 방식**: 반드시 **`GROUP BY 묶을컬럼`**을 명시해 주어야 합니다.
*   **실전 예제**: "각 카테고리별로 등록된 도서의 개수와 가장 비싼 책의 가격을 계산해 줘!"
    ```sql
    SELECT c.name AS 카테고리명, COUNT(b.id) AS 도서수, MAX(b.price) AS 최고가
    FROM category c
    LEFT JOIN book b ON c.id = b.category_id
    GROUP BY c.name;
    ```
    *   *분석*: 카테고리별로 책을 묶어서 그룹을 지은 뒤(`GROUP BY c.name`), 해당 그룹 안에 책이 총 몇 권 속해 있는지 개수를 세고(`COUNT(b.id)`), 가격 중 가장 높은 값(`MAX(b.price)`)을 연산해 출력합니다.

---

### 10. 서브쿼리(Subquery)와 검색 최적화를 위한 인덱스(Index)

#### 🔄 ① 서브쿼리(Subquery): "쿼리 안의 쿼리"
SQL 명령어 안에 또 다른 SQL 명령어를 중첩해서 사용하는 기법입니다. 보통 "조건에 쓰일 값 자체를 쿼리로 먼저 찾아내야 할 때" 많이 사용합니다.

*   **실전 예제**: "한 번도 책을 빌린 적이 없는 회원의 아이디와 이름을 찾아줘!"
    *   *생각해보기*: 대여 대장(`rental`) 테이블의 `member_id` 목록에 **존재하지 않는** 회원을 회원 테이블(`member`)에서 찾으면 됩니다!
    ```sql
    SELECT id, name
    FROM member
    WHERE id NOT IN (
        SELECT DISTINCT member_id 
        FROM rental
    );
    ```
    *   *분석*: 괄호 안의 `(SELECT DISTINCT member_id FROM rental)`이 서브쿼리입니다. 대여 기록이 있는 회원 번호 목록(예: 1, 2, 3, 5, 6, 7)을 먼저 쏙 뽑아내어 리스트로 만들고, 바깥의 메인 쿼리에서 이 리스트에 포함되지 않는 회원을 찾아서(`WHERE id NOT IN (...)`) 돌려줍니다.

---

#### ⚡ ② 인덱스(Index): "책 맨 뒷장의 '찾아보기' 색인"
테이블에 데이터가 100만 건쯤 들어있을 때, 특정한 책 제목을 찾으려면 DB는 1번 행부터 100만 번 행까지 전부 훑어봐야 합니다. 이를 'Full Table Scan'이라고 하며 시간이 아주 오래 걸립니다. 
이를 빠르게 해결하기 위해 미리 정렬된 색인표를 만들어두는 것을 **인덱스(Index)**라고 합니다.

*   **인덱스를 걸면 좋은 컬럼**:
    *   `WHERE` 절의 조건으로 매우 자주 검색되는 컬럼
    *   `ORDER BY`로 정렬 기준에 자주 쓰이는 컬럼
    *   `JOIN`의 연결고리(ON)에 들어가는 컬럼
*   **실무 꿀팁 (단점 알기)**:
    인덱스는 책 뒷장의 찾아보기 페이지처럼 용량을 따로 차지하며, 데이터가 삽입/수정/삭제될 때마다 색인표도 매번 다시 정렬해 주어야 하므로 오히려 전체적인 수정 성능이 느려질 수 있습니다. 따라서 **자주 조회되는 꼭 필요한 컬럼에만 전략적으로 지정**해야 합니다.
*   **실전 예제**: "책 제목(`title`) 검색이 매우 잦으므로 책 제목 컬럼에 인덱스를 걸어 최적화하자!"
    ```sql
    CREATE INDEX idx_book_title ON book(title);
    ```

---

## 🏁 미션 해결을 위한 최종 쿼리 15개 템플릿

아래는 미션 요구사항(기본 조회 4개, 조인 4개, 집계 3개, 서브쿼리 1개, 수정/삭제 2개, 인덱스 1개)을 빈틈없이 만족하는 15가지 핵심 쿼리 세트입니다. DBeaver에 넣고 하나씩 실행하며 결과를 확인해 보세요!

### 📊 범주 1. 기본 조회 (4개)
```sql
-- 1. [조회] 15,000원 이상인 도서의 제목과 저자를 가격 내림차순으로 조회
SELECT title, author, price 
FROM book 
WHERE price >= 15000 
ORDER BY price DESC;

-- 2. [조회] 전화번호에 '5555'가 포함된 회원의 ID와 이름을 조회
SELECT login_id, name 
FROM member 
WHERE phone LIKE '%5555%';

-- 3. [조회] 아직 반납되지 않은 대여 기록의 대여번호, 회원ID, 도서ID를 조회 (반납일이 비어있음)
SELECT id, member_id, book_id 
FROM rental 
WHERE return_date IS NULL;

-- 4. [조회] 가장 가격이 높은 책 TOP 3의 제목과 가격을 조회
SELECT title, price 
FROM book 
ORDER BY price DESC 
LIMIT 3;
```

### 🤝 범주 2. 조인 조회 (4개)
```sql
-- 5. [INNER JOIN] 대여 기록과 함께 회원명, 도서명을 결합하여 최근 대여 순으로 조회
SELECT r.id AS 대여번호, m.name AS 회원명, b.title AS 도서명, r.rental_date AS 대여일
FROM rental r
INNER JOIN member m ON r.member_id = m.id
INNER JOIN book b ON r.book_id = b.id
ORDER BY r.rental_date DESC;

-- 6. [INNER JOIN] 특정 회원(예: '홍길동')이 대여하고 반납을 완료한 책 목록과 반납일 조회
SELECT m.name AS 회원명, b.title AS 도서명, r.return_date AS 반납일
FROM rental r
INNER JOIN member m ON r.member_id = m.id
INNER JOIN book b ON r.book_id = b.id
WHERE m.name = '홍길동' AND r.return_date IS NOT NULL;

-- 7. [LEFT JOIN] 전체 회원 목록을 조회하면서 각 회원의 대여 횟수를 결합하여 조회
SELECT m.name AS 회원명, COUNT(r.id) AS 대여건수
FROM member m
LEFT JOIN rental r ON m.id = r.member_id
GROUP BY m.name
ORDER BY 대여건수 DESC;

-- 8. [INNER JOIN] 카테고리별 도서명과 가격 정보 결합 조회
SELECT c.name AS 카테고리, b.title AS 도서명, b.price AS 가격
FROM book b
INNER JOIN category c ON b.category_id = c.id
ORDER BY c.name, b.price DESC;
```

### 📈 범주 3. 집계 및 그룹화 (3개)
```sql
-- 9. [집계] 도서관에 등록된 전체 도서의 총 가격, 평균 가격, 도서 총 개수를 계산
SELECT SUM(price) AS 전체도서총합, AVG(price) AS 평균도서가격, COUNT(id) AS 총도서수 
FROM book;

-- 10. [집계 + GROUP BY] 카테고리별 도서 권수와 평균 도서 가격을 조회 (평균 가격 기준 내림차순)
SELECT c.name AS 카테고리명, COUNT(b.id) AS 도서수, AVG(b.price) AS 평균가격
FROM category c
LEFT JOIN book b ON c.id = b.category_id
GROUP BY c.name
ORDER BY 평균가격 DESC;

-- 11. [집계 + GROUP BY] 현재 대여 중인(미반납) 도서의 총 개수를 회원별로 집계하여 조회
SELECT m.name AS 회원명, COUNT(r.id) AS 미반납건수
FROM rental r
INNER JOIN member m ON r.member_id = m.id
WHERE r.return_date IS NULL
GROUP BY m.name;
```

### 🔄 범주 4. 서브쿼리 (1개 이상)
```sql
-- 12. [서브쿼리] 전체 도서의 평균 가격보다 더 비싼 도서의 제목과 가격을 조회
SELECT title, price 
FROM book 
WHERE price > (SELECT AVG(price) FROM book);
```

### ✏️ 범주 5. 데이터 수정 및 삭제 (2개)
```sql
-- 13. [수정] 박민수 회원이 빌려간 5번 도서에 대해 반납 처리 (반납일을 오늘 날짜로 업데이트)
UPDATE rental 
SET return_date = '2026-06-09' 
WHERE member_id = 4 AND book_id = 5 AND return_date IS NULL;

-- 14. [삭제] 2026년 5월 15일 이전에 반납 완료된 과거의 대여 기록을 영구적으로 삭제
DELETE FROM rental 
WHERE return_date < '2026-05-15';
```

### ⚡ 범주 6. 인덱스 생성 (1개)
```sql
-- 15. [인덱스] 회원들의 아이디(login_id)로 검색하는 연산이 잦으므로 인덱스 생성
-- 적용 이유: 회원 로그인 또는 아이디 중복 검색 시 풀 스캔을 하지 않고 즉시 찾도록 검색 속도를 100배 향상시키기 위함.
CREATE INDEX idx_member_login ON member(login_id);
```

---

## 🎁 보너스 미션 가이드

### ① 조인 1개를 두 방식으로 풀기 (JOIN vs Subquery)
같은 요구사항도 조인을 쓸 때와 서브쿼리를 쓸 때 쿼리의 형태와 작동 효율이 달라집니다.
*   **요구사항**: "홍길동 회원의 대여 기록(대여일, 도서ID)을 모두 뽑아줘"
*   **방식 A (JOIN 사용)**:
    ```sql
    SELECT r.rental_date, r.book_id
    FROM rental r
    INNER JOIN member m ON r.member_id = m.id
    WHERE m.name = '홍길동';
    ```
*   **방식 B (서브쿼리 사용)**:
    ```sql
    SELECT rental_date, book_id
    FROM rental
    WHERE member_id = (SELECT id FROM member WHERE name = '홍길동');
    ```
*   *비교*: 조인은 두 테이블을 물리적으로 합친 후 조건절을 검사하며, 서브쿼리는 먼저 홍길동의 ID가 `1`임을 알아낸 뒤 그 ID만 가지고 검색합니다. 데이터가 아주 많을 때는 상황에 따라 성능 차이가 발생할 수 있습니다.

### ② 데이터 정합성 깨뜨려 보기 (에러 체감)
FK 제약조건이 실제로 어떻게 잘못된 입력을 막아주는지 직접 목격해 봅시다.
*   **시도**: 회원 테이블에 없는 유령 회원 ID인 `99`번 회원이 1번 책을 대여하는 쿼리를 실행해 봅니다.
    ```sql
    INSERT INTO rental (member_id, book_id, rental_date) 
    VALUES (99, 1, '2026-06-09');
    ```
*   **결과**: SQLite에서는 `FOREIGN KEY constraint failed`라는 에러가 발생하며 저장에 실패합니다.
*   **기록 요령**: 보고서에 "외래키 제약조건 덕분에 존재하지 않는 유령 회원의 대여와 같이 잘못된 데이터가 테이블에 쌓이는 것을 시스템 레벨에서 원천 차단해 줌을 확인했다"라고 기록하시면 훌륭한 점수를 받을 수 있습니다!

---

## 📂 최종 제출물 구성 체크리스트

과제를 제출할 때 아래 구조로 파일을 깨끗하게 정리해 보세요. 채점관의 가독성을 배려하는 것이 실력 있는 주니어 백엔드 개발자의 첫걸음입니다!

```text
📁 library-db-mission
 ├── 📄 schema.sql        (CREATE TABLE 및 CREATE INDEX 모음)
 ├── 📄 seed.sql          (INSERT INTO 샘플 데이터 모음)
 ├── 📄 queries.sql       (15개 핵심 쿼리 및 설명 주석)
 └── 📁 captures          (각 쿼리 실행 결과 캡처 이미지 또는 결과 텍스트 파일)
```

축하합니다! 이 가이드를 차근차근 완독하고 예제를 실행해보셨다면, 여러분은 이미 단순 엑셀 정리를 넘어선 **데이터 관계 설계와 SQL 조회 기술**의 기초를 완벽하게 장악하신 것입니다. 이제 다른 초보자에게도 이 개념들을 기분 좋게 설명해 보세요! 🚀

"""
index.py — 역색인(Inverted Index) 모듈
========================================

이 모듈은 커밋 검색을 빠르게 수행하기 위한 역색인(Inverted Index)을 구현합니다.

────────────────────────────────────────────
역색인(Inverted Index)이란?
────────────────────────────────────────────
일반적인 색인(Forward Index)은 "문서 → 키워드 목록"의 매핑입니다.
예: 커밋 a1b2c3 → ["add", "login", "feature"]

역색인은 이를 뒤집어서 "키워드 → 문서 목록"의 매핑입니다.
예: "login" → [a1b2c3, d4e5f6, ...]

────────────────────────────────────────────
왜 역색인을 사용하는가? (시간복잡도 관점)
────────────────────────────────────────────
■ 역색인이 없을 때 (순회 검색, 전수 조사):
  - 모든 커밋을 하나씩 확인해야 합니다.
  - N개 커밋, 각 메시지 평균 길이 M → O(N × M)
  - 커밋이 10만 개라면, 매 검색마다 10만 개를 모두 확인!

■ 역색인이 있을 때:
  - 키워드 조회: O(1) 평균 (dict 해시맵 조회)
  - 결과가 K개이면: O(K)
  - 커밋이 10만 개여도, 검색 결과가 5개면 O(5)!

■ 대가(trade-off):
  - 추가 메모리를 사용합니다 (인덱스 저장 공간).
  - 커밋 추가 시 인덱스 갱신 비용이 있습니다.
  - 이것은 "공간-시간 트레이드오프(space-time trade-off)"의 전형적 예입니다.

────────────────────────────────────────────
실제 세계에서의 역색인
────────────────────────────────────────────
- Google, Naver 등 검색 엔진의 핵심 자료구조입니다.
- Elasticsearch, Apache Lucene 같은 검색 엔진이 역색인을 사용합니다.
- 데이터베이스의 텍스트 인덱스(Full-Text Index)도 역색인의 변형입니다.
"""


class InvertedIndex:
    """
    역색인 클래스.

    두 종류의 인덱스를 관리합니다:
    1. keyword_index: 키워드 → 커밋 해시 집합
    2. author_index:  작성자 → 커밋 해시 집합

    ── 왜 set을 사용하는가? ──
    - 같은 커밋이 중복 등록되는 것을 자동으로 방지합니다.
    - 'in' 연산이 O(1) 평균입니다 (리스트는 O(n)).
    - 합집합(|), 교집합(&) 같은 집합 연산이 가능합니다.

    Attributes:
        keyword_index (dict): {키워드(str): {커밋 해시(str), ...}}
        author_index (dict):  {작성자(str): {커밋 해시(str), ...}}
    """

    def __init__(self):
        """
        빈 역색인을 생성합니다.
        두 인덱스 모두 빈 딕셔너리로 시작합니다.
        """
        # ── 키워드 역색인 ──
        # 예: {"add": {"a1b2c3", "d4e5f6"}, "login": {"d4e5f6"}}
        self.keyword_index = {}

        # ── 작성자 역색인 ──
        # 예: {"alice": {"a1b2c3", "d4e5f6", "g7h8i9"}}
        self.author_index = {}

    def add_commit(self, commit):
        """
        새 커밋을 역색인에 등록합니다.

        ── 토큰화(Tokenization) 과정 ──
        1. 커밋 메시지를 공백 기준으로 분리(split)합니다.
           예: "Add login feature" → ["Add", "login", "feature"]
        2. 각 토큰을 소문자로 변환(lower)합니다.
           예: ["Add", "login", "feature"] → ["add", "login", "feature"]
        3. 각 토큰을 keyword_index에 등록합니다.

        ── 왜 소문자로 정규화하는가? ──
        대소문자를 구분하지 않는 검색을 위해서입니다.
        "Add"로 커밋했더라도 "add"로 검색할 수 있어야 합니다.
        이것을 정규화(normalization)라고 합니다.

        Args:
            commit (Commit): 역색인에 추가할 커밋 객체
        """
        # ── 1. 키워드 인덱스 갱신 ──

        # Step 1-1: 메시지를 공백 기준으로 분리합니다.
        # split()은 인자 없이 호출하면 연속 공백도 하나로 처리합니다.
        # 예: "  Add   login  " → ["Add", "login"]
        tokens = commit.message.split()

        # Step 1-2: 각 토큰을 소문자로 정규화하고 인덱스에 추가합니다.
        for token in tokens:
            # 소문자로 변환
            keyword = token.lower()

            # ── dict에 키가 없으면 빈 set을 먼저 생성 ──
            # 이 패턴은 Python에서 매우 자주 사용됩니다.
            # "defaultdict"를 쓸 수도 있지만, 명시적으로 작성합니다.
            if keyword not in self.keyword_index:
                self.keyword_index[keyword] = set()

            # 커밋 해시를 해당 키워드의 집합에 추가합니다.
            # set이므로 같은 해시가 이미 있으면 무시됩니다.
            self.keyword_index[keyword].add(commit.hash)

        # ── 2. 작성자 인덱스 갱신 ──

        # 작성자 이름도 소문자로 정규화합니다.
        # 검색 시에도 소문자로 비교하므로 일관성을 유지합니다.
        author_key = commit.author.lower()

        if author_key not in self.author_index:
            self.author_index[author_key] = set()

        self.author_index[author_key].add(commit.hash)

    def search_keyword(self, keyword):
        """
        키워드로 커밋을 검색합니다.

        ── 시간복잡도 ──
        - dict 조회: O(1) 평균
        - 결과 복사: O(K), K = 해당 키워드를 포함하는 커밋 수

        Args:
            keyword (str): 검색할 키워드 (예: "login")

        Returns:
            set: 해당 키워드를 포함하는 커밋 해시들의 집합
                 키워드가 인덱스에 없으면 빈 집합 반환
        """
        # 검색 키워드도 소문자로 정규화하여 대소문자 무관 검색을 수행합니다.
        # .get()은 키가 없으면 두 번째 인자(기본값)를 반환합니다.
        # 여기서는 빈 set()을 반환합니다.
        return self.keyword_index.get(keyword.lower(), set())

    def search_author(self, author):
        """
        작성자 이름으로 커밋을 검색합니다.

        ── 시간복잡도 ──
        - dict 조회: O(1) 평균
        - 결과 복사: O(K), K = 해당 작성자의 커밋 수

        Args:
            author (str): 검색할 작성자 이름 (예: "Alice")

        Returns:
            set: 해당 작성자의 커밋 해시들의 집합
                 작성자가 인덱스에 없으면 빈 집합 반환
        """
        return self.author_index.get(author.lower(), set())

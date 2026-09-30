"""
models.py — Mini Git 핵심 데이터 모델
=====================================

이 모듈은 Mini Git의 두 가지 핵심 클래스를 정의합니다:

1. Commit  — 하나의 커밋을 표현하는 노드 (DAG의 정점)
2. Repository — 저장소 전체 상태를 관리하는 컨트롤러

────────────────────────────────────────────
왜 DAG(Directed Acyclic Graph)인가?
────────────────────────────────────────────
Git의 커밋 그래프는 DAG입니다.
- "방향성(Directed)":  각 커밋은 자신의 부모(parent)를 가리킵니다.
                       즉, 간선의 방향이 자식 → 부모입니다.
- "비순환(Acyclic)":   커밋 A → B → C → A 같은 순환이 불가능합니다.
                       왜냐하면 커밋은 항상 이미 존재하는 커밋만 부모로 가질 수 있기 때문입니다.
                       미래의 커밋을 부모로 지정할 수 없으므로, 순환이 구조적으로 불가능합니다.

이 구조 덕분에:
- 위상 정렬(topological sort)이 가능하고,
- 두 커밋의 공통 조상(merge-base)을 찾을 수 있으며,
- rebase, cherry-pick 같은 고급 연산의 기반이 됩니다.

────────────────────────────────────────────
해시(Hash)의 역할
────────────────────────────────────────────
실제 Git은 커밋 내용(트리, 부모, 작성자, 메시지 등)을
SHA-1으로 해싱하여 40자리 hex 문자열을 만듭니다.
이 해시가 커밋의 고유 식별자(ID)가 됩니다.

우리 Mini Git도 동일한 원리를 사용하되,
가독성을 위해 앞 6자리만 사용합니다.
만약 6자리가 충돌(collision)하면, 내부 카운터를 붙여 유일성을 보장합니다.
"""

import hashlib  # SHA-1 해시 생성을 위한 파이썬 표준 라이브러리
import time     # 커밋 타임스탬프(시간 기록)를 위한 표준 라이브러리

# ──────────────────────────────────────────────────────────────────────
# 역색인 모듈을 임포트합니다.
# 커밋이 생성될 때마다 역색인(inverted index)을 갱신해야 하므로,
# Repository 클래스가 InvertedIndex를 내부적으로 사용합니다.
# ──────────────────────────────────────────────────────────────────────
from index import InvertedIndex


class Commit:
    """
    커밋 노드를 표현하는 클래스.

    실제 Git에서 하나의 커밋 객체는 다음 정보를 담고 있습니다:
    - tree:    해당 시점의 파일 상태 스냅샷 (우리는 파일 추적을 하지 않으므로 생략)
    - parent:  이전 커밋(들)의 해시 (0개: 최초 커밋, 1개: 일반 커밋, 2개: 머지 커밋)
    - author:  작성자 이름
    - message: 커밋 메시지
    - timestamp: 커밋 시간

    이 클래스는 위의 정보 중 우리에게 필요한 것만 구현합니다.

    Attributes:
        hash (str):        커밋의 고유 식별자 (SHA-1 앞 6자리 hex)
        message (str):     커밋 메시지 (예: "Add login feature")
        author (str):      작성자 이름 (예: "Alice")
        timestamp (float): 커밋 생성 시각 (Unix timestamp, time.time() 값)
        parents (list):    부모 커밋의 해시 리스트
                           - 빈 리스트 []: 최초 커밋 (root commit)
                           - ["abc123"]: 일반 커밋
                           - ["abc123", "def456"]: 머지 커밋 (보너스)
    """

    def __init__(self, message, author, timestamp, parents=None):
        """
        Commit 객체를 생성합니다.

        Args:
            message (str):     커밋 메시지
            author (str):      작성자 이름
            timestamp (float): Unix timestamp (time.time()으로 생성)
            parents (list):    부모 커밋 해시 리스트 (기본값: None → 빈 리스트)

        ── 내부 동작 ──
        1. parents가 None이면 빈 리스트로 초기화합니다.
        2. _generate_hash() 메서드를 호출하여 해시를 생성합니다.
        """
        # ── 부모 커밋 리스트 초기화 ──
        # Python에서 기본 인자로 가변 객체(list)를 쓰면 위험합니다.
        # 모든 인스턴스가 같은 리스트 객체를 공유하게 되기 때문입니다.
        # 그래서 None을 기본값으로 쓰고, None이면 새 리스트를 만듭니다.
        # 이것은 Python의 관용적 패턴(idiom)입니다.
        self.parents = parents if parents is not None else []

        self.message = message      # 커밋 메시지 저장
        self.author = author        # 작성자 이름 저장
        self.timestamp = timestamp  # Unix 타임스탬프 저장

        # ── 해시 생성 ──
        # 커밋 내용을 기반으로 SHA-1 해시의 앞 6자리를 생성합니다.
        # 이 해시는 나중에 Repository에서 충돌 검사를 거쳐 최종 확정됩니다.
        self.hash = self._generate_hash()

    def _generate_hash(self):
        """
        SHA-1 해시를 생성하여 앞 6자리 hex 문자열을 반환합니다.

        ── 해시 생성 원리 ──
        1. 커밋의 고유 정보(메시지, 작성자, 타임스탬프, 부모 해시들)를
           하나의 문자열로 결합합니다.
        2. 이 문자열을 UTF-8 바이트로 인코딩합니다.
        3. hashlib.sha1()으로 SHA-1 해시를 계산합니다.
        4. hexdigest()로 40자리 hex 문자열을 얻습니다.
        5. 앞 6자리만 잘라서 반환합니다.

        ── 왜 SHA-1인가? ──
        실제 Git이 SHA-1을 사용합니다 (최근에는 SHA-256으로 전환 중).
        SHA-1은 입력이 1비트만 달라도 완전히 다른 해시를 생성하므로,
        서로 다른 커밋은 거의 확실하게 다른 해시를 갖습니다.

        Returns:
            str: 6자리 hex 문자열 (예: "a1b2c3")
        """
        # ── Step 1: 해시 입력 문자열 구성 ──
        # 부모 해시들을 쉼표로 결합하여 하나의 문자열로 만듭니다.
        # 부모가 없으면(최초 커밋) 빈 문자열이 됩니다.
        parent_str = ",".join(self.parents)

        # 모든 커밋 정보를 파이프(|)로 구분하여 하나의 문자열로 결합합니다.
        # 이 문자열이 해시 함수의 입력이 됩니다.
        content = f"{self.message}|{self.author}|{self.timestamp}|{parent_str}"

        # ── Step 2: SHA-1 해시 계산 ──
        # .encode('utf-8'): 문자열을 바이트로 변환 (해시 함수는 바이트를 입력으로 받음)
        # hashlib.sha1():   SHA-1 해시 객체 생성
        # .hexdigest():     해시 값을 40자리 hex 문자열로 변환
        # [:6]:             앞 6자리만 사용 (가독성을 위해)
        return hashlib.sha1(content.encode('utf-8')).hexdigest()[:6]

    def __repr__(self):
        """
        Commit 객체의 문자열 표현을 반환합니다.
        디버깅할 때 print(commit)으로 쉽게 내용을 확인할 수 있습니다.

        Returns:
            str: "Commit(hash=a1b2c3, message='Initial commit')" 형태의 문자열
        """
        return f"Commit(hash={self.hash}, message='{self.message}')"


class Repository:
    """
    Mini Git 저장소 전체 상태를 관리하는 클래스.

    실제 Git 저장소의 .git/ 디렉토리에 해당하는 역할을 합니다.
    다음 정보를 관리합니다:

    1. 모든 커밋 객체 (해시맵으로 빠른 조회)
    2. 브랜치 목록과 각 브랜치가 가리키는 커밋
    3. HEAD (현재 작업 중인 브랜치)
    4. 현재 사용자 정보
    5. 역색인 (키워드/작성자 기반 검색)

    ── Git에서 HEAD란? ──
    HEAD는 "현재 체크아웃된 브랜치"를 가리키는 특수 포인터입니다.
    실제 Git에서는 .git/HEAD 파일에 "ref: refs/heads/main" 같은 내용이 들어있습니다.
    우리 구현에서는 단순히 브랜치 이름을 문자열로 저장합니다.

    ── Git에서 브랜치란? ──
    브랜치는 "특정 커밋을 가리키는 이동 가능한 포인터"입니다.
    실제 Git에서는 .git/refs/heads/main 파일에 커밋 해시 40자리가 들어있습니다.
    새 커밋을 만들면, 현재 브랜치의 포인터가 새 커밋으로 이동합니다.

    Attributes:
        commits (dict):           해시 → Commit 객체 매핑 (해시맵)
        branches (dict):          브랜치명 → 커밋 해시 매핑
        head (str or None):       현재 활성 브랜치명 (없으면 None)
        current_user (str or None): 현재 사용자명 (없으면 None)
        inverted_index (InvertedIndex): 역색인 객체 (키워드/작성자 검색용)
        initialized (bool):      저장소 초기화 여부
        _hash_set (set):          생성된 해시 목록 (충돌 방지용)
        _hash_counter (int):      해시 충돌 시 사용하는 카운터
    """

    def __init__(self):
        """
        Repository 객체를 생성합니다.
        이 시점에서는 아직 초기화(init)되지 않은 빈 상태입니다.
        init() 메서드를 호출해야 실제 사용이 가능합니다.
        """
        # ── 커밋 저장소 (해시맵) ──
        # dict를 사용하여 O(1) 평균 시간에 커밋을 조회할 수 있습니다.
        # key: 커밋 해시 (str), value: Commit 객체
        self.commits = {}

        # ── 브랜치 목록 ──
        # key: 브랜치 이름 (str), value: 해당 브랜치가 가리키는 커밋 해시 (str)
        self.branches = {}

        # ── HEAD 포인터 ──
        # 현재 활성 브랜치의 이름을 저장합니다.
        self.head = None

        # ── 현재 사용자 ──
        self.current_user = None

        # ── 역색인 ──
        # 커밋이 생성될 때마다 자동으로 갱신됩니다.
        self.inverted_index = InvertedIndex()

        # ── 초기화 플래그 ──
        # init() 호출 전에 다른 명령어를 쓰려 하면 에러를 내기 위한 플래그입니다.
        self.initialized = False

        # ── 해시 충돌 방지 도구 ──
        # _hash_set: 이미 사용된 모든 해시를 저장합니다.
        # _hash_counter: 충돌 시 해시 재생성에 사용하는 카운터입니다.
        self._hash_set = set()
        self._hash_counter = 0

    def _ensure_unique_hash(self, commit):
        """
        커밋 해시의 유일성을 보장합니다.

        SHA-1의 앞 6자리만 사용하므로 충돌 가능성이 있습니다.
        (6자리 hex = 16^6 = 약 1677만 가지)

        충돌이 발생하면:
        1. 내부 카운터를 증가시킵니다.
        2. 원본 내용 + 카운터를 결합하여 새 해시를 생성합니다.
        3. 유일한 해시를 찾을 때까지 반복합니다.

        Args:
            commit (Commit): 해시 유일성을 확인할 커밋 객체

        Side Effects:
            commit.hash가 유일한 값으로 변경될 수 있습니다.
        """
        # 현재 해시가 이미 사용 중인지 확인합니다.
        while commit.hash in self._hash_set:
            # ── 충돌 발생! 새 해시를 생성합니다 ──
            self._hash_counter += 1  # 카운터 증가

            # 원본 커밋 정보에 카운터를 추가하여 새로운 해시를 만듭니다.
            # 카운터가 다르면 해시도 (거의 확실하게) 달라집니다.
            content = (f"{commit.message}|{commit.author}|"
                       f"{commit.timestamp}|{self._hash_counter}")
            commit.hash = hashlib.sha1(
                content.encode('utf-8')
            ).hexdigest()[:6]

        # 유일한 해시를 찾았으므로 세트에 등록합니다.
        self._hash_set.add(commit.hash)

    def init(self, user_name):
        """
        저장소를 초기화합니다.

        실제 Git의 `git init` 명령어에 해당합니다.
        다음을 수행합니다:
        1. main 브랜치를 생성합니다.
        2. HEAD를 main으로 설정합니다.
        3. 현재 사용자를 설정합니다.
        4. 초기화 플래그를 True로 설정합니다.

        ── 주의: main 브랜치의 초기 커밋 ──
        실제 Git에서는 init 직후에는 커밋이 없고,
        첫 커밋을 해야 main 브랜치가 실제로 커밋을 가리킵니다.
        우리 구현에서도 main 브랜치는 초기에 None(커밋 없음)을 가리킵니다.

        Args:
            user_name (str): 사용자 이름 (예: "Alice")

        Returns:
            str: 초기화 결과 메시지
        """
        # ── 기존 데이터 초기화 (재초기화 대비) ──
        self.commits = {}
        self.branches = {}
        self._hash_set = set()
        self._hash_counter = 0
        self.inverted_index = InvertedIndex()

        # ── main 브랜치 생성 ──
        # None은 "아직 커밋이 없음"을 의미합니다.
        self.branches["main"] = None

        # ── HEAD와 사용자 설정 ──
        self.head = "main"
        self.current_user = user_name
        self.initialized = True

        # ── 결과 메시지 반환 ──
        return (f"Initialized repository.\n"
                f"Current branch: main\n"
                f"Current user: {user_name}")

    def commit(self, message):
        """
        새 커밋을 생성합니다.

        실제 Git의 `git commit -m "message"` 명령어에 해당합니다.

        ── 커밋 생성 과정 ──
        1. 현재 HEAD가 가리키는 커밋을 부모로 설정합니다.
        2. Commit 객체를 생성합니다 (SHA-1 해시 자동 생성).
        3. 해시 유일성을 확인/보장합니다.
        4. 커밋을 저장소(해시맵)에 추가합니다.
        5. 현재 브랜치의 포인터를 새 커밋으로 이동합니다.
        6. 역색인을 갱신합니다.

        Args:
            message (str): 커밋 메시지 (예: "Add login feature")

        Returns:
            str: 커밋 생성 결과 메시지 또는 에러 메시지
        """
        # ── 초기화 확인 ──
        if not self.initialized:
            return "Error: Repository not initialized. Use INIT first."

        # ── 부모 커밋 결정 ──
        # 현재 HEAD 브랜치가 가리키는 커밋이 부모가 됩니다.
        # 브랜치가 아직 커밋을 가리키지 않으면(첫 커밋) 부모는 없습니다.
        current_commit_hash = self.branches[self.head]
        parents = [current_commit_hash] if current_commit_hash else []

        # ── Commit 객체 생성 ──
        timestamp = time.time()  # 현재 시각을 Unix timestamp로 기록
        new_commit = Commit(
            message=message,
            author=self.current_user,
            timestamp=timestamp,
            parents=parents
        )

        # ── 해시 유일성 보장 ──
        self._ensure_unique_hash(new_commit)

        # ── 저장소에 커밋 추가 ──
        # dict에 추가 → O(1) 평균 시간
        self.commits[new_commit.hash] = new_commit

        # ── 브랜치 포인터 이동 ──
        # 현재 브랜치가 새 커밋을 가리키도록 업데이트합니다.
        # 이것이 "브랜치는 이동하는 포인터"라는 Git의 핵심 개념입니다.
        self.branches[self.head] = new_commit.hash

        # ── 역색인 갱신 ──
        # 새 커밋의 메시지 키워드와 작성자를 역색인에 등록합니다.
        self.inverted_index.add_commit(new_commit)

        # ── 결과 메시지 반환 ──
        return f"[{self.head} {new_commit.hash}] {message}"

    def branch(self, branch_name):
        """
        새 브랜치를 생성합니다.

        실제 Git의 `git branch <name>` 명령어에 해당합니다.

        ── 브랜치 생성의 본질 ──
        브랜치는 단순히 "특정 커밋의 해시를 가리키는 포인터"입니다.
        새 브랜치를 만들면, 현재 HEAD가 가리키는 커밋과 동일한 커밋을 가리킵니다.
        실제 Git에서 브랜치 생성은 파일 하나를 만드는 것과 같으므로 매우 가볍습니다.

        Args:
            branch_name (str): 새 브랜치 이름 (예: "feature")

        Returns:
            str: 브랜치 생성 결과 메시지 또는 에러 메시지
        """
        # ── 초기화 확인 ──
        if not self.initialized:
            return "Error: Repository not initialized. Use INIT first."

        # ── 중복 브랜치 확인 ──
        if branch_name in self.branches:
            return f"Error: Branch '{branch_name}' already exists."

        # ── 브랜치 생성 ──
        # 현재 HEAD 브랜치가 가리키는 커밋과 동일한 커밋을 가리킵니다.
        self.branches[branch_name] = self.branches[self.head]

        return f"Created branch: {branch_name}"

    def switch(self, branch_name):
        """
        다른 브랜치로 전환합니다.

        실제 Git의 `git switch <name>` (또는 `git checkout <name>`)에 해당합니다.

        ── 전환의 본질 ──
        HEAD 포인터가 가리키는 브랜치 이름만 변경합니다.
        실제 Git에서는 작업 디렉토리의 파일도 바뀌지만,
        우리는 파일 추적을 하지 않으므로 HEAD만 변경합니다.

        Args:
            branch_name (str): 전환할 브랜치 이름 (예: "feature")

        Returns:
            str: 전환 결과 메시지 또는 에러 메시지
        """
        # ── 초기화 확인 ──
        if not self.initialized:
            return "Error: Repository not initialized. Use INIT first."

        # ── 브랜치 존재 여부 확인 ──
        if branch_name not in self.branches:
            return f"Unknown branch: {branch_name}"

        # ── HEAD 이동 ──
        self.head = branch_name
        return f"Switched to branch: {branch_name}"

    def merge(self, branch_name):
        """
        [보너스 5.2] 지정된 브랜치를 현재 브랜치로 머지합니다.

        ── 머지(Merge)란? ──
        두 갈래로 나뉘었던 작업을 하나로 합치는 것입니다.
        머지 커밋은 부모가 2개입니다:
        - 부모 1: 현재 브랜치(HEAD)의 최신 커밋
        - 부모 2: 대상 브랜치의 최신 커밋

        이것이 DAG에서 "여러 부모를 가진 노드"가 생기는 이유입니다.

        ── 우리 구현의 제한 ──
        실제 Git 머지는 파일 내용을 합치고 충돌을 해결하지만,
        우리는 파일 추적을 하지 않으므로 "머지 커밋 생성"만 합니다.

        Args:
            branch_name (str): 머지할 대상 브랜치 이름

        Returns:
            str: 머지 결과 메시지 또는 에러 메시지
        """
        # ── 초기화 확인 ──
        if not self.initialized:
            return "Error: Repository not initialized. Use INIT first."

        # ── 대상 브랜치 존재 여부 확인 ──
        if branch_name not in self.branches:
            return f"Unknown branch: {branch_name}"

        # ── 자기 자신 머지 방지 ──
        if branch_name == self.head:
            return "Error: Cannot merge a branch into itself."

        # ── 머지할 두 커밋 확인 ──
        current_hash = self.branches[self.head]
        target_hash = self.branches[branch_name]

        # 둘 중 하나라도 커밋이 없으면 머지 불가
        if current_hash is None or target_hash is None:
            return "Error: Cannot merge branches without commits."

        # 같은 커밋을 가리키고 있으면 이미 합쳐진 상태
        if current_hash == target_hash:
            return "Already up to date."

        # ── 머지 커밋 생성 ──
        # 부모가 2개인 커밋을 만듭니다.
        # 이것이 DAG에서 "두 경로가 만나는 지점"입니다.
        merge_message = f"Merge branch '{branch_name}' into {self.head}"
        timestamp = time.time()
        merge_commit = Commit(
            message=merge_message,
            author=self.current_user,
            timestamp=timestamp,
            parents=[current_hash, target_hash]  # 부모가 2개!
        )

        # ── 해시 유일성 보장 & 저장소 추가 ──
        self._ensure_unique_hash(merge_commit)
        self.commits[merge_commit.hash] = merge_commit

        # ── 현재 브랜치 포인터를 머지 커밋으로 이동 ──
        self.branches[self.head] = merge_commit.hash

        # ── 역색인 갱신 ──
        self.inverted_index.add_commit(merge_commit)

        return (f"Merged '{branch_name}' into '{self.head}'.\n"
                f"[{self.head} {merge_commit.hash}] {merge_message}")

    def get_head_commit_hash(self):
        """
        현재 HEAD가 가리키는 커밋의 해시를 반환합니다.

        Returns:
            str or None: 현재 커밋 해시 (커밋이 없으면 None)
        """
        if not self.initialized or self.head is None:
            return None
        return self.branches.get(self.head)

    def get_all_commits(self):
        """
        저장소의 모든 커밋을 딕셔너리로 반환합니다.

        Returns:
            dict: {해시: Commit 객체} 형태의 딕셔너리
        """
        return self.commits

    def get_commit(self, commit_hash):
        """
        해시로 특정 커밋을 조회합니다.

        ── 시간복잡도: O(1) 평균 ──
        dict(해시맵) 기반이므로 평균적으로 상수 시간에 조회됩니다.

        Args:
            commit_hash (str): 조회할 커밋 해시

        Returns:
            Commit or None: 해당 커밋 객체 (없으면 None)
        """
        return self.commits.get(commit_hash)

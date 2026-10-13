# 📚 [Mini Git] 극한 상세 학습 가이드: 일타 강사와 함께하는 CS 딥다이브

안녕하세요! 여러분의 컴퓨터 공학 멘토, 일타 강사입니다. 
오늘은 우리가 그동안 그저 "명령어만 외워서" 썼던 Git이, 실제로는 얼마나 아름답고 경이로운 컴퓨터 공학의 결정체인지 바닥부터 파헤쳐 볼 겁니다. 

초심자 친구에게 설명할 때 "Git은 버전 관리 시스템이야~"라고 앵무새처럼 말하는 대신, **"Git은 사실 은행의 조작 불가능한 장부이자, 블록체인의 시조새 같은 거야!"**라고 자신 있게 말할 수 있도록 만들어 드리겠습니다. 

자, 본격적인 여행에 앞서 우리가 밟고 지나갈 전체 로드맵을 먼저 살펴볼까요?

---

## 🗺️ 전체 로드맵 (목차)

**Phase 1: "절대 조작할 수 없는 은행 장부" — Git의 철학과 핵심 구조 (현재 챕터)**
1. **[Why]** 위조 불가능한 은행 장부와 블록체인: Git은 왜 이렇게 생겨먹었나?
2. **[Concept]** 해시(Hash)와 SHA-1: 디지털 지문은 어떻게 역사를 보호하는가?
3. **[Concept]** DAG (방향성 비순환 그래프): 타임 패러독스를 막는 시간의 화살
4. **[Code]** `minigit/models.py` 한 줄 한 줄 해부하기 (Repository와 Commit)

**Phase 2: "수만 권의 장부를 0.1초 만에 뒤지는 법" — 검색 엔진과 그래프 탐색** *(다음 챕터)*
1. **[Concept]** 역색인(Inverted Index): 구글 검색 엔진이 내 PC로 들어왔다
2. **[Code]** `minigit/index.py` 해부: 키워드와 작성자로 커밋을 낚아채기
3. **[Concept]** BFS와 DFS: 미로 찾기로 배우는 최단 경로와 조상 추적
4. **[Code]** `minigit/graph.py` 해부: 시간 여행의 궤적을 쫓다

**Phase 3: "혼돈의 우주를 정렬하고 합치다" — 정렬과 알고리즘의 꽃** *(마지막 챕터)*
1. **[Concept]** 위상 정렬(Kahn's Algorithm): 인과율에 따른 우주 시간표 세우기
2. **[Concept]** LCS (Longest Common Subsequence): 두 장부의 차이점(Diff)을 귀신같이 찾아내는 마법
3. **[Code]** `minigit/diff.py` & `minigit/sorting.py` 해부

---

## Phase 1: "절대 조작할 수 없는 은행 장부" — Git의 철학과 핵심 구조

### 1. [Why] 위조 불가능한 은행 장부와 블록체인
상상해 봅시다. 당신이 전 세계의 모든 돈이 오가는 중앙 은행의 수석 장부 관리자입니다. 
이 장부에는 치명적인 규칙이 하나 있습니다. **"한 번 적힌 내용은 수정 테이프로 지울 수 없다."**
누군가 "A가 B에게 100만 원을 보냈다"라는 기록을 몰래 "10만 원"으로 고친다면 은행의 신뢰는 붕괴될 것입니다.

그렇다면 당신은 과거의 기록이 조작되지 않았음을 어떻게 증명할 수 있을까요?
가장 천재적인 방법은, **'다음 페이지를 적을 때, 이전 페이지의 전체 내용(요약본)을 도장처럼 찍어버리는 것'**입니다. 
만약 누군가 몰래 과거의 10페이지를 조작했다면? 11페이지에 찍혀 있는 '10페이지의 도장'과 모양이 달라지기 때문에 즉시 발각됩니다. 10페이지를 조작하려면 11페이지도 조작해야 하고, 12, 13, 14페이지까지 연쇄적으로 전부 위조해야만 합니다. 사실상 조작이 불가능해지는 것이죠.

이것이 바로 비트코인을 비롯한 **블록체인(Blockchain)의 핵심 원리**이며, 리누스 토르발스(Linus Torvalds)가 2005년에 **Git을 설계할 때 사용한 근본 철학**입니다! Git의 `Commit`은 장부의 한 페이지이고, 각 페이지는 부모 페이지의 '도장'을 품고 있습니다.

### 2. [Concept] 해시(Hash)와 SHA-1: 디지털 지문
앞서 말한 '도장'을 컴퓨터 공학에서는 **해시(Hash)**라고 부릅니다.
해시 함수는 아무리 긴 글이든, 짧은 글이든 집어넣기만 하면 항상 고정된 길이의 무작위 같은 문자열을 뱉어냅니다. (우리의 `Mini Git`은 원본 Git처럼 SHA-1 해시를 사용합니다.)

- 입력: "Add login feature" 
- 출력: `d4e5f6` (해시의 앞 6자리만 쓴다고 가정해 보죠)

> 💡 **소크라테스식 문답: "해시를 만들 때 무엇무엇을 넣고 갈아 넣어야 완벽한 지문이 될까요?"**
> 만약 커밋 메시지("Add login feature")만으로 해시를 만든다면? 나중에 누군가 똑같은 메시지로 커밋을 만들면 해시가 중복될 것입니다. 
> 그래서 우리는 **1) 커밋 메시지, 2) 작성자, 3) 타임스탬프(초 단위 시간), 4) 부모 커밋의 해시** 이 4가지를 모두 믹서기에 넣고 돌립니다. 단 1초라도 시간이 다르거나, 작성자가 다르면 완전히 다른 해시가 탄생하죠.

### 3. [Concept] DAG (방향성 비순환 그래프): 시간의 화살
이제 장부 페이지들이 어떻게 연결되는지 볼까요?
Git의 히스토리는 단순한 일직선(List)이 아닙니다. 여러 명이 동시에 작업하면 장부는 여러 갈래로 뻗어나가고(Branch), 나중에 하나로 합쳐집니다(Merge).
이런 구조를 **그래프(Graph)**라고 부릅니다. 그중에서도 아주 특별한 형태인 **DAG(Directed Acyclic Graph)**입니다.

- **Directed (방향성)**: 자식 커밋이 부모 커밋을 가리킵니다. (과거를 향해 화살표가 뻗음)
- **Acyclic (비순환)**: 꼬리에 꼬리를 물고 돌아서 다시 자기 자신으로 돌아오는 뱅뱅 도는 길(Cycle)이 없습니다.

> 💡 **소크라테스식 문답: "왜 Cycle(순환)이 발생하면 안 될까요?"**
> 시간을 거슬러 올라가는 타임 패러독스를 상상해 보세요. 커밋 C의 부모가 B이고, B의 부모가 A인데, A의 부모가 미래의 커밋 C가 될 수 있을까요? **불가능합니다.** 새로운 커밋을 만들 때는 오직 '이미 존재하는 과거의 커밋'만을 부모로 삼을 수 있기 때문에, 구조적으로 영원히 Cycle이 생길 수 없습니다. 이것이 바로 Git이 DAG 구조일 수밖에 없는 이유입니다.

---

### 4. [Code] `minigit/models.py` 한 줄 한 줄 해부하기

이제 이론으로 무장했으니, 우리가 짠 `minigit/models.py` 코드가 얼마나 완벽하게 이 철학을 구현하고 있는지 해부해 봅시다.

#### 🔎 `Commit` 클래스 해부
```python
class Commit:
    def __init__(self, message: str, author: str, timestamp: float, parents: Optional[List[str]] = None) -> None:
        if parents is not None:
            self.parents: List[str] = parents
        else:
            self.parents: List[str] = []

        self.message: str = message
        self.author: str = author
        self.timestamp: float = timestamp
        self.hash: str = self._generate_hash() # 객체가 생성될 때 운명의 지문이 찍힙니다!
```
- **해석**: 장부의 한 페이지(`Commit`)를 만드는 생성자입니다. 위에서 이야기한 4가지 요소(부모, 메시지, 작성자, 시간)를 고스란히 가지고 있습니다. 그리고 마지막 순간에 `_generate_hash()`를 호출하여 자기 자신의 이름을 스스로 결정합니다.

```python
    def _generate_hash(self) -> str:
        parent_str: str = ",".join(self.parents)
        content: str = f"{self.message}|{self.author}|{self.timestamp}|{parent_str}"
        return hashlib.sha1(content.encode('utf-8')).hexdigest()[:6]
```
- **해석**: 대망의 해시 생성 함수입니다! `content` 문자열을 조립하는 부분을 보세요. 메시지, 작성자, 시간, 그리고 **부모의 해시(`parent_str`)**를 `|` 기호로 이어 붙였습니다. 
- **🔥 일타 강사의 핵심 포인트**: 부모의 해시가 현재 커밋의 해시 생성에 재료로 쓰인다는 것, 이것이 바로 **블록체인의 연결고리**입니다! 만약 누군가 과거의 커밋을 몰래 수정하면, 그 과거 커밋의 해시가 변하게 됩니다. 그러면 그 커밋을 부모로 삼던 모든 자식 커밋들의 해시까지 도미노처럼 변해야 합니다. 이 단 두 줄의 코드가 바로 **'역사 조작을 방지하는 방어벽'**입니다.

#### 🔎 `Repository` 클래스 해부
`Commit`이 장부의 한 페이지라면, `Repository`는 장부 그 자체와 책갈피들을 관리하는 도서관장입니다.

```python
class Repository:
    def __init__(self) -> None:
        self.commits: Dict[str, Commit] = {} # 해시맵: 0.1초 만에 커밋을 찾기 위한 마법 주머니
        self.branches: Dict[str, Optional[str]] = {} # 책갈피: 브랜치 이름 -> 커밋 해시
        self.head: Optional[str] = None # 내가 지금 보고 있는 책갈피
        # ... (생략)
```
- **해석**: `commits`는 파이썬의 딕셔너리(`Dict`)를 사용합니다. 컴퓨터 공학에서는 이를 **해시맵(HashMap)**이라고 부릅니다. 나중에 수십만 개의 커밋이 쌓여도, 해시값만 알면 단번에 `O(1)`의 속도로 커밋 객체를 꺼내올 수 있습니다.
- `branches`는 단지 **'특정 커밋의 해시값을 적어둔 가벼운 포스트잇(책갈피)'**에 불과합니다. 초보자들이 "브랜치를 새로 파면 폴더가 통째로 복사되나요?"라고 묻곤 하는데, 절대 아닙니다! 그저 6자리 문자열(해시)을 가리키는 변수 하나가 추가될 뿐입니다. 그래서 Git의 브랜치 생성이 그토록 번개처럼 빠른 것입니다.

#### 🔎 `commit` 생성의 순간 (데이터 파이프라인 패턴)
새로운 커밋을 등록하는 `Repository.commit()` 메서드를 살펴봅시다. 
우리 코드는 에러를 막기 위해 철저한 **3-Step Data Flow**로 짜여 있습니다.

```python
    def commit(self, message: str) -> str:
        # ── 1. Data Refinement (데이터 정제) ──
        clean_message: str = message.strip()

        # ── 2. Validation (유효성 검사) ──
        if not self.initialized:
            return ErrorMessages.REPO_NOT_INIT
        if not clean_message:
            return ErrorMessages.INVALID_COMMIT
            
        # ── 3. Logic Execution (비즈니스 로직 실행) ──
        current_commit_hash: Optional[str] = None
        if self.head is not None:
            current_commit_hash = self.branches.get(self.head)
            
        parents: List[str] = []
        if current_commit_hash is not None:
            parents.append(current_commit_hash)
            
        timestamp: float = time.time()
        new_commit: Commit = Commit(
            message=clean_message,
            author=self.current_user if self.current_user is not None else "Unknown",
            timestamp=timestamp,
            parents=parents
        )
        
        self._ensure_unique_hash(new_commit)
        self.commits[new_commit.hash] = new_commit
        
        if self.head is not None:
            self.branches[self.head] = new_commit.hash # 현재 브랜치(포스트잇)를 새 커밋으로 옮겨 붙인다!
            
        self.inverted_index.add_commit(new_commit)

        return SystemMessages.COMMIT_SUCCESS.format(...)
```
- **해석**:
  1. 가장 먼저 **정제(Refinement)**와 **검증(Validation)**을 거칩니다. 쓰레기 데이터가 들어오면 장부를 더럽히기 전에 문전 박대합니다.
  2. 현재 내가 속한 브랜치(`self.head`)가 가리키는 커밋을 **새로운 커밋의 부모(`parents`)**로 지정합니다.
  3. `Commit` 객체를 생성하여 지문(해시)을 찍습니다.
  4. 그 커밋을 도서관 주머니(`self.commits`)에 보관합니다.
  5. **가장 중요한 부분**: 현재 브랜치라는 포스트잇을 방금 만든 '새로운 커밋'으로 옮겨 붙입니다. (`self.branches[self.head] = new_commit.hash`)

어떤가요? 그저 `git commit -m "..."` 라고 치면 내부에서 무슨 요술이 일어나는 줄 알았던 분들도, 이제는 "아, 새 페이지 객체를 만들고 브랜치 포스트잇을 거기로 옮겨 붙이는구나!"라고 눈에 그리듯 설명할 수 있을 것입니다.

---

## Phase 2: "수만 권의 장부를 0.1초 만에 뒤지는 법" — 검색 엔진과 그래프 탐색

지난 챕터에서 우리는 절대 조작할 수 없는 견고한 은행 장부(DAG와 해시)를 만들었습니다. 하지만 장부가 10만 권, 100만 권으로 늘어난다면 어떨까요? "결제 버그"라는 단어가 포함된 장부 기록을 찾기 위해 100만 권을 처음부터 끝까지 다 읽어야 할까요?

### 1. [Concept] 역색인(Inverted Index): 도서관의 마법 색인 카드
우리가 두꺼운 전공 서적에서 특정 단어를 찾을 때, 1페이지부터 마지막 페이지까지 전부 읽지 않습니다. 책 맨 뒤에 있는 **'찾아보기(색인, Index)'**를 펴서 단어를 찾은 뒤 곧바로 해당 페이지를 펼치죠. 

이 개념을 컴퓨터 공학에서는 **역색인(Inverted Index)**이라고 부릅니다.
- **일반 색인 (Forward Index)**: 문서 → 단어 목록 (예: 장부 1번에는 "결제", "버그", "수정"이 있다)
- **역색인 (Inverted Index)**: 단어 → 문서 목록 (예: "버그"라는 단어는 장부 1번, 5번, 90번에 있다)

구글(Google)이나 네이버 같은 전 세계의 검색 엔진은 모두 이 '역색인' 자료구조를 심장으로 사용합니다. 아무리 웹사이트가 많아도 단어만 입력하면 빛의 속도로 결과를 가져오는 비결이 바로 이것입니다.

> 💡 **소크라테스식 문답: "그렇다면 왜 모든 데이터베이스는 처음부터 역색인만 쓰지 않을까요?"**
> 세상에 공짜는 없습니다! 역색인은 검색할 때는 빛의 속도(`O(1)`)를 자랑하지만, 치명적인 단점이 있습니다. 바로 **'새로운 장부가 추가될 때마다 색인 카드를 일일이 업데이트해야 한다는 것'**입니다. 게다가 색인 카드를 보관할 거대한 도서관 서랍(메모리 공간)이 추가로 필요합니다. 이를 컴퓨터 공학에서는 **공간-시간 트레이드오프(Space-Time Trade-off)**라고 부릅니다.

### 2. [Code] `minigit/index.py` 한 줄 한 줄 해부하기

이 경이로운 역색인이 코드로는 어떻게 구현되는지 살펴보겠습니다.

#### 🔎 `InvertedIndex` 초기화와 토큰화 로직
```python
class InvertedIndex:
    def __init__(self) -> None:
        self.keyword_index: Dict[str, Set[str]] = {} # {"login": {"a1b2c3", "d4e5f6"}}
        self.author_index: Dict[str, Set[str]] = {}  # {"alice": {"a1b2c3"}}

    def add_commit(self, commit: 'Commit') -> None:
        # ── 1. Data Refinement (데이터 정제) ──
        tokens: List[str] = commit.message.split()
        normalized_tokens: List[str] = []
        for token in tokens:
            normalized_tokens.append(token.lower())
            
        author_key: str = commit.author.lower()
        commit_hash: str = commit.hash
```
- **해석**: 우리는 두 개의 거대한 서랍장(`keyword_index`, `author_index`)을 만들었습니다. 여기서 주목할 점은 값(value)으로 리스트(`List`)가 아닌 집합(`Set`)을 사용했다는 것입니다. 파이썬의 Set은 해시 테이블로 구현되어 있어, 특정 해시가 존재하는지 확인할 때 평균 0.1초(`O(1)`)도 걸리지 않는 놀라운 성능을 발휘합니다.
- 커밋이 추가되면 문장을 공백 기준으로 쪼갭니다(`split`). "Add login feature"는 `["Add", "login", "feature"]`가 되죠. 이를 **토큰화(Tokenization)**라고 부릅니다.
- **🔥 일타 강사의 핵심 포인트**: 그다음 모든 단어를 `lower()`를 사용해 **소문자로 정규화(Normalization)**합니다. 왜 그럴까요? 사용자가 "Login"이라고 대문자로 검색하든 "login"이라고 소문자로 검색하든 똑같은 결과를 보여주기 위해서입니다. 이 사소해 보이는 한 줄이 사용자 경험(UX)을 결정짓습니다.

---

### 3. [Concept] BFS와 DFS: 미로 탐험과 아리아드네의 실타래
단어 검색은 역색인으로 단번에 해결했습니다. 이제 "이 장부에서 저 장부로 가는 **가장 빠른 길(최단 경로)**"이나 "이 장부의 **모든 조상 기록**"을 찾아야 한다면 어떻게 할까요?

우리의 커밋 히스토리는 얽히고설킨 거대한 미로(DAG)와 같습니다. 이 미로를 헤매지 않고 탐험하는 두 가지 절대적인 나침반이 바로 **BFS**와 **DFS**입니다.

- **BFS (너비 우선 탐색, Breadth-First Search)**: 바닥에 물을 쏟았을 때 물이 사방으로 균일하게 퍼져나가는 모습을 상상해 보세요. 출발지에서 한 발짝, 두 발짝 거리에 있는 방들을 차례대로 탐색합니다. **'최단 경로'**를 찾을 때 무조건 BFS를 써야 하는 이유가 바로 이 '균일하게 퍼져나가는 성질' 때문입니다. BFS는 들어온 순서대로 나가는 **큐(Queue, 대기열)**라는 바구니를 사용합니다.
- **DFS (깊이 우선 탐색, Depth-First Search)**: 좁고 깊은 동굴을 탐험할 때, 길이 막힐 때까지 횃불을 들고 끝까지 파고들었다가 막히면 돌아 나오는 방식입니다. 미로의 **'모든 구석구석(조상들)'**을 빠짐없이 탐색할 때 유리합니다. DFS는 나중에 들어온 것이 먼저 나가는 **스택(Stack, 프링글스 통)**을 사용합니다.

### 4. [Code] `minigit/graph.py` 한 줄 한 줄 해부하기

#### 🔎 `find_shortest_path` (BFS) 해부
```python
def find_shortest_path(commits_dict: Dict[str, Commit], hash1: str, hash2: str) -> Optional[List[str]]:
    # ... (인접 리스트 초기화 생략) ...
    visited: Set[str] = set()
    parent_map: Dict[str, str] = {} # "내가 어디서 왔는지"를 기록하는 헨젤과 그레텔의 빵 부스러기
    queue: deque[str] = deque()

    queue.append(clean_hash1)
    visited.add(clean_hash1)
```
- **해석**: BFS를 시작하기 전 준비물입니다. `visited`는 내가 이미 지나온 방귀 뀐 방에 다시 들어가지 않기 위한 메모장입니다. `queue`는 다음에 탐색할 방들의 대기열입니다.
- **🔥 일타 강사의 핵심 포인트**: `parent_map`을 주목하세요! BFS는 목적지를 발견하고 나면 탐색을 즉시 멈춥니다. 하지만 "어떤 경로로 여기까지 왔지?"를 알려면 뒤로 되돌아가야(Backtrack) 합니다. 새로운 방에 들어올 때마다 "난 A방에서 이쪽으로 넘어왔어"라고 부모를 기록해 두는 것이 `parent_map`의 역할입니다.

```python
    while queue:
        current: str = queue.popleft()
        if current == clean_hash2:
            found = True
            break

        neighbors: List[str] = adjacency.get(current, [])
        sorted_neighbors: List[str] = _insertion_sort_strings(neighbors)

        for neighbor in sorted_neighbors:
            if neighbor not in visited:
                visited.add(neighbor)
                parent_map[neighbor] = current
                queue.append(neighbor)
```
- **해석**: `popleft()`로 큐의 가장 앞에 있는 방을 꺼내 확인합니다. 목적지가 아니면 이어진 다음 방들(`neighbors`)을 모두 큐의 맨 뒤(`append`)에 밀어 넣습니다.
- **소크라테스식 문답: "여기서 `_insertion_sort_strings`로 이웃들을 굳이 정렬하는 이유는 무엇일까요?"**
  만약 목적지까지 가는 최단 경로가 2개 이상 존재한다면 어떡할까요? 어떤 길을 택해도 거리(촌수)는 같습니다. 이럴 때 언제나 동일하고 예측 가능한 결과(예: 사전순으로 더 빠른 해시의 경로)를 출력하도록 탐색 순서를 강제하는 것입니다. 프로그래밍에서 '결정론적(Deterministic) 결과'는 테스트와 디버깅을 위해 생명처럼 중요합니다!

#### 🔎 `find_ancestors` (DFS) 해부
```python
def find_ancestors(commits_dict: Dict[str, Commit], commit_hash: str) -> List[str]:
    # ... (생략) ...
    ancestors: List[str] = []
    visited: Set[str] = set()
    stack: List[str] = [] # 이번엔 Queue가 아니라 Stack입니다!
    # ...
    while stack:
        current: str = stack.pop() # 맨 뒤에서 꺼냅니다 (프링글스 통)
        if current in visited:
            continue

        visited.add(current)
        ancestors.append(current)

        current_commit: Commit = commits_dict[current]
        for parent_hash in current_commit.parents:
            if parent_hash in commits_dict and parent_hash not in visited:
                stack.append(parent_hash)
    
    return ancestors
```
- **해석**: 조상 탐색은 뿌리 끝까지 깊게 파고드는 DFS가 제격입니다. 코드는 BFS와 거의 똑같이 생겼지만, 자료구조 하나만 바뀌었습니다. 큐 대신 **스택(`stack`)**을 쓰고, `popleft()` 대신 `pop()`(맨 뒤에서 꺼내기)을 씁니다. 단 하나의 함수 차이로 '넓게 퍼지는 물결(BFS)'이 '깊게 파고드는 드릴(DFS)'로 바뀌는 셈입니다. 이것이 자료구조의 위력입니다!

---

## Phase 3: "혼돈의 우주를 정렬하고 합치다" — 정렬과 알고리즘의 꽃

미로 탐험을 무사히 마친 여러분을 환영합니다. 마지막 챕터에서는 파편화된 커밋 히스토리를 보기 좋게 정렬하는 방법과 두 파일의 차이점(Diff)을 귀신같이 찾아내는 알고리즘의 꽃을 맛보겠습니다.

### 1. [Concept] 위상 정렬 (Topological Sort): 수강신청의 절대 법칙
여러분이 `git log`를 쳤을 때 커밋들이 시간 순서대로 예쁘게 나오는 것은 우연이 아닙니다. 여러 브랜치에서 동시다발적으로 생성된 커밋들을 '어떤 순서로 보여줄 것인가'는 컴퓨터 공학에서 매우 까다로운 문제입니다.

이때 사용되는 것이 **위상 정렬(Topological Sort)**, 그중에서도 **Kahn's Algorithm**입니다.
이 알고리즘의 작동 방식은 **'대학교 수강신청의 선수과목'**과 완벽히 똑같습니다!

- 'C언어(부모 커밋)'를 들어야만 '자료구조(자식 커밋)'를 들을 수 있습니다.
- '자료구조'와 '컴퓨터 구조'를 모두 들어야만 '운영체제'를 들을 수 있습니다.
- 그렇다면 '운영체제'를 듣기 위한 과목 수강 순서는 어떻게 될까요?

Kahn's Algorithm은 **"나를 가리키는 화살표(진입 차수, In-degree)가 0인 과목부터 하나씩 듣는다"**는 단순명쾌한 규칙을 따릅니다. 화살표가 0이라는 건 선수과목이 없거나, 이미 다 들었다는 뜻이니까요!

### 2. [Code] `minigit/graph.py` 위상 정렬 해부
```python
def topological_sort(commits_dict: Dict[str, Commit]) -> List[str]:
    # 1. 진입 차수(in-degree) 계산: "이 과목을 듣기 위해 먼저 들어야 할 선수과목이 몇 개인가?"
    in_degree: Dict[str, int] = {hash_val: 0 for hash_val in commits_dict}
    for hash_val, commit in commits_dict.items():
        for parent_hash in commit.parents:
            if parent_hash in in_degree:
                in_degree[parent_hash] += 1 # 자식이 부모를 가리키므로, 부모의 진입 차수가 증가합니다.
```
- **해석**: 먼저 모든 과목의 '선수과목 개수(`in_degree`)'를 0으로 초기화한 뒤, 부모-자식 관계를 훑으며 화살표 개수를 셉니다. Git의 화살표는 "자식 → 부모"를 향하므로, 부모가 화살표를 맞게 됩니다. 즉, 가장 최신 커밋(자식)이 진입 차수가 가장 낮아 먼저 출력됩니다!

```python
    # 2. 진입 차수가 0인 노드를 큐에 삽입: "당장 수강할 수 있는 과목들을 바구니에 담자!"
    queue: deque[str] = deque([h for h in in_degree if in_degree[h] == 0])
    result: List[str] = []

    # 3. 큐에서 꺼내며 연결된 간선 제거: "과목을 수강 완료했으니, 다음 과목들의 선수조건을 하나씩 지워주자!"
    while queue:
        # 여러 개가 0일 경우, 작성일(timestamp) 기준으로 정렬하여 최신 커밋이 먼저 오게 합니다.
        # (생략: 큐에서 꺼내기 전 1차 정렬 로직)
        
        current: str = queue.popleft()
        result.append(current)
        
        current_commit: Commit = commits_dict[current]
        for parent_hash in current_commit.parents:
            if parent_hash in in_degree:
                in_degree[parent_hash] -= 1 # 선수과목 완료!
                if in_degree[parent_hash] == 0:
                    queue.append(parent_hash) # 이제 이 과목도 들을 수 있게 되었습니다!
```
- **🔥 일타 강사의 핵심 포인트**: 이 알고리즘은 단순히 순서만 섞는 것이 아니라, **'인과율(Causality)'**을 절대로 위배하지 않도록 보장합니다. 부모 커밋이 자식 커밋보다 로그에 먼저 출력되는 타임 패러독스는 Kahn's Algorithm 아래에서는 절대 일어날 수 없습니다!

### 3. [Concept] LCS (Longest Common Subsequence): 두 장부의 차이를 찾는 마법 (Diff)
버전 관리의 꽃은 단연 "내가 어제 짠 코드랑 오늘 짠 코드가 뭐가 다르지?"를 보여주는 `diff` 기능입니다. 컴퓨터는 이를 어떻게 알아낼까요?

여기엔 **LCS 알고리즘**이라는 기법이 사용됩니다. 이는 범죄 현장에서 발견된 **유전자(DNA) 서열 두 개를 비교하여 공통부분과 돌연변이를 찾아내는 방식**과 같습니다.

- 원본: `A B C D E`
- 수정본: `A C D F E`
- LCS(공통부분): `A C D E` (B가 삭제되고 F가 추가됨을 알아낼 수 있습니다!)

#### 🔎 `minigit/diff.py` 해부
```python
def lcs(lines_a: List[str], lines_b: List[str]) -> List[List[int]]:
    m: int = len(lines_a)
    n: int = len(lines_b)
    # 0으로 채워진 (m+1) x (n+1) 격자판을 만듭니다. (동적 계획법, DP 표)
    dp: List[List[int]] = []
    for _ in range(m + 1):
        dp.append([0] * (n + 1))

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if lines_a[i - 1] == lines_b[j - 1]:
                # 두 글자가 같다면, 왼쪽 대각선 위쪽 값에 1을 더합니다 (공통부분 길이 1 증가!)
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                # 다르다면, 왼쪽이나 위쪽 중 더 큰 값을 물려받습니다.
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    return dp
```
- **해석**: 이 코드는 **동적 계획법(Dynamic Programming, DP)**이라는 컴퓨터 공학 최고의 최적화 기법 중 하나입니다. 한 번 계산한 작은 문제의 정답을 격자판(`dp`)에 기록해 두고, 더 큰 문제를 풀 때 재활용하여 중복 계산을 없앱니다.
- **소크라테스식 문답: "격자판 크기를 왜 하필 `m+1`, `n+1`로 만들었을까요?"**
  0번째 인덱스는 '비교할 글자가 하나도 없는 텅 빈 상태(Base Case)'를 의미합니다. 빈 상태와의 공통부분은 언제나 0이므로, 격자판 가장자리에 0을 깔아두면 `i-1` 인덱스를 참조할 때 배열을 벗어나는 오류(`IndexError`)를 방지할 수 있는 우아한 꼼수입니다!

### 4. [Concept] Merge Sort vs Quick Sort: 정렬의 안정성(Stability)
마지막으로 짚고 넘어갈 것은 커밋들을 정렬하는 **안정성(Stability)**의 개념입니다.
우리가 날짜순이나 작성자순으로 커밋을 정렬할 때 `sorting.py`를 사용합니다.

- **Merge Sort (병합 정렬)**: 한 번 쪼개진 덩어리를 다시 합칠 때 순서를 잃지 않는 **안정 정렬(Stable Sort)**입니다. 예를 들어 날짜순으로 정렬된 커밋들을 다시 '작성자 이름순'으로 정렬하면, 같은 작성자 내에서는 여전히 '날짜순'이 유지됩니다.
- **Quick Sort (퀵 정렬)**: 무작위 피벗을 잡고 좌우로 던지는 방식이라 순서가 뒤죽박죽 섞이는 **불안정 정렬(Unstable Sort)**입니다. 평균적으로 매우 빠르지만, 다중 기준 정렬(Multi-criteria sorting)을 할 때는 기준이 파괴되는 단점이 있습니다.

---

> 🎓 **일타 강사의 수료증 수여**
> 
> 축하합니다! 드디어 3단계에 걸친 대장정이 끝났습니다.
> "조작 불가능한 해시 장부(블록체인)"에서 시작해, "도서관 역색인과 미로 탐험(검색과 그래프)", 그리고 마침내 "수강신청 인과율(위상정렬)과 유전자 비교(LCS)"까지. 
> 
> 이제 여러분은 누군가 "Git이 뭐야?"라고 물어본다면, "그거 커밋하고 푸시하는 거 아냐?"라는 시시한 대답 대신 칠판에 DAG와 해시맵, 역색인을 그리며 한 시간 동안 침을 튀길 수 있는 **진정한 컴퓨터 공학 스토리텔러**로 거듭나셨습니다. 
> 
> 이 가이드가 여러분의 코딩 여정에 등대가 되기를 바랍니다. 수고하셨습니다!

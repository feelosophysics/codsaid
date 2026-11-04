# Mini Git을 처음부터 끝까지 읽는 실습 가이드

이 문서는 **명령 한 개를 실행하고, 바뀐 데이터를 확인한 다음, 그 코드를 읽는 순서**로 진행합니다. Python 문법을 모두 알고 있다고 가정하지 않습니다. 각 절의 예제를 직접 입력하고, 납득되지 않는 상태 변화는 `STATUS`, `LOG`로 확인하세요.

Mini Git은 실제 Git 전체가 아닙니다. 커밋의 메시지·작성자·시각·부모를 메모리에 보관합니다. 파일 내용과 네트워크, 저장소 파일은 다루지 않습니다. `DIFF`는 별도로 지정한 텍스트 파일 두 개만 비교합니다.

## 0. 준비와 읽는 순서

프로젝트 루트(`README.md`가 있는 폴더)에서 Python 3.10 이상으로 실행합니다.

```text
python -m minigit
```

Windows에서 `python`이 Microsoft Store 별칭이라 실행되지 않으면 설치된 Python 실행 파일이나 `py -3.12 -m minigit`을 사용하세요. `-m minigit`은 `minigit/__main__.py`를 실행합니다. `mini-git>`는 **프로그램이 보여 주는 프롬프트**이므로 직접 입력하지 않습니다. `QUIT` 또는 `EXIT`으로 끝내며, 종료하면 메모리의 커밋은 사라집니다.

읽을 파일은 다음 일곱 개입니다. 처음에는 모든 파일을 펼쳐 보지 말고, 해당 절에서 이름이 나올 때 여세요.

| 파일 | 할 일 |
| --- | --- |
| `minigit/__main__.py` | 한 줄을 명령과 인자로 나누고 결과를 출력 |
| `minigit/models.py` | 커밋과 저장소 상태를 만들고 변경 |
| `minigit/index.py` | 메시지 단어와 작성자 검색용 표 |
| `minigit/graph.py` | 로그, 최단 경로, 조상 탐색 |
| `minigit/sorting.py` | 직접 만든 두 정렬과 시간 비교 |
| `minigit/diff.py` | 줄 단위 파일 비교 |
| `minigit/constants.py` | 공통 설정과 출력 문구 |

이후의 `A`, `B`, `C`는 설명용 커밋 이름입니다. 프로그램은 실제로 `35f1d9-1`처럼 **매 실행 달라지는 ID**를 보여 줍니다. `PATH`나 `ANCESTORS`를 따라 할 때는 자기 화면에 나온 ID를 복사하세요.

### Python 문법을 읽는 작은 지도

```python
branch_name = "main"            # = 는 오른쪽 값을 왼쪽 이름에 저장
parents = []                    # list: 순서가 있는 묶음
parents.append("abc123-1")     # 마지막에 한 항목 추가
branches = {"main": "abc123-1"} # dict: 이름(키) → 값
branches["main"] = "def456-2"  # 해당 키가 가리키는 값 변경
found = {"abc123-1"}           # set: 중복이 없는 묶음
```

`None`은 “아직 값이 없음”입니다. `main: None`은 브랜치는 있지만 첫 커밋은 없다는 뜻입니다. `if value is None:`은 이 상태를 검사합니다. `for item in items:`는 묶음에서 하나씩 꺼내 반복합니다. `return`은 함수의 결과를 호출자에게 돌려주고 함수를 끝냅니다.

`def commit(self, message: str) -> str:`에서 `def`는 함수 정의, `message`는 입력, `-> str`은 결과가 문자열이라는 **타입 힌트**입니다. 타입 힌트가 값을 자동으로 검사하지는 않습니다. `self`는 지금 사용하는 객체 자신입니다. `Repository()`를 만들 때 `__init__`이 실행되어 그 객체의 빈 저장소가 준비됩니다. `self.branches`는 그 저장소에 속한 값이고, 함수 안의 `parents`는 그 호출 동안 쓰는 지역 변수입니다.

## 1. INIT: 한 줄이 저장소에 도착하는 길

```text
mini-git> INIT "Alice Lee"
Initialized repository.
Current branch: main
Current user: Alice Lee
```

흐름은 `run() → parse_input() → execute() → Repository.init()`입니다.

1. `run()`의 `input("mini-git> ")`이 한 줄을 읽습니다.
2. `parse_input()`은 `shlex`로 `["INIT", "Alice Lee"]`를 만듭니다. 따옴표 안의 공백은 단어 사이 경계가 아닙니다.
3. `execute()`는 첫 단어를 대문자로 바꾸어 명령을 고르고, 나머지 `["Alice Lee"]`를 인자로 분리합니다. 저장소 명령 표에서 INIT에 연결된 함수 `repo.init`과 오류 문구를 꺼냅니다.
4. 공통 인자 검사에서 **정확히 하나**인지 확인한 다음 `action(args[0])`을 부릅니다. 여기서 action은 `repo.init`입니다. 함수도 표의 값으로 보관할 수 있으며, 괄호를 붙여 호출할 때 실행됩니다.
5. `Repository.init()`은 빈 커밋 표, `{"main": None}` 브랜치 표, 현재 브랜치 `head = "main"`, 작성자를 설정합니다. 문자열 결과를 `run()`이 출력합니다.

현재 상태를 확인해 보세요.

```text
mini-git> STATUS
Current user:   Alice Lee
Current branch: main
HEAD commit:    (no commits yet)
Total commits:  0
Branches:       main
```

`INIT`을 다시 하면 기존 커밋·브랜치·검색 표는 비워집니다. 단, **같은 프로그램 실행 중** 생성 ID의 번호는 계속 증가합니다. 그래서 재초기화 후에도 예전 ID를 다시 발급하지 않습니다.

### 따옴표와 오류도 실행해 보기

```text
mini-git> INIT Alice ignored
Error: Invalid args: INIT <user_name>
mini-git> COMMIT "unfinished
Error: Invalid args
```

두 번째 입력은 `shlex`가 닫히지 않은 따옴표를 발견해 `ValueError`를 내고, `run()`의 `try/except`가 이를 화면 오류로 바꿉니다. `parse_input()`에서 역슬래시 이스케이프를 끈 것은 따옴표 없는 Windows 경로의 `\`를 보존하기 위해서입니다. 입력 안에서 `\"`처럼 따옴표를 이스케이프하는 문법은 지원하지 않습니다. 공백이 있는 경로는 전체를 따옴표로 감싸세요.

**직접 설명해 보기:** `INIT "Alice Lee"`에서 왜 `args` 길이는 2가 아니라 1일까요?

## 2. COMMIT: 노드 하나와 세 군데의 상태 변화

```text
mini-git> COMMIT "Start project"
[main <실제 ID>] Start project
```

`Commit` 객체에는 `hash`(ID), `message`, `author`, `timestamp`, `parents` 다섯 필드가 있습니다. `parents`는 **부모 ID의 리스트**입니다. 첫 커밋은 `[]`, 보통 커밋은 `[이전 ID]`, 병합 커밋은 `[현재 끝 ID, 대상 끝 ID]`입니다. `timestamp`는 1970년 이후 초 단위 수이며, 화면에서는 `format_timestamp()`로 읽기 쉬운 날짜가 됩니다.

`Repository.commit()`은 먼저 현재 브랜치가 가리키는 ID를 읽습니다. 첫 커밋이라면 `None`이므로 부모 리스트를 비워 둡니다. 그 다음 공통 함수 `_add_commit()`이 아래 순서로 일합니다.

```text
메시지 + 작성자 + 시각 + 부모 ID → SHA-1 앞 6자리
SHA-1 앞 6자리 + 증가 번호       → 전체 커밋 ID
commits[ID] = 새 Commit         → ID로 찾을 수 있게 저장
branches[head] = ID            → 현재 브랜치 끝을 새 커밋으로 이동
inverted_index.add_commit(...) → 검색 표도 갱신
```

예를 들어 ID가 `a1b2c3-1`이면 `a1b2c3`은 내용 지문의 일부, `1`은 세션에서 반복되지 않는 번호입니다. SHA-1 앞 6자리만으로는 충돌할 수 있으므로 번호를 붙였습니다. **실제 Git의 객체 ID는 이 형태가 아닙니다.** 이 프로젝트의 필드는 `hash`라고 부르지만, 전체 ID에는 교육용 번호가 들어갑니다.

`commits`는 `dict[str, Commit]`입니다. `commits[ID]`로 해당 커밋을 평균 O(1)에 찾습니다. `branches`는 `dict[str, str | None]`으로, 브랜치 이름을 끝 커밋 ID에 연결합니다. `str | None`은 “문자열일 수도, 아직 값이 없을 수도 있다”는 타입 힌트입니다.

두 번째 커밋을 만드세요.

```text
mini-git> COMMIT "Add login feature"
[main <두 번째 ID>] Add login feature
```

```text
첫 커밋 A  ←  두 번째 커밋 B
parents[A] = []
parents[B] = [A]
branches["main"] = B
```

화살표는 **새 커밋에서 부모로** 향합니다. 새로운 커밋의 부모는 이미 저장된 커밋에서만 고르므로, 미래 노드를 가리켜 되돌아오는 순환이 생기지 않습니다. 방향이 있고 순환이 없는 그래프가 DAG입니다. `Commit.__init__()`의 `parents[:]`는 리스트 복사입니다. 호출자가 전달한 부모 리스트를 나중에 바꿔도 커밋에 기록된 부모가 함께 바뀌지 않게 합니다.

**직접 설명해 보기:** `commits[B]`와 `branches["main"]`은 각각 무엇을 돌려줄까요?

## 3. BRANCH, SWITCH, USER: 포인터와 작성자

현재 `main`이 B를 가리킨다고 가정하고 다음을 입력하세요.

```text
mini-git> BRANCH feature
mini-git> SWITCH feature
mini-git> USER "Bob Smith"
mini-git> COMMIT "Add search page"
```

| 단계 | `head` | `branches["main"]` | `branches["feature"]` | 새 커밋 작성자 |
| --- | --- | --- | --- | --- |
| B 생성 직후 | `main` | B | 없음 | Alice Lee |
| BRANCH 후 | `main` | B | B | 없음 |
| SWITCH 후 | `feature` | B | B | 없음 |
| USER 후 | `feature` | B | B | 이후 Bob Smith |
| C 생성 후 | `feature` | B | C | Bob Smith |

`BRANCH`는 커밋을 복사하지 않고 **같은 ID를 가리키는 이름**을 추가합니다. `SWITCH`는 `head`에 저장한 브랜치 이름만 바꿉니다. 그래서 다른 브랜치에서 커밋해도 `main`은 B에 머물러 있습니다. `USER`는 이후 커밋의 작성자만 바꾸는 학습용 추가 명령입니다. 이미 만들어진 커밋의 작성자는 바뀌지 않습니다. 작성자별 검색과 정렬을 직접 확인하려고 넣었습니다.

```text
mini-git> SWITCH main
mini-git> COMMIT "Update main"
```

이제 `main`의 끝을 D라고 하면 모양은 다음과 같습니다.

```text
        C (feature)
       ↙
A ← B
       ↖
        D (main, HEAD)
```

여기서 C와 D의 부모는 둘 다 B입니다. `HEAD`는 이 프로그램에서 **현재 브랜치 이름**(`"main"`)이며, `LOG` 화면의 `(HEAD)` 표시는 그 브랜치가 가리키는 커밋 D에 붙습니다.

## 4. LOG: 부모가 먼저 나오게 하기

`LOG`를 입력하면 전체 커밋을 보여 줍니다. 미션은 일반적인 “최신순”이 아니라 **모든 부모가 자식보다 앞**에 있어야 한다고 정했습니다. 위 그림의 가능한 순서는 `A, B, C, D` 또는 `A, B, D, C`입니다. `C`와 `D` 사이에는 부모 관계가 없어서 둘의 순서는 자유입니다.

`graph.topological_sort()`는 Kahn 위상 정렬을 사용합니다.

1. `remaining_parents[ID]`에 아직 출력하지 않은 부모 수를 적습니다. A는 0, B는 1, C와 D도 1입니다.
2. 부모 수가 0인 A를 `deque` 큐에 넣습니다.
3. `popleft()`로 A를 꺼내 출력하고, A의 자식 B의 남은 부모 수를 1 줄입니다.
4. B가 0이 되면 큐에 넣습니다. 같은 과정을 반복하면 C와 D가 준비됩니다.

`deque`는 양쪽에서 넣고 뺄 수 있는 자료구조입니다. 여기서는 오른쪽 `append()`와 왼쪽 `popleft()`를 써서 먼저 들어온 항목을 먼저 처리합니다(FIFO). 모든 정점 V와 부모 연결 E를 한 번씩 다루므로 위상 정렬은 O(V+E) 시간입니다. 저장소가 만들 수 없는 순환을 외부 코드가 억지로 주입하면 함수는 `ValueError`를 냅니다.

`LOG --sort-by=date`와 `LOG --sort-by=author`는 **다른 요청**입니다. 각각 시각과 작성자 이름(소문자)을 기준으로 `sorting.merge_sort()`를 사용합니다. 따라서 `--sort-by=date` 결과는 부모 우선 순서와 다를 수 있습니다. 비교 기준은 `lambda commit: commit.timestamp`처럼 짧은 함수로 전달합니다. 여기서 `lambda`는 “커밋 하나를 받아 시각을 돌려주는 이름 없는 함수”입니다.

### 머지 정렬을 읽어 보기

`merge_sort()`는 원소를 반으로 나누고 재귀적으로 정렬한 다음 `_merge()`로 합칩니다. **재귀**는 함수가 자기 자신을 다시 부르는 것입니다. 길이 0 또는 1이면 더 나누지 않고 복사본을 돌려줘 재귀가 끝납니다.

```text
[3, 1, 2, 4]
  → [3, 1] / [2, 4]
  → [3] [1] / [2] [4]
  → [1, 3] / [2, 4]
  → [1, 2, 3, 4]
```

`_merge()`는 두 조각의 맨 앞 원소를 비교합니다. 키가 **같을 때 왼쪽을 먼저** 결과에 넣습니다(`<=`). 원래 앞에 있던 동률 원소가 계속 앞에 남으므로 **안정 정렬**입니다. 각 분할 층에서 n개를 다루고 층이 약 `log₂n`개이므로 평균·최악 시간은 O(n log n), 추가 공간은 O(n)입니다. 표준 정렬 함수 `sorted()`와 `list.sort()`는 미션 제약 때문에 쓰지 않습니다.

**직접 설명해 보기:** 작성자가 같은 커밋 두 개를 `LOG --sort-by=author`로 보면 어떤 순서를 유지할까요?

## 5. PATH: 양방향 연결에서 가장 짧은 길

앞 절의 C와 D는 서로의 부모가 아닙니다. 하지만 부모 연결을 **양방향** 길로 보면 `C → B → D`로 갈 수 있습니다. 프로그램이 실제로 출력한 C와 D의 ID를 사용해 보세요.

```text
mini-git> PATH <C의 ID> <D의 ID>
Path: <C의 ID> -> <B의 ID> -> <D의 ID>
```

`graph.find_shortest_path()`는 먼저 모든 커밋에서 양방향 인접 목록을 만듭니다. B의 이웃에는 A, C, D가, C의 이웃에는 B가 들어갑니다. 그 다음 BFS(너비 우선 탐색)를 합니다.

- `queue`에는 다음에 방문할 ID를 넣습니다. 큐를 쓰므로 시작점에서 1칸, 2칸, 3칸 떨어진 순서로 방문합니다.
- `visited`는 이미 발견한 ID의 `set`입니다. 되돌아가며 반복 방문하지 않게 합니다.
- `previous[새 ID] = 발견해 준 ID`는 나중에 목적지에서 출발점까지 되짚는 발자국입니다.

`set`은 같은 값을 두 번 담지 않으며 평균 O(1)에 포함 여부를 확인합니다. BFS가 목적지를 **처음** 발견했을 때 거리가 가장 짧습니다. 최단 경로가 여러 개라면 이웃 ID 뒤에 `->`를 붙인 값을 우리가 만든 머지 정렬로 비교합니다. 예를 들어 `r → a → z`와 `r → b → z`는 a가 먼저지만, `a`와 `a!`처럼 접두사가 겹칠 때는 `a!->`가 `a->`보다 먼저입니다. 구분자까지 비교해야 전체 경로 문자열의 사전순과 맞습니다. ID 자체에 `->`를 넣지는 않습니다.

서로 다른 첫 커밋에서 시작한 두 갈래는 연결되지 않을 수 있습니다. `INIT Alice` 직후, 커밋 전에 `BRANCH spare`를 만들고 `main`과 `spare`에서 각각 첫 커밋을 만들면 두 개의 뿌리가 생깁니다. 두 뿌리 사이의 `PATH`는 `No path`입니다. 없는 ID를 입력하면 `Unknown commit` 오류가 먼저 나옵니다.

인접 목록과 BFS 자체는 O(V+E)이고, 사전순 동률 선택을 위한 이웃 정렬 비용이 더해집니다. 이웃 수를 d라고 하면 전체 시간은 대략 O(V+E+Σ d log d), 공간은 O(V+E)입니다.

## 6. ANCESTORS: 한 방향으로 끝까지 탐색

```text
mini-git> ANCESTORS <D의 ID>
Ancestors of <D의 ID>:
  <B의 ID> ...
  <A의 ID> ...
```

`graph.find_ancestors()`는 **부모 방향만** 따라갑니다. 시작 커밋 자신은 결과에 넣지 않습니다. `stack` 리스트의 끝에 부모를 `append()`하고 끝에서 `pop()`하므로 나중에 넣은 것을 먼저 꺼냅니다(LIFO). 이 방식이 DFS(깊이 우선 탐색)입니다. 한 갈래를 깊이 따라간 뒤 남은 갈래로 돌아옵니다.

병합된 그래프에서는 서로 다른 갈래에서 같은 조상을 다시 만날 수 있습니다. `visited` 집합으로 중복 출력을 막습니다. 도달 가능한 커밋과 연결을 한 번씩 살펴보므로 O(V+E) 시간입니다. 조상 출력 순서는 미션의 조건이 아니며, **빠짐없이 한 번씩 나오는지**가 중요합니다.

## 7. SEARCH: 모든 커밋을 읽지 않고 후보 찾기

`COMMIT "Add login feature"`를 만들 때 `InvertedIndex.add_commit()`이 메시지를 `split()`하고 `lower()`를 적용합니다. 작성자도 소문자로 저장합니다.

```text
keyword_index["add"]     → {A의 ID}
keyword_index["login"]   → {A의 ID}
keyword_index["feature"] → {A의 ID}
author_index["alice lee"] → {A의 ID}
```

이 방향이 **역색인**입니다. 커밋에서 단어를 찾는 대신 단어에서 커밋 ID 집합을 바로 찾습니다. 같은 메시지에 `login`이 두 번 있어도 `set`에는 그 커밋 ID가 한 번만 들어갑니다.

```text
mini-git> SEARCH login
mini-git> SEARCH "login feature"
mini-git> SEARCH --author="Alice Lee"
```

한 단어 검색은 색인에 있는 ID 집합을 바로 가져옵니다. 구절 검색은 **첫 단어의 ID 집합만 후보로 꺼낸 뒤**, 그 후보 메시지의 단어 목록에 검색 단어들이 연속해서 있는지 확인합니다. `login new feature`는 `"login feature"`와 일치하지 않습니다. 모든 커밋을 다시 훑지 않습니다. 결과 집합은 순서가 없으므로, **결과 후보만** 시각·ID 기준으로 머지 정렬하여 출력합니다.

토큰은 공백으로 나눈 그대로입니다. `login`과 `login,`은 다른 단어입니다. 대소문자는 무시합니다. 작성자 검색은 이름 **전체**를 비교하므로 공백이 있는 이름은 `SEARCH --author="Bob Smith"`처럼 씁니다. 작성자가 여러 명인 예제는 `USER`로 만들 수 있습니다.

커밋을 추가할 때 토큰을 색인에 쓰는 비용과 메모리가 듭니다. 대신 조회는 평균 O(1)에 후보 집합을 찾고, 결과 K개를 출력하려면 적어도 O(K)가 필요합니다. 구절 검색은 후보의 메시지도 검사합니다. 출력 순서 정렬은 O(K log K)입니다. “검색 전체가 항상 O(1)”이라는 뜻은 아닙니다.

**직접 설명해 보기:** `SEARCH "login feature"`가 `SEARCH login`보다 확인할 일이 더 많은 이유는 무엇일까요?

## 8. MERGE: 부모가 둘인 커밋

3절의 갈라진 브랜치 상태로 돌아가서 `main`에서 실행합니다.

```text
mini-git> SWITCH main
mini-git> MERGE feature
Merged 'feature' into 'main'.
[main <병합 ID>] Merge branch 'feature' into main
```

`Repository.merge()`는 현재 브랜치 끝 D와 `feature` 끝 C를 찾아 `parents = [D, C]`인 커밋 M을 만듭니다. `_add_commit()`이 M 저장, `main` 이동, 역색인 갱신을 **보통 커밋과 똑같이** 처리합니다.

```text
M.parents = [D, C]       # main의 새 끝 M에서 두 갈래로 향한다
C.parents = [B]
D.parents = [B]
B.parents = [A]
A.parents = []
```

연결 방향은 언제나 새 커밋에서 오래된 부모로 향합니다. 두 브랜치가 같은 커밋을 가리키면 `Already up to date.`를 돌려주고 새 커밋을 만들지 않습니다. 커밋이 없는 브랜치를 병합하거나 자기 브랜치를 대상으로 하면 오류를 돌려줍니다. 이 병합은 **파일 내용을 합치지 않습니다.** 그래프에 부모 둘을 기록하는 학습용 기능입니다.

`LOG`를 다시 보면 M의 두 부모 C와 D가 모두 M보다 앞에 있습니다. `ANCESTORS M`에는 두 갈래와 공통 조상 B, A가 중복 없이 들어가야 합니다.

## 9. DIFF: 두 파일의 줄을 비교하는 표

텍스트 편집기로 프로젝트 폴더에 다음 두 UTF-8 파일을 만드세요.

```text
before.txt       after.txt
----------       ---------
same             same
old              new
```

```text
mini-git> DIFF before.txt after.txt
--- before.txt
+++ after.txt

  same
- old
+ new

Summary: 1 addition(s), 1 deletion(s), 1 unchanged line(s)
```

`diff_files()`가 두 파일을 읽어 `splitlines()`로 줄 목록을 만들고 `compute_diff()`를 부릅니다. 파일이 없으면 `File not found`, 읽기 실패나 UTF-8 디코딩 오류면 `Error reading`을 돌려줍니다. Windows에서 공백이 있는 절대 경로는 `DIFF "C:\my files\before.txt" "C:\my files\after.txt"`처럼 입력합니다.

`compute_lcs_table()`의 LCS는 **순서를 유지하며 두 파일에 함께 나타나는 줄의 최대 개수**입니다. `dp[i][j]`는 첫 파일의 앞 i줄과 둘째 파일의 앞 j줄을 비교한 결과입니다.

| `dp[i][j]` | 빈 목록 | `same` | `new` |
| --- | ---: | ---: | ---: |
| 빈 목록 | 0 | 0 | 0 |
| `same` | 0 | 1 | 1 |
| `old` | 0 | 1 | 1 |

두 줄이 같으면 왼쪽 위 대각선 값에 1을 더합니다. 다르면 위쪽과 왼쪽 값 중 큰 값을 가져옵니다. 표의 오른쪽 아래에서 거꾸로 이동하면서 공통 줄(` `), 첫 파일에서 삭제된 줄(`-`), 둘째 파일에 추가된 줄(`+`)을 기록합니다. 거꾸로 모았으므로 마지막에 `reverse()`합니다. 비교 시간과 표 메모리는 두 파일의 줄 수가 m, n일 때 O(mn)입니다. `dp.append([0] * columns)`에서 `[0] * columns`는 0을 필요한 칸 수만큼 채운 **새 행**입니다.

**직접 설명해 보기:** 두 파일의 줄 순서를 무시하고 공통 줄 개수만 세면 어떤 정보가 사라질까요?

## 10. BENCHMARK: 두 정렬을 비교하고 해석하기

```text
mini-git> BENCHMARK
Sorting benchmark (seconds; smaller is faster)
...
```

`benchmark_sorts()`는 여러 크기의 숫자 목록을 만들고, 크기를 시드로 한 `random.Random(size).shuffle(data)`로 섞습니다. 같은 크기에서는 같은 입력이 만들어집니다. `time.perf_counter()`를 정렬 전후에 읽고 차이를 초 단위로 보여 줍니다. `shuffle()`은 입력을 섞는 동작이며 금지된 표준 **정렬** API는 아닙니다.

머지 정렬은 4절처럼 반으로 나누고 합칩니다. 퀵 정렬은 가운데 원소를 피벗으로 고른 다음 **작은 값 / 같은 값 / 큰 값** 세 리스트에 순서대로 넣습니다. 작은 그룹과 큰 그룹에 다시 같은 작업을 합니다. 이 구현은 원소를 원래 순서대로 각 그룹에 넣으므로 **같은 키의 상대 순서를 유지하는 안정 정렬**입니다. 일반적인 제자리 퀵 정렬이 불안정하다는 설명을 이 코드에 그대로 적용하면 틀립니다.

| 구현 | 평균 시간 | 최악 시간 | 추가 공간 | 안정성 |
| --- | --- | --- | --- | --- |
| 이 코드의 머지 정렬 | O(n log n) | O(n log n) | O(n) | 안정 |
| 이 코드의 세 그룹 퀵 정렬 | O(n log n) | O(n²) | 평균 O(n), 최악 O(n²) | 안정 |

퀵 정렬이 계속 한쪽으로 치우쳐 나뉘면 느려지고 재귀 호출도 깊어질 수 있습니다. 벤치마크의 “승자”는 **그 입력과 그 실행 환경에서 측정한 시간**일 뿐, 모든 입력에서 더 빠르다는 증명은 아닙니다. 아주 작은 차이는 실행 때마다 바뀔 수 있습니다.

## 11. 전체 흐름을 다시 연결하기

```text
입력 한 줄
  ↓  __main__.py: parse_input → execute → 저장소 함수 / handle_...
Repository 상태 변경 ──→ models.py: Commit / branches / head
        │
        ├─ COMMIT·MERGE → index.py: 단어·작성자 역색인 갱신
        ├─ LOG·PATH·ANCESTORS → graph.py
        ├─ LOG --sort-by·검색 결과 → sorting.py
        └─ DIFF → diff.py
  ↓
결과 문자열을 CLI가 출력
```

미션 요구사항을 코드에 연결하면 다음과 같습니다.

| 요구 | 구현에서 확인할 곳 |
| --- | --- |
| 0개 이상 부모와 DAG | `Commit.parents`, `Repository._add_commit()` |
| ID 조회·세션 내 유일성 | `Repository.commits`, 증가 번호가 붙은 ID |
| 브랜치·HEAD | `Repository.branch()`, `switch()`, `get_head_commit_hash()` |
| 부모 우선 LOG | `graph.topological_sort()` |
| 무방향 최단 경로·사전순 동률 | `graph.find_shortest_path()` |
| 모든 조상 | `graph.find_ancestors()` |
| 단어·작성자 역색인 | `InvertedIndex` |
| 직접 구현한 정렬 | `sorting.merge_sort()`, `quick_sort()` |
| REPL과 오류 | `MiniGitCLI.run()`, `parse_input()`, `execute()`의 공통 검사와 개별 `handle_...` |

### 파일을 불러오는 문법과 실행 시작점

`from minigit.models import Repository`는 다른 파일에 정의한 `Repository` 이름을 가져옵니다. `minigit/__init__.py`는 이 폴더가 Python 패키지임을 나타내는 파일이며, 여기에는 실행 로직이 없습니다. `python -m minigit`을 실행하면 `minigit/__main__.py`의 `if __name__ == "__main__":` 아래에서 CLI 객체를 만들고 `run()`을 부릅니다. 테스트가 `MiniGitCLI`를 **가져오기만** 할 때는 대화형 입력이 갑자기 시작되지 않습니다.

`constants.py`에는 `main` 같은 공통 설정과 여러 함수에서 쓰는 성공·오류 문구를 모았습니다. `ErrorMessages.INVALID_INIT`처럼 클래스 이름으로 문구를 읽으며, 객체를 따로 만들지는 않습니다. 함수에서 화면에 직접 `print()`하는 곳은 주로 `run()`입니다. 다른 함수들은 결과 **문자열을 return**하므로 테스트에서 결과를 확인하기 쉽습니다.

`index.py`의 `if TYPE_CHECKING:` 아래 `Commit` import는 타입을 읽는 도구에만 필요합니다. 실행 중에는 `models.py`가 `index.py`를, `index.py`가 다시 `models.py`를 바로 불러오는 순환을 피합니다. 여러 파일의 `from __future__ import annotations`는 타입 힌트에 아직 아래쪽에서 정의될 이름을 적을 수 있게 돕습니다. 처음 읽을 때는 두 줄 모두 **실행 순서와 타입 표기를 위한 장치**로 이해하면 충분합니다.

### 스스로 확인할 작은 실험

1. `INIT` 후 `STATUS`와 `LOG`는 각각 무엇을 보여 주나요?
2. 브랜치를 **첫 커밋 전에** 두 개로 만든 뒤 서로 다른 첫 커밋을 만들면 왜 `PATH`가 `No path`가 될까요?
3. `USER "Bob Smith"` 전후에 만든 커밋을 `SEARCH --author="Alice Lee"`와 `SEARCH --author="Bob Smith"`로 각각 찾아보세요.
4. `MERGE` 전후에 `ANCESTORS` 결과에 어떤 변화가 생기나요?
5. `SEARCH feature`와 `SEARCH "login feature"`는 어떤 메시지에서 결과가 달라지나요?
6. `LOG`와 `LOG --sort-by=date`가 다른 순서가 될 수 있는 이유를 설명해 보세요.

확인 기준: (1) `STATUS`에는 브랜치와 빈 HEAD가, `LOG`에는 `No commits yet.`가 나옵니다. (2) 두 커밋에는 공통 부모가 없어 양방향 간선으로도 연결되지 않습니다. (3) `USER`는 과거 커밋을 고치지 않습니다. (4) 병합 커밋은 두 부모의 조상을 모두 가집니다. (5) 단어 하나 검색과 연속 구절 검색은 조건이 다릅니다. (6) 날짜순 정렬은 부모 우선 조건을 강제하지 않습니다.

실제 동작을 자동으로 확인하려면 루트에서 `python -m unittest discover -s tests -v`를 실행하세요. 테스트는 읽는 순서와 별개로, 요구사항을 코드가 계속 만족하는지 확인하는 도구입니다.


## 2026-10-07 구현 검토 반영

인자 하나를 받는 INIT·COMMIT·USER·BRANCH·SWITCH·MERGE는 execute의 작은 명령 표와 공통 검사로 연결합니다. 다른 문법과 출력 처리가 필요한 명령은 개별 handler를 유지합니다. LOG와 ANCESTORS는 커밋 표시 함수를 공유합니다.

PATH 동률 비교는 ID 뒤의 `->`까지 비교합니다. ID에 경로 구분자를 넣는 것은 허용하지 않습니다. 현재 생성되는 ID는 이 제한을 만족합니다.

터미널 출력에서는 C0/C1 제어문자를 보이는 표기로 바꾸고 원본 메시지는 보존합니다. DIFF는 파일당 1,048,576바이트, LCS 표는 1,000,000칸을 상한으로 두며 경로 오류·UTF-8 오류·상한 초과를 안내합니다. 이 상한은 학습용 프로그램의 자원 정책이며 알고리즘의 시간복잡도를 바꾸지 않습니다.

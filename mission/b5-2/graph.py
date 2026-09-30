"""
graph.py — 그래프 알고리즘 모듈
================================

이 모듈은 커밋 DAG(방향성 비순환 그래프)에서 수행되는
세 가지 핵심 그래프 알고리즘을 구현합니다:

1. 위상 정렬 (Topological Sort)  — Kahn's Algorithm
2. 최단 경로 탐색 (Shortest Path) — BFS (너비 우선 탐색)
3. 조상 탐색 (Ancestor Search)    — DFS (깊이 우선 탐색)

────────────────────────────────────────────
그래프 알고리즘과 Git의 관계
────────────────────────────────────────────
Git의 커밋 히스토리는 DAG입니다. 이 DAG 위에서:
- `git log`     → 위상 정렬 (부모가 먼저 출력)
- `git log --ancestry-path` → BFS/DFS로 경로 탐색
- `git merge-base` → 공통 조상 탐색 (BFS/DFS)

우리가 구현하는 세 알고리즘은 이런 Git 내부 연산의 기초입니다.

────────────────────────────────────────────
BFS vs DFS — 언제 어떤 것을 쓰는가?
────────────────────────────────────────────
■ BFS (너비 우선 탐색):
  - 시작점에서 가까운 노드부터 방문합니다.
  - 무가중치 그래프에서 최단 경로를 보장합니다.
  - 큐(Queue)를 사용합니다.
  - 공간복잡도: O(V) (최악의 경우 한 레벨의 모든 노드를 큐에 저장)

■ DFS (깊이 우선 탐색):
  - 한 방향으로 끝까지 깊이 들어간 후 되돌아옵니다.
  - 모든 경로를 탐색하거나, 연결 요소를 찾을 때 적합합니다.
  - 스택(Stack) 또는 재귀를 사용합니다.
  - 공간복잡도: O(V) (최악의 경우 경로의 모든 노드를 스택에 저장)

두 알고리즘 모두 시간복잡도는 O(V + E)입니다.
(V = 정점 수, E = 간선 수)
"""

from collections import deque  # BFS와 Kahn's Algorithm에서 사용할 큐(Queue)


def topological_sort(commits_dict):
    """
    Kahn's Algorithm으로 커밋 그래프의 위상 정렬을 수행합니다.

    ── 위상 정렬(Topological Sort)이란? ──
    DAG의 모든 노드를, "모든 간선이 앞에서 뒤를 가리키도록" 일렬로 나열하는 것입니다.
    즉, 노드 A에서 노드 B로 가는 간선이 있으면, A는 반드시 B보다 앞에 옵니다.

    커밋 그래프에서는:
    - 간선: 자식 → 부모 (커밋은 자신의 부모를 참조)
    - 위상 정렬 결과: 부모 커밋이 항상 자식 커밋보다 먼저 출력

    ── Kahn's Algorithm 동작 원리 ──
    1. 모든 노드의 진입차수(in-degree)를 계산합니다.
       진입차수 = "나를 가리키는 간선의 수" = "나를 부모로 가진 자식의 수"
    2. 진입차수가 0인 노드를 큐에 넣습니다.
       (진입차수 0 = 자식이 없는 노드 = "가장 최근" 커밋)
    3. 큐에서 노드를 꺼내 결과에 추가합니다.
    4. 해당 노드의 부모들의 진입차수를 1 감소시킵니다.
    5. 진입차수가 0이 된 부모를 큐에 추가합니다.
    6. 큐가 빌 때까지 반복합니다.

    ── 그런데 잠깐! 우리의 간선 방향 ──
    Git에서 간선은 "자식 → 부모"입니다.
    위상 정렬에서 "부모가 먼저"이려면, "자식 → 부모" 간선 방향 기준으로
    진입차수(= 나에게 들어오는 간선 수)를 계산해야 합니다.
    부모 노드의 진입차수 = 자신을 부모로 참조하는 자식의 수.
    진입차수 0인 노드 = 자식이 없는 "말단(leaf)" 커밋.

    결과를 뒤집으면(reverse) 부모가 먼저 오는 순서가 됩니다.

    ── 시간복잡도: O(V + E) ──
    V = 커밋 수, E = 부모-자식 간선 수
    각 노드와 간선을 정확히 한 번씩 처리합니다.

    Args:
        commits_dict (dict): {해시: Commit 객체} 형태의 딕셔너리

    Returns:
        list: 위상 정렬된 Commit 객체 리스트 (부모가 자식보다 먼저)
    """
    # ── 커밋이 없으면 빈 리스트 반환 ──
    if not commits_dict:
        return []

    # ── Step 1: 진입차수(in-degree) 계산 ──
    # 여기서 "진입차수"는 "나를 부모로 참조하는 자식 커밋의 수"입니다.
    # 즉, 간선 방향이 자식 → 부모일 때, 부모 노드에 들어오는 간선 수입니다.
    in_degree = {}  # {커밋 해시: 진입차수}

    # 모든 커밋의 진입차수를 0으로 초기화합니다.
    for commit_hash in commits_dict:
        in_degree[commit_hash] = 0

    # 각 커밋의 부모들의 진입차수를 1씩 증가시킵니다.
    # 자식 → 부모 간선이 있으면, 부모의 진입차수가 증가합니다.
    for commit_hash, commit in commits_dict.items():
        for parent_hash in commit.parents:
            if parent_hash in in_degree:
                in_degree[parent_hash] += 1

    # ── Step 2: 진입차수 0인 노드를 큐에 추가 ──
    # 진입차수 0 = 자식이 없는 말단 커밋 (가장 최근 커밋들)
    queue = deque()
    for commit_hash, degree in in_degree.items():
        if degree == 0:
            queue.append(commit_hash)

    # ── Step 3: BFS 스타일로 노드를 순서대로 처리 ──
    result = []  # 위상 정렬 결과

    while queue:
        # 큐에서 노드를 꺼냅니다.
        current_hash = queue.popleft()
        current_commit = commits_dict[current_hash]
        result.append(current_commit)

        # 현재 노드의 부모들의 진입차수를 감소시킵니다.
        # 진입차수가 0이 되면 큐에 추가합니다.
        for parent_hash in current_commit.parents:
            if parent_hash in in_degree:
                in_degree[parent_hash] -= 1
                if in_degree[parent_hash] == 0:
                    queue.append(parent_hash)

    # ── Step 4: 결과를 뒤집어서 "부모가 먼저"인 순서로 만듭니다 ──
    # Kahn's 알고리즘은 진입차수 0 (자식 없는 것)부터 시작하므로,
    # 결과를 뒤집으면 루트(부모)가 먼저 옵니다.
    result.reverse()

    return result


def find_shortest_path(commits_dict, hash1, hash2):
    """
    두 커밋 사이의 최단 경로를 BFS로 찾습니다.

    ── 미션 정의 ──
    "커밋-부모 연결을 무방향 간선으로 간주했을 때의 최단 경로"입니다.
    즉, 부모→자식 방향뿐 아니라 자식→부모 방향으로도 이동할 수 있습니다.

    ── 왜 BFS가 최단 경로를 보장하는가? ──
    BFS는 시작점에서 거리 1인 노드를 모두 방문한 후,
    거리 2인 노드를 모두 방문하고, 거리 3인 노드를 방문하고...
    이렇게 "레벨 순서"로 탐색합니다.

    따라서 목적지를 처음 발견한 시점이 곧 최단 경로입니다.
    이것은 간선의 가중치가 모두 동일할 때만 성립합니다.
    (가중치가 다르면 Dijkstra 알고리즘을 써야 합니다.)

    ── 사전순 최소 경로 선택 ──
    미션에서 "최단 경로가 여러 개면, 경로를 hash1->hash2->... 문자열로
    만들었을 때 사전순이 가장 작은 경로를 선택"하라고 했습니다.

    이를 위해 인접 노드를 정렬하여 사전순으로 먼저 탐색합니다.
    BFS에서 같은 거리의 경로 중 사전순 최소를 보장하려면,
    각 노드에서 이웃을 정렬된 순서로 탐색해야 합니다.

    ── 구현 방식 ──
    1. 먼저 무방향 인접 리스트를 구축합니다.
    2. hash1에서 BFS를 시작합니다.
    3. 각 노드에서 방문할 이웃을 정렬된 순서로 처리합니다.
    4. hash2에 도달하면 경로를 역추적합니다.

    ── 시간복잡도: O(V + E) ──
    (인접 노드 정렬 비용은 각 노드의 차수에 비례하므로,
     전체적으로 O(E log E)가 추가될 수 있습니다.)

    Args:
        commits_dict (dict): {해시: Commit 객체} 딕셔너리
        hash1 (str): 시작 커밋 해시
        hash2 (str): 목적지 커밋 해시

    Returns:
        list or None: 최단 경로의 해시 리스트 (예: ["a1b2c3", "d4e5f6"])
                      경로가 없으면 None
    """
    # ── 같은 커밋인 경우 ──
    if hash1 == hash2:
        return [hash1]

    # ── Step 1: 무방향 인접 리스트 구축 ──
    # 각 커밋 노드에 대해, 부모-자식 관계를 양방향으로 연결합니다.
    # 예: 자식 A → 부모 B이면,
    #     adjacency[A]에 B를 추가하고, adjacency[B]에 A도 추가합니다.
    adjacency = {}  # {커밋 해시: [이웃 해시 목록]}

    for commit_hash in commits_dict:
        adjacency[commit_hash] = []

    for commit_hash, commit in commits_dict.items():
        for parent_hash in commit.parents:
            if parent_hash in commits_dict:
                # 양방향 간선 추가
                adjacency[commit_hash].append(parent_hash)
                adjacency[parent_hash].append(commit_hash)

    # ── Step 2: BFS 실행 ──
    # visited: 방문 여부를 추적합니다 (같은 노드를 다시 방문하지 않기 위해)
    # parent_map: 경로 역추적을 위한 "부모 기록"
    #             parent_map[B] = A → "B를 발견한 것은 A에서 출발했을 때"
    visited = set()
    parent_map = {}  # {노드: 이전 노드} — BFS 트리의 부모를 기록

    queue = deque()
    queue.append(hash1)
    visited.add(hash1)

    found = False  # 목적지 발견 여부

    while queue:
        current = queue.popleft()

        # 목적지에 도달했으면 탐색 종료
        if current == hash2:
            found = True
            break

        # ── 이웃 노드를 정렬된 순서로 탐색 ──
        # 정렬하면 사전순으로 먼저 오는 해시를 먼저 방문합니다.
        # 이것이 "사전순 최소 경로"를 보장하는 핵심입니다.
        # 주의: 여기서는 커스텀 정렬이 아닌 문자열 비교이므로
        #       Python의 기본 비교를 활용합니다.
        #       (미션의 정렬 금지는 커밋 목록 정렬에 해당)
        neighbors = adjacency.get(current, [])
        # 인접 노드를 정렬하기 위해 간단한 삽입 정렬을 사용합니다.
        # (미션에서 sorted()/list.sort() 사용 금지)
        sorted_neighbors = _insertion_sort_strings(neighbors)

        for neighbor in sorted_neighbors:
            if neighbor not in visited:
                visited.add(neighbor)
                parent_map[neighbor] = current
                queue.append(neighbor)

    # ── Step 3: 경로 역추적 ──
    if not found:
        return None

    # parent_map을 따라 hash2에서 hash1까지 역으로 추적합니다.
    path = []
    current = hash2
    while current != hash1:
        path.append(current)
        current = parent_map[current]
    path.append(hash1)

    # 역순으로 추적했으므로 뒤집어서 hash1 → hash2 순서로 만듭니다.
    path.reverse()

    return path


def _insertion_sort_strings(arr):
    """
    문자열 배열을 삽입 정렬로 정렬합니다.

    BFS에서 인접 노드를 사전순으로 탐색하기 위해 사용합니다.
    sorted()/list.sort() 사용이 금지되었으므로 직접 구현합니다.

    ── 삽입 정렬(Insertion Sort) ──
    - 배열을 앞에서부터 순회하며, 각 원소를 "이미 정렬된 부분"의
      올바른 위치에 삽입합니다.
    - 시간복잡도: O(n²) 최악, O(n) 최선 (이미 정렬된 경우)
    - 인접 리스트 크기는 보통 작으므로(커밋의 부모 수 ≤ 2~3) 충분합니다.

    Args:
        arr (list): 정렬할 문자열 리스트

    Returns:
        list: 정렬된 새 리스트 (원본은 변경되지 않음)
    """
    # 원본을 변경하지 않기 위해 복사합니다.
    result = arr[:]

    # 두 번째 원소부터 시작합니다 (첫 번째 원소는 이미 "정렬됨").
    for i in range(1, len(result)):
        key = result[i]  # 현재 삽입할 원소
        j = i - 1

        # key보다 큰 원소들을 오른쪽으로 한 칸씩 밀어냅니다.
        while j >= 0 and result[j] > key:
            result[j + 1] = result[j]
            j -= 1

        # key를 올바른 위치에 삽입합니다.
        result[j + 1] = key

    return result


def find_ancestors(commits_dict, commit_hash):
    """
    특정 커밋의 모든 조상을 DFS로 찾습니다.

    ── 조상(Ancestor)이란? ──
    커밋 A의 조상은, A에서 부모 포인터를 따라가며 도달할 수 있는 모든 커밋입니다.
    즉, A의 부모, 부모의 부모, 부모의 부모의 부모... 모두가 조상입니다.

    ── 왜 DFS를 사용하는가? ──
    조상 탐색은 "도달 가능한 모든 노드를 찾는 문제"입니다.
    BFS와 DFS 모두 가능하지만, DFS가 더 직관적입니다:
    - 한 조상 경로를 끝까지 따라간 후, 다른 경로를 탐색합니다.
    - 스택 기반이므로 구현이 간결합니다.

    ── DAG에서의 주의점 ──
    머지 커밋이 있으면 같은 조상에 여러 경로로 도달할 수 있습니다.
    visited set을 사용하여 중복 방문을 방지합니다.

       A (merge commit)
      / \
     B   C
      \ /
       D (공통 조상)

    위 그래프에서 A의 조상을 찾을 때, D는 B를 거쳐서도, C를 거쳐서도 도달 가능합니다.
    visited가 없으면 D를 두 번 방문하고, D의 조상도 두 번 탐색하게 됩니다.

    ── 시간복잡도: O(V + E) ──
    각 노드와 간선을 최대 한 번씩 방문합니다.

    Args:
        commits_dict (dict): {해시: Commit 객체} 딕셔너리
        commit_hash (str): 조상을 찾을 커밋의 해시

    Returns:
        list: 조상 커밋 해시 리스트 (자기 자신은 포함하지 않음)
    """
    # ── 시작 커밋 존재 확인 ──
    if commit_hash not in commits_dict:
        return []

    # ── DFS를 위한 자료구조 초기화 ──
    # 스택 기반 반복적 DFS를 사용합니다 (재귀 대신).
    # 재귀는 Python의 스택 깊이 제한(기본 1000)에 걸릴 수 있으므로,
    # 명시적 스택을 사용하는 것이 안전합니다.
    ancestors = []   # 발견된 조상 목록
    visited = set()  # 방문한 노드 기록 (중복 방문 방지)
    stack = []       # DFS 스택

    # ── 시작 커밋의 부모들을 스택에 추가 ──
    # 자기 자신은 조상이 아니므로, 부모부터 시작합니다.
    start_commit = commits_dict[commit_hash]
    for parent_hash in start_commit.parents:
        if parent_hash in commits_dict:
            stack.append(parent_hash)

    # ── DFS 반복 ──
    while stack:
        # 스택에서 노드를 꺼냅니다 (LIFO: Last In, First Out).
        current = stack.pop()

        # 이미 방문한 노드는 건너뜁니다.
        if current in visited:
            continue

        # ── 방문 처리 ──
        visited.add(current)
        ancestors.append(current)

        # ── 현재 노드의 부모들을 스택에 추가 ──
        current_commit = commits_dict[current]
        for parent_hash in current_commit.parents:
            if parent_hash in commits_dict and parent_hash not in visited:
                stack.append(parent_hash)

    return ancestors

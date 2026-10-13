"""커밋 그래프에서 사용하는 세 가지 탐색.

커밋의 parents는 새 커밋 → 오래된 커밋 방향이다. LOG는 부모가 먼저
나와야 하므로 방향을 뒤집어 생각하고, PATH는 간선을 양방향으로 본다.
"""

from __future__ import annotations

from collections import deque

from minigit.models import Commit
from minigit.sorting import merge_sort


def topological_sort(commits: dict[str, Commit]) -> list[Commit]:
    """모든 부모를 자식보다 먼저 돌려준다. Kahn 위상 정렬, O(V+E).

    remaining_parents[id]는 아직 출력되지 않은 부모의 수다.
    값이 0인 커밋부터 큐에 넣고, 출력할 때마다 자식의 수를 하나 줄인다.
    """
    children: dict[str, list[str]] = {}
    remaining_parents: dict[str, int] = {}
    for commit_hash in commits:
        # 모든 ID의 빈 자식 목록을 먼저 만든다. 첫 커밋도 빠뜨리지 않기 위해서다.
        children[commit_hash] = []

    # items()는 (ID, Commit 객체) 쌍을 하나씩 준다.
    for commit_hash, commit in commits.items():
        remaining_parents[commit_hash] = 0
        for parent_hash in commit.parents:
            if parent_hash in commits:
                # 원래 저장 방향(자식 → 부모)을 뒤집어 부모 → 자식 표를 만든다.
                children[parent_hash].append(commit_hash)
                remaining_parents[commit_hash] += 1

    # deque의 popleft()는 먼저 넣은 항목을 빠르게 꺼낸다(FIFO).
    ready: deque[str] = deque()
    for commit_hash in commits:
        if remaining_parents[commit_hash] == 0:
            ready.append(commit_hash)
    result: list[Commit] = []

    while ready:
        commit_hash = ready.popleft()
        result.append(commits[commit_hash])
        for child_hash in children[commit_hash]:
            # 부모 하나를 출력했으므로 자식이 기다릴 부모 수를 하나 줄인다.
            remaining_parents[child_hash] -= 1
            if remaining_parents[child_hash] == 0:
                ready.append(child_hash)

    if len(result) != len(commits):
        raise ValueError("Commit graph contains a cycle")
    return result


def find_shortest_path(
    commits: dict[str, Commit], start: str, target: str
) -> list[str] | None:
    """부모 연결을 양방향으로 본 최단 경로를 BFS로 찾는다.

    같은 길이면 ID 뒤의 구분자까지 비교해 전체 경로 문자열 순서를 따른다.
    'a'와 'a!'처럼 ID가 접두사를 공유해도 'a->'와 'a!->'를 비교한다.
    ID 안의 '->'는 금지한다. 저장소가 생성하는 ID에는 이 구분자가 없다.
    """
    if start not in commits or target not in commits:
        return None
    if start == target:
        return [start]

    adjacency: dict[str, list[str]] = {}
    for commit_hash in commits:
        if "->" in commit_hash:
            raise ValueError("Commit ID cannot contain the path separator '->'")
        adjacency[commit_hash] = []
    for commit_hash, commit in commits.items():
        for parent_hash in commit.parents:
            if parent_hash in commits:
                # 양방향 길: 자식에서도 부모로, 부모에서도 자식으로 갈 수 있다.
                adjacency[commit_hash].append(parent_hash)
                adjacency[parent_hash].append(commit_hash)

    # dict[발견한 ID] = 직전에 방문한 ID. 이 표로 도착점부터 되짚는다.
    previous: dict[str, str] = {}
    visited = {start}
    queue = deque([start])

    while queue:
        current = queue.popleft()
        # 같은 거리의 경로 중 사전순 첫 경로를 고르려고 이웃을 정렬한다.
        for neighbor in merge_sort(adjacency[current], key_func=lambda neighbor: neighbor + "->"):
            if neighbor in visited:
                continue
            # 큐에 넣을 때 방문 표시하여 여러 경로가 같은 ID를 중복 예약하지 않게 한다.
            visited.add(neighbor)
            previous[neighbor] = current
            if neighbor == target:
                path = [target]
                # path[-1]은 현재 리스트의 마지막 ID다. previous를 따라 출발점까지 간다.
                while path[-1] != start:
                    path.append(previous[path[-1]])
                path.reverse()
                return path
            queue.append(neighbor)
    return None


def find_ancestors(commits: dict[str, Commit], commit_hash: str) -> list[str]:
    """부모 방향으로만 DFS를 하여 중복 없는 조상 ID를 돌려준다."""
    if commit_hash not in commits:
        return []

    # list.pop()은 마지막 항목부터 꺼낸다(LIFO). 이것이 DFS의 스택이다.
    stack = commits[commit_hash].parents[:]
    visited: set[str] = set()
    ancestors: list[str] = []

    while stack:
        current = stack.pop()
        if current not in commits or current in visited:
            continue
        # 병합 뒤 공통 조상은 여러 갈래에서 다시 만나므로 한 번만 넣는다.
        visited.add(current)
        ancestors.append(current)
        for parent_hash in commits[current].parents:
            stack.append(parent_hash)
    return ancestors

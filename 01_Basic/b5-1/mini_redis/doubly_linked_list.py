"""
[DoublyLinkedList: 이중 연결 리스트 및 Sentinel Node 패턴 구현 모듈]

1. 어떤 로직인가:
   - 양방향 포인터(`prev`, `next`)를 가진 노드들과, 양 끝단에 위치한 Head/Tail Sentinel(더미) 노드로 구성된 이중 연결 리스트입니다.

2. 왜 존재하는가 (존재 이유 및 목적):
   - Redis의 핵심인 LRU(Least Recently Used) 캐시 교체 정책을 구현할 때,
     노드의 참조만 가지고 있다면 O(1) 시간 내에 노드를 떼어내거나(`remove_node`)
     맨 앞으로 이동(`move_to_front`)시키기 위해 존재합니다.
   - Head와 Tail 더미 노드는 "리스트가 비어있을 때" 나 "첫 노드를 지울 때" 일일이 `if node.prev is None` 같은
     복잡한 null 에러 검사를 하지 않아도 되도록 코드를 대폭 단순화(Sentinel Pattern)합니다.

3. 알고리즘 및 시간 복잡도:
   - 맨 앞/뒤 삽입 (`insert_front`, `insert_back`): O(1)
   - 노드 고립 제거 (`remove_node`): O(1)
   - 맨 앞으로 이동 (`move_to_front`): O(1)
"""

from typing import Any, Optional, List


class Node:
    """
    [이중 연결 리스트 노드]
    1. 어떤 로직인가: key, value와 함께 앞(`prev`), 뒤(`next`) 노드의 메모리 주소를 가지는 객체입니다.
    2. 왜 존재하는가: 양방향으로 연결된 노드 관계를 형성하기 위함입니다.
    """

    def __init__(self, key: Optional[str] = None, value: Any = None) -> None:
        """무엇: __init__ 연산을 수행합니다.
        상태: 필요한 값, 연결, 또는 크기만 갱신하고 자료구조 불변식을 유지합니다.
        이유: 상위 Redis 명령이 예측 가능한 결과와 일관된 상태를 전제로 이 연산을 조합합니다.
        복잡도: 직접 접근은 O(1), 순회나 재배치가 있으면 O(N)."""
        self.key: Optional[str] = key     # Redis 키 (예: "user:1")
        self.value: Any = value           # Redis 값 (예: "Alice")
        self.prev: Optional["Node"] = None # 이전 노드 참조 포인터
        self.next: Optional["Node"] = None # 다음 노드 참조 포인터


class DoublyLinkedList:
    """
    Head/Tail 더미 노드 기반 이중 연결 리스트 클래스입니다.
    """

    def __init__(self) -> None:
        """무엇: __init__ 연산을 수행합니다.
        상태: 필요한 값, 연결, 또는 크기만 갱신하고 자료구조 불변식을 유지합니다.
        이유: 상위 Redis 명령이 예측 가능한 결과와 일관된 상태를 전제로 이 연산을 조합합니다.
        복잡도: 직접 접근은 O(1), 순회나 재배치가 있으면 O(N)."""
        self.head: Node = Node()
        self.tail: Node = Node()

        # Head <-> Tail 연결 (처음엔 둘만 연결된 빈 리스트 상태)
        self.head.next = self.tail
        self.tail.prev = self.head
        self._size: int = 0

    def __len__(self) -> int:
        """무엇: __len__ 연산을 수행합니다.
        상태: 필요한 값, 연결, 또는 크기만 갱신하고 자료구조 불변식을 유지합니다.
        이유: 상위 Redis 명령이 예측 가능한 결과와 일관된 상태를 전제로 이 연산을 조합합니다.
        복잡도: 직접 접근은 O(1), 순회나 재배치가 있으면 O(N)."""
        return self._size

    def is_empty(self) -> bool:
        """무엇: is_empty 연산을 수행합니다.
        상태: 필요한 값, 연결, 또는 크기만 갱신하고 자료구조 불변식을 유지합니다.
        이유: 상위 Redis 명령이 예측 가능한 결과와 일관된 상태를 전제로 이 연산을 조합합니다.
        복잡도: 직접 접근은 O(1), 순회나 재배치가 있으면 O(N)."""
        return self._size == 0

    def insert_front(self, node: Node) -> None:
        """무엇: insert_front 연산을 수행합니다.
        상태: 필요한 값, 연결, 또는 크기만 갱신하고 자료구조 불변식을 유지합니다.
        이유: 상위 Redis 명령이 예측 가능한 결과와 일관된 상태를 전제로 이 연산을 조합합니다.
        복잡도: 직접 접근은 O(1), 순회나 재배치가 있으면 O(N)."""
        if node is None:
            raise ValueError("Node cannot be None")

        first_node: Optional[Node] = self.head.next

        # 4개의 포인터를 재연결하여 노드를 Head와 기존 첫 노드 사이에 끼워넣음
        node.prev = self.head
        node.next = first_node

        self.head.next = node
        if first_node is not None:
            first_node.prev = node

        self._size += 1

    def add_front(self, key: str, value: Any) -> Node:
        """무엇: add_front 연산을 수행합니다.
        상태: 필요한 값, 연결, 또는 크기만 갱신하고 자료구조 불변식을 유지합니다.
        이유: 상위 Redis 명령이 예측 가능한 결과와 일관된 상태를 전제로 이 연산을 조합합니다.
        복잡도: 직접 접근은 O(1), 순회나 재배치가 있으면 O(N)."""
        node = Node(key=key, value=value)
        self.insert_front(node)
        return node

    def insert_back(self, node: Node) -> None:
        """무엇: insert_back 연산을 수행합니다.
        상태: 필요한 값, 연결, 또는 크기만 갱신하고 자료구조 불변식을 유지합니다.
        이유: 상위 Redis 명령이 예측 가능한 결과와 일관된 상태를 전제로 이 연산을 조합합니다.
        복잡도: 직접 접근은 O(1), 순회나 재배치가 있으면 O(N)."""
        if node is None:
            raise ValueError("Node cannot be None")

        last_node: Optional[Node] = self.tail.prev

        node.prev = last_node
        node.next = self.tail

        if last_node is not None:
            last_node.next = node
        self.tail.prev = node

        self._size += 1

    def remove_node(self, node: Node) -> None:
        """무엇: 앞과 뒤 노드를 직접 연결해 대상 노드를 제거합니다.
        상태: 대상 포인터를 해제하고 size가 하나 줄어듭니다.
        이유: 노드를 이미 알고 있으면 탐색 없이 LRU 순서를 갱신하거나 삭제할 수 있습니다.
        복잡도: O(1)."""
        if node is None or node.prev is None or node.next is None:
            return

        prev_node: Node = node.prev
        next_node: Node = node.next

        # 앞 노드의 next를 뒤 노드로, 뒤 노드의 prev를 앞 노드로 바로 연결!
        prev_node.next = next_node
        next_node.prev = prev_node

        # 고립된 노드의 포인터 해제 (메모리 해제 및 버그 방지)
        node.prev = None
        node.next = None

        self._size -= 1

    def move_to_front(self, node: Node) -> None:
        """무엇: 기존 노드를 head 뒤의 MRU 위치로 이동합니다.
        상태: 키와 값은 유지되고 최근 사용 순서만 바뀝니다.
        이유: GET과 SET 성공이 같은 LRU 규칙을 적용합니다.
        복잡도: O(1)."""
        if node is None:
            return

        self.remove_node(node)
        self.insert_front(node)

    def remove_back(self) -> Optional[Node]:
        """무엇: remove_back 연산을 수행합니다.
        상태: 필요한 값, 연결, 또는 크기만 갱신하고 자료구조 불변식을 유지합니다.
        이유: 상위 Redis 명령이 예측 가능한 결과와 일관된 상태를 전제로 이 연산을 조합합니다.
        복잡도: 직접 접근은 O(1), 순회나 재배치가 있으면 O(N)."""
        if self.is_empty():
            return None

        lru_node: Optional[Node] = self.tail.prev
        if lru_node is not None and lru_node != self.head:
            self.remove_node(lru_node)
            return lru_node
        return None

    def remove_front(self) -> Optional[Node]:
        """무엇: remove_front 연산을 수행합니다.
        상태: 필요한 값, 연결, 또는 크기만 갱신하고 자료구조 불변식을 유지합니다.
        이유: 상위 Redis 명령이 예측 가능한 결과와 일관된 상태를 전제로 이 연산을 조합합니다.
        복잡도: 직접 접근은 O(1), 순회나 재배치가 있으면 O(N)."""
        if self.is_empty():
            return None

        front_node: Optional[Node] = self.head.next
        if front_node is not None and front_node != self.tail:
            self.remove_node(front_node)
            return front_node
        return None

    def values(self) -> List[Any]:
        """무엇: values 연산을 수행합니다.
        상태: 필요한 값, 연결, 또는 크기만 갱신하고 자료구조 불변식을 유지합니다.
        이유: 상위 Redis 명령이 예측 가능한 결과와 일관된 상태를 전제로 이 연산을 조합합니다.
        복잡도: 직접 접근은 O(1), 순회나 재배치가 있으면 O(N)."""
        result: List[Any] = []
        curr: Optional[Node] = self.head.next
        while curr is not None and curr != self.tail:
            result.append(curr.value)
            curr = curr.next
        return result

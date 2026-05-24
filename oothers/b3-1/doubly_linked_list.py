class Node:
    """
    이중 연결 리스트(Doubly Linked List)와 해시맵 체이닝에 사용될 노드 클래스입니다.
    데이터 무결성과 포인터 추적을 위해 prev, next, key, value 속성을 가집니다.
    """
    def __init__(self, key=None, value=None):
        self.key = key       # 데이터 식별자 (예: Redis의 키 문자열)
        self.value = value   # 실제 저장되는 값
        self.prev = None     # 이전 노드를 가리키는 포인터
        self.next = None     # 다음 노드를 가리키는 포인터

class DoublyLinkedList:
    """
    이중 연결 리스트(Doubly Linked List) 구현 클래스입니다.
    
    Head와 Tail 쪽에 더미(Dummy) 노드(Sentinel Node)를 두어,
    노드 삽입/삭제 시 경계 조건(Edge cases: 리스트가 비어있거나 노드가 양 끝일 때)을
    예외 처리 없이 깔끔하고 O(1) 시간 복잡도로 다룰 수 있게 설계되었습니다.
    
    이 자료구조는 Redis의 LRU(Least Recently Used) 추적뿐만 아니라,
    해시맵의 버킷 체이닝 및 Pub/Sub의 메시지 큐 등 다양한 목적으로 재사용 가능합니다.
    """
    def __init__(self):
        self.head = Node()  # 맨 앞 더미 노드 (가장 최근에 사용된 데이터, Most Recently Used)
        self.tail = Node()  # 맨 뒤 더미 노드 (가장 오래전에 사용된 데이터, Least Recently Used)
        
        # 처음 생성 시 head와 tail을 서로 연결 (리스트 비어있음)
        self.head.next = self.tail
        self.tail.prev = self.head
        self._size = 0
        
    def __len__(self) -> int:
        return self._size
        
    def is_empty(self) -> bool:
        return self._size == 0

    def insert_front(self, node: Node) -> None:
        """
        주어진 노드를 리스트의 맨 앞(head 바로 다음)에 삽입합니다. (O(1))
        LRU 정책에서 '새롭게 생성되거나 조회된 데이터'를 가장 최신 상태로 갱신할 때 사용합니다.
        
        :param node: 삽입할 Node 인스턴스
        """
        # 기존에 head 바로 다음에 있던 첫 번째 노드
        first_node = self.head.next
        
        # 새로운 노드의 연결 설정
        node.prev = self.head
        node.next = first_node
        
        # 기존 노드들의 연결 업데이트
        self.head.next = node
        first_node.prev = node
        
        self._size += 1

    def insert_back(self, node: Node) -> None:
        """
        주어진 노드를 리스트의 맨 뒤(tail 바로 앞)에 삽입합니다. (O(1))
        큐(Queue)로 사용할 때 enqueue 연산에 해당합니다.
        
        :param node: 삽입할 Node 인스턴스
        """
        last_node = self.tail.prev
        
        node.prev = last_node
        node.next = self.tail
        
        last_node.next = node
        self.tail.prev = node
        
        self._size += 1

    def remove_node(self, node: Node) -> None:
        """
        특정 노드를 리스트에서 삭제합니다. (O(1))
        이중 연결 리스트의 강력한 장점으로, 노드의 참조만 알고 있다면
        배열처럼 O(N) 순회 없이 앞뒤 포인터 조작만으로 즉시 제거가 가능합니다.
        
        :param node: 삭제할 Node 인스턴스
        """
        prev_node = node.prev
        next_node = node.next
        
        # 앞 노드의 next를 뒤 노드로, 뒤 노드의 prev를 앞 노드로 연결하여 대상 노드 고립
        prev_node.next = next_node
        next_node.prev = prev_node
        
        # 고립된 노드의 포인터 초기화 (메모리 해제 및 버그 방지)
        node.prev = None
        node.next = None
        
        self._size -= 1

    def move_to_front(self, node: Node) -> None:
        """
        이미 리스트에 존재하는 특정 노드를 맨 앞으로 이동시킵니다. (O(1))
        LRU 캐시에서 '기존 데이터가 다시 조회/수정 되었을 때' 최신 상태로 갱신하기 위한 핵심 연산입니다.
        
        :param node: 맨 앞으로 옮길 Node 인스턴스
        """
        self.remove_node(node)    # 현재 위치에서 제거
        self.insert_front(node)   # 맨 앞으로 삽입

    def remove_back(self) -> Node:
        """
        리스트의 가장 뒤(tail 바로 앞)에 있는 노드를 삭제하고 반환합니다. (O(1))
        메모리 초과 시 LRU 제거 정책에 의해 '가장 오래 사용되지 않은(Least Recently Used)'
        데이터를 추출하고 삭제할 때 사용합니다.
        
        :return: 삭제된 맨 뒤의 노드, 비어있으면 None 반환
        """
        if self.is_empty():
            return None
            
        lru_node = self.tail.prev
        self.remove_node(lru_node)
        return lru_node
        
    def remove_front(self) -> Node:
        """
        리스트의 가장 앞(head 바로 뒤)에 있는 노드를 삭제하고 반환합니다. (O(1))
        큐(Queue)로 사용할 때 dequeue 연산에 해당합니다.
        
        :return: 삭제된 맨 앞의 노드, 비어있으면 None 반환
        """
        if self.is_empty():
            return None
            
        front_node = self.head.next
        self.remove_node(front_node)
        return front_node

    def values(self):
        """
        리스트 내의 모든 노드 값을 배열 형태로 순차적 반환합니다. (O(N))
        디버깅 및 테스트, 혹은 큐 전체 조회를 위해 사용합니다.
        
        :return: 모든 값들의 리스트
        """
        result = []
        curr = self.head.next
        while curr != self.tail:
            result.append(curr.value)
            curr = curr.next
        return result

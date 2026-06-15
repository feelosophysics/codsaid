from dynamic_array import DynamicArray

class MinHeap:
    """
    최소 힙(Min-Heap) 구현 클래스입니다.
    완전 이진 트리(Complete Binary Tree) 구조를 1차원 배열(DynamicArray)을 통해 구현합니다.
    부모 노드 인덱스 = (현재 인덱스 - 1) // 2
    왼쪽 자식 인덱스 = 현재 인덱스 * 2 + 1
    오른쪽 자식 인덱스 = 현재 인덱스 * 2 + 2
    
    이 클래스는 Mini Redis에서 TTL(Time-To-Live) 관리를 위해 사용됩니다.
    저장되는 아이템은 주로 (만료_타임스탬프, 키) 형태의 튜플이며,
    만료 시간이 가장 적은(가장 먼저 만료되는) 아이템이 항상 루트(인덱스 0)에 위치합니다.
    """
    def __init__(self):
        # 내부 저장소로 내장 list 대신 직접 구현한 동적 배열 사용
        self._data = DynamicArray()

    def __len__(self) -> int:
        return len(self._data)
        
    def is_empty(self) -> bool:
        return self._data.is_empty()

    def _swap(self, i: int, j: int) -> None:
        """
        배열의 두 인덱스 값을 교환합니다.
        """
        temp = self._data.get(i)
        self._data.set(i, self._data.get(j))
        self._data.set(j, temp)

    def _heapify_up(self, index: int) -> None:
        """
        삽입(push) 시 트리의 아래에서 위로 올라가며 최소 힙 속성(부모 <= 자식)을 복구합니다.
        시간 복잡도: O(log N)
        """
        parent_idx = (index - 1) // 2
        
        # 현재 노드가 루트가 아니고, 현재 노드의 값이 부모 노드의 값보다 작다면 스왑 (최소 힙)
        # 아이템 비교 시 튜플의 첫 번째 요소(만료 시간)를 기준으로 비교됨
        while index > 0 and self._data.get(index) < self._data.get(parent_idx):
            self._swap(index, parent_idx)
            index = parent_idx
            parent_idx = (index - 1) // 2

    def _heapify_down(self, index: int) -> None:
        """
        추출(pop) 시 트리의 루트에서 아래로 내려가며 최소 힙 속성을 복구합니다.
        시간 복잡도: O(log N)
        """
        size = len(self._data)
        while True:
            smallest = index
            left_child_idx = 2 * index + 1
            right_child_idx = 2 * index + 2
            
            # 왼쪽 자식이 존재하고 현재 노드(혹은 지금까지 찾은 최솟값)보다 작다면 smallest 갱신
            if left_child_idx < size and self._data.get(left_child_idx) < self._data.get(smallest):
                smallest = left_child_idx
                
            # 오른쪽 자식이 존재하고 지금까지 찾은 최솟값보다 작다면 smallest 갱신
            if right_child_idx < size and self._data.get(right_child_idx) < self._data.get(smallest):
                smallest = right_child_idx
                
            # 자식 노드 중 더 작은 값이 없어 속성이 만족되었다면 종료
            if smallest == index:
                break
                
            self._swap(index, smallest)
            index = smallest

    def push(self, item) -> None:
        """
        새로운 아이템을 힙에 삽입합니다. (O(log N))
        
        :param item: 삽입할 요소, 보통 (만료 시간, 키) 튜플 형태
        """
        self._data.append(item)
        self._heapify_up(len(self._data) - 1)

    def pop(self):
        """
        힙에서 최솟값(가장 상단의 값)을 제거하고 반환합니다. (O(log N))
        
        :return: 최소값 아이템
        """
        if self.is_empty():
            raise IndexError("pop from empty MinHeap")
            
        size = len(self._data)
        
        if size == 1:
            return self._data.pop()
            
        # 루트 노드 백업 (반환용)
        root = self._data.get(0)
        
        # 가장 마지막 노드를 루트로 옮기고, 마지막 노드 삭제
        last_item = self._data.pop()
        self._data.set(0, last_item)
        
        # 루트부터 아래로 재배열
        self._heapify_down(0)
        
        return root

    def peek(self):
        """
        최솟값(루트)을 제거하지 않고 반환만 합니다. (O(1))
        TTL 검사 로직(while peek()[0] < 현재시간)에서 매우 자주 사용됩니다.
        
        :return: 최소값 아이템, 비어있으면 None
        """
        if self.is_empty():
            return None
        return self._data.get(0)

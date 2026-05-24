class DynamicArray:
    """
    동적 배열(Dynamic Array) 구현 클래스입니다. (보너스 과제 5.1)
    
    파이썬의 내장 list 기능(append 등 동적 크기 조절)을 사용하지 않고, 
    오직 고정된 크기(capacity)를 가진 배열([None] * capacity)만 할당하여
    내부적으로 크기를 추적(size)하고 꽉 찰 경우 2배로 확장(resize)하는 로직을 직접 구현합니다.
    이 클래스는 이후 구현할 MinHeap이나 HashMap 버킷의 기본 저장소로 활용될 수 있습니다.
    """
    
    def __init__(self, capacity: int = 8):
        """
        초기화 메서드
        
        :param capacity: 초기 배열의 허용 용량 (기본값: 8)
        """
        if capacity <= 0:
            raise ValueError("Capacity must be greater than 0")
        
        self._capacity = capacity  # 현재 배열이 담을 수 있는 최대 요소 수
        self._size = 0             # 현재 배열에 실제 저장된 요소 수
        # 고정 크기 배열 할당 (이후 길이를 늘리거나 줄이는 연산 불가)
        self._data = [None] * self._capacity

    def __len__(self) -> int:
        """
        배열의 현재 크기를 반환합니다 (O(1)).
        """
        return self._size
        
    def is_empty(self) -> bool:
        """
        배열이 비어있는지 확인합니다 (O(1)).
        """
        return self._size == 0
        
    def _resize(self) -> None:
        """
        배열이 꽉 찼을 때 호출되며, 용량(capacity)을 2배로 늘린 새로운 고정 크기 배열을 생성하고
        기존 데이터를 복사합니다 (Amortized O(1), Worst O(N)).
        """
        new_capacity = self._capacity * 2
        new_data = [None] * new_capacity
        
        # 기존 배열의 요소들을 새로운 배열로 얕은 복사
        for i in range(self._size):
            new_data[i] = self._data[i]
            
        self._data = new_data
        self._capacity = new_capacity

    def append(self, value) -> None:
        """
        배열의 맨 끝에 새로운 값을 추가합니다 (Amortized O(1)).
        용량이 부족하면 내부적으로 _resize()가 호출됩니다.
        
        :param value: 추가할 데이터
        """
        if self._size == self._capacity:
            self._resize()
            
        self._data[self._size] = value
        self._size += 1

    def _check_bounds(self, index: int) -> None:
        """
        인덱스가 유효한 범위 내에 있는지 검사합니다.
        
        :param index: 검사할 인덱스
        :raises IndexError: 인덱스가 범위를 벗어나면 예외 발생
        """
        # 음수 인덱싱은 편의상 지원하지 않는 것으로 엄격히 제한
        if index < 0 or index >= self._size:
            raise IndexError(f"Index {index} out of bounds for size {self._size}")

    def get(self, index: int):
        """
        특정 인덱스의 값을 반환합니다 (O(1)).
        
        :param index: 가져올 요소의 인덱스
        :return: 저장된 데이터
        """
        self._check_bounds(index)
        return self._data[index]

    def set(self, index: int, value) -> None:
        """
        특정 인덱스의 값을 수정합니다 (O(1)).
        
        :param index: 수정할 요소의 인덱스
        :param value: 새로운 데이터
        """
        self._check_bounds(index)
        self._data[index] = value

    def remove_at(self, index: int) -> None:
        """
        특정 인덱스의 요소를 삭제하고, 뒤에 있는 요소들을 한 칸씩 앞으로 당깁니다 (O(N)).
        
        :param index: 삭제할 요소의 인덱스
        """
        self._check_bounds(index)
        
        # 삭제 대상의 다음 인덱스부터 끝까지, 값을 한 칸씩 앞(왼쪽)으로 덮어씀
        for i in range(index, self._size - 1):
            self._data[i] = self._data[i + 1]
            
        # 배열의 마지막 요소에 남아있는 기존 레퍼런스를 정리(메모리 누수 방지)
        self._data[self._size - 1] = None
        self._size -= 1
        
    def pop(self):
        """
        배열의 마지막 요소를 제거하고 반환합니다 (O(1)).
        MinHeap 등에서 활용하기 좋습니다.
        
        :return: 삭제된 데이터
        """
        if self.is_empty():
            raise IndexError("pop from empty DynamicArray")
            
        value = self._data[self._size - 1]
        self._data[self._size - 1] = None # 레퍼런스 해제
        self._size -= 1
        return value

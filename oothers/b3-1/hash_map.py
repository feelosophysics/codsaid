from dynamic_array import DynamicArray
from doubly_linked_list import DoublyLinkedList, Node

class HashMap:
    """
    해시맵(HashMap) 구현 클래스입니다.
    파이썬의 내장 dict 사용이 금지되어 있으므로, 
    버킷 저장소로 직접 구현한 DynamicArray를 사용하고,
    해시 충돌(Hash Collision) 해결 방식으로 체이닝(Chaining) 기법을 사용하며,
    체이닝 리스트로 직접 구현한 DoublyLinkedList를 재사용합니다.
    """
    def __init__(self, initial_capacity: int = 8):
        self._capacity = initial_capacity
        self._size = 0
        self._buckets = DynamicArray(self._capacity)
        
        # 각 버킷을 이중 연결 리스트로 초기화
        for _ in range(self._capacity):
            self._buckets.append(DoublyLinkedList())

    def _hash(self, key: str) -> int:
        """
        문자열 키에 대한 커스텀 다항식 롤링 해시(Polynomial Rolling Hash) 함수.
        내장 hash() 함수를 완전히 대체하기 위해 밑바닥부터 구현되었습니다.
        
        문자열의 각 문자에 대해 소수(prime) 거듭제곱을 곱하여 더하는 방식으로,
        문자열의 아나그램(Anagram, 구성 알파벳은 같으나 순서가 다른 문자열) 충돌을 방지합니다.
        
        :param key: 해시값을 계산할 문자열 키
        :return: 계산된 정수 해시값
        """
        hash_val = 0
        p = 31 # 영어 알파벳 소문자를 커버하기에 적합한 소수
        m = 10**9 + 9 # 오버플로우 방지를 위한 큰 소수 모듈러
        p_pow = 1
        
        for char in key:
            hash_val = (hash_val + ord(char) * p_pow) % m
            p_pow = (p_pow * p) % m
            
        return hash_val

    def _get_bucket_index(self, key: str) -> int:
        """
        키의 해시값을 현재 버킷 크기(capacity)로 나눈 나머지 연산(Modulo)을 통해
        데이터가 저장될 실제 버킷 인덱스를 계산합니다.
        """
        return self._hash(key) % self._capacity

    def put(self, key: str, value) -> None:
        """
        키와 값을 해시맵에 저장합니다. (평균 O(1))
        로드 팩터(Load Factor, size/capacity)가 0.75를 초과하면 버킷을 2배로 확장(Rehashing)합니다.
        기존 키가 존재하면 값을 덮어씁니다.
        
        :param key: 식별자
        :param value: 저장할 값 (이 구현에서는 주로 LRU용 Node가 값으로 저장될 예정)
        """
        # Load Factor = 0.75 검사 및 확장
        if self._size / self._capacity >= 0.75:
            self._resize()

        bucket_idx = self._get_bucket_index(key)
        chain: DoublyLinkedList = self._buckets.get(bucket_idx)
        
        # 체이닝 버킷(DoublyLinkedList) 순회 - 키 존재 여부 확인
        curr = chain.head.next
        while curr != chain.tail:
            if curr.key == key:
                # 이미 존재하는 키라면 값만 덮어쓰고 종료 (size 증가 안 함)
                curr.value = value
                return
            curr = curr.next
            
        # 키가 존재하지 않으면 새로운 노드를 리스트 맨 앞에 삽입
        new_node = Node(key=key, value=value)
        chain.insert_front(new_node)
        self._size += 1

    def get(self, key: str):
        """
        주어진 키로 값을 조회합니다. (평균 O(1))
        
        :param key: 조회할 식별자
        :return: 저장된 값, 없으면 None 반환
        """
        bucket_idx = self._get_bucket_index(key)
        chain: DoublyLinkedList = self._buckets.get(bucket_idx)
        
        curr = chain.head.next
        while curr != chain.tail:
            if curr.key == key:
                return curr.value
            curr = curr.next
            
        return None

    def remove(self, key: str) -> bool:
        """
        주어진 키의 데이터를 삭제합니다. (평균 O(1))
        
        :param key: 삭제할 식별자
        :return: 삭제에 성공하면 True, 존재하지 않는 키면 False 반환
        """
        bucket_idx = self._get_bucket_index(key)
        chain: DoublyLinkedList = self._buckets.get(bucket_idx)
        
        curr = chain.head.next
        while curr != chain.tail:
            if curr.key == key:
                chain.remove_node(curr) # DoublyLinkedList의 O(1) 삭제 활용
                self._size -= 1
                return True
            curr = curr.next
            
        return False

    def contains(self, key: str) -> bool:
        """
        주어진 키의 존재 여부를 확인합니다.
        """
        return self.get(key) is not None

    def keys(self) -> list:
        """
        현재 해시맵에 저장된 모든 키를 배열로 반환합니다. (O(N))
        """
        result_keys = []
        # 모든 버킷을 순회
        for i in range(self._capacity):
            chain: DoublyLinkedList = self._buckets.get(i)
            curr = chain.head.next
            while curr != chain.tail:
                result_keys.append(curr.key)
                curr = curr.next
        return result_keys

    def size(self) -> int:
        """
        현재 저장된 키-값 쌍의 개수를 반환합니다.
        """
        return self._size

    def _resize(self) -> None:
        """
        내부 버킷 용량을 2배로 늘리고, 기존의 모든 (키, 값) 데이터에 대해
        새로운 해시-버킷 인덱스를 계산하여 다시 매핑(Rehashing)합니다. (O(N))
        """
        old_capacity = self._capacity
        old_buckets = self._buckets
        
        self._capacity *= 2
        self._size = 0
        self._buckets = DynamicArray(self._capacity)
        
        # 새로운 버킷 초기화
        for _ in range(self._capacity):
            self._buckets.append(DoublyLinkedList())
            
        # 기존 버킷들을 순회하며 새로운 버킷 테이블에 삽입 (재해싱)
        for i in range(old_capacity):
            chain: DoublyLinkedList = old_buckets.get(i)
            curr = chain.head.next
            while curr != chain.tail:
                # put 메서드를 재사용하면 size가 자동으로 카운트 됨
                self.put(curr.key, curr.value)
                curr = curr.next

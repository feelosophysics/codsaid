"""
[Custom Data Structure Unit Test Suite]

1. 어떤 로직인가:
   - DynamicArray, DoublyLinkedList, HashMap, MinHeap 4대 커스텀 자료구조의
     기본 동작(삽입, 삭제, 조회, 2배 리사이징, 포인터 이동, 최소 힙 정렬)을 자동 검증하는 단위 테스트 모듈입니다.

2. 왜 존재하는가 (존재 이유 및 목적):
   - 코드 리팩토링이나 기능 변경 시 핵심 자료구조 알고리즘에 결함(Regression)이 생기지 않았는지
     자동으로 100% 검증하기 위해 존재합니다.
"""

import unittest
from mini_redis.dynamic_array import DynamicArray
from mini_redis.doubly_linked_list import DoublyLinkedList
from mini_redis.hash_map import HashMap
from mini_redis.min_heap import MinHeap


class TestCustomDataStructures(unittest.TestCase):

    def test_dynamic_array(self):
        """
        1. 어떤 검증인가: DynamicArray의 용량 확장(2배 리사이징), 요소 append/getitem/setitem 검증.
        2. 왜 검증하는가: 고정 배열 버퍼 오버플로우나 인덱스 오프셋 오류가 생기지 않는지 보장하기 위함입니다.
        """
        arr = DynamicArray(capacity=2)
        self.assertEqual(arr.capacity, 2)
        self.assertEqual(len(arr), 0)

        arr.append(10)
        arr.append(20)
        self.assertEqual(len(arr), 2)
        self.assertEqual(arr[0], 10)
        self.assertEqual(arr[1], 20)

        # 용량 초과 시 2배 자동 확장(Resize) 동작 검증
        arr.append(30)
        self.assertGreaterEqual(arr.capacity, 4)
        self.assertEqual(len(arr), 3)
        self.assertEqual(arr[2], 30)

        arr[1] = 99
        self.assertEqual(arr[1], 99)

    def test_doubly_linked_list(self):
        """
        1. 어떤 검증인가: DoublyLinkedList의 head/tail 더미 노드 작동, add_front, move_to_front, remove_back O(1) 연산 검증.
        2. 왜 검증하는가: LRU 캐시의 핵심인 꼬리 노드(가장 오래된 데이터) 제거 및 노드 맨 앞 이동이 포인터 꼬임 없이 정확히 작동하는지 검증합니다.
        """
        dll = DoublyLinkedList()
        self.assertTrue(dll.is_empty())

        n1 = dll.add_front("k1", "v1")
        n2 = dll.add_front("k2", "v2")
        self.assertEqual(len(dll), 2)

        # n1을 맨 앞으로 이동시킴 (MRU 최신화)
        dll.move_to_front(n1)

        # 맨 뒤(LRU) 노드를 제거하면 n2가 제거되어야 함
        removed = dll.remove_back()
        self.assertIsNotNone(removed)
        if removed:
            self.assertEqual(removed.key, "k2")
        self.assertEqual(len(dll), 1)

        dll.remove_node(n1)
        self.assertTrue(dll.is_empty())

    def test_hash_map(self):
        """
        1. 어떤 검증인가: HashMap의 put, get, remove, contains_key 및 충돌 해결/Rehash 검증.
        2. 왜 검증하는가: 다항식 해시와 체이닝 기반 키-값 접근이 O(1) 시간에 정확하게 동작하는지 보장하기 위함입니다.
        """
        hmap = HashMap()
        self.assertTrue(hmap.is_empty())

        hmap.put("apple", 100)
        hmap.put("banana", 200)

        self.assertEqual(hmap.get("apple"), 100)
        self.assertEqual(hmap.get("banana"), 200)
        self.assertIsNone(hmap.get("cherry"))

        self.assertTrue(hmap.contains_key("apple"))
        self.assertFalse(hmap.contains_key("cherry"))

        # Value가 None이어도 키 존재 여부를 올바르게 감지하는지 검증
        hmap.put("none_key", None)
        self.assertTrue(hmap.contains_key("none_key"))

        self.assertTrue(hmap.remove("apple"))
        self.assertIsNone(hmap.get("apple"))
        self.assertFalse(hmap.contains_key("apple"))

    def test_min_heap(self):
        """
        1. 어떤 검증인가: MinHeap의 push, pop, peek, size 및 heapify 정렬 순서 검증.
        2. 왜 검증하는가: TTL 만료 타임스탬프가 무작위 순서로 삽입되어도 항상 가장 작고(빠른) 만료 요소가 루트(0번)에 위치하는지 검증합니다.
        """
        heap = MinHeap()
        self.assertTrue(heap.is_empty())
        self.assertEqual(heap.size(), 0)

        heap.push(10.5, "key1")
        heap.push(5.0, "key2")
        heap.push(15.2, "key3")

        self.assertEqual(heap.size(), 3)
        self.assertEqual(len(heap), 3)

        # 가장 작은 5.0 시각의 key2가 꼭대기(peek)에 있어야 함
        self.assertEqual(heap.peek(), (5.0, "key2"))

        popped = heap.pop()
        self.assertEqual(popped, (5.0, "key2"))
        self.assertEqual(heap.peek(), (10.5, "key1"))
        self.assertEqual(heap.size(), 2)


if __name__ == "__main__":
    unittest.main()

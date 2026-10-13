"""
[PubSub: 단일 스레드 커스텀 발행-구독 메커니즘 모듈]

1. 어떤 로직인가:
   - HashMap(채널명 -> DoublyLinkedList 메시지 큐)을 사용하여, 메시지 발행(`publish`)과 구독(`subscribe`), 
     그리고 수동 읽기(`poll`) 기능을 제공하는 커스텀 Pub/Sub 모듈입니다.

2. 왜 존재하는가 (존재 이유 및 목적):
   - 단일 스레드 REPL 환경에서 터미널 블로킹 없이 메시지 브로커 기능을 시뮬레이션하기 위해 존재합니다.
"""

from typing import List
from .hash_map import HashMap
from .doubly_linked_list import DoublyLinkedList, Node


class PubSub:
    """
    Pub/Sub 발행-구독 클래스입니다.
    """

    def __init__(self) -> None:
        """무엇: __init__ 연산을 수행합니다.
        상태: 필요한 값, 연결, 또는 크기만 갱신하고 자료구조 불변식을 유지합니다.
        이유: 상위 Redis 명령이 예측 가능한 결과와 일관된 상태를 전제로 이 연산을 조합합니다.
        복잡도: 직접 접근은 O(1), 순회나 재배치가 있으면 O(N)."""
        self._channels: HashMap = HashMap()

    def subscribe(self, channel: str) -> None:
        """무엇: subscribe 연산을 수행합니다.
        상태: 필요한 값, 연결, 또는 크기만 갱신하고 자료구조 불변식을 유지합니다.
        이유: 상위 Redis 명령이 예측 가능한 결과와 일관된 상태를 전제로 이 연산을 조합합니다.
        복잡도: 직접 접근은 O(1), 순회나 재배치가 있으면 O(N)."""
        if not self._channels.contains(channel):
            self._channels.put(channel, DoublyLinkedList())

    def publish(self, channel: str, message: str) -> int:
        """무엇: PUBLISH 명령으로 채널 큐의 뒤에 메시지를 넣습니다.
        상태: 해당 채널의 대기열만 늘고, 구독되지 않은 채널은 0을 반환합니다.
        이유: 뒤 삽입과 POLL의 앞 제거가 발행 순서를 보존하는 FIFO를 만듭니다.
        복잡도: 평균 O(1)."""
        if not self._channels.contains(channel):
            return 0

        message_queue: DoublyLinkedList = self._channels.get(channel)
        message_queue.insert_back(Node(value=message))
        return 1

    def poll(self, channel: str) -> List[str]:
        """무엇: POLL 명령으로 채널 큐의 메시지를 앞에서부터 모두 꺼냅니다.
        상태: 반환된 메시지는 큐에서 제거되어 다시 소비되지 않습니다.
        이유: 단일 스레드 REPL에서 블로킹 없이 배치 수신을 제공합니다.
        복잡도: O(K)."""
        if not self._channels.contains(channel):
            return []

        message_queue: DoublyLinkedList = self._channels.get(channel)
        messages: List[str] = []

        while not message_queue.is_empty():
            node: Node = message_queue.remove_front()
            if node is not None and node.value is not None:
                messages.append(str(node.value))

        return messages

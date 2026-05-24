from hash_map import HashMap
from doubly_linked_list import DoublyLinkedList, Node

class PubSub:
    """
    Pub/Sub(발행-구독) 시스템을 구현한 클래스입니다. (보너스 5.5)
    
    기본 제약 조건에 따라 파이썬 내장 dict 대신 직접 구현한 HashMap을 사용합니다.
    HashMap의 키는 '채널명(Channel)'이며, 값은 메시지를 쌓아둘 큐(DoublyLinkedList)입니다.
    
    단일 스레드 REPL 환경의 한계로 인해, SUBSCRIBE 입력 시 터미널을 블로킹하지 않고
    채널만 생성/구독 처리하며, PUBLISH 시 해당 채널 큐에 메시지를 쌓습니다.
    이후 사용자가 POLL 명령어를 통해 큐에 쌓인 메시지를 일괄로 읽어오는 방식으로 동작합니다.
    """
    def __init__(self):
        # 채널명 -> 메시지 큐(DoublyLinkedList) 매핑
        self._channels = HashMap()

    def subscribe(self, channel: str) -> None:
        """
        특정 채널을 구독합니다.
        채널이 없으면 새로운 메시지 큐(DoublyLinkedList)를 할당하여 HashMap에 저장합니다.
        
        :param channel: 구독할 채널명
        """
        if not self._channels.contains(channel):
            self._channels.put(channel, DoublyLinkedList())

    def publish(self, channel: str, message: str) -> int:
        """
        특정 채널에 메시지를 발행합니다.
        메시지는 해당 채널의 큐 맨 뒤에 삽입(enqueue) 됩니다.
        
        :param channel: 발행할 채널명
        :param message: 발행할 메시지
        :return: 메시지를 수신한 구독자 수(여기서는 큐에 쌓인 성공 여부로 항상 1을 리턴, 채널 없으면 0)
        """
        if not self._channels.contains(channel):
            # 채널이 없으면 수신자 0명
            return 0
            
        message_queue: DoublyLinkedList = self._channels.get(channel)
        # 큐(이중 연결 리스트)의 맨 뒤에 노드 삽입
        message_queue.insert_back(Node(value=message))
        return 1

    def poll(self, channel: str) -> list:
        """
        특정 채널의 큐에 쌓인 모든 메시지를 꺼내옵니다(dequeue).
        단일 스레드 CLI 환경을 위한 특별 명령어입니다.
        
        :param channel: 메시지를 읽을 채널명
        :return: 메시지 배열
        """
        if not self._channels.contains(channel):
            return []
            
        message_queue: DoublyLinkedList = self._channels.get(channel)
        messages = []
        
        # 큐가 빌 때까지 앞에서부터 꺼냄
        while not message_queue.is_empty():
            node = message_queue.remove_front()
            messages.append(node.value)
            
        return messages

class TreeNode:
    """
    이진 탐색 트리(Binary Search Tree)에 사용될 노드 클래스입니다.
    데이터 식별자인 key와 왼쪽/오른쪽 자식 노드를 가리키는 포인터를 가집니다.
    """
    def __init__(self, key):
        self.key = key
        self.left = None
        self.right = None

class BST:
    """
    이진 탐색 트리(Binary Search Tree)와 다양한 순회(Traversal) 알고리즘 구현 클래스입니다.
    (보너스 과제 5.3, 5.4)
    
    트리의 핵심 속성: 왼쪽 서브트리의 모든 키는 현재 노드의 키보다 작고, 
    오른쪽 서브트리의 모든 키는 현재 노드의 키보다 큽니다.
    이 속성 덕분에 평균 O(log N) 시간에 탐색이 가능합니다.
    (최악의 경우 편향 트리에서는 O(N)이 될 수 있으며, 이는 Red-Black 트리 등으로 해결 가능합니다)
    """
    def __init__(self):
        self.root = None

    def insert(self, key) -> None:
        """새로운 키를 삽입합니다."""
        if self.root is None:
            self.root = TreeNode(key)
        else:
            self._insert_recursive(self.root, key)

    def _insert_recursive(self, node: TreeNode, key) -> None:
        if key < node.key:
            if node.left is None:
                node.left = TreeNode(key)
            else:
                self._insert_recursive(node.left, key)
        elif key > node.key:
            if node.right is None:
                node.right = TreeNode(key)
            else:
                self._insert_recursive(node.right, key)
        # 키가 이미 존재하면 아무것도 하지 않음 (중복 허용 안함)

    def search(self, key) -> bool:
        """특정 키의 존재 여부를 탐색합니다."""
        return self._search_recursive(self.root, key)

    def _search_recursive(self, node: TreeNode, key) -> bool:
        if node is None:
            return False
        if key == node.key:
            return True
        elif key < node.key:
            return self._search_recursive(node.left, key)
        else:
            return self._search_recursive(node.right, key)

    def delete(self, key) -> None:
        """키를 트리에서 삭제합니다."""
        self.root = self._delete_recursive(self.root, key)

    def _find_min(self, node: TreeNode) -> TreeNode:
        """오른쪽 서브트리에서 가장 작은 값을 찾는 유틸리티 (삭제 연산에 사용)"""
        current = node
        while current.left is not None:
            current = current.left
        return current

    def _delete_recursive(self, node: TreeNode, key) -> TreeNode:
        if node is None:
            return node

        # 1. 삭제할 노드를 찾기 위해 순회
        if key < node.key:
            node.left = self._delete_recursive(node.left, key)
        elif key > node.key:
            node.right = self._delete_recursive(node.right, key)
        else:
            # 2. 삭제할 노드를 찾았을 때의 처리
            
            # 자식이 하나이거나 없는 경우
            if node.left is None:
                return node.right
            elif node.right is None:
                return node.left
                
            # 자식이 두 개인 경우: 오른쪽 서브트리의 최솟값을 찾아 현재 노드를 덮어쓰고,
            # 그 최솟값 노드를 오른쪽 서브트리에서 재귀적으로 삭제함.
            temp = self._find_min(node.right)
            node.key = temp.key
            node.right = self._delete_recursive(node.right, temp.key)

        return node

    # --- 순회(Traversal) 알고리즘 구현 (보너스 5.3) ---

    def preorder(self) -> list:
        """전위 순회: 루트 -> 왼쪽 -> 오른쪽. (주로 트리 구조를 복사/직렬화 할 때 쓰임)"""
        result = []
        self._preorder_recursive(self.root, result)
        return result

    def _preorder_recursive(self, node: TreeNode, result: list):
        if node:
            result.append(node.key)
            self._preorder_recursive(node.left, result)
            self._preorder_recursive(node.right, result)

    def inorder(self) -> list:
        """중위 순회: 왼쪽 -> 루트 -> 오른쪽. (BST에서 정렬된 결과를 얻을 수 있는 강력한 속성)"""
        result = []
        self._inorder_recursive(self.root, result)
        return result

    def _inorder_recursive(self, node: TreeNode, result: list):
        if node:
            self._inorder_recursive(node.left, result)
            result.append(node.key)
            self._inorder_recursive(node.right, result)

    def postorder(self) -> list:
        """후위 순회: 왼쪽 -> 오른쪽 -> 루트. (주로 트리의 노드를 잎부터 위로 삭제할 때 쓰임)"""
        result = []
        self._postorder_recursive(self.root, result)
        return result

    def _postorder_recursive(self, node: TreeNode, result: list):
        if node:
            self._postorder_recursive(node.left, result)
            self._postorder_recursive(node.right, result)
            result.append(node.key)

    def level_order(self) -> list:
        """
        레벨 순회 (BFS): 위에서 아래로, 좌에서 우로.
        
        힙(Heap)과의 연관성 관점:
        힙은 '완전 이진 트리(Complete Binary Tree)' 구조를 띠며, 이 트리를 
        레벨 순회로 탐색한 결과가 곧 MinHeap 클래스에서 사용하는 1차원 배열(DynamicArray)의
        저장 순서와 완벽히 일치합니다.
        (즉, 배열의 인덱스는 레벨 순회 방문 순서를 의미합니다.)
        """
        if not self.root:
            return []
            
        result = []
        # 내장 컬렉션 큐 대신 파이썬의 기본 리스트를 큐로 단순 사용
        queue = [self.root]
        
        while queue:
            # 리스트의 pop(0)은 O(N)이지만 순회 학습 목적이므로 허용함
            current = queue.pop(0)
            result.append(current.key)
            
            if current.left:
                queue.append(current.left)
            if current.right:
                queue.append(current.right)
                
        return result

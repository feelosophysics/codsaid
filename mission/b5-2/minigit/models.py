"""커밋과 저장소 상태.

Commit은 한 시점의 메타데이터다. Repository는 커밋 목록, 브랜치 포인터,
현재 브랜치(HEAD), 검색용 역색인을 함께 관리한다. 파일 내용은 저장하지 않는다.
"""

from __future__ import annotations

import hashlib
import time

from minigit.constants import ConfigConstants, ErrorMessages, SystemMessages
from minigit.index import InvertedIndex


class Commit:
    """그래프의 노드 하나. parents에는 부모 커밋의 식별자가 들어간다."""

    def __init__(
        self,
        commit_hash: str,
        message: str,
        author: str,
        timestamp: float,
        parents: list[str],
    ) -> None:
        # self.이름은 이 Commit 객체가 살아 있는 동안 유지되는 필드다.
        self.hash = commit_hash
        self.message = message
        self.author = author
        self.timestamp = timestamp
        # [:]는 새 리스트를 만든다. 호출자가 원본을 바꿔도 이 커밋의 부모는 바뀌지 않는다.
        self.parents = parents[:]

    def __repr__(self) -> str:
        return f"Commit(hash={self.hash!r}, message={self.message!r})"


class Repository:
    """한 번 실행하는 동안의 Mini Git 저장소."""

    def __init__(self) -> None:
        # dict[키] = 값. 해시로 커밋을 찾고, 브랜치 이름으로 끝 커밋을 찾는다.
        self.commits: dict[str, Commit] = {}
        self.branches: dict[str, str | None] = {}
        # None은 아직 현재 브랜치/작성자가 정해지지 않았다는 뜻이다.
        self.head: str | None = None  # HEAD에는 커밋 해시가 아닌 현재 브랜치 이름을 둔다.
        self.current_user: str | None = None
        self.inverted_index = InvertedIndex()
        self.initialized = False
        self._next_number = 1

    def init(self, user_name: str) -> str:
        """저장소를 새로 시작한다. 기존 커밋과 색인은 모두 비운다."""
        user_name = user_name.strip()
        # strip()은 양끝 공백을 지운다. 공백만 입력한 이름도 빈 문자열이 된다.
        if not user_name:
            return ErrorMessages.INVALID_INIT

        self.commits = {}
        self.branches = {ConfigConstants.DEFAULT_BRANCH: None}
        # 첫 커밋 전에는 main이 가리킬 ID가 없으므로 값이 None이다.
        self.head = ConfigConstants.DEFAULT_BRANCH
        self.current_user = user_name
        self.inverted_index = InvertedIndex()
        # 재초기화 뒤에도 번호는 이어서 쓴다. 한 REPL 세션의 ID는 재사용하지 않는다.
        self.initialized = True
        return SystemMessages.INIT_SUCCESS.format(branch=self.head, user=user_name)

    def set_user(self, user_name: str) -> str:
        """이후 커밋의 작성자를 바꾼다. 기존 커밋은 그대로 둔다."""
        if not self.initialized:
            return ErrorMessages.REPO_NOT_INIT
        user_name = user_name.strip()
        if not user_name:
            return ErrorMessages.INVALID_USER
        self.current_user = user_name
        # 이전 Commit 객체의 author 필드는 수정하지 않는다.
        return SystemMessages.USER_CHANGED.format(user=user_name)

    def _add_commit(self, message: str, parents: list[str]) -> Commit:
        """일반/병합 커밋이 공유하는 생성 절차: ID → 저장 → 브랜치 → 색인.

        SHA-1의 앞 여섯 글자는 내용과 부모에 따른 '지문'이다. 그 부분은 충돌할
        수 있으므로 증가 번호를 덧붙여 전체 ID의 세션 내 유일성을 보장한다.
        실제 Git의 객체 ID 방식과 같은 것은 아니다.
        """
        assert self.head is not None and self.current_user is not None
        timestamp = time.time()
        # 같은 메시지도 시간·부모에 따라 다른 지문이 될 수 있다.
        # 번호는 지문 충돌 여부와 관계없이 반드시 한 번씩 증가한다.
        content = f"{message}|{self.current_user}|{timestamp}|{','.join(parents)}"
        digest = hashlib.sha1(content.encode("utf-8")).hexdigest()[:6]
        commit_hash = f"{digest}-{self._next_number:x}"
        self._next_number += 1

        new_commit = Commit(commit_hash, message, self.current_user, timestamp, parents)
        # 부모는 이미 commits에 있다. 새 노드가 미래 노드를 가리킬 수 없어 순환이 생기지 않는다.
        self.commits[new_commit.hash] = new_commit
        # HEAD에는 브랜치 이름이 있으므로 그 브랜치의 값(ID)을 바꾼다.
        self.branches[self.head] = new_commit.hash
        # 검색 표를 같은 시점에 갱신해야 방금 만든 커밋도 검색된다.
        self.inverted_index.add_commit(new_commit)
        return new_commit

    def commit(self, message: str) -> str:
        """현재 브랜치 끝을 부모로 하는 커밋을 만든다."""
        if not self.initialized:
            return ErrorMessages.REPO_NOT_INIT
        message = message.strip()
        if not message:
            return ErrorMessages.INVALID_COMMIT

        head_hash = self.get_head_commit_hash()
        parents: list[str] = []
        if head_hash is not None:
            # 최초 커밋을 제외한 일반 커밋의 부모는 현재 브랜치 끝 하나다.
            parents.append(head_hash)
        new_commit = self._add_commit(message, parents)
        return SystemMessages.COMMIT_SUCCESS.format(
            branch=self.head, hash=new_commit.hash, message=message
        )

    def branch(self, branch_name: str) -> str:
        """새 브랜치는 현재 브랜치와 같은 커밋을 가리키며 시작한다."""
        if not self.initialized:
            return ErrorMessages.REPO_NOT_INIT
        branch_name = branch_name.strip()
        if not branch_name:
            return ErrorMessages.INVALID_BRANCH
        if branch_name in self.branches:
            return ErrorMessages.BRANCH_ALREADY_EXISTS.format(name=branch_name)

        # 객체 복사 대신 ID만 복사한다. 두 브랜치는 처음에 같은 커밋을 가리킨다.
        self.branches[branch_name] = self.get_head_commit_hash()
        return SystemMessages.BRANCH_CREATED.format(name=branch_name)

    def switch(self, branch_name: str) -> str:
        """HEAD의 브랜치 이름만 바꾼다. 기존 커밋은 움직이지 않는다."""
        if not self.initialized:
            return ErrorMessages.REPO_NOT_INIT
        branch_name = branch_name.strip()
        if not branch_name:
            return ErrorMessages.INVALID_SWITCH
        if branch_name not in self.branches:
            return ErrorMessages.UNKNOWN_BRANCH.format(name=branch_name)

        # 전환은 브랜치 포인터를 이동하지 않는다. 현재 보는 브랜치 이름만 바뀐다.
        self.head = branch_name
        return SystemMessages.SWITCHED_BRANCH.format(name=branch_name)

    def merge(self, branch_name: str) -> str:
        """현재 끝과 대상 브랜치 끝을 부모로 하는 커밋을 만든다."""
        if not self.initialized:
            return ErrorMessages.REPO_NOT_INIT
        branch_name = branch_name.strip()
        if not branch_name:
            return ErrorMessages.INVALID_MERGE
        if branch_name not in self.branches:
            return ErrorMessages.UNKNOWN_BRANCH.format(name=branch_name)
        if branch_name == self.head:
            return ErrorMessages.MERGE_SELF

        current_hash = self.get_head_commit_hash()
        target_hash = self.branches[branch_name]
        if current_hash is None or target_hash is None:
            return ErrorMessages.MERGE_NO_COMMITS
        if current_hash == target_hash:
            return SystemMessages.ALREADY_UP_TO_DATE

        # 병합도 Commit 하나다. 부모 리스트에 두 끝 ID를 순서대로 넣는다.
        message = f"Merge branch '{branch_name}' into {self.head}"
        new_commit = self._add_commit(message, [current_hash, target_hash])
        return SystemMessages.MERGE_SUCCESS.format(
            branch=branch_name, head=self.head, hash=new_commit.hash, message=message
        )

    def get_head_commit_hash(self) -> str | None:
        """현재 브랜치가 가리키는 커밋 ID. 첫 커밋 전에는 None."""
        if self.head is None:
            return None
        # 예: head == 'main'이면 branches['main']의 ID(또는 None)를 돌려준다.
        return self.branches[self.head]

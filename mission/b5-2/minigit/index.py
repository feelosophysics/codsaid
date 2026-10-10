"""역색인: 검색어에서 해당 커밋들의 ID를 곧바로 찾기 위한 표."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # 타입 검사에만 필요한 import. 실행 중 models.py와 서로 불러오는 일을 막는다.
    from minigit.models import Commit


class InvertedIndex:
    """두 표를 관리한다: 단어 → ID 집합, 작성자 → ID 집합."""

    def __init__(self) -> None:
        # dict[str, set[str]]: 문자열 단어를 주면 해당 커밋 ID 집합을 얻는다.
        self.keyword_index: dict[str, set[str]] = {}
        self.author_index: dict[str, set[str]] = {}

    def add_commit(self, commit: Commit) -> None:
        """커밋 생성 시 한 번 호출하여 두 표를 동시에 갱신한다."""
        # split()은 공백으로 나눈다. 문장부호는 단어에 남는다.
        # set은 한 메시지에 같은 단어가 여러 번 나와도 ID를 한 번만 넣는다.
        for word in set(commit.message.lower().split()):
            if word not in self.keyword_index:
                # 이 단어를 처음 봤을 때 빈 ID 주머니를 만든다.
                self.keyword_index[word] = set()
            self.keyword_index[word].add(commit.hash)

        author = commit.author.lower()
        if author not in self.author_index:
            self.author_index[author] = set()
        self.author_index[author].add(commit.hash)

    def search_keyword(self, keyword: str) -> set[str]:
        """완전한 단어 하나를 찾는다. 예: login은 login,과 다르다."""
        # get(키, 기본값)은 키가 없을 때 빈 set을 준다. copy()는 내부 표 보호용이다.
        return self.keyword_index.get(keyword.lower().strip(), set()).copy()

    def search_phrase(self, phrase: str, commits: dict[str, Commit]) -> set[str]:
        """연속 구절 검색. 첫 단어의 색인으로 후보만 꺼내어 확인한다.

        예: 'login feature'는 'add login feature'에는 있고
        'login new feature'에는 없다. 전체 커밋을 순회하지 않는다.
        """
        words = phrase.lower().split()
        if not words:
            return set()

        candidates = self.search_keyword(words[0])
        if len(words) == 1:
            return candidates

        matches: set[str] = set()
        # candidates는 전체 커밋이 아닌 첫 단어를 가진 커밋들뿐이다.
        for commit_hash in candidates:
            message_words = commits[commit_hash].message.lower().split()
            # 모든 가능한 시작 위치를 검사한다. 슬라이스는 연속된 부분만 가져온다.
            for start in range(len(message_words) - len(words) + 1):
                if message_words[start:start + len(words)] == words:
                    # 이 커밋에서 한 번 찾았으면 더 뒤쪽은 볼 필요가 없다.
                    matches.add(commit_hash)
                    break
        return matches

    def search_author(self, author: str) -> set[str]:
        """작성자 이름 전체를 대소문자 구분 없이 비교한다."""
        return self.author_index.get(author.lower().strip(), set()).copy()

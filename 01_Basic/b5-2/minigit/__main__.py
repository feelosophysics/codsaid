"""대화형 CLI 진입점. 프로젝트 폴더에서 python -m minigit 으로 실행한다.

REPL은 입력(Read) → 명령 실행(Eval) → 결과 출력(Print)을 종료할 때까지
반복(Loop)한다. 명령은 대소문자를 구분하지 않고, 공백이 있는 인자는
큰따옴표나 작은따옴표로 감싼다.
"""

from __future__ import annotations

import datetime
import shlex

from minigit.constants import ConfigConstants, ErrorMessages, SystemMessages
from minigit.diff import diff_files
from minigit.graph import find_ancestors, find_shortest_path, topological_sort
from minigit.models import Commit, Repository
from minigit.sorting import benchmark_sorts, merge_sort


def format_timestamp(timestamp: float) -> str:
    """1970년 이후 초 단위 수를 사람이 읽는 지역 날짜로 바꾼다."""
    return datetime.datetime.fromtimestamp(timestamp).strftime(
        ConfigConstants.TIME_FORMAT
    )


def format_commit_details(commit: Commit) -> str:
    """LOG와 ANCESTORS가 공유하는 커밋 ID·작성자·시각 표시."""
    return f"{commit.hash} ({commit.author}, {format_timestamp(commit.timestamp)})"


def escape_terminal_controls(text: str) -> str:
    """원본 데이터는 보존하고 출력 경계에서 제어문자를 보이는 표기로 바꾼다."""
    characters: list[str] = []
    for character in text:
        number = ord(character)
        is_control = number < 32 or 127 <= number <= 159
        if is_control and character not in ("\n", "\t"):
            characters.append(f"\\x{number:02x}")
        else:
            characters.append(character)
    return "".join(characters)


class MiniGitCLI:
    """명령을 해석하고 Repository와 알고리즘 함수에 일을 맡긴다."""

    def __init__(self) -> None:
        # CLI 객체 하나에 저장소 객체 하나를 둔다. 명령을 여러 번 입력해도 상태가 이어진다.
        self.repo = Repository()

    def parse_input(self, user_input: str) -> list[str]:
        """따옴표 안의 공백은 한 인자로 묶는다. 잘못 닫힌 따옴표는 오류다.

        shlex의 기본 escape 기능은 따옴표 없는 Windows 경로의 역슬래시를
        없애므로 비활성화한다. 이 CLI에서는 역슬래시 이스케이프를 지원하지 않는다.
        """
        # shlex는 따옴표를 이해하는 문자열 분리 도구다.
        # 예: 'COMMIT "hello world"' → ['COMMIT', 'hello world']
        lexer = shlex.shlex(user_input, posix=True)
        lexer.whitespace_split = True
        lexer.commenters = ""
        lexer.escape = ""
        return list(lexer)

    def handle_log(self, args: list[str]) -> str:
        """기본 LOG는 DAG 순서, 옵션 LOG는 직접 구현한 머지 정렬을 쓴다."""
        # 옵션을 먼저 검사하면 커밋이 하나도 없을 때도 오타를 숨기지 않는다.
        if len(args) > 1:
            return ErrorMessages.INVALID_LOG
        sort_by: str | None = None
        if args:
            if not args[0].startswith("--sort-by="):
                return ErrorMessages.INVALID_LOG
            sort_by = args[0].split("=", 1)[1].lower()
            if sort_by not in ("date", "author"):
                return ErrorMessages.INVALID_SORT_KEY.format(key=sort_by)
        if not self.repo.initialized:
            return ErrorMessages.REPO_NOT_INIT
        if not self.repo.commits:
            return SystemMessages.NO_COMMITS_YET

        if sort_by == "date":
            # values()는 dict에 저장된 Commit 객체들이다. lambda는 비교할 값을 꺼낸다.
            ordered = merge_sort(
                list(self.repo.commits.values()), key_func=lambda commit: commit.timestamp
            )
        elif sort_by == "author":
            ordered = merge_sort(
                list(self.repo.commits.values()),
                key_func=lambda commit: commit.author.lower(),
            )
        else:
            ordered = topological_sort(self.repo.commits)

        # 브랜치는 커밋에 붙은 속성이 아니라, 커밋 ID를 가리키는 별도 포인터다.
        branch_labels: dict[str, list[str]] = {}
        for branch_name, branch_hash in self.repo.branches.items():
            if branch_hash is not None:
                # setdefault(key, [])는 키가 처음 나타나면 빈 리스트를 준비한다.
                branch_labels.setdefault(branch_hash, []).append(branch_name)

        lines: list[str] = []
        head_hash = self.repo.get_head_commit_hash()
        for commit in ordered:
            labels = branch_labels.get(commit.hash, [])
            label_text = ""
            if labels:
                label_text = f" [{', '.join(labels)}]"
            is_head = head_hash == commit.hash
            head_text = ""
            if is_head:
                head_text = " (HEAD)"
            # f"..."는 중괄호 안의 변수 값을 문자열에 채워 넣는다.
            lines.append(
                f"commit {format_commit_details(commit)}{label_text}{head_text}"
            )
            lines.append(f"  {commit.message}")
            lines.append("")
        # join은 줄 목록을 하나의 문자열로 묶고, rstrip은 마지막 빈 줄만 지운다.
        return "\n".join(lines).rstrip()

    def handle_path(self, args: list[str]) -> str:
        if len(args) != 2:
            return ErrorMessages.INVALID_PATH
        if not self.repo.initialized:
            return ErrorMessages.REPO_NOT_INIT
        for commit_hash in args:
            if commit_hash not in self.repo.commits:
                return ErrorMessages.UNKNOWN_COMMIT.format(hash=commit_hash)
        path = find_shortest_path(self.repo.commits, args[0], args[1])
        if path is None:
            return SystemMessages.NO_PATH
        # ['A', 'B'] → 'A -> B'. 시작점 하나뿐이면 그 ID만 출력된다.
        return "Path: " + " -> ".join(path)

    def handle_ancestors(self, args: list[str]) -> str:
        if len(args) != 1:
            return ErrorMessages.INVALID_ANCESTORS
        if not self.repo.initialized:
            return ErrorMessages.REPO_NOT_INIT
        commit_hash = args[0]
        if commit_hash not in self.repo.commits:
            return ErrorMessages.UNKNOWN_COMMIT.format(hash=commit_hash)
        ancestors = find_ancestors(self.repo.commits, commit_hash)
        if not ancestors:
            return f"No ancestors found for commit {commit_hash}"
        lines = [f"Ancestors of {commit_hash}:"]
        for ancestor_hash in ancestors:
            commit = self.repo.commits[ancestor_hash]
            lines.append(
                f"  {format_commit_details(commit)}: {commit.message}"
            )
        return "\n".join(lines)

    def handle_search(self, args: list[str]) -> str:
        if len(args) != 1:
            return ErrorMessages.INVALID_SEARCH
        if not self.repo.initialized:
            return ErrorMessages.REPO_NOT_INIT

        query = args[0]
        if query.startswith("--author="):
            author = query.split("=", 1)[1].strip()
            if not author:
                return ErrorMessages.INVALID_SEARCH
            hashes = self.repo.inverted_index.search_author(author)
            description = f"author '{author}'"
        else:
            if not query.strip() or query.startswith("--"):
                return ErrorMessages.INVALID_SEARCH
            hashes = self.repo.inverted_index.search_phrase(query, self.repo.commits)
            description = f"keyword '{' '.join(query.lower().split())}'"

        if not hashes:
            return SystemMessages.SEARCH_NO_RESULTS.format(search_type=description)
        # 색인의 set은 순서가 없다. 후보만 정렬하므로 모든 커밋을 훑지 않는다.
        found: list[Commit] = []
        for commit_hash in hashes:
            found.append(self.repo.commits[commit_hash])
        found = merge_sort(found, key_func=lambda commit: (commit.timestamp, commit.hash))
        lines = [
            SystemMessages.SEARCH_FOUND.format(count=len(found), search_type=description),
            "",
        ]
        for commit in found:
            lines.append(f"  - {commit.hash}: {commit.message}")
        return "\n".join(lines)

    def handle_diff(self, args: list[str]) -> str:
        if len(args) != 2 or not all(args):
            return ErrorMessages.INVALID_DIFF
        return diff_files(args[0], args[1])

    def handle_status(self) -> str:
        if not self.repo.initialized:
            return ErrorMessages.REPO_NOT_INIT
        head_hash = self.repo.get_head_commit_hash()
        head_description = "(no commits yet)"
        if head_hash is not None:
            head_description = f"{head_hash} - {self.repo.commits[head_hash].message}"
        return "\n".join(
            [
                f"Current user:   {self.repo.current_user}",
                f"Current branch: {self.repo.head}",
                f"HEAD commit:    {head_description}",
                f"Total commits:  {len(self.repo.commits)}",
                f"Branches:       {', '.join(self.repo.branches)}",
            ]
        )

    def execute(self, tokens: list[str]) -> str:
        """첫 단어로 명령을 고르고 나머지 단어를 인자로 전달한다."""
        if not tokens:
            return ErrorMessages.INVALID_ARGS
        # upper()로 명령 이름만 대문자로 만든다. 메시지와 사용자 이름은 보존한다.
        command = tokens[0].upper()
        # [1:]은 두 번째 원소부터 끝까지의 새 리스트다.
        args = tokens[1:]
        # 이 여섯 명령은 같은 문법이다: 인자 하나 → 저장소의 동작.
        repository_commands = {
            "INIT": (self.repo.init, ErrorMessages.INVALID_INIT),
            "COMMIT": (self.repo.commit, ErrorMessages.INVALID_COMMIT),
            "USER": (self.repo.set_user, ErrorMessages.INVALID_USER),
            "BRANCH": (self.repo.branch, ErrorMessages.INVALID_BRANCH),
            "SWITCH": (self.repo.switch, ErrorMessages.INVALID_SWITCH),
            "MERGE": (self.repo.merge, ErrorMessages.INVALID_MERGE),
        }
        if command in repository_commands:
            action, invalid_message = repository_commands[command]
            if len(args) != 1:
                return invalid_message
            return action(args[0])
        if command == "LOG":
            return self.handle_log(args)
        if command == "PATH":
            return self.handle_path(args)
        if command == "ANCESTORS":
            return self.handle_ancestors(args)
        if command == "SEARCH":
            return self.handle_search(args)
        if command == "DIFF":
            return self.handle_diff(args)
        if command == "BENCHMARK":
            if args:
                return ErrorMessages.INVALID_ARGS
            return benchmark_sorts()
        if command == "STATUS":
            if args:
                return ErrorMessages.INVALID_ARGS
            return self.handle_status()
        if command == "HELP":
            if args:
                return ErrorMessages.INVALID_ARGS
            return SystemMessages.HELP_TEXT
        return SystemMessages.UNKNOWN_COMMAND.format(command=tokens[0])

    def run(self) -> None:
        """입력 한 줄마다 파싱 → 실행 → 출력. EXIT/QUIT 또는 EOF에서 종료."""
        print(SystemMessages.WELCOME)
        # while True는 종료 명령을 만날 때까지 계속 입력을 기다린다.
        while True:
            try:
                user_input = input(SystemMessages.PROMPT)
            except EOFError:
                # 입력 스트림이 끝나면 깔끔하게 종료한다.
                print(SystemMessages.GOODBYE)
                break
            except KeyboardInterrupt:
                # Ctrl+C는 현재 입력만 취소한다.
                print()
                continue

            try:
                tokens = self.parse_input(user_input)
            except ValueError:
                # 닫히지 않은 따옴표 등을 정상 명령으로 해석하지 않는다.
                print(ErrorMessages.INVALID_ARGS)
                continue
            if not tokens:
                # 빈 줄에는 실행할 명령이 없다.
                continue
            if tokens[0].upper() in ("EXIT", "QUIT"):
                if len(tokens) != 1:
                    print(ErrorMessages.INVALID_ARGS)
                    continue
                print(SystemMessages.GOODBYE)
                break
            print(escape_terminal_controls(self.execute(tokens)))


if __name__ == "__main__":
    MiniGitCLI().run()

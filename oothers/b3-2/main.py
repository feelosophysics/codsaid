"""
main.py — Mini Git CLI 진입점 (REPL)
======================================

이 파일은 Mini Git 프로그램의 진입점(entry point)입니다.
REPL(Read-Eval-Print Loop) 패턴으로 동작합니다.

────────────────────────────────────────────
REPL(Read-Eval-Print Loop)이란?
────────────────────────────────────────────
대화형 프로그램의 기본 구조입니다:
1. Read:  사용자 입력을 읽습니다.
2. Eval:  입력을 해석(파싱)하고 실행합니다.
3. Print: 결과를 출력합니다.
4. Loop:  위 과정을 반복합니다.

Python 인터프리터(>>> 프롬프트)가 REPL의 대표적 예입니다.
셸(bash, zsh)도 REPL입니다.

────────────────────────────────────────────
명령어 파싱(Command Parsing)
────────────────────────────────────────────
사용자 입력을 "명령어"와 "인자(arguments)"로 분리해야 합니다.

난이도가 있는 부분:
- 따옴표 안의 공백은 인자를 분리하면 안 됩니다.
  예: COMMIT "Add login feature" → ["COMMIT", "Add login feature"]
- 옵션 파싱: --sort-by=date, --author=Alice 형태 처리

이를 위해 Python 표준 라이브러리의 shlex 모듈을 사용합니다.
shlex.split()은 셸과 동일한 규칙으로 문자열을 분리합니다.

────────────────────────────────────────────
실행 방법
────────────────────────────────────────────
  python main.py

프롬프트가 표시되면 명령어를 입력합니다:
  mini-git> init "Alice"
  mini-git> commit "Initial commit"
  mini-git> exit
"""

import shlex      # 셸 스타일 문자열 분리 (따옴표 처리)
import time       # 타임스탬프 포맷팅
import datetime   # 사람이 읽을 수 있는 날짜/시간 변환

# ── 우리가 만든 모듈들을 임포트 ──
from models import Repository           # 저장소 관리
from graph import (                     # 그래프 알고리즘
    topological_sort,                   # LOG 명령어: 위상 정렬
    find_shortest_path,                 # PATH 명령어: BFS 최단 경로
    find_ancestors                      # ANCESTORS 명령어: DFS 조상 탐색
)
from sorting import (                   # 정렬 알고리즘
    merge_sort,                         # LOG --sort-by 에 사용
    benchmark_sorts                     # BENCHMARK 명령어
)
from diff import diff_files             # DIFF 명령어: 파일 비교


def format_timestamp(ts):
    """
    Unix 타임스탬프를 사람이 읽을 수 있는 형식으로 변환합니다.

    ── Unix 타임스탬프란? ──
    1970년 1월 1일 00:00:00 UTC부터 경과한 초(seconds)입니다.
    예: 1700000000 → 2023-11-14 22:13:20

    Args:
        ts (float): Unix 타임스탬프

    Returns:
        str: "YYYY-MM-DD HH:MM:SS" 형식의 문자열
    """
    # datetime.fromtimestamp(): Unix 타임스탬프를 datetime 객체로 변환
    # .strftime(): datetime 객체를 지정 형식의 문자열로 변환
    # %Y: 4자리 연도, %m: 2자리 월, %d: 2자리 일
    # %H: 24시간제 시, %M: 분, %S: 초
    dt = datetime.datetime.fromtimestamp(ts)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def parse_input(user_input):
    """
    사용자 입력을 명령어와 인자로 분리합니다.

    ── 파싱 규칙 ──
    1. 따옴표로 감싼 문자열은 하나의 인자로 취급합니다.
       예: COMMIT "Add login feature" → ["COMMIT", "Add login feature"]
    2. 명령어는 대소문자를 구분하지 않습니다 (INIT = init = Init).
    3. 빈 입력은 빈 리스트를 반환합니다.

    ── shlex.split()의 동작 ──
    셸(bash)과 동일한 규칙으로 문자열을 분리합니다:
    - 공백으로 토큰을 구분합니다.
    - 따옴표 안의 공백은 토큰을 분리하지 않습니다.
    - 이스케이프 문자(\\)를 처리합니다.

    Args:
        user_input (str): 사용자가 입력한 원시 문자열

    Returns:
        list: [명령어, 인자1, 인자2, ...] 형태의 리스트
              빈 입력이면 빈 리스트
    """
    # ── 빈 입력 처리 ──
    user_input = user_input.strip()
    if not user_input:
        return []

    # ── shlex.split()으로 따옴표를 올바르게 처리 ──
    try:
        tokens = shlex.split(user_input)
    except ValueError:
        # 따옴표가 닫히지 않은 경우 등의 파싱 에러
        # 이 경우 단순 공백 분리로 폴백합니다.
        tokens = user_input.split()

    return tokens


def handle_init(repo, args):
    """
    INIT 명령어를 처리합니다.

    사용법: INIT <user_name>
    예시:   INIT "Alice"
            INIT Bob

    Args:
        repo (Repository): 저장소 객체
        args (list): 파싱된 인자 리스트 (명령어 제외)

    Returns:
        str: 실행 결과 메시지
    """
    # ── 인자 검증 ──
    if len(args) < 1:
        return "Invalid args: INIT <user_name>"

    user_name = args[0]
    return repo.init(user_name)


def handle_commit(repo, args):
    """
    COMMIT 명령어를 처리합니다.

    사용법: COMMIT <message>
    예시:   COMMIT "Add login feature"
            COMMIT Initial_commit

    Args:
        repo (Repository): 저장소 객체
        args (list): 파싱된 인자 리스트 (명령어 제외)

    Returns:
        str: 실행 결과 메시지
    """
    if len(args) < 1:
        return "Invalid args: COMMIT <message>"

    # 여러 인자를 공백으로 합쳐서 메시지로 사용합니다.
    # 따옴표로 감싸지 않은 경우에도 자연스럽게 처리됩니다.
    # 예: COMMIT Add login feature → message = "Add login feature"
    message = " ".join(args)
    return repo.commit(message)


def handle_branch(repo, args):
    """
    BRANCH 명령어를 처리합니다.

    사용법: BRANCH <branch_name>
    예시:   BRANCH feature

    Args:
        repo (Repository): 저장소 객체
        args (list): 파싱된 인자 리스트 (명령어 제외)

    Returns:
        str: 실행 결과 메시지
    """
    if len(args) < 1:
        return "Invalid args: BRANCH <branch_name>"

    return repo.branch(args[0])


def handle_switch(repo, args):
    """
    SWITCH 명령어를 처리합니다.

    사용법: SWITCH <branch_name>
    예시:   SWITCH feature

    Args:
        repo (Repository): 저장소 객체
        args (list): 파싱된 인자 리스트 (명령어 제외)

    Returns:
        str: 실행 결과 메시지
    """
    if len(args) < 1:
        return "Invalid args: SWITCH <branch_name>"

    return repo.switch(args[0])


def handle_log(repo, args):
    """
    LOG 명령어를 처리합니다.

    ── 두 가지 모드 ──
    1. LOG (인자 없음):
       위상 정렬(Kahn's Algorithm)로 커밋을 출력합니다.
       부모가 항상 자식보다 먼저 출력됩니다.

    2. LOG --sort-by=date|author:
       머지 정렬(Merge Sort)로 커밋을 지정 기준에 따라 정렬하여 출력합니다.
       - date: 타임스탬프 기준 오름차순
       - author: 작성자 이름 기준 사전순

    ── 왜 Merge Sort를 사용하는가? ──
    Merge Sort는 안정 정렬이므로,
    같은 키를 가진 커밋들의 상대적 순서가 유지됩니다.
    예: 같은 작성자의 커밋들이 원래 순서(시간순)대로 나옵니다.

    사용법: LOG
            LOG --sort-by=date
            LOG --sort-by=author
    """
    if not repo.initialized:
        return "Error: Repository not initialized. Use INIT first."

    commits_dict = repo.get_all_commits()
    if not commits_dict:
        return "No commits yet."

    # ── 옵션 파싱 ──
    sort_by = None
    for arg in args:
        if arg.startswith("--sort-by="):
            sort_by = arg.split("=", 1)[1].lower()
            # split("=", 1): "=" 기준으로 최대 1번만 분리
            # [1]: "=" 뒤의 값을 가져옴

    if sort_by:
        # ── 정렬 모드 ──
        commits_list = list(commits_dict.values())

        if sort_by == "date":
            # 타임스탬프 기준 정렬 (오름차순)
            sorted_commits = merge_sort(
                commits_list,
                key_func=lambda c: c.timestamp
            )
        elif sort_by == "author":
            # 작성자 이름 기준 정렬 (사전순, 대소문자 무시)
            sorted_commits = merge_sort(
                commits_list,
                key_func=lambda c: c.author.lower()
            )
        else:
            return f"Invalid sort key: {sort_by}. Use 'date' or 'author'."
    else:
        # ── 위상 정렬 모드 (기본) ──
        sorted_commits = topological_sort(commits_dict)

    # ── 커밋 출력 포맷팅 ──
    # 각 커밋의 브랜치 소속을 찾기 위한 역매핑을 구축합니다.
    # {커밋 해시: [브랜치1, 브랜치2, ...]}
    hash_to_branches = {}
    for branch_name, branch_hash in repo.branches.items():
        if branch_hash is not None:
            if branch_hash not in hash_to_branches:
                hash_to_branches[branch_hash] = []
            hash_to_branches[branch_hash].append(branch_name)

    lines = []
    for commit in sorted_commits:
        # 시간 포맷팅
        time_str = format_timestamp(commit.timestamp)

        # 브랜치 표시
        branch_labels = hash_to_branches.get(commit.hash, [])
        branch_str = ""
        if branch_labels:
            branch_str = " [" + ", ".join(branch_labels) + "]"

        # HEAD 표시
        head_marker = ""
        if repo.head and repo.branches.get(repo.head) == commit.hash:
            head_marker = " (HEAD)"

        lines.append(
            f"commit {commit.hash} ({commit.author}, {time_str})"
            f"{branch_str}{head_marker}"
        )
        lines.append(f"  {commit.message}")
        lines.append("")  # 빈 줄로 구분

    return "\n".join(lines).rstrip()


def handle_path(repo, args):
    """
    PATH 명령어를 처리합니다.

    두 커밋 사이의 최단 경로를 BFS로 찾습니다.

    ── 무방향 간선으로 간주 ──
    커밋-부모 관계를 양방향 이동 가능한 간선으로 취급합니다.
    즉, 부모에서 자식으로도, 자식에서 부모로도 이동할 수 있습니다.

    사용법: PATH <commit1> <commit2>
    예시:   PATH a1b2c3 d4e5f6
    """
    if not repo.initialized:
        return "Error: Repository not initialized. Use INIT first."

    if len(args) < 2:
        return "Invalid args: PATH <commit1> <commit2>"

    hash1 = args[0]
    hash2 = args[1]

    # ── 커밋 존재 여부 확인 ──
    if hash1 not in repo.commits:
        return f"Unknown commit: {hash1}"
    if hash2 not in repo.commits:
        return f"Unknown commit: {hash2}"

    # ── BFS로 최단 경로 탐색 ──
    path = find_shortest_path(repo.commits, hash1, hash2)

    if path is None:
        return "No path"

    # ── 경로 출력 포맷 ──
    path_str = " -> ".join(path)
    return f"Path: {path_str}"


def handle_ancestors(repo, args):
    """
    ANCESTORS 명령어를 처리합니다.

    특정 커밋의 모든 조상을 DFS로 탐색하여 출력합니다.

    ── 조상의 정의 ──
    부모 포인터를 재귀적으로 따라가며 도달할 수 있는 모든 커밋입니다.
    자기 자신은 포함하지 않습니다.

    사용법: ANCESTORS <commit_hash>
    예시:   ANCESTORS d4e5f6
    """
    if not repo.initialized:
        return "Error: Repository not initialized. Use INIT first."

    if len(args) < 1:
        return "Invalid args: ANCESTORS <commit_hash>"

    commit_hash = args[0]

    # ── 커밋 존재 여부 확인 ──
    if commit_hash not in repo.commits:
        return f"Unknown commit: {commit_hash}"

    # ── DFS로 조상 탐색 ──
    ancestors = find_ancestors(repo.commits, commit_hash)

    if not ancestors:
        return f"No ancestors found for commit {commit_hash}"

    # ── 결과 출력 ──
    lines = [f"Ancestors of {commit_hash}:"]
    for ancestor_hash in ancestors:
        commit = repo.get_commit(ancestor_hash)
        if commit:
            time_str = format_timestamp(commit.timestamp)
            lines.append(f"  {commit.hash} ({commit.author}, {time_str}): "
                         f"{commit.message}")
        else:
            lines.append(f"  {ancestor_hash}")

    return "\n".join(lines)


def handle_search(repo, args):
    """
    SEARCH 명령어를 처리합니다.

    ── 두 가지 검색 모드 ──
    1. SEARCH <keyword>:         키워드로 커밋 메시지 검색 (역색인 기반)
    2. SEARCH --author=<name>:   작성자 이름으로 검색 (역색인 기반)

    ── 역색인의 위력 ──
    역색인이 없다면 모든 커밋을 순회해야 하므로 O(N)입니다.
    역색인이 있으면 O(1)에 후보를 찾을 수 있습니다!

    사용법: SEARCH "login"
            SEARCH --author=Alice
    """
    if not repo.initialized:
        return "Error: Repository not initialized. Use INIT first."

    if len(args) < 1:
        return "Invalid args: SEARCH <keyword> or SEARCH --author=<name>"

    # ── 작성자 검색인지 키워드 검색인지 구분 ──
    if args[0].startswith("--author="):
        # 작성자 검색 모드
        author_name = args[0].split("=", 1)[1]
        commit_hashes = repo.inverted_index.search_author(author_name)
        search_type = f"author '{author_name}'"
    else:
        # 키워드 검색 모드
        keyword = " ".join(args).lower()
        commit_hashes = repo.inverted_index.search_keyword(keyword)
        search_type = f"keyword '{keyword}'"

    # ── 결과 출력 ──
    if not commit_hashes:
        return f"No commits found for {search_type}."

    lines = [f"Found {len(commit_hashes)} commit(s) for {search_type}:"]
    lines.append("")

    for commit_hash in commit_hashes:
        commit = repo.get_commit(commit_hash)
        if commit:
            lines.append(f"  - {commit.hash}: {commit.message}")

    return "\n".join(lines)


def handle_merge(repo, args):
    """
    [보너스 5.2] MERGE 명령어를 처리합니다.

    현재 브랜치에 지정된 브랜치를 병합합니다.
    부모가 2개인 머지 커밋을 생성합니다.

    사용법: MERGE <branch_name>
    예시:   MERGE feature
    """
    if not repo.initialized:
        return "Error: Repository not initialized. Use INIT first."

    if len(args) < 1:
        return "Invalid args: MERGE <branch_name>"

    return repo.merge(args[0])


def handle_diff(args):
    """
    [보너스 5.1] DIFF 명령어를 처리합니다.

    두 텍스트 파일을 줄 단위로 비교합니다.
    LCS(최장 공통 부분수열) 알고리즘을 사용합니다.

    사용법: DIFF <file1> <file2>
    예시:   DIFF old_version.txt new_version.txt
    """
    if len(args) < 2:
        return "Invalid args: DIFF <file1> <file2>"

    return diff_files(args[0], args[1])


def handle_benchmark():
    """
    [보너스 5.3] BENCHMARK 명령어를 처리합니다.

    Merge Sort와 Quick Sort의 성능을 다양한 입력 크기로 비교합니다.
    """
    return benchmark_sorts()


def handle_status(repo):
    """
    STATUS 명령어를 처리합니다. (편의 기능)

    현재 저장소 상태를 요약하여 출력합니다.

    사용법: STATUS
    """
    if not repo.initialized:
        return "Error: Repository not initialized. Use INIT first."

    lines = []
    lines.append(f"Current user:   {repo.current_user}")
    lines.append(f"Current branch: {repo.head}")

    head_hash = repo.get_head_commit_hash()
    if head_hash:
        commit = repo.get_commit(head_hash)
        lines.append(f"HEAD commit:    {head_hash} - {commit.message}")
    else:
        lines.append("HEAD commit:    (no commits yet)")

    lines.append(f"Total commits:  {len(repo.commits)}")
    lines.append(f"Branches:       {', '.join(repo.branches.keys())}")

    return "\n".join(lines)


def handle_help():
    """
    HELP 명령어를 처리합니다.

    사용 가능한 모든 명령어와 사용법을 출력합니다.
    """
    help_text = """
╔══════════════════════════════════════════════════════════════╗
║                    Mini Git — Command Help                   ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  INIT <user_name>         Initialize repository              ║
║  COMMIT <message>         Create a new commit                ║
║  BRANCH <name>            Create a new branch                ║
║  SWITCH <name>            Switch to a branch                 ║
║  LOG                      Show commits (topological order)   ║
║  LOG --sort-by=date       Show commits sorted by date        ║
║  LOG --sort-by=author     Show commits sorted by author      ║
║  PATH <hash1> <hash2>     Find shortest path between commits ║
║  ANCESTORS <hash>         Find all ancestors of a commit     ║
║  SEARCH <keyword>         Search commits by keyword          ║
║  SEARCH --author=<name>   Search commits by author           ║
║  STATUS                   Show repository status             ║
║                                                              ║
║  ── Bonus Commands ──                                        ║
║  MERGE <branch_name>      Merge a branch into current        ║
║  DIFF <file1> <file2>     Compare two text files (LCS)       ║
║  BENCHMARK                Compare sorting algorithms         ║
║                                                              ║
║  HELP                     Show this help message             ║
║  EXIT / QUIT              Exit Mini Git                      ║
╚══════════════════════════════════════════════════════════════╝
"""
    return help_text.strip()


def main():
    """
    Mini Git REPL 메인 루프.

    ── REPL 동작 흐름 ──
    1. 프롬프트(mini-git>) 출력
    2. 사용자 입력 읽기
    3. 입력 파싱 (명령어 + 인자 분리)
    4. 명령어에 따른 핸들러 호출
    5. 결과 출력
    6. 1번으로 돌아감 (exit/quit이면 종료)
    """
    # ── 저장소 객체 생성 ──
    # 아직 초기화되지 않은 빈 저장소입니다.
    # init 명령어를 실행해야 사용 가능합니다.
    repo = Repository()

    # ── 환영 메시지 출력 ──
    print("=" * 50)
    print("  Welcome to Mini Git!")
    print("  Type 'help' for available commands.")
    print("=" * 50)
    print()

    # ── REPL 메인 루프 ──
    while True:
        try:
            # ── Read: 사용자 입력 읽기 ──
            user_input = input("mini-git> ")
        except EOFError:
            # EOF (Ctrl+D)가 입력되면 종료합니다.
            print("\nGoodbye!")
            break
        except KeyboardInterrupt:
            # Ctrl+C가 입력되면 현재 입력만 취소합니다.
            print()  # 새 줄로 이동
            continue

        # ── Eval: 입력 파싱 및 실행 ──

        # 입력을 토큰으로 분리합니다.
        tokens = parse_input(user_input)
        if not tokens:
            continue  # 빈 입력은 무시

        # 명령어 추출 (대소문자 무시)
        command = tokens[0].upper()
        args = tokens[1:]  # 나머지는 인자

        # ── 명령어 라우팅 ──
        # 각 명령어를 해당 핸들러 함수로 연결합니다.
        # 이것은 "명령 패턴(Command Pattern)"의 간단한 구현입니다.

        result = None  # 실행 결과를 담을 변수

        if command in ("EXIT", "QUIT"):
            # ── 종료 명령 ──
            print("Goodbye!")
            break

        elif command == "INIT":
            result = handle_init(repo, args)

        elif command == "COMMIT":
            result = handle_commit(repo, args)

        elif command == "BRANCH":
            result = handle_branch(repo, args)

        elif command == "SWITCH":
            result = handle_switch(repo, args)

        elif command == "LOG":
            result = handle_log(repo, args)

        elif command == "PATH":
            result = handle_path(repo, args)

        elif command == "ANCESTORS":
            result = handle_ancestors(repo, args)

        elif command == "SEARCH":
            result = handle_search(repo, args)

        elif command == "MERGE":
            result = handle_merge(repo, args)

        elif command == "DIFF":
            result = handle_diff(args)

        elif command == "BENCHMARK":
            result = handle_benchmark()

        elif command == "STATUS":
            result = handle_status(repo)

        elif command == "HELP":
            result = handle_help()

        else:
            result = f"Unknown command: {tokens[0]}. Type 'help' for available commands."

        # ── Print: 결과 출력 ──
        if result:
            print(result)
            print()  # 결과 후 빈 줄로 가독성 향상


# ── 스크립트 직접 실행 시에만 main() 호출 ──
# 이 조건문은 Python의 관용적 패턴입니다.
# 다른 파일에서 import할 때는 main()이 실행되지 않습니다.
# 오직 `python main.py`로 직접 실행할 때만 main()이 실행됩니다.
if __name__ == "__main__":
    main()

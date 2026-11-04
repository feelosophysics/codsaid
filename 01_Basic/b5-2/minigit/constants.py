"""여러 파일에서 함께 쓰는 설정과 화면 문구.

명령을 이해하는 데 필요한 이름은 사용 위치에 두고, 반복되는 문구만 모았다.
"""


class ConfigConstants:
    DEFAULT_BRANCH = "main"
    TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
    MAX_DIFF_FILE_BYTES = 1_048_576
    MAX_DIFF_CELLS = 1_000_000


class ErrorMessages:
    REPO_NOT_INIT = "Error: Repository not initialized. Use INIT first."
    INVALID_ARGS = "Error: Invalid args"
    INVALID_INIT = "Error: Invalid args: INIT <user_name>"
    INVALID_USER = "Error: Invalid args: USER <user_name>"
    INVALID_COMMIT = "Error: Invalid args: COMMIT <message>"
    INVALID_BRANCH = "Error: Invalid args: BRANCH <branch_name>"
    INVALID_SWITCH = "Error: Invalid args: SWITCH <branch_name>"
    INVALID_LOG = "Error: Invalid args: LOG [--sort-by=date|author]"
    INVALID_PATH = "Error: Invalid args: PATH <commit1> <commit2>"
    INVALID_ANCESTORS = "Error: Invalid args: ANCESTORS <commit_hash>"
    INVALID_SEARCH = "Error: Invalid args: SEARCH <keyword> or SEARCH --author=<name>"
    INVALID_MERGE = "Error: Invalid args: MERGE <branch_name>"
    INVALID_DIFF = "Error: Invalid args: DIFF <file1> <file2>"
    INVALID_SORT_KEY = "Error: Invalid sort key: {key}. Use 'date' or 'author'."
    UNKNOWN_BRANCH = "Error: Unknown branch: {name}"
    BRANCH_ALREADY_EXISTS = "Error: Branch '{name}' already exists."
    UNKNOWN_COMMIT = "Error: Unknown commit: {hash}"
    MERGE_SELF = "Error: Cannot merge a branch into itself."
    MERGE_NO_COMMITS = "Error: Cannot merge branches without commits."
    FILE_NOT_FOUND = "Error: File not found: {path}"
    FILE_READ_ERROR = "Error: Error reading {path}: {error}"
    DIFF_LIMIT = "Error: DIFF input too large: {reason}"


class SystemMessages:
    PROMPT = "mini-git> "
    WELCOME = "Welcome to Mini Git! Type HELP for commands."
    GOODBYE = "Goodbye!"
    UNKNOWN_COMMAND = "Unknown command: {command}. Type HELP for commands."
    NO_COMMITS_YET = "No commits yet."
    NO_PATH = "No path"
    ALREADY_UP_TO_DATE = "Already up to date."
    INIT_SUCCESS = "Initialized repository.\nCurrent branch: {branch}\nCurrent user: {user}"
    USER_CHANGED = "Current user: {user}"
    COMMIT_SUCCESS = "[{branch} {hash}] {message}"
    BRANCH_CREATED = "Created branch: {name}"
    SWITCHED_BRANCH = "Switched to branch: {name}"
    MERGE_SUCCESS = "Merged '{branch}' into '{head}'.\n[{head} {hash}] {message}"
    SEARCH_NO_RESULTS = "No commits found for {search_type}."
    SEARCH_FOUND = "Found {count} commit(s) for {search_type}:"
    HELP_TEXT = """Commands (put spaces inside quotes):
  INIT <user_name>          Initialize or reset the repository
  USER <user_name>          Set author for future commits
  COMMIT <message>          Make a commit on the current branch
  BRANCH <branch_name>      Create a branch at the current commit
  SWITCH <branch_name>      Change the current branch
  LOG                       Show every commit, parents first
  LOG --sort-by=date        Show commits by timestamp
  LOG --sort-by=author      Show commits by author
  PATH <hash1> <hash2>      Shortest undirected path
  ANCESTORS <hash>          Show all ancestors
  SEARCH <keyword>          Search a word or quoted phrase
  SEARCH --author=<name>    Search by author
  MERGE <branch_name>       Make a two-parent merge commit
  DIFF <file1> <file2>      Compare UTF-8 text files
  BENCHMARK                 Compare two handwritten sorts
  STATUS                    Show current repository state
  HELP                      Show this help
  EXIT / QUIT               Leave Mini Git"""

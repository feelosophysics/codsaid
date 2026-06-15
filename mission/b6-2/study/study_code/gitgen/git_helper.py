# ==============================================================================
# 파일명: study/study_code/gitgen/git_helper.py
# 목적: 파이썬 프로그램 내부에서 외부 Git 명령어(status, diff, add, commit)를 실행하고 제어하는 헬퍼 모듈입니다.
# ==============================================================================

"""
[파이썬 문법 및 컴퓨터 과학(CS) 개념 설명]

1. 운영체제(OS)와 프로세스(Process)
   - 프로세스는 OS로부터 메모리와 자원을 할당받아 실행 중인 프로그램의 인스턴스를 뜻합니다.
   - 파이썬 프로그램도 하나의 프로세스(부모 프로세스)입니다. 이 파이썬 프로그램 안에서 다른 프로그램(예: 'git')을 실행시키려면,
     OS 커널에 요청해 새로운 자식 프로세스(Child Process)를 생성해야 합니다.

2. 프로세스 생성 모델 (Fork & Exec)
   - 유닉스 계열 OS(macOS, Linux 등)는 새로운 프로세스를 만들 때 기존 프로세스를 복제하는 `fork()` 시스템 콜을 수행한 뒤,
     새로 만든 프로세스의 메모리 영역을 실행할 프로그램(여기서는 Git 바이너리)의 코드로 덮어씌우는 `exec()`를 수행합니다.
   - 파이썬의 `subprocess` 모듈은 이 복잡한 OS 수준의 동작을 추상화하여 편리한 API로 제공합니다.

3. `subprocess.run` 함수의 매개변수 상세 분석
   - `['git', 'status', '-s']`: 실행할 명령어와 옵션들을 공백 기준의 문자열 리스트로 전달합니다. 쉘 인젝션(Shell Injection) 보안 취약점을 차단하기 위한 파이썬의 권장 방식입니다.
   - `capture_output=True`: 자식 프로세스가 출력한 표준 출력(stdout)과 표준 에러(stderr)를 화면에 바로 띄우지 않고, 파이썬 메모리로 파이프(Pipe) 연결하여 가져오겠다는 뜻입니다.
   - `text=True`: 프로세스로부터 넘어오는 로우(Raw) 바이너리 바이트(bytes) 데이터를 문자열(str) 형식으로 자동 디코딩해 주도록 설정합니다.
   - `check=True`: 실행한 명령어의 종료 코드가 0이 아닌 경우(에러 발생 시) `subprocess.CalledProcessError` 예외를 즉시 던지도록 강제합니다.

4. 프로세스 종료 코드 (Exit Code)
   - 프로세스가 실행을 끝마치면 운영체제에게 작업 결과를 숫자로 보고합니다. 이를 종료 코드(Exit Status/Exit Code)라고 합니다.
   - 컴퓨터 과학의 오랜 규칙에 따라, `0`은 성공(Success)을 의미하고, `0이 아닌 모든 숫자(1, 2, 128 등)`는 에러나 비정상 종료를 나타냅니다.
   - 예컨대 Git 저장소가 아닌 디렉토리에서 Git 명령어를 수행하면 Git 프로세스는 에러 코드(대개 128)를 반환하고, 파이썬의 `check=True` 옵션은 이를 예외 상황으로 인지하여 캐치합니다.

5. Git Short Status (`git status -s`)의 출력 형식 분석
   - `git status -s`는 변경 상태를 간결하게 2글자의 상태 코드와 파일 경로 형태로 반환합니다: `XY 파일경로`
   - 첫 번째 글자 `X`는 인덱스(Stage) 영역의 상태를 나타냅니다.
   - 두 번째 글자 `Y`는 작업 디렉토리(Worktree, Unstaged) 영역의 상태를 나타냅니다.
   - 상태 기호 종류:
     - `' '` (공백): 변경 없음
     - `'M'` : 파일 수정됨 (Modified)
     - `'A'` : 파일 추가됨 (Added)
     - `'D'` : 파일 삭제됨 (Deleted)
     - `'?'` : 추적하지 않는 새 파일 (Untracked)
   - 예: ` M main.py` -> X가 공백, Y가 M이므로 'Unstaged 수정 상태'
   - 예: `M  main.py` -> X가 M, Y가 공백이므로 'Staged(git add 완료) 상태'
   - 예: `?? main.py` -> 추적 대상이 아닌 새 파일 상태
"""

# Git 명령어 실행을 통해 저장소 상태 및 변경 사항을 수집하는 모듈을 설명하는 모듈 수준의 Docstring
"""Git 명령어 실행을 통해 저장소 상태 및 변경 사항을 수집하는 모듈입니다."""

import sys         # 시스템 제어(프로그램 종료 sys.exit 등)를 위해 파이썬 표준 라이브러리 sys 임포트
import subprocess  # 외부 운영체제 프로세스 실행을 위해 파이썬 표준 라이브러리 subprocess 임포트

def get_git_status():
    """현재 Git 저장소의 상태(변경된 파일 목록)를 수집하여 2글자 요약 포맷 문자열로 반환합니다.
    
    내부적으로 `git status -s` 프로세스를 실행합니다.
    만약 현재 작업 폴더가 Git 저장소(Repository)가 아닌 곳에서 실행 시 에러 메시지를 출력하고 프로세스를 종료합니다.
    """
    try:
        # subprocess.run을 사용하여 'git status -s'를 동기(Synchronous) 방식으로 호출합니다.
        # 프로세스 실행이 완료될 때까지 파이썬 프로세스는 대기(Block) 상태가 됩니다.
        result = subprocess.run(
            ['git', 'status', '-s'], 
            capture_output=True, 
            text=True, 
            check=True
        )
        # 실행 결과의 표준 출력(result.stdout) 끝부분에 남는 불필요한 공백/개행 문자(\n)들을 제거(.rstrip())한 뒤 반환합니다.
        return result.stdout.rstrip()
    except subprocess.CalledProcessError:
        # Git 명령이 실패하는 주된 원인은 현재 위치가 Git 초기화가 안 된 폴더이기 때문입니다.
        print("[ERROR] Git 저장소가 아니거나 Git 명령어를 실행할 수 없습니다.")
        # sys.exit(1)은 프로세스 종료 코드로 '1'(실패)을 반환하며 파이썬 가상머신을 즉시 탈출시킵니다.
        sys.exit(1)


def get_git_diff(staged_only=False):
    """현재 Git 저장소에 있는 실제 코드 변경 내용(diff)을 수집하여 문자열로 반환합니다.
    
    - staged_only가 True이면 스테이징 영역에 올라간(--cached) 변경 사항만 수집합니다.
    - staged_only가 False이면 먼저 Unstaged 변경 사항을 조회하고,
      Unstaged가 비어 있을 경우 Staged 변경 사항을 차선책으로 조회하여 반환합니다.
    """
    try:
        # 1. staged_only 매개변수가 True인 경우 (무조건 git diff --cached만 수행)
        if staged_only:
            # '--cached' 옵션은 'git diff'에서 스테이징 영역의 코드를 볼 때 사용하는 옵션입니다.
            result = subprocess.run(
                ['git', 'diff', '--cached'], 
                capture_output=True, 
                text=True, 
                check=True
            )
            return result.stdout.strip()
            
        # 2. staged_only가 False인 경우 (Unstaged 변경사항 우선 조회)
        # 옵션 없는 'git diff'는 아직 git add 되지 않은 순수 작업 공간(Worktree)의 변경사항을 보여줍니다.
        result = subprocess.run(
            ['git', 'diff'], 
            capture_output=True, 
            text=True, 
            check=True
        )
        diff_text = result.stdout.strip()
        
        # 가드 클로즈(Early Return): 만약 Unstaged 변경 코드 텍스트(diff_text)가 존재한다면 바로 리턴합니다.
        if diff_text:
            return diff_text
            
        # 3. Unstaged 변경 사항이 없다면 이미 git add 되어 있는 변경 코드(Staged)를 조회하여 반환합니다.
        result = subprocess.run(
            ['git', 'diff', '--cached'], 
            capture_output=True, 
            text=True, 
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        print("[ERROR] Git diff 명령어를 실행할 수 없습니다.")
        sys.exit(1)


def has_unstaged_changes():
    """현재 Stage(git add)되지 않았거나 새로 추가되어 추적 대상이 아닌(untracked) 파일이 존재하는지 확인합니다.
    
    'git status -s'의 각 줄(Line)의 2글자 상태 코드를 파싱하여 판별합니다.
    """
    # 현재 저장소 상태 텍스트를 불러옵니다.
    status_text = get_git_status()
    
    # 변경 파일이 아예 없다면(빈 문자열인 경우) Unstaged 변경사항도 없으므로 False를 리턴합니다.
    if not status_text:
        return False
        
    # 줄바꿈 기호를 기준으로 각 줄을 쪼개어 파일 단위 리스트를 만듭니다.
    lines = status_text.splitlines()
    
    # 각 파일별 상태 라인을 순회하며 검증합니다.
    for line in lines:
        # 최소한 2글자 이상의 상태 기호가 존재하는 안전한 라인인지 확인합니다.
        if len(line) >= 2:
            # 2글자 상태 표시 정보 중 첫 번째 글자(Staged 표시)와 두 번째 글자(Unstaged 표시) 추출
            first_char = line[0]
            second_char = line[1]
            
            # 두 번째 글자가 공백(' ')이 아니라는 것은 Unstaged 영역에 수정본이 남아 있음을 의미하며,
            # 첫 번째 글자가 물음표('?')라는 것은 Git이 새로 감지한 추적되지 않는 파일(??)임을 의미합니다.
            if second_char != ' ' or first_char == '?':
                return True  # 조건 충족 시 Unstaged 변경사항이 있으므로 즉시 True를 리턴하고 루프를 탈출합니다.
                
    # 모든 라인을 다 돌아도 조건에 매칭되는 행이 없다면 Unstaged 변경 사항이 없는 것입니다.
    return False


def has_staged_changes():
    """현재 스테이징 영역(git add 완료 상태)에 변경 사항이 등록되어 있는지 확인합니다.
    
    마찬가지로 'git status -s' 결과를 한 줄씩 검사하여 판별합니다.
    """
    status_text = get_git_status()
    
    if not status_text:
        return False
        
    lines = status_text.splitlines()
    for line in lines:
        if len(line) >= 2:
            first_char = line[0]
            # 첫 번째 글자(X)가 공백(' ')도 아니고 물음표('?')도 아니라는 것은
            # 해당 파일이 '스테이징 영역(Staged)'에 인덱싱(예: M, A, D 등)되었음을 뜻합니다.
            if first_char != ' ' and first_char != '?':
                return True
                
    return False


def git_add_all():
    """현재 디렉토리와 하위 디렉토리 내의 모든 변경 및 추가 사항을 스테이징(git add .) 처리합니다.
    
    작업 실패 시 에러 메시지를 출력하고 프로그램을 종료(sys.exit(1))합니다.
    """
    try:
        # 'git add .' 명령어 실행. check=True로 설정하여 에러 코드가 리턴되면 자동으로 예외가 발생합니다.
        subprocess.run(['git', 'add', '.'], check=True)
        print("[INFO] 모든 변경 사항을 성공적으로 stage(git add .) 하였습니다.")
    except subprocess.CalledProcessError:
        print("[ERROR] 'git add .' 명령어 실행 중 오류가 발생했습니다.")
        sys.exit(1)


def run_git_commit(commit_message):
    """최종 전달받은 커밋 메시지를 매개변수로 받아 실제 로컬 Git 커밋(`git commit -m "메시지"`)을 실행합니다.
    
    메시지가 공백뿐이거나 비어 있으면 실행을 제어하고 에러 처리합니다.
    """
    # 1. 데이터 정제 및 유효성 검사 (Early Return)
    # .strip()을 호출하여 메시지 양끝의 불필요한 공백과 줄바꿈을 제거합니다.
    clean_message = commit_message.strip()
    # 만약 메시지가 완전히 비어버린 경우 커밋을 중단시킵니다.
    if not clean_message:
        print("[ERROR] 커밋 메시지가 비어 있어 커밋을 진행할 수 없습니다.")
        sys.exit(1)
        
    # 2. 로직 실행
    try:
        # subprocess.run을 호출해 'git commit -m "내용"'을 실행합니다.
        # 터미널 명령어 수준의 git commit -m 과 동일하게 동작합니다.
        subprocess.run(['git', 'commit', '-m', clean_message], check=True)
        print("[INFO] 커밋이 성공적으로 완료되었습니다!")
    except subprocess.CalledProcessError:
        print("[ERROR] 'git commit' 명령어 실행 중 오류가 발생했습니다.")
        sys.exit(1)

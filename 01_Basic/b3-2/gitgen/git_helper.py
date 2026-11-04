"""Git 명령어 실행을 통해 저장소 상태 및 변경 사항을 수집하는 모듈입니다."""

import sys
import subprocess

def get_git_status():
    """현재 Git 저장소의 상태(변경된 파일 목록)를 수집하여 문자열로 반환합니다.
    
    subprocess.run을 호출하여 'git status -s'를 실행하고 결과를 텍스트로 받아옵니다.
    만약 Git 저장소가 아닌 곳에서 실행 시 프로그램을 비정상 종료합니다.
    """
    try:
        result = subprocess.run(['git', 'status', '-s'], capture_output=True, text=True, check=True)
        return result.stdout.rstrip()
    except subprocess.CalledProcessError:
        print("[ERROR] Git 저장소가 아니거나 Git 명령어를 실행할 수 없습니다.")
        sys.exit(1)


def get_git_diff(staged_only=False):
    """현재 Git 저장소에 있는 변경 내용(코드의 추가/삭제 정보)을 수집하여 반환합니다.
    
    staged_only가 True이면 staged (--cached) 변경 사항만 조회하고 반환합니다.
    False이면 unstaged 변경 사항을 조회하고, 없을 경우 staged 변경 사항을 조회하여 반환합니다.
    """
    try:
        if staged_only:
            result = subprocess.run(['git', 'diff', '--cached'], capture_output=True, text=True, check=True)
            return result.stdout.strip()
            
        result = subprocess.run(['git', 'diff'], capture_output=True, text=True, check=True)
        diff_text = result.stdout.strip()
        
        # Early Return: unstaged 변경 사항이 있는 경우 즉시 반환
        if diff_text:
            return diff_text
            
        # unstaged가 비어 있다면 staged (--cached) 변경 사항을 조회하여 반환
        result = subprocess.run(['git', 'diff', '--cached'], capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        print("[ERROR] Git diff 명령어를 실행할 수 없습니다.")
        sys.exit(1)


def has_unstaged_changes():
    """현재 Stage되지 않은 변경 사항(unstaged or untracked)이 존재하는지 확인합니다.
    
    'git status -s' 결과를 한 줄씩 검사하여 unstaged 변경 사항 유무를 판단합니다.
    """
    status_text = get_git_status()
    
    if not status_text:
        return False
        
    lines = status_text.splitlines()
    for line in lines:
        if len(line) >= 2:
            first_char = line[0]
            second_char = line[1]
            if second_char != ' ' or first_char == '?':
                return True
                
    return False


def has_staged_changes():
    """현재 Stage(git add)된 변경 사항이 존재하는지 확인합니다.
    
    'git status -s' 결과를 한 줄씩 검사하여 staged 변경 사항 유무를 판단합니다.
    """
    status_text = get_git_status()
    
    if not status_text:
        return False
        
    lines = status_text.splitlines()
    for line in lines:
        if len(line) >= 2:
            first_char = line[0]
            if first_char != ' ' and first_char != '?':
                return True
                
    return False


def git_add_all():
    """현재 디렉토리의 모든 변경 사항을 스테이징(git add .) 처리합니다.
    
    실패 시 에러 메시지를 출력하고 프로그램을 종료합니다.
    """
    try:
        subprocess.run(['git', 'add', '.'], check=True)
        print("[INFO] 모든 변경 사항을 성공적으로 stage(git add .) 하였습니다.")
    except subprocess.CalledProcessError:
        print("[ERROR] 'git add .' 명령어 실행 중 오류가 발생했습니다.")
        sys.exit(1)


def run_git_commit(commit_message):
    """지정된 커밋 메시지로 Git 커밋을 수행합니다.
    
    커밋 메시지가 비어있는 경우 에러를 반환하며, 커밋 실행 후 완료 메시지를 출력합니다.
    """
    # 1. 데이터 정제 및 유효성 검사 (Early Return)
    clean_message = commit_message.strip()
    if not clean_message:
        print("[ERROR] 커밋 메시지가 비어 있어 커밋을 진행할 수 없습니다.")
        sys.exit(1)
        
    # 2. 로직 실행
    try:
        subprocess.run(['git', 'commit', '-m', clean_message], check=True)
        print("[INFO] 커밋이 성공적으로 완료되었습니다!")
    except subprocess.CalledProcessError:
        print("[ERROR] 'git commit' 명령어 실행 중 오류가 발생했습니다.")
        sys.exit(1)


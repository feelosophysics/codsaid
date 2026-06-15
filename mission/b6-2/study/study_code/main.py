# ==============================================================================
# 파일명: study/study_code/main.py
# 목적: AI Git 자동 커밋 및 PR 생성 도구의 메인 실행(Entry Point) 모듈입니다.
# ==============================================================================

"""
[파이썬 문법 및 컴퓨터 과학(CS) 개념 설명]

1. 명령줄 인수 파싱 (CLI Argument Parsing - `argparse` 모듈)
   - CLI(Command Line Interface) 환경에서 프로그램을 실행할 때 전달하는 매개변수들을 처리해 주는 표준 라이브러리입니다.
   - 예: `python main.py commit --model gemini-1.5-flash`에서 'commit'과 '--model' 등을 구분하고 바인딩합니다.
   - **Subparsers**: 명령어 구조를 계층화합니다. 여기서는 `commit` 명령어와 `pr` 명령어를 분기하여 서로 다른 서브 명령어로 취급할 수 있게 만듭니다.
   - **`action='store_true'`**: CLI 옵션(예: `--safe-mode`)이 지정되면 True를 할당하고, 없으면 기본값으로 False를 자동 저장하도록 지시합니다.

2. 가상환경 및 환경 변수(Environment Variable - `dotenv` 모듈)
   - 환경 변수는 운영체제(OS)가 프로세스를 실행할 때 제공하는 전역적인 키-값(Key-Value) 문자열 정보 테이블입니다.
   - 소스 코드 내에 API Key나 DB 패스워드 같은 민감한 설정값을 직접 작성(Hardcoding)하면 보안상 큰 위험이 따르므로, OS 환경 변수에 값을 저장해두고 불러와서 사용합니다.
   - `load_dotenv()` 함수는 현재 디렉토리의 `.env` 파일에 기록된 키-값 데이터를 프로세스의 실제 OS 환경 변수 영역(`os.environ`)으로 로드시켜 주는 역할을 수행합니다.

3. 로컬 패키지 임포트 및 검색 경로 (`sys.path`)
   - 파이썬에서 `from gitgen.git_helper import ...`와 같은 구문을 실행하면, 파이썬 인터프리터는 모듈 검색 경로 리스트(`sys.path`)에서 'gitgen'이라는 이름의 폴더를 찾기 시작합니다.
   - 사용자가 `python study/study_code/main.py` 명령어를 통해 이 파일을 직접 실행하면, 파이썬은 실행 대상 파일이 위치한 디렉토리인 `study/study_code`를 `sys.path[0]`(검색 최우선 경로)에 자동으로 추가해 줍니다.
   - 덕분에 `study/study_code` 내부에 있는 `gitgen` 폴더를 정상적으로 인식하여 하위 모듈들을 문제없이 가져올 수 있습니다.

4. `input()` 함수와 블로킹 I/O (Blocking Input/Output)
   - `input("질문 내용: ")` 함수는 사용자로부터 터미널 입력을 대기합니다.
   - CS 원리: 프로세스가 사용자 키보드 입력을 처리하는 시스템 콜을 실행하면, 운영체제는 해당 프로세스를 '대기(Blocked)' 상태로 전환하고 CPU 연산에서 제외시킵니다. 사용자가 입력을 마치고 Enter키를 누르는 순간 인터럽트(Interrupt)가 발생하여 프로세스가 다시 '실행 가능(Ready/Running)' 상태가 되어 코드를 이어 나가게 됩니다.

5. 엔트리 포인트(Entry Point) 패턴: `if __name__ == "__main__":`
   - 파이썬 파일이 작동할 때, 파이썬 엔진은 내부의 특별한 내장 변수인 `__name__` 값을 채웁니다.
   - 터미널에서 `python main.py`처럼 이 파일을 직접 타겟으로 지정해 실행하면, `__name__` 변수에는 `"__main__"` 이라는 문자열이 대입됩니다.
   - 반대로 다른 파일에서 `import main` 형태로 이 파일을 불러다 쓰기만 하는 경우에는 해당 파일의 본래 모듈명인 `"main"`이 대입됩니다.
   - 이 구문을 활용하여 '라이브러리(임포트용)'로 쓰일 때는 메인 코드가 돌지 않고, 오직 '실행형 스크립트'로 작동할 때만 `main()` 함수를 실행하도록 제어할 수 있습니다.
"""

# 메인 실행 모듈에 대한 모듈 수준의 Docstring
"""AI 기반 Git 커밋 & PR 자동 생성기 도구의 메인 실행 모듈입니다.

사용자의 Git 변경 사항을 수집하고 AI API를 호출하여 최적의 커밋 메시지 또는 PR 초안을 생성합니다.
"""

import sys       # 파이썬 인터프리터 제어 및 에러 코드 반환을 위해 파이썬 표준 라이브러리 sys 임포트
import argparse  # 명령줄 인자(CLI Arguments) 파싱을 위해 파이썬 표준 라이브러리 argparse 임포트
from dotenv import load_dotenv  # 로컬 .env 환경 설정 파일 로드를 위해 외부 dotenv 라이브러리 임포트

# 로컬 gitgen 패키지 내의 하위 모듈 함수들을 명시적으로 불러옵니다.
from gitgen.git_helper import (
    get_git_status,
    get_git_diff,
    has_unstaged_changes,
    has_staged_changes,
    git_add_all,
    run_git_commit
)
from gitgen.safe_mode import apply_safe_mode       # 민감 정보 필터링 기능 로드
from gitgen.config import load_convention          # 팀 내 약속 설정 파일 로더 로드
from gitgen.gemini_client import call_gemini_api   # AI REST API 클라이언트 함수 로드
from gitgen.prompt_templates import PromptTemplates # 프롬프트 문자열 그룹 클래스 로드


def generate_commit_message(args, diff_text, status_text, convention):
    """Git 변경 코드 내용(diff)과 현재 저장소 상태(status), 그리고 설정 파일(convention)을 결합하여
    AI에게 전달할 최종 프롬프트를 만들고, API 호출 결과를 출력 및 반환합니다.
    """
    # PromptTemplates 클래스의 정적 변수를 읽어와 .format()으로 변경 사항 데이터 삽입
    prompt = PromptTemplates.COMMIT_MESSAGE_PROMPT.format(
        status_text=status_text,
        diff_text=diff_text
    )
    
    # 딕셔너리가 유효(None이 아님)하고, 키 값 'commit'이 설정되어 있는 경우
    # 해당 규칙을 프롬프트 문자열 끝부분에 결합(String Concatenation)합니다.
    if convention and 'commit' in convention:
        commit_conv = convention['commit']
        prompt += "\n[팀 컨벤션 규칙]\n"
        
        # 제목 규칙(prefix_rules)이 존재하는 경우 텍스트 조립
        if 'prefix_rules' in commit_conv:
            prompt += "- 다음 Prefix 중 하나를 반드시 제목 앞에 사용해주세요:\n  "
            # 리스트에 든 여러 태그(feat, fix 등)를 줄바꿈과 띄어쓰기로 이어붙입니다.
            prompt += "\n  ".join(commit_conv['prefix_rules']) + "\n"
            
        # 포맷 규칙(format_requirements)이 존재하는 경우 텍스트 조립
        if 'format_requirements' in commit_conv:
            prompt += "- 추가 포맷 요구사항:\n  "
            prompt += "\n  ".join(commit_conv['format_requirements']) + "\n"

    # AI 모델이 스스로 생각을 말하거나 꾸밈말을 덧붙이지 않도록 엄격한 출력 제약 조건을 끝에 부착합니다.
    prompt += "\n위 규칙을 준수하여 결과물(커밋 메시지)만 출력해주세요. 다른 인사말이나 부연 설명은 하지 마세요."
    
    # gemini_client 모듈의 call_gemini_api 함수를 호출해 HTTP POST API 전송을 대기(Block)합니다.
    result = call_gemini_api(
        prompt, 
        args.model, 
        args.temperature, 
        args.max_tokens, 
        thinking_level=args.thinking_level
    )
    
    # 생성된 커밋 메시지 결과물을 화면에 구분선과 함께 출력합니다.
    print("[DONE] 커밋 메시지 생성 완료\n")
    print("--- Commit Message ---")
    print(result)
    print("----------------------")
    return result


def generate_pr_draft(args, diff_text, status_text, convention):
    """Git 변경 사항 정보를 토대로 AI에게 PR 제목 및 상세 설명 마크다운 본문을 작성해 달라고 요청합니다."""
    # PR용 템플릿에 맞추어 문자열을 포맷팅합니다.
    prompt = PromptTemplates.PR_DRAFT_PROMPT.format(
        status_text=status_text,
        diff_text=diff_text
    )
    
    # PR 규칙 설정이 있는 경우 프롬프트에 추가 결합합니다.
    if convention and 'pr' in convention:
        pr_conv = convention['pr']
        prompt += "\n[팀 컨벤션 규칙]\n"
        
        if 'additional_requirements' in pr_conv:
            prompt += "- 추가 요구사항:\n  "
            prompt += "\n  ".join(pr_conv['additional_requirements']) + "\n"

    prompt += "\n위 규칙을 준수하여 결과물(PR 초안)만 출력해주세요. 마크다운 형식으로 작성해주세요. 다른 인사말이나 부연 설명은 하지 마세요."
    
    result = call_gemini_api(
        prompt, 
        args.model, 
        args.temperature, 
        args.max_tokens, 
        thinking_level=args.thinking_level
    )
    
    # 최종 작성된 PR 초안 텍스트 출력
    print("[DONE] PR 초안 생성 완료\n")
    print("--- PR Draft ---")
    print(result)
    print("-----------------")


def main():
    """AI Git 도구의 전체적인 진입 흐름 및 실행 제어를 분기하는 핵심 함수입니다.
    
    1. CLI 파라미터를 등록하고 파싱합니다.
    2. 명령어(commit / pr)에 따라 Git 변경 이력을 가져옵니다.
    3. 사용자 인터랙션(Staging 여부)을 받고 비즈니스 함수를 구동합니다.
    """
    # ArgumentParser 객체를 초기화하여 도움말 텍스트와 이름을 부여합니다.
    parser = argparse.ArgumentParser(description="AI 기반 Git 커밋 & PR 자동 생성기")
    
    # 명령어 그룹화를 위한 서브 파서(subparsers) 풀을 구성합니다.
    # dest='command'를 지정하여 사용자가 'commit'을 쳤는지 'pr'을 쳤는지 구별하게 합니다.
    subparsers = parser.add_subparsers(dest='command', help='실행할 명령어 (commit 또는 pr)')
    subparsers.add_parser('commit', help='커밋 메시지 자동 생성')
    subparsers.add_parser('pr', help='PR 제목 및 본문 자동 생성')
    
    # 공통 실행 옵션 등록 (기본값 설정 및 도움말 포함)
    parser.add_argument('--model', '-model', type=str, default='gemma-4-31b-it', help='사용할 AI 모델 이름 (기본값: gemma-4-31b-it)')
    parser.add_argument('--temperature', '-temperature', type=float, default=0.7, help='AI 응답의 창의성 정도 (0.0 ~ 1.0, 기본값: 0.7)')
    parser.add_argument('--max-tokens', '-max-tokens', type=int, default=2000, help='생성할 최대 토큰 수 (기본값: 2000)')
    parser.add_argument('--safe-mode', '-safe-mode', action='store_true', help='안전 모드 활성화 (민감 정보 마스킹 및 전송량 제한)')
    parser.add_argument('--safe-lines', '-safe-lines', type=int, default=200, help='안전 모드 활성화 시 전송할 최대 diff 라인 수 (기본값: 200)')
    parser.add_argument('--thinking-level', '-thinking-level', type=str, default='unspecified', choices=['high', 'unspecified'], help='Gemma 4 모델 사용 시 사고 수준 설정 (기본값: unspecified)')
    
    # CLI에서 넘겨준 문자열 배열(sys.argv)을 분석하여 args 네임스페이스 객체로 변환합니다.
    args = parser.parse_args()
    
    # 1. CLI 아규먼트 유효성 검사 (Early Return / Guard Clause 적용)
    # commit 이나 pr 명령이 생략된 경우 도움말 가이드를 뿌리고 프로그램 강제 탈출 처리합니다.
    if not args.command:
        parser.print_help()
        sys.exit(1)

    # .env 파일에서 환경 설정 값을 읽어 들여 파이썬 실행 전역 환경 변수에 이식합니다.
    load_dotenv()
    # 팀 내 설정 파일 .ai-gitgen.yml 로드를 시도합니다.
    convention = load_convention()
    
    # 2. 명령어 분기 및 비즈니스 로직 연동
    if args.command == 'commit':
        # API 전송 범위를 결정할 플래그 초기화
        staged_only = False
        just_staged = False
        
        # Git Status를 검사해 현재 'Staged(git add된)' 파일들이 존재하는지 사전에 추적해 둡니다.
        already_staged = has_staged_changes()
        
        # 1) 작업 공간에 Unstaged(수정되었으나 아직 add하지 않은) 변경이 있는지 먼저 판별합니다.
        if has_unstaged_changes():
            # 사용자에게 y/n 키 입력을 유도합니다 (대기/블로킹 I/O 발생).
            # .strip()은 앞뒤 쓸데없는 스페이스 제거, .lower()는 대소문자 구분 없이 소문자로 단일화.
            user_input = input("unstaged 변경 사항이 있습니다. 모두 stage(git add .)하고 진행할까요? (y/n): ").strip().lower()
            if user_input == 'y' or user_input == 'yes':
                # 사용자가 동의(y)하면 'git add .' 명령어 함수를 실행하여 모두 인덱스 영역에 등록합니다.
                git_add_all()
                just_staged = True
            else:
                # 동의하지 않는 경우, 이미 add된(staged) 부분에 대해서만 분석하고 커밋을 생성하게 지정합니다.
                staged_only = True
                
        # 2) 최종 검사 단계 (Staged된 변경 사항이 진짜로 단 한 개도 없는 상태인 경우)
        if not has_staged_changes():
            print("[INFO] 커밋할 stage된 변경 사항이 없습니다. 작업을 종료합니다.")
            sys.exit(0) # 0 코드를 주어 정상적으로 프로세스를 반환하고 프로그램을 조기 퇴장시킵니다.
            
        # 이미 이전에 스테이징된 코드가 있었는데, 이번 루프에서 새로 git add를 총괄 수행한 게 아닌 경우
        if already_staged and not just_staged:
            print("[INFO] 이미 stage(git add)된 변경 사항이 존재합니다.")
            
        # 3) 커밋 대상 정보 수집
        status_text = get_git_status()
        diff_text = get_git_diff(staged_only=staged_only)
        
        # CLI에서 '--safe-mode' 옵션을 주었을 경우 데이터 마스킹 적용
        if args.safe_mode:
            diff_text = apply_safe_mode(diff_text, max_lines=args.safe_lines)
            
        # 4) AI 커밋 메시지 초안 생성 진행
        commit_message = generate_commit_message(args, diff_text, status_text, convention)
        
        # 5) 커밋 수행 승인 절차
        confirm = input("\n이 메시지로 커밋하시겠습니까? (y/n): ").strip().lower()
        if confirm == 'y' or confirm == 'yes':
            # 승인 시 git commit -m 명령어 최종 수행
            run_git_commit(commit_message)
        else:
            print("[INFO] 커밋이 취소되었습니다.")
            
    elif args.command == 'pr':
        # PR 작성 명령어 분기
        status_text = get_git_status()
        diff_text = get_git_diff()
        
        # 변경 내역이 없는 무의미한 저장소인 경우 조기 퇴장
        if not status_text and not diff_text:
            print("[INFO] 변경 사항이 없습니다. PR 메시지를 생성하지 않고 종료합니다.")
            sys.exit(0)
            
        # 안전 모드 검사 및 적용
        if args.safe_mode:
            diff_text = apply_safe_mode(diff_text, max_lines=args.safe_lines)
            
        # PR 설명문 생성 비즈니스 함수 구동
        generate_pr_draft(args, diff_text, status_text, convention)


# 이 모듈이 인터프리터에 의해 독립 실행(예: python main.py)되었을 때만
# 아래의 main() 함수 진입점을 발동시킵니다.
if __name__ == "__main__":
    main()

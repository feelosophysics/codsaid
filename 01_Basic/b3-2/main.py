"""AI 기반 Git 커밋 & PR 자동 생성기 도구의 메인 실행 모듈입니다.

사용자의 Git 변경 사항을 수집하고 AI API를 호출하여 최적의 커밋 메시지 또는 PR 초안을 생성합니다.
"""

import sys
import argparse
from dotenv import load_dotenv

from gitgen.git_helper import (
    get_git_status,
    get_git_diff,
    has_unstaged_changes,
    has_staged_changes,
    git_add_all,
    run_git_commit
)
from gitgen.safe_mode import apply_safe_mode
from gitgen.config import load_convention
from gitgen.gemini_client import call_gemini_api
from gitgen.prompt_templates import PromptTemplates


def generate_commit_message(args, diff_text, status_text, convention):
    """Git 변경 사항 및 컨벤션을 바탕으로 커밋 메시지를 생성합니다.
    
    PromptTemplates 클래스에서 기본 템플릿 프롬프트를 가져오며,
    YAML 파일에서 읽어온 규칙을 결합해 AI API를 호출합니다.
    """
    prompt = PromptTemplates.COMMIT_MESSAGE_PROMPT.format(
        status_text=status_text,
        diff_text=diff_text
    )
    
    # 컨벤션 규칙이 있고 commit 설정이 존재하는 경우 프롬프트에 결합
    if convention and 'commit' in convention:
        commit_conv = convention['commit']
        prompt += "\n[팀 컨벤션 규칙]\n"
        
        if 'prefix_rules' in commit_conv:
            prompt += "- 다음 Prefix 중 하나를 반드시 제목 앞에 사용해주세요:\n  "
            prompt += "\n  ".join(commit_conv['prefix_rules']) + "\n"
            
        if 'format_requirements' in commit_conv:
            prompt += "- 추가 포맷 요구사항:\n  "
            prompt += "\n  ".join(commit_conv['format_requirements']) + "\n"

    prompt += "\n위 규칙을 준수하여 결과물(커밋 메시지)만 출력해주세요. 다른 인사말이나 부연 설명은 하지 마세요."
    
    result = call_gemini_api(prompt, args.model, args.temperature, args.max_tokens, thinking_level=args.thinking_level)
    
    print("[DONE] 커밋 메시지 생성 완료\n")
    print("--- Commit Message ---")
    print(result)
    print("----------------------")
    return result


def generate_pr_draft(args, diff_text, status_text, convention):
    """Git 변경 사항 및 컨벤션을 바탕으로 Pull Request(PR) 초안을 작성합니다.
    
    PromptTemplates 클래스에서 기본 템플릿 프롬프트를 가져옵니다.
    """
    prompt = PromptTemplates.PR_DRAFT_PROMPT.format(
        status_text=status_text,
        diff_text=diff_text
    )
    
    # 컨벤션 규칙이 있고 PR 설정이 존재하는 경우 프롬프트에 결합
    if convention and 'pr' in convention:
        pr_conv = convention['pr']
        prompt += "\n[팀 컨벤션 규칙]\n"
        
        if 'additional_requirements' in pr_conv:
            prompt += "- 추가 요구사항:\n  "
            prompt += "\n  ".join(pr_conv['additional_requirements']) + "\n"

    prompt += "\n위 규칙을 준수하여 결과물(PR 초안)만 출력해주세요. 마크다운 형식으로 작성해주세요. 다른 인사말이나 부연 설명은 하지 마세요."
    
    result = call_gemini_api(prompt, args.model, args.temperature, args.max_tokens, thinking_level=args.thinking_level)
    
    print("[DONE] PR 초안 생성 완료\n")
    print("--- PR Draft ---")
    print(result)
    print("-----------------")


def main():
    """AI Git 커밋 및 PR 생성 도구의 진입점 함수입니다.
    
    CLI 아규먼트를 파싱하고, 명령에 따라 해당하는 커밋/PR 자동 작성 기능을 분기 실행합니다.
    """
    parser = argparse.ArgumentParser(description="AI 기반 Git 커밋 & PR 자동 생성기")
    
    subparsers = parser.add_subparsers(dest='command', help='실행할 명령어 (commit 또는 pr)')
    subparsers.add_parser('commit', help='커밋 메시지 자동 생성')
    subparsers.add_parser('pr', help='PR 제목 및 본문 자동 생성')
    
    parser.add_argument('--model', '-model', type=str, default='gemma-4-31b-it', help='사용할 AI 모델 이름 (기본값: gemma-4-31b-it)')
    parser.add_argument('--temperature', '-temperature', type=float, default=0.3, help='AI 응답의 창의성 정도 (0.0 ~ 1.0, 기본값: 0.3)')
    parser.add_argument('--max-tokens', '-max-tokens', type=int, default=2000, help='생성할 최대 토큰 수 (기본값: 2000)')
    parser.add_argument('--safe-mode', '-safe-mode', action='store_true', help='안전 모드 활성화 (민감 정보 마스킹 및 전송량 제한)')
    parser.add_argument('--safe-lines', '-safe-lines', type=int, default=200, help='안전 모드 활성화 시 전송할 최대 diff 라인 수 (기본값: 200)')
    parser.add_argument('--thinking-level', '-thinking-level', type=str, default='unspecified', choices=['high', 'unspecified'], help='Gemma 4 모델 사용 시 사고 수준 설정 (기본값: unspecified)')
     
    args = parser.parse_args()
    
    # 1. CLI 아규먼트 유효성 검사 (Early Return)
    if not args.command:
        parser.print_help()
        sys.exit(1)

    load_dotenv()
    convention = load_convention()
    
    # 2. 메인 비즈니스 로직 실행
    if args.command == 'commit':
        staged_only = False
        just_staged = False
        
        # 이미 stage된 변경 사항이 있는지 사전 감지
        already_staged = has_staged_changes()
        
        # Unstaged 변경 사항이 있을 경우 사용자에게 staging 여부를 물어봅니다.
        if has_unstaged_changes():
            user_input = input("unstaged 변경 사항이 있습니다. 모두 stage(git add .)하고 진행할까요? (y/n): ").strip().lower()
            if user_input == 'y' or user_input == 'yes':
                git_add_all()
                just_staged = True
            else:
                staged_only = True
                
        # 최종적으로 stage된 변경 사항이 없으면 종료 (Guard Clause)
        if not has_staged_changes():
            print("[INFO] 커밋할 stage된 변경 사항이 없습니다. 작업을 종료합니다.")
            sys.exit(0)
            
        # 이미 stage된 파일이 있었고, 방금 전체 stage를 새로 하지 않았다면 안내 메시지를 출력합니다.
        if already_staged and not just_staged:
            print("[INFO] 이미 stage(git add)된 변경 사항이 존재합니다.")
            
        status_text = get_git_status()
        diff_text = get_git_diff(staged_only=staged_only)
        
        # 안전 모드 처리
        if args.safe_mode:
            diff_text = apply_safe_mode(diff_text, max_lines=args.safe_lines)
            
        commit_message = generate_commit_message(args, diff_text, status_text, convention)
        
        # 커밋 최종 승인 확인
        confirm = input("\n이 메시지로 커밋하시겠습니까? (y/n): ").strip().lower()
        if confirm == 'y' or confirm == 'yes':
            run_git_commit(commit_message)
        else:
            print("[INFO] 커밋이 취소되었습니다.")
            
    elif args.command == 'pr':
        status_text = get_git_status()
        diff_text = get_git_diff()
        
        if not status_text and not diff_text:
            print("[INFO] 변경 사항이 없습니다. PR 메시지를 생성하지 않고 종료합니다.")
            sys.exit(0)
            
        if args.safe_mode:
            diff_text = apply_safe_mode(diff_text, max_lines=args.safe_lines)
            
        generate_pr_draft(args, diff_text, status_text, convention)


if __name__ == "__main__":
    main()

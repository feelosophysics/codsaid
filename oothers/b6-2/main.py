import os
import sys
import argparse
import subprocess
import json
import urllib.request
import urllib.error
import re
try:
    import yaml # pip install pyyaml 이 필요할 수 있음
except ImportError:
    yaml = None # yaml 라이브러리가 없으면 기본 설정 사용

# =====================================================================
# 설정 및 유틸리티 함수
# =====================================================================

def get_git_status():
    """
    현재 Git 저장소의 상태(변경된 파일 목록)를 가져옵니다.
    
    subprocess.run을 사용하여 운영체제의 쉘 명령어를 파이썬 안에서 실행합니다.
    'git status -s'는 짧은 형식으로 상태를 출력해줍니다.
    """
    try:
        # capture_output=True: 명령어 실행 결과를 화면에 출력하지 않고 변수에 저장
        # text=True: 결과를 바이트(bytes) 대신 문자열(string)로 반환
        result = subprocess.run(['git', 'status', '-s'], capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        print("[ERROR] Git 저장소가 아니거나 Git 명령어를 실행할 수 없습니다.")
        sys.exit(1)

def get_git_diff():
    """
    현재 Git 저장소의 변경 내용(diff)을 가져옵니다.
    """
    try:
        # unstaged 변경사항
        result = subprocess.run(['git', 'diff'], capture_output=True, text=True, check=True)
        diff_text = result.stdout.strip()
        
        # 만약 unstaged 변경사항이 없다면 staged 변경사항을 확인
        if not diff_text:
            result = subprocess.run(['git', 'diff', '--cached'], capture_output=True, text=True, check=True)
            diff_text = result.stdout.strip()
            
        return diff_text
    except subprocess.CalledProcessError:
        print("[ERROR] Git diff 명령어를 실행할 수 없습니다.")
        sys.exit(1)

def apply_safe_mode(diff_text):
    """
    안전 모드(safe-mode)가 켜져 있을 때, 민감한 정보를 마스킹하거나 길이를 제한합니다.
    """
    print("[INFO] 안전 모드(safe-mode)가 활성화되었습니다. 민감 정보를 마스킹하고 길이를 제한합니다.")
    
    # 1. 길이 제한 (최대 200줄로 제한)
    lines = diff_text.split('\n')
    if len(lines) > 200:
        lines = lines[:200]
        lines.append("\n... (안전 모드로 인해 200줄까지만 전송됩니다) ...")
        diff_text = '\n'.join(lines)
    
    # 2. 정규표현식(Regex)을 이용한 마스킹
    # 이메일 마스킹 (예: test@example.com -> ***@***.***)
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    diff_text = re.sub(email_pattern, '***@***.***', diff_text)
    
    # API Key 형태 마스킹 (예: sk-어쩌고저쩌고 20자 이상 문자열)
    # 영어 대소문자와 숫자가 섞인 20자 이상의 문자열을 마스킹 대상이라고 간주할 수 있음
    apikey_pattern = r'sk-[a-zA-Z0-9]{20,}'
    diff_text = re.sub(apikey_pattern, 'sk-***MASKED***', diff_text)
    
    # Bearer 토큰 형태 마스킹
    bearer_pattern = r'Bearer\s+[a-zA-Z0-9\-\._~+/]+=*'
    diff_text = re.sub(bearer_pattern, 'Bearer ***MASKED***', diff_text)

    return diff_text

def load_convention():
    """
    프로젝트 루트 디렉토리의 .ai-gitgen.yml 파일을 읽어 팀 컨벤션을 불러옵니다.
    """
    config_file = '.ai-gitgen.yml'
    if os.path.exists(config_file):
        if yaml is None:
            print("[WARN] .ai-gitgen.yml 파일이 존재하지만 pyyaml 라이브러리가 설치되어 있지 않습니다. 기본값을 사용합니다.")
            print("       설치 방법: pip install pyyaml")
            return None
            
        with open(config_file, 'r', encoding='utf-8') as f:
            try:
                config = yaml.safe_load(f)
                print("[INFO] .ai-gitgen.yml 컨벤션 파일을 성공적으로 불러왔습니다.")
                return config
            except yaml.YAMLError as exc:
                print(f"[ERROR] 컨벤션 파일 파싱 오류: {exc}")
                return None
    return None

# =====================================================================
# AI API 통신 함수
# =====================================================================

def call_gemini_api(prompt, model, temperature, max_tokens):
    """
    Google Gemini REST API를 호출하여 프롬프트에 대한 응답을 받습니다.
    """
    api_key = os.environ.get("AI_API_KEY")
    if not api_key:
        print("[ERROR] AI_API_KEY 환경변수가 설정되지 않았습니다.")
        print("## 예) export AI_API_KEY=\"여러분의_API_KEY\"")
        sys.exit(1)
        
    print("[INFO] AI API 요청 중...")
    
    # Gemini API 엔드포인트 URL (REST API)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    
    # 요청 본문 (Payload) 구성
    # Gemini API가 요구하는 형식에 맞게 딕셔너리를 만듭니다.
    data = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens
        }
    }
    
    # 딕셔너리를 JSON 문자열로 변환한 후 바이트(bytes)로 인코딩합니다.
    json_data = json.dumps(data).encode('utf-8')
    
    # HTTP 요청 헤더 설정
    headers = {
        'Content-Type': 'application/json'
    }
    
    # 요청(Request) 객체 생성
    req = urllib.request.Request(url, data=json_data, headers=headers, method='POST')
    
    try:
        # API 호출 및 응답(Response) 받기
        with urllib.request.urlopen(req) as response:
            response_body = response.read().decode('utf-8')
            response_json = json.loads(response_body)
            
            # Gemini 응답 JSON에서 텍스트 추출
            # 응답 구조: candidates[0] -> content -> parts[0] -> text
            if 'candidates' in response_json and len(response_json['candidates']) > 0:
                return response_json['candidates'][0]['content']['parts'][0]['text']
            else:
                print("[ERROR] 예상치 못한 API 응답 구조입니다.")
                return "API 호출 실패 (응답 텍스트 없음)"
                
    except urllib.error.HTTPError as e:
        print(f"[ERROR] API HTTP 오류 발생: {e.code} {e.reason}")
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"[ERROR] API 네트워크 오류 발생: {e.reason}")
        sys.exit(1)

# =====================================================================
# 메인 로직 (커밋 및 PR 생성)
# =====================================================================

def generate_commit_message(args, diff_text, status_text, convention):
    """
    커밋 메시지 자동 생성 로직
    """
    # 프롬프트(AI에게 지시할 내용) 구성
    prompt = f"""
다음은 Git 변경 사항입니다. 이를 바탕으로 커밋 메시지를 작성해주세요.

[Git Status]
{status_text}

[Git Diff]
{diff_text}

[요구사항]
1. 커밋 메시지는 한국어로 작성해주세요.
2. 커밋 제목 1줄은 필수로 포함해주세요. 제목은 50자 이내로 작성해주세요.
3. 커밋 본문에는 변경된 파일이나 모듈을 1~3개 언급해주세요.
4. 커밋 본문에 핵심 변경 사항 1~2개를 불릿 포인트(-)로 요약해주세요.
"""

    # .ai-gitgen.yml 컨벤션이 있을 경우 프롬프트에 추가
    if convention and 'commit' in convention:
        prompt += "\n[팀 컨벤션 규칙]\n"
        if 'prefix_rules' in convention['commit']:
            prompt += "- 다음 Prefix 중 하나를 반드시 제목 앞에 사용해주세요:\n  "
            prompt += "\n  ".join(convention['commit']['prefix_rules']) + "\n"
        if 'format_requirements' in convention['commit']:
            prompt += "- 추가 포맷 요구사항:\n  "
            prompt += "\n  ".join(convention['commit']['format_requirements']) + "\n"

    prompt += "\n위 규칙을 준수하여 결과물(커밋 메시지)만 출력해주세요. 다른 인사말이나 부연 설명은 하지 마세요."

    # API 호출
    result = call_gemini_api(prompt, args.model, args.temperature, args.max_tokens)
    
    print("[DONE] 커밋 메시지 생성 완료\n")
    print("--- Commit Message ---")
    print(result)
    print("----------------------")


def generate_pr_draft(args, diff_text, status_text, convention):
    """
    Pull Request 제목 및 본문 자동 생성 로직
    """
    # 프롬프트 구성
    prompt = f"""
다음은 Git 변경 사항입니다. 이를 바탕으로 Pull Request(PR) 초안을 작성해주세요.

[Git Status]
{status_text}

[Git Diff]
{diff_text}

[요구사항]
1. PR 초안은 한국어로 작성해주세요.
2. PR 제목 1줄을 먼저 적어주세요. 제목은 80자 이내로 작성해주세요.
3. 본문은 다음 섹션 헤더를 반드시 포함해야 합니다:
   ## Why (변경 배경)
   ## What (핵심 변경 사항)
   ## How to Test (테스트 방법)
4. 각 섹션에는 최소 1개 이상의 불릿 포인트(-)가 포함되어야 합니다.
"""

    # .ai-gitgen.yml 컨벤션이 있을 경우 프롬프트에 추가
    if convention and 'pr' in convention:
        prompt += "\n[팀 컨벤션 규칙]\n"
        if 'additional_requirements' in convention['pr']:
            prompt += "- 추가 요구사항:\n  "
            prompt += "\n  ".join(convention['pr']['additional_requirements']) + "\n"

    prompt += "\n위 규칙을 준수하여 결과물(PR 초안)만 출력해주세요. 마크다운 형식으로 작성해주세요. 다른 인사말이나 부연 설명은 하지 마세요."

    # API 호출
    result = call_gemini_api(prompt, args.model, args.temperature, args.max_tokens)
    
    print("[DONE] PR 초안 생성 완료\n")
    print("--- PR Draft ---")
    print(result)
    print("-----------------")


# =====================================================================
# 진입점 (프로그램 실행 시작점)
# =====================================================================

def main():
    # argparse를 사용하여 터미널에서 입력받을 명령어와 옵션을 정의합니다.
    parser = argparse.ArgumentParser(description="AI 기반 Git 커밋 & PR 자동 생성기")
    
    # 서브 명령어 추가 ('commit', 'pr')
    subparsers = parser.add_subparsers(dest='command', help='실행할 명령어 (commit 또는 pr)')
    
    # commit 명령어 생성
    commit_parser = subparsers.add_parser('commit', help='커밋 메시지 자동 생성')
    
    # pr 명령어 생성
    pr_parser = subparsers.add_parser('pr', help='PR 제목 및 본문 자동 생성')
    
    # 공통 옵션 추가 (API 파라미터 등)
    # 어느 명령어를 치든 뒤에 붙일 수 있는 옵션들입니다.
    parser.add_argument('--model', type=str, default='gemini-1.5-flash', help='사용할 AI 모델 이름 (기본값: gemini-1.5-flash)')
    parser.add_argument('--temperature', type=float, default=0.7, help='AI 응답의 창의성 정도 (0.0 ~ 1.0, 기본값: 0.7)')
    parser.add_argument('--max-tokens', type=int, default=500, help='생성할 최대 토큰 수 (기본값: 500)')
    parser.add_argument('--safe-mode', action='store_true', help='안전 모드 활성화 (민감 정보 마스킹 및 전송량 제한)')
    
    # 사용자가 터미널에 입력한 값을 파싱(해석)합니다.
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)

    # 1. Git 변경 사항 수집
    status_text = get_git_status()
    diff_text = get_git_diff()
    
    if not status_text and not diff_text:
        print("[INFO] 변경 사항이 없습니다. 커밋/PR 메시지를 생성하지 않고 종료합니다.")
        sys.exit(0)
        
    print(f"[INFO] Git status 수집 완료: 변경 감지")
    print(f"[INFO] Git diff 수집 완료: {len(diff_text.splitlines())}줄")
    
    # 2. 안전 모드(safe-mode) 적용 (Bonus 5.3)
    if args.safe_mode:
        diff_text = apply_safe_mode(diff_text)
        
    # 3. 팀 컨벤션 로드 (Bonus 5.2)
    convention = load_convention()
    
    # 4. 명령어 분기 처리
    if args.command == 'commit':
        generate_commit_message(args, diff_text, status_text, convention)
    elif args.command == 'pr':
        generate_pr_draft(args, diff_text, status_text, convention)

# 이 파이썬 파일이 직접 실행될 때만 main() 함수를 호출하라는 뜻입니다.
if __name__ == "__main__":
    main()

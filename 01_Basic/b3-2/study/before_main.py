import os  # 운영체제(OS)와 상호작용하기 위한 라이브러리 (예: 환경 변수 조회, 파일 경로 확인 등)
import sys  # 파이썬 인터프리터와 상호작용하기 위한 라이브러리 (예: 프로그램 강제 종료 sys.exit() 등)
import argparse  # 터미널에서 입력받는 명령어 및 옵션(인자)을 쉽게 다루기 위한 라이브러리
import subprocess  # 파이썬 안에서 외부 시스템 명령어(예: git status, git diff)를 실행하기 위한 라이브러리
import json  # JSON 형식의 데이터를 문자열과 파이썬 객체(딕셔너리, 리스트) 간에 상호 변환하기 위한 라이브러리
import urllib.request  # 파이썬 내장 라이브러리로, 외부 서버와 HTTP 통신(웹 요청)을 하기 위한 도구
import urllib.error  # HTTP 통신 도중 발생하는 예외(에러)들을 처리하기 위한 라이브러리
import re  # 정규표현식(Regular Expression)을 사용하여 문자열의 특정 패턴을 검색, 매치, 치환하기 위한 라이브러리

# ---------------------------------------------------------------------
# [.env 파일 로드 로직]
# 외부 라이브러리(python-dotenv)가 설치되어 있지 않더라도, 
# 직접 .env 파일을 읽어서 파이썬의 환경 변수(os.environ)에 직접 주입해 주는 안전장치 코드입니다.
# ---------------------------------------------------------------------
try:
    from dotenv import load_dotenv  # python-dotenv 라이브러리에서 load_dotenv 함수를 가져옵니다.
    load_dotenv()  # 프로젝트 루트의 .env 파일을 자동으로 읽어서 시스템 환경 변수로 등록합니다.
except ImportError:
    # 만약 컴퓨터에 python-dotenv 라이브러리가 설치되어 있지 않아 에러가 나면 이 블록이 실행됩니다.
    # 라이브러리가 없어도 프로그램을 작동시키기 위해, .env 파일을 직접 한 줄씩 파싱하는 대안 코드를 실행합니다.
    if os.path.exists('.env'):  # 현재 폴더에 '.env' 파일이 실제로 존재하는지 확인합니다.
        with open('.env', 'r', encoding='utf-8') as f:  # .env 파일을 읽기 모드('r')로 안전하게 엽니다.
            for line in f:
                line = line.strip()  # 줄 바꿈 문자(\n)나 좌우 공백을 제거합니다.
                
                # 빈 줄이거나 샵(#)으로 시작하는 주석 줄은 그냥 건너뜁니다.
                if not line or line.startswith('#'):
                    continue
                
                # 등호(=) 기호가 포함되어 있다면 '변수명=값' 형태의 환경 변수 설정 줄로 인식합니다.
                if '=' in line:
                    # 등호를 기준으로 딱 1번만 쪼갭니다 (예: AI_API_KEY=key_value)
                    key, val = line.split('=', 1)
                    key = key.strip()  # 변수명 좌우의 불필요한 공백을 지웁니다.
                    val = val.strip().strip("'").strip('"')  # 값 좌우의 공백과 따옴표('', "")를 제거합니다.
                    os.environ[key] = val  # 파이썬 환경 변수 사전(os.environ)에 해당 값을 저장합니다.

# ---------------------------------------------------------------------
# [YAML 설정 파일 로드 준비]
# 팀 컨벤션 규칙이 담긴 .ai-gitgen.yml 파일을 파싱하기 위해 pyyaml 라이브러리를 임포트합니다.
# ---------------------------------------------------------------------
try:
    import yaml  # YAML 형식의 설정 파일을 쉽게 다루기 위한 pyyaml 라이브러리 임포트
except ImportError:
    # pyyaml 라이브러리가 설치되어 있지 않다면 yaml 변수를 None으로 설정하여 예외를 방지합니다.
    yaml = None  # 라이브러리가 없음을 표시해 두고, 나중에 처리 시 기본 규칙만 사용하게 유도합니다.


# =====================================================================
# 설정 및 유틸리티 함수
# =====================================================================

def get_git_status():
    """
    현재 Git 저장소의 상태(변경된 파일 목록)를 수집하여 문자열로 반환하는 함수입니다.
    
    파이썬의 subprocess를 이용하여 운영체제의 쉘 명령어를 실행합니다.
    'git status -s'에서 '-s'는 'short'의 약자로, 변경 사항을 한 줄씩 축약해서 보여줍니다.
    예) M main.py, ?? .env.example
    """
    try:
        # subprocess.run을 호출하여 실제로 'git status -s'라는 명령어를 실행합니다.
        # capture_output=True: 명령어 실행 결과(stdout/stderr)가 터미널 화면에 찍히지 않고 파이썬 내부 변수에 저장되도록 합니다.
        # text=True: 명령어 반환값(바이트 배열)을 파이썬이 다루기 쉬운 문자열(string) 형태로 자동 변환해 줍니다.
        # check=True: 만약 명령어 실행이 실패하면(예: Git 폴더가 아닌 곳에서 실행 시) CalledProcessError 예외를 강제로 발생시킵니다.
        result = subprocess.run(['git', 'status', '-s'], capture_output=True, text=True, check=True)
        return result.stdout.strip()  # 실행 결과를 앞뒤 공백을 깎아서 반환합니다.
    except subprocess.CalledProcessError:
        # Git 명령어가 실패한 경우 예외 처리를 통해 에러 메시지를 띄우고 시스템을 종료시킵니다.
        print("[ERROR] Git 저장소가 아니거나 Git 명령어를 실행할 수 없습니다.")
        sys.exit(1)  # 1번 종료 코드는 프로그램에 이상이 있어 비정상 종료됨을 OS에 알리는 신호입니다.

def get_git_diff():
    """
    현재 Git 저장소에 있는 변경 내용(코드의 구체적인 추가/삭제 행 정보)을 수집하여 반환하는 함수입니다.
    """
    try:
        # 1단계: 아직 git add하지 않은 임시 변경 사항(unstaged)을 조회합니다.
        result = subprocess.run(['git', 'diff'], capture_output=True, text=True, check=True)
        diff_text = result.stdout.strip()
        
        # 2단계: 만약 아직 add하지 않은 변경 사항이 하나도 없다면, 이미 git add를 마친 상태(staged)의 변경 사항이 있는지 확인합니다.
        if not diff_text:
            # '--cached' 옵션은 이미 스테이징 영역에 올라간(git add 완료된) 변경 내역을 보겠다는 뜻입니다.
            result = subprocess.run(['git', 'diff', '--cached'], capture_output=True, text=True, check=True)
            diff_text = result.stdout.strip()
            
        return diff_text  # 최종적으로 수집된 코드 차이점(diff) 문자열을 반환합니다.
    except subprocess.CalledProcessError:
        # Git diff 명령어 실패 시 프로그램을 강제 종료합니다.
        print("[ERROR] Git diff 명령어를 실행할 수 없습니다.")
        sys.exit(1)

def apply_safe_mode(diff_text, max_lines=200):
    """
    안전 모드(safe-mode)가 활성화되어 있을 때 호출됩니다.
    
    1. 코드 차이점(diff)이 너무 길어 토큰 요금이 과도하게 청구되는 것을 막기 위해 줄 수를 제한합니다.
    2. 소스코드에 하드코딩되어 유출될 위험이 있는 민감 정보(이메일, API 키, 토큰, IP 주소, 비밀번호 등)를
       정규표현식(Regex)을 이용해 '***MASKED***' 형태로 안전하게 변환(마스킹)합니다.
    """
    print(f"[INFO] 안전 모드(safe-mode)가 활성화되었습니다. 민감 정보를 마스킹하고 길이를 {max_lines}줄로 제한합니다.")
    
    # -------------------------------------------------------------
    # [1단계: 전송 텍스트 줄 수 제한]
    # -------------------------------------------------------------
    lines = diff_text.split('\n')  # 개행 문자(\n)를 기준으로 전체 텍스트를 줄 단위 리스트로 쪼갭니다.
    if len(lines) > max_lines:  # 실제 줄 수가 우리가 지정한 최대 허용치(예: 200줄)보다 많은 경우
        lines = lines[:max_lines]  # 앞에서부터 허용하는 줄 수까지만 슬라이싱합니다.
        # 잘린 부분 뒤에 잘렸다는 경고 문구를 덧붙여서 AI도 인지할 수 있게 합니다.
        lines.append(f"\n... (안전 모드로 인해 {max_lines}줄까지만 전송됩니다) ...")
        diff_text = '\n'.join(lines)  # 다시 줄 바꿈 문자로 합쳐 하나의 문자열로 되돌립니다.
    
    # -------------------------------------------------------------
    # [2단계: 정규표현식(Regex)을 이용한 민감 정보 마스킹]
    # -------------------------------------------------------------
    
    # 1) 이메일 마스킹 (예: user@example.com -> ***@***.***)
    # 영문/숫자/특수기호 @ 영문/숫자/대시 . 2글자 이상 영어 구조를 찾아 매칭시킵니다.
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    diff_text = re.sub(email_pattern, '***@***.***', diff_text)
    
    # 2) API Key 형태 마스킹 (예: sk-로 시작하는 20자 이상의 영숫자 토큰)
    # sk- 뒤에 대소문자 및 숫자가 최소 20자 이상 연속되는 패턴을 매칭시킵니다.
    apikey_pattern = r'sk-[a-zA-Z0-9]{20,}'
    diff_text = re.sub(apikey_pattern, 'sk-***MASKED***', diff_text)
    
    # 3) Bearer 토큰 형태 마스킹 (HTTP 인증 헤더 등에서 자주 사용됨)
    # Bearer 뒤에 공백이 있고 토큰용 허용 특수문자나 영문숫자가 연속되는 패턴을 매칭시킵니다.
    bearer_pattern = r'Bearer\s+[a-zA-Z0-9\-\._~+/]+=*'
    diff_text = re.sub(bearer_pattern, 'Bearer ***MASKED***', diff_text)

    # 4) IPv4 주소 마스킹 (예: 192.168.1.100 -> ***.***.***.***)
    # 1~3자리 숫자 4개가 마침표(.)로 구분되어 연속되는 패턴을 매칭시킵니다.
    ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
    diff_text = re.sub(ip_pattern, '***.***.***.***', diff_text)

    # 5) 비밀번호/비밀키 형태 마스킹 (예: password="...", client_secret="...")
    # 대소문자 구분 없이( (?i) ) password, secret, passwd, private_key 라는 단어 뒤에 
    # 콜론(:) 또는 등호(=)가 나오고 따옴표(' 또는 ")로 감싸진 값 부분을 매칭시킵니다.
    secret_pattern = r'(?i)(password|secret|passwd|private_key)\s*[:=]\s*["\']([^"\']+)["\']'
    
    def mask_secret(match):
        """
        정규표현식에 매칭된 비밀번호 정보 중 일부만 남기고 마스킹하기 위한 보조 함수입니다.
        예) "password123" -> "pa*********" (앞의 두 글자만 남기고 글자 길이만큼 * 처리)
        """
        key = match.group(1)  # 변수명 부분 (예: password)
        val = match.group(2)  # 실제 값 부분 (예: password123)
        # 값이 너무 짧으면 그냥 다 별표로 바꾸고, 4자 이상이면 앞 2글자만 남기고 별표로 채웁니다.
        masked_val = val[:2] + '*' * (len(val) - 2) if len(val) > 4 else '****'
        # 원래 등호(=) 또는 콜론(:) 기호 중 사용된 구분자를 파악합니다.
        delimiter = ':' if ':' in match.group(0) else '='
        return f'{key}{delimiter}"{masked_val}"'
    
    # re.sub에 함수(mask_secret)를 매개변수로 전달하면, 매칭된 부분들이 해당 함수의 반환값으로 치환됩니다.
    diff_text = re.sub(secret_pattern, mask_secret, diff_text)

    return diff_text  # 안전하게 세탁된 최종 변경 내역 문자열을 반환합니다.

def load_convention():
    """
    프로젝트 루트 디렉토리에 있는 .ai-gitgen.yml 파일을 읽어와서
    팀원들이 합의한 커밋 접두어(Prefix)나 PR 템플릿 규칙을 파이썬 딕셔너리로 반환합니다.
    """
    config_file = '.ai-gitgen.yml'  # 설정 파일명 정의
    if os.path.exists(config_file):  # 설정 파일이 프로젝트 폴더에 존재하는지 확인
        if yaml is None:
            # 설정 파일은 있는데 파이썬에 pyyaml 라이브러리가 설치되어 있지 않은 상황을 경고합니다.
            print("[WARN] .ai-gitgen.yml 파일이 존재하지만 pyyaml 라이브러리가 설치되어 있지 않습니다. 기본값을 사용합니다.")
            print("       설치 방법: pip install pyyaml")
            return None
            
        with open(config_file, 'r', encoding='utf-8') as f:
            try:
                # yaml.safe_load는 외부 사용자가 입력한 나쁜 코드가 실행되지 않게 안전하게 YAML 파일만 해석해 줍니다.
                config = yaml.safe_load(f)
                print("[INFO] .ai-gitgen.yml 컨벤션 파일을 성공적으로 불러왔습니다.")
                return config  # 파싱된 딕셔너리 구조를 반환합니다.
            except yaml.YAMLError as exc:
                # YAML 파일 형식 자체에 오타나 구조적 에러가 있을 때 발생합니다.
                print(f"[ERROR] 컨벤션 파일 파싱 오류: {exc}")
                return None
    return None  # 설정 파일이 아예 없다면 None을 돌려주어 기본 모드로 작동시킵니다.

# =====================================================================
# AI API 통신 함수
# =====================================================================

def call_gemini_api(prompt, model, temperature, max_tokens, thinking_level='unspecified'):
    """
    Google Gemini/Gemma REST API서버에 HTTP POST 방식으로 요청을 보내고,
    AI 모델이 답변으로 생성한 최종 요약 텍스트를 돌려받는 핵심 통신 함수입니다.
    """
    # 1. 환경 변수에서 구글 API 키를 가져옵니다.
    api_key = os.environ.get("AI_API_KEY")
    if not api_key:
        print("[ERROR] AI_API_KEY 환경변수가 설정되지 않았습니다.")
        print("## 예) export AI_API_KEY=\"여러분의_API_KEY\"")
        sys.exit(1)
        
    # 2. API 키의 유효성을 1차로 검증합니다 (혹시 한글 등이 복사-붙여넣기 과정에서 섞였는지 검사)
    # 영숫자(isalnum)와 대시(-), 언더바(_) 기호 외에 다른 불필요한 문자가 있는지 확인합니다.
    if not api_key.isalnum() and not all(c in api_key for c in '-_'):
        # 아스키 범위를 넘어선 한글 등의 특수 문자가 들어간 경우 100% 오류가 발생하므로 사전에 차단합니다.
        if any(ord(c) > 127 for c in api_key):
            print("[ERROR] API Key에 유효하지 않은 문자(한글 또는 특수 기호)가 포함되어 있습니다.")
            print("        Google AI Studio에서 발급받은 영문/숫자 형태의 키만 입력해 주세요.")
            sys.exit(1)

    print("[INFO] AI API 요청 중...")
    
    # v1beta 버전을 사용합니다. 최신 Gemma 4나 Gemini 2.5 모델과 호환성이 높은 버전입니다.
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    
    # 3. 요청 본문(JSON) 데이터 구성을 시작합니다.
    # API가 받아들이는 생성 설정(generationConfig) 딕셔너리를 빌드합니다.
    generation_config = {
        "temperature": temperature,      # 창의성 수치 (낮을수록 일관되고 결정론적임)
        "maxOutputTokens": max_tokens     # 응답 제한 토큰 수
    }
    
    # [모델별 추론(Thinking) 파라미터 분기 처리]
    # 모델명에 "gemini"가 들어간 모델(예: gemini-2.5-flash)은 
    # 기본적으로 생성되는 생각 과정을 끄기 위해 "thinkingBudget": 0 설정을 전송해야 400 에러를 피할 수 있습니다.
    if "gemini" in model.lower():
        generation_config["thinkingConfig"] = {
            "thinkingBudget": 0  # 생각 과정 토큰 낭비를 막기 위해 비활성화
        }
    # 모델명에 "gemma"가 들어간 모델(예: gemma-4-31b-it)은 'thinkingBudget'을 쓰면 400 에러를 냅니다.
    # 대신 생각 수준을 조절하는 'thinkingLevel' 필드를 사용해 'high' 혹은 기본값을 선택할 수 있습니다.
    elif "gemma" in model.lower() and thinking_level == "high":
        generation_config["thinkingConfig"] = {
            "thinkingLevel": "high"  # Gemma 4 모델의 심층 사고 모드 활성화
        }

    # API가 공식 요구하는 전체 JSON 규격에 맞춥니다.
    data = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": generation_config
    }
    
    # 딕셔너리를 문자열(JSON)로 변환(dumps)하고, 네트워크 전송이 가능하게 utf-8 바이트코드로 인코딩합니다.
    json_data = json.dumps(data).encode('utf-8')
    
    # 4. HTTP 헤더 정보를 사전(dict)으로 지정합니다.
    # 구글 API는 'x-goog-api-key'라는 고유 헤더에 진짜 API Key값을 담아 보내야 인증에 통과시켜 줍니다.
    headers = {
        'Content-Type': 'application/json',
        'x-goog-api-key': api_key
    }
    
    # urllib.request.Request 객체를 생성합니다. (전송할 주소, 데이터, 헤더 정보, 전송 방식 POST 기재)
    req = urllib.request.Request(url, data=json_data, headers=headers, method='POST')
    
    try:
        # 실제로 인터넷망을 타고 구글 서버와 연결하여 응답을 받아옵니다 (urlopen)
        with urllib.request.urlopen(req) as response:
            # 받아온 웹 페이지 바이트 결과물을 문자열(utf-8)로 해독(decode)합니다.
            response_body = response.read().decode('utf-8')
            # 문자열을 파이썬 딕셔너리로 파싱(loads)합니다.
            response_json = json.loads(response_body)
            
            # [응답 JSON에서 생각 파트 발라내기]
            if 'candidates' in response_json and len(response_json['candidates']) > 0:
                # API가 반환한 파트 리스트를 조회합니다.
                parts = response_json['candidates'][0]['content']['parts']
                
                # 'thought'라는 속성(Key)이 참(True)인 파트는 AI의 내부 생각 과정이므로 제외하고,
                # 순수한 대답 글(text)만 수집합니다.
                actual_parts = [p['text'] for p in parts if not p.get('thought')]
                
                if actual_parts:
                    return "".join(actual_parts)  # 쪼개진 순수 텍스트 파트들을 하나로 병합하여 반환합니다.
                
                # 만약 생각(thought) 과정이 너무 길어서 max_tokens 한도에 도달해 최종 답변을 생성하지 못했다면,
                # 최소한의 결과라도 제공하기 위해 생각 로그의 첫 번째 파트라도 임시 반환합니다.
                return parts[0]['text']
            else:
                print("[ERROR] 예상치 못한 API 응답 구조입니다.")
                return "API 호출 실패 (응답 텍스트 없음)"
                
    except urllib.error.HTTPError as e:
        # 구글 서버가 200 성공 코드가 아닌 에러 코드를 내려준 경우 예외 처리를 실행합니다.
        if e.code == 404:
            print(f"[ERROR] API 호출 경로를 찾을 수 없습니다 (404 Not Found).")
            print(f"        원인 1: 요청하신 모델('{model}')이 단종(Deprecated)되었거나 현재 계정에서 접근할 수 없습니다.")
            print("        원인 2: API Key가 유효하지 않거나 Google Cloud 프로젝트에 연결되지 않았습니다.")
            print("        해결책: '--model gemini-2.5-flash' 옵션을 추가하여 최신 무료 모델로 다시 시도해 보세요.")
        elif e.code == 429:
            print(f"[ERROR] API 호출 제한 초과 (429 Too Many Requests).")
            print("        원인 1: 무료 요금제의 분당 호출 제한(15 RPM) 또는 일일 제한(1500 RPD)을 초과했습니다.")
            print("        원인 2: Google AI Studio 계정/프로젝트의 할당량(Quota) 설정이 0이거나 제한되어 있습니다.")
            print("        해결책 1: 잠시(1~2분) 후 다시 시도해 보세요.")
            print("        해결책 2: Google AI Studio(https://aistudio.google.com/)의 Dashboard 혹은 Google Cloud Console에서 할당량 제한을 확인해 주세요.")
        elif e.code == 500:
            print(f"[ERROR] API 서버 내부 오류 발생 (500 Internal Server Error).")
            print("        원인: Google AI Studio 서버 측에 일시적인 시스템 장애가 발생했습니다.")
            print("        해결책: 1~2분 대기 후 다시 시도해 보시고, 지속될 경우 API 요청 페이로드 크기를 줄여보세요.")
        elif e.code == 503:
            print(f"[ERROR] API 서버 일시 이용 불가 (503 Service Unavailable).")
            print("        원인: 구글 서버 점검 중이거나 트래픽 과부하 상태입니다.")
            print("        해결책: 잠시 후 다시 실행해 주시기 바랍니다.")
        else:
            # 기타 400 Bad Request, 403 Forbidden 등 다뤄지지 않은 에러 코드에 대응합니다.
            print(f"[ERROR] API HTTP 오류 발생: {e.code} {e.reason}")
        sys.exit(1)  # 에러 발생 시 프로그램을 즉시 종료합니다.
    except urllib.error.URLError as e:
        # 무선 인터넷이 끊겼거나 DNS 조회가 안 되는 등 로컬 네트워크 망에 문제가 생긴 경우입니다.
        print(f"[ERROR] API 네트워크 오류 발생: {e.reason}")
        sys.exit(1)
    except UnicodeEncodeError:
        # API 키 문자열 인코딩 중 알 수 없는 유니코드 에러 발생 시 처리입니다.
        print("[ERROR] API Key 인코딩 중 오류가 발생했습니다. 키 값에 한글이나 잘못된 문자가 포함되어 있는지 확인해 주세요.")
        sys.exit(1)
    except Exception as e:
        # 예기치 못한 기타 모든 예외 상황을 안전하게 캡처하여 출력합니다.
        print(f"[ERROR] 알 수 없는 오류 발생: {e}")
        sys.exit(1)

# =====================================================================
# 메인 로직 (커밋 및 PR 생성)
# =====================================================================

def generate_commit_message(args, diff_text, status_text, convention):
    """
    Git 변경 사항을 바탕으로 규격에 맞는 커밋 메시지를 생성하도록 지시하는 프롬프트를 구성하고,
    AI API를 호출하여 결과를 콘솔에 출력해 주는 함수입니다.
    """
    # AI에게 가이드라인과 템플릿 양식을 확실히 전달하기 위해 프롬프트를 빌드합니다.
    prompt = f"""
다음은 Git 변경 사항입니다. 이를 바탕으로 규격에 맞는 커밋 메시지를 작성해주세요.

[Git Status]
{status_text}

[Git Diff]
{diff_text}

[요구사항]
1. 커밋 메시지는 한국어로 작성해주세요.
2. 커밋 제목 1줄은 필수로 포함해주세요. 제목은 50자 이내로 작성해주세요.
3. 커밋 본문에는 실제로 변경된 파일이나 모듈 명칭을 반드시 1~3개 명시해야 합니다.
4. 커밋 본문에는 이번 커밋의 핵심 변경 사항 1~2개를 반드시 불릿 포인트(-)로 구체적으로 작성해야 합니다. 절대 내용이 비어있는 빈 불릿('-')을 생성하지 마십시오.

[권장 출력 형식]
[커밋 제목] (예: feat: OO 기능 추가)

- 변경 파일: [실제 변경된 파일명 언급]
- 핵심 변경 사항: [무엇을 왜 변경했는지 1~2개 요약]
"""

    # .ai-gitgen.yml 설정 파일에서 로드된 커밋 관련 컨벤션 정보가 있다면 이를 프롬프트에 결합합니다.
    if convention and 'commit' in convention:
        prompt += "\n[팀 컨벤션 규칙]\n"
        if 'prefix_rules' in convention['commit']:
            prompt += "- 다음 Prefix 중 하나를 반드시 제목 앞에 사용해주세요:\n  "
            # 리스트로 명시된 접두사 규칙들을 개행 문자로 조인하여 보기 좋게 덧붙입니다.
            prompt += "\n  ".join(convention['commit']['prefix_rules']) + "\n"
        if 'format_requirements' in convention['commit']:
            prompt += "- 추가 포맷 요구사항:\n  "
            prompt += "\n  ".join(convention['commit']['format_requirements']) + "\n"

    # AI가 엉뚱한 인사말("여기 커밋 메시지입니다!")을 출력하는 것을 사전에 방지하기 위한 제약 조건입니다.
    prompt += "\n위 규칙을 준수하여 결과물(커밋 메시지)만 출력해주세요. 다른 인사말이나 부연 설명은 하지 마세요."

    # 동적으로 완성된 프롬프트를 call_gemini_api 함수로 전송하여 결과를 받아옵니다.
    result = call_gemini_api(prompt, args.model, args.temperature, args.max_tokens, thinking_level=args.thinking_level)
    
    # 최종 결과를 터미널 화면에 예쁘게 포장하여 출력합니다.
    print("[DONE] 커밋 메시지 생성 완료\n")
    print("--- Commit Message ---")
    print(result)
    print("----------------------")


def generate_pr_draft(args, diff_text, status_text, convention):
    """
    Git 변경 사항을 바탕으로 Pull Request(PR) 초안을 작성하도록 지시하는 프롬프트를 구성하고,
    AI API를 호출하여 결과를 콘솔에 출력해 주는 함수입니다.
    """
    # PR 초안 템플릿(Why, What, How to Test 구조)을 만족하도록 프롬프트를 구성합니다.
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

    # .ai-gitgen.yml 컨벤션에 지정된 PR용 커스텀 요구사항이 있다면 프롬프트 하단에 합쳐 줍니다.
    if convention and 'pr' in convention:
        prompt += "\n[팀 컨벤션 규칙]\n"
        if 'additional_requirements' in convention['pr']:
            prompt += "- 추가 요구사항:\n  "
            prompt += "\n  ".join(convention['pr']['additional_requirements']) + "\n"

    # AI가 부연 설명이나 사족을 달지 않고 온전히 마크다운 PR 포맷 결과만 출력하게 제약합니다.
    prompt += "\n위 규칙을 준수하여 결과물(PR 초안)만 출력해주세요. 마크다운 형식으로 작성해주세요. 다른 인사말이나 부연 설명은 하지 마세요."

    # API 호출을 시도합니다.
    result = call_gemini_api(prompt, args.model, args.temperature, args.max_tokens, thinking_level=args.thinking_level)
    
    # 결과를 출력합니다.
    print("[DONE] PR 초안 생성 완료\n")
    print("--- PR Draft ---")
    print(result)
    print("-----------------")


# =====================================================================
# 진입점 (프로그램 실행 시작점)
# =====================================================================

def main():
    # 1. argparse 객체를 만들고 도구 설명(description)을 작성합니다.
    parser = argparse.ArgumentParser(description="AI 기반 Git 커밋 & PR 자동 생성기")
    
    # 2. 서브 명령어 그룹을 생성합니다. 사용자는 터미널에 'commit' 또는 'pr' 중 하나를 필수로 타이핑해야 합니다.
    subparsers = parser.add_subparsers(dest='command', help='실행할 명령어 (commit 또는 pr)')
    
    # 사용자가 'commit'을 쳤을 때 동작할 세부 파서 등록
    # (추후 commit 전용 옵션이 필요하면 'commit_parser = ...' 형태로 받아옵니다.)
    subparsers.add_parser('commit', help='커밋 메시지 자동 생성')
    
    # 사용자가 'pr'을 쳤을 때 동작할 세부 파서 등록
    # (추후 pr 전용 옵션이 필요하면 'pr_parser = ...' 형태로 받아옵니다.)
    subparsers.add_parser('pr', help='PR 제목 및 본문 자동 생성')
    
    # 3. 공통 CLI 옵션들을 추가합니다.
    # '--옵션명'과 '-옵션명' 형태를 모두 지원하여 사용자 편의성을 높였습니다.
    parser.add_argument('--model', '-model', type=str, default='gemma-4-31b-it', help='사용할 AI 모델 이름 (기본값: gemma-4-31b-it)')
    parser.add_argument('--temperature', '-temperature', type=float, default=0.7, help='AI 응답의 창의성 정도 (0.0 ~ 1.0, 기본값: 0.7)')
    parser.add_argument('--max-tokens', '-max-tokens', type=int, default=2000, help='생성할 최대 토큰 수 (기본값: 2000)')
    parser.add_argument('--safe-mode', '-safe-mode', action='store_true', help='안전 모드 활성화 (민감 정보 마스킹 및 전송량 제한)')
    parser.add_argument('--safe-lines', '-safe-lines', type=int, default=200, help='안전 모드 활성화 시 전송할 최대 diff 라인 수 (기본값: 200)')
    parser.add_argument('--thinking-level', '-thinking-level', type=str, default='unspecified', choices=['high', 'unspecified'], help='Gemma 4 모델 사용 시 사고 수준 설정 (기본값: unspecified)')
    
    # 4. 실제로 사용자가 터미널에 입력한 아규먼트를 파싱(해독)하여 args 변수에 담습니다.
    args = parser.parse_args()
    
    # 만약 아무런 명령어도 입력하지 않고 실행했다면 사용법 가이드를 화면에 출력하고 종료합니다.
    if not args.command:
        parser.print_help()
        sys.exit(1)

    # 5. Git 변경 사항 데이터 수집 과정을 진행합니다.
    status_text = get_git_status()  # 변경된 파일명 및 상태 정보 가져오기
    diff_text = get_git_diff()      # 변경된 코드 세부 차이점 가져오기
    
    # 수집한 정보가 둘 다 비어있다면, 변경 사항이 아예 없는 깨끗한 상태이므로 종료합니다.
    if not status_text and not diff_text:
        print("[INFO] 변경 사항이 없습니다. 커밋/PR 메시지를 생성하지 않고 종료합니다.")
        sys.exit(0)  # 0번 종료 코드는 에러 없이 정상적으로 모든 수행을 마쳤음을 OS에 알립니다.
        
    print(f"[INFO] Git status 수집 완료: 변경 감지")
    print(f"[INFO] Git diff 수집 완료: {len(diff_text.splitlines())}줄")
    
    # 6. 안전 모드(safe-mode) 스위치가 활성화되어 있다면 민감정보를 마스킹합니다.
    if args.safe_mode:
        diff_text = apply_safe_mode(diff_text, max_lines=args.safe_lines)
        
    # 7. 팀 컨벤션 규칙 파일(.ai-gitgen.yml)을 로드합니다.
    convention = load_convention()
    
    # 8. 서브 명령어 분기를 수행하여 비즈니스 로직을 호출합니다.
    if args.command == 'commit':
        generate_commit_message(args, diff_text, status_text, convention)
    elif args.command == 'pr':
        generate_pr_draft(args, diff_text, status_text, convention)

# 이 파이썬 스크립트가 다른 파일에 의해 import되지 않고, 터미널에서 직접 실행된 경우에만 main()을 시작하라는 구문입니다.
if __name__ == "__main__":
    main()

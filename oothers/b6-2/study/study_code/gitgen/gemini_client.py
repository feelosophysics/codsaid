# ==============================================================================
# 파일명: study/study_code/gitgen/gemini_client.py
# 목적: Google Gemini/Gemma REST API 서버와 직접 통신하여 프롬프트를 전송하고 AI 답변을 받아오는 클라이언트 모듈입니다.
# ==============================================================================

"""
[파이썬 문법 및 컴퓨터 과학(CS) 개념 설명]

1. HTTP 프로토콜과 REST API (Representational State Transfer API)
   - 웹상에서 컴퓨터끼리 통신하기 위해 정의한 규약을 HTTP(HyperText Transfer Protocol)라고 합니다.
   - REST API는 HTTP의 기본 규칙(URI, Method, Header, Body)을 활용하여 서버의 자원을 요청하고 제어하는 아키텍처 스타일입니다.
   - 이 프로그램은 로컬 컴퓨터(클라이언트)가 Google API 서버(호스트)에게 AI 생성 서비스 자원을 요청하는 클라이언트-서버 구조로 동작합니다.

2. HTTP 요청(Request)의 구성 요소
   - **URL(Uniform Resource Locator)**: 데이터나 서비스를 제공하는 인터넷 상의 주소입니다.
   - **HTTP Method (요청 메서드)**: 수행할 작업 유형을 나타냅니다.
     - `GET`: 데이터를 안전하게 조회(Read)할 때 사용. (Body가 통상적으로 없음)
     - `POST`: 새로운 자원을 생성(Create)하거나 대량의 데이터를 전송할 때 사용. (본 파일은 AI 분석 데이터를 보내기 때문에 POST 방식을 사용)
   - **HTTP Header (요청 헤더)**: 메타데이터 정보(데이터 타입, 인증 토큰 등)를 키-값 쌍으로 담는 공간입니다.
     - `Content-Type: application/json`: "우리가 보내는 데이터 바디가 JSON 형식이다"라고 서버에게 알려줍니다.
     - `x-goog-api-key`: 구글 서버가 허용한 클라이언트인지 판단할 수 있는 인증 키(API Key)를 실어 보냅니다.
   - **HTTP Body (요청 바디)**: 실제 전송할 알맹이 데이터(JSON화된 프롬프트와 옵션 설정값)가 담깁니다.

3. TCP/IP 소켓 통신과 바이트 인코드/디코드
   - 컴퓨터 네트워크 카드는 문자열("Hello")을 직접 선로로 보내지 못합니다. 0과 1의 비트 열, 즉 바이트(Bytes) 배열로 변환해야 전송할 수 있습니다.
   - `json.dumps(data)`는 파이썬 객체(dict)를 텍스트 문자열(str)로 바꾸며(직렬화),
     `.encode('utf-8')`은 그 문자열을 가상 머신 외부의 소켓 버퍼로 내보내기 위한 2진수 바이트열(`bytes`)로 인코딩합니다.
   - 반대로 응답을 받을 때도 `response.read()`가 읽어온 바이트열 데이터를 `.decode('utf-8')`을 통해 문자열로 디코딩한 뒤, `json.loads()`로 역직렬화하여 파이썬 객체로 사용합니다.

4. 컴퓨터 과학 기본: 아스키(ASCII) 코드와 한글 감지 (`ord` 함수)
   - ASCII(American Standard Code for Information Interchange)는 컴퓨터 초기 영문자와 일부 특수문자 전용으로 만든 7비트 문자 인코딩 체계입니다.
   - 0부터 127번까지 정의되어 있으며, 한글이나 기타 전 세계 유니코드 문자는 이 범위를 벗어납니다(128 이상).
   - 파이썬의 `ord(char)` 함수는 특정 문자 하나의 유니코드 정수 값을 리턴합니다.
   - `ord(char) > 127` 조건식은 API 키 내에 영문/숫자 외에 잘못 들어간 비아스키 문자(한글, 중국어, 특수 기호 등)가 섞여 있는지 판별하는 훌륭한 CS적 유효성 검사 기법입니다.

5. REST API 에러 종류
   - `urllib.error.HTTPError`: 구글 서버와 연결은 되었으나 서버 측에서 거부한 경우입니다(HTTP 상태 코드 400, 401, 403, 429, 500 등).
     - 400: Bad Request (잘못된 JSON 데이터나 모델명)
     - 401/403: Unauthorized/Forbidden (API 키가 틀렸거나 만료됨)
     - 429: Too Many Requests (호출 제한 횟수 초과)
   - `urllib.error.URLError`: DNS 서버 실패(인터넷 연결 끊김) 혹은 잘못된 호스트 주소 입력 등 연결 자체를 실패한 경우(Client-side)입니다.
"""

# Google API 클라이언트 모듈에 대한 모듈 수준의 Docstring
"""Google Gemini/Gemma REST API 서버에 요청을 전송하고 응답을 파싱하는 클라이언트 모듈입니다."""

import os              # 환경 변수(os.environ)를 가져오기 위해 파이썬 표준 라이브러리 os 임포트
import sys             # 프로그램 즉시 종료(sys.exit) 처리를 위해 파이썬 표준 라이브러리 sys 임포트
import json            # 딕셔너리와 JSON 텍스트 간 상호 변환을 위해 파이썬 표준 라이브러리 json 임포트
import urllib.request  # 외부 인터넷 주소(URL)로 HTTP 요청을 전송하기 위해 파이썬 표준 라이브러리 urllib.request 임포트
import urllib.error    # HTTP 통신 중 에러를 처리하기 위해 파이썬 표준 라이브러리 urllib.error 임포트

def validate_api_key(api_key):
    """넘겨받은 AI API 키의 기본 형식과 유효성을 철저히 검증합니다.
    
    비어있거나(None/빈 문자열), 비아스키 문자(한글/특수문자) 등이 섞여 있으면
    에러 사유를 친절히 안내한 뒤 즉각적으로 프로그램을 강제 종료(sys.exit(1))시킵니다.
    """
    # 1. 데이터 존재 유무 검사 (Early Return)
    # API 키가 비어 있는 경우(!api_key) 프로세스를 정상 수행할 수 없으므로 early exit 처리합니다.
    if not api_key:
        print("[ERROR] AI_API_KEY 환경변수가 설정되지 않았습니다.")
        print("## 예) export AI_API_KEY=\"여러분의_API_KEY\"")
        sys.exit(1)

    # 2. API 키 유효 문자 구성 검사
    # 리스트 컴프리헨션을 사용하면 한 줄로 적을 수 있지만, 초심자의 명확한 제어 흐름 이해를 위해
    # 명시적 플래그(is_valid)와 break문이 있는 for 루프로 풀어서 작성되었습니다.
    is_valid = True
    # .isalnum()은 해당 문자열이 '알파벳과 숫자'로만 이루어져 있는지 판별해 줍니다.
    if not api_key.isalnum():
        for char in api_key:
            # 구글 API 키에는 간혹 대시(-)나 언더바(_)가 들어갈 수 있으므로 허용 리스트를 둡니다.
            if char not in '-_':
                is_valid = False
                break  # 비허용 문자가 한 개라도 발견되면 즉시 탐색 중단(Optimization)
                
    # 만약 유효한 문자 조합이면 에러를 띄우지 않고 조용히 함수를 반환합니다.
    if is_valid:
        return

    # 3. 비아스키 문자(한글/전각 특수문자 등) 감지 세션
    has_non_ascii = False
    for char in api_key:
        # 아스키 코드는 127번까지 존재합니다. 유니코드 값이 127을 초과하면 한글 등 비영어권 문자입니다.
        if ord(char) > 127:
            has_non_ascii = True
            break  # 한글 감지 시 즉각 정지
            
    # 한글이나 깨진 특수문자가 식별된 경우 에러 로그 출력
    if has_non_ascii:
        print("[ERROR] API Key에 유효하지 않은 문자(한글 또는 특수 기호)가 포함되어 있습니다.")
        print("        Google AI Studio에서 발급받은 영문/숫자 형태의 키만 입력해 주세요.")
        sys.exit(1)


def call_gemini_api(prompt, model, temperature, max_tokens, thinking_level='unspecified'):
    """사용자가 조합해 준 프롬프트 텍스트를 담아 구글 제미나이/젬마 API 서버를 호출합니다.
    
    성공 시 결과 텍스트만 추출해 리턴하고, API 실패 시 HTTP 에러 정보를 파싱해 보여주고 종료합니다.
    """
    # 1. 데이터 정제 및 유효성 검사 (Early Return)
    # 시스템 환경 변수 딕셔너리에서 'AI_API_KEY' 항목을 조회합니다. 없으면 None 반환.
    api_key = os.environ.get("AI_API_KEY")
    # 앞서 정의한 API 키 정밀 유효성 검사 함수 실행
    validate_api_key(api_key)

    # 2. HTTP 요청 패킷 조립
    print("[INFO] AI API 요청 중...")
    # 구글 API 서버 엔드포인트 URL 동적 구성
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    
    # AI 생성 제어 옵션 딕셔너리 구성
    generation_config = {
        "temperature": temperature,      # 답변 창의성 정도 제어
        "maxOutputTokens": max_tokens     # 응답 최대 토큰 수 한계 설정
    }
    
    # 모델명 대소문자 무관 처리를 위해 소문자로 변환하여 비교합니다.
    model_lower = model.lower()
    
    # 구글 제미나이(Gemini) 모델의 경우 '생각하기(Thinking)' 기능을 꺼야(thinkingBudget=0) 
    # API 무료 한도(Free Tier) 내에서 오류 없이 동작하므로 아래 설정을 추가합니다.
    if "gemini" in model_lower:
        generation_config["thinkingConfig"] = {
            "thinkingBudget": 0
        }
    # 젬마(Gemma 2/4) 모델 계열이면서 thinking_level을 높은 수준('high')으로 지정한 경우 
    # 생각 과정을 깊게 수행하도록 활성화합니다.
    elif "gemma" in model_lower and thinking_level == "high":
        generation_config["thinkingConfig"] = {
            "thinkingLevel": "high"
        }

    # 구글 API 규격(JSON payload schema)에 맞춰 요청 본문 데이터 구조화
    data = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": generation_config
    }
    
    # 직렬화 및 바이트 인코딩 수행
    json_data = json.dumps(data).encode('utf-8')
    
    # HTTP 헤더 설정
    headers = {
        'Content-Type': 'application/json',
        'x-goog-api-key': api_key  # 키 헤더 인증 방식 적용
    }
    
    # urllib.request.Request 객체를 생성합니다. HTTP Method는 POST로 고정 선언합니다.
    req = urllib.request.Request(url, data=json_data, headers=headers, method='POST')
    
    # 3. 네트워크 통신 실행 및 예외 처리
    try:
        # Request를 실행하여 소켓 스트림을 개방하고 서버 응답을 대기합니다.
        # with문 덕분에 작업 완료 후 소켓 스트림 자원이 OS에 정상 반환됨이 보장됩니다.
        with urllib.request.urlopen(req) as response:
            # 응답 본문 바이트열 수신 및 디코딩
            response_body = response.read().decode('utf-8')
            # JSON 형식의 응답 문자열을 파이썬 딕셔너리로 역직렬화(Parsing)
            response_json = json.loads(response_body)
            
            # API 응답 결과 데이터 검증
            if 'candidates' not in response_json or not response_json['candidates']:
                print("[ERROR] 예상치 못한 API 응답 구조입니다.")
                return "API 호출 실패 (응답 텍스트 없음)"
                
            # 구글 API 응답 JSON에서 생성 문장 파트들의 리스트를 가져옵니다.
            parts = response_json['candidates'][0]['content']['parts']
            
            # AI 모델의 생각 과정(thought) 블록이 포함되어 있는 경우,
            # 초심자용 출력 화면을 깔끔하게 유지하기 위해 생각 과정을 제외한 순수 텍스트만 명시적 for 루프로 거릅니다.
            actual_parts = []
            for p in parts:
                # 딕셔너리의 .get('thought') 메서드는 해당 키가 없으면 None을 리턴하므로 에러를 유발하지 않습니다.
                # 'thought' 블록이 아닌(not) 일반 텍스트 파트만 수집합니다.
                if not p.get('thought'):
                    actual_parts.append(p['text'])
                    
            # 필터링된 실제 답변 문자열이 존재하면 공백 없이 결합해서 리턴합니다.
            if actual_parts:
                return "".join(actual_parts)
                
            # 거를 항목이 없다면 안전하게 0번째 부품의 텍스트 원본을 리턴합니다.
            return parts[0]['text']
            
    except urllib.error.HTTPError as e:
        # 서버에서 응답 에러를 반환했을 경우 HTTPError가 잡힙니다.
        # 오류 발생 시 구글 API 응답 내부의 상세 원인(code, status, message)을 추출하여 출력합니다.
        error_code = e.code             # HTTP Status Code (예: 400, 403)
        error_status = "UNKNOWN_ERROR"  # API 내부 에러 사유 (예: INVALID_ARGUMENT)
        error_message = e.reason        # 예외 기본 에러 메시지
        
        try:
            # 에러 스트림 버퍼 데이터를 읽어옵니다.
            error_body = e.read().decode('utf-8')
            # 에러 바디 파싱
            error_json = json.loads(error_body)
            # 구글 API 에러 포맷인 {"error": {"code": 400, "message": "...", "status": "..."}} 형태로 파싱
            if "error" in error_json:
                err_detail = error_json["error"]
                error_code = err_detail.get("code", error_code)
                error_status = err_detail.get("status", error_status)
                error_message = err_detail.get("message", error_message)
        except Exception:
            # 에러 바디 파싱 시도 중 또 다른 부차적인 에러가 나더라도 무시(pass)하여 
            # 최상위 HTTPError 정보(e.code, e.reason)라도 보여줄 수 있게 조치합니다.
            pass
            
        print("[ERROR] API HTTP 오류가 발생하였습니다.")
        print(f"        상태 코드(Code): {error_code}")
        print(f"        에러 유형(Status): {error_status}")
        print(f"        상세 내용(Message): {error_message}")
        sys.exit(1)
        
    except urllib.error.URLError as e:
        # 네트워크 전선 단선, 공유기 단절, DNS 호스트 해석 불가 시 동작
        print(f"[ERROR] API 네트워크 오류 발생: {e.reason}")
        sys.exit(1)
    except UnicodeEncodeError:
        # API Key 인코딩 중 비정상 문자로 인해 바이트 인코딩 실패 시 동작
        print("[ERROR] API Key 인코딩 중 오류가 발생했습니다. 키 값에 한글이나 잘못된 문자가 포함되어 있는지 확인해 주세요.")
        sys.exit(1)
    except Exception as e:
        # 기타 메모리 부족, 비정상적 라이브러리 충돌 등 모든 최상위 일반 예외 처리
        print(f"[ERROR] 알 수 없는 오류 발생: {e}")
        sys.exit(1)

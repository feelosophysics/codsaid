"""Google Gemini/Gemma REST API 서버에 요청을 전송하고 응답을 파싱하는 클라이언트 모듈입니다."""

import os
import sys
import json
import urllib.request
import urllib.error

def validate_api_key(api_key):
    """API Key의 형식과 유효성을 명시적인 for 루프로 검증합니다.
    
    유효하지 않은 문자나 한글이 있을 경우, 안내 메시지를 출력하고 프로그램을 종료합니다.
    """
    # 1. 데이터 유효성 검사 (Early Return)
    if not api_key:
        print("[ERROR] AI_API_KEY 환경변수가 설정되지 않았습니다.")
        print("## 예) export AI_API_KEY=\"여러분의_API_KEY\"")
        sys.exit(1)

    # 2. API 키 유효 문자 검사 (컴프리헨션 지양, 명시적 for 루프)
    is_valid = True
    if not api_key.isalnum():
        for char in api_key:
            if char not in '-_':
                is_valid = False
                break
                
    if is_valid:
        return

    # 3. 비아스키 문자(한글/특수문자) 감지
    has_non_ascii = False
    for char in api_key:
        if ord(char) > 127:
            has_non_ascii = True
            break
            
    if has_non_ascii:
        print("[ERROR] API Key에 유효하지 않은 문자(한글 또는 특수 기호)가 포함되어 있습니다.")
        print("        Google AI Studio에서 발급받은 영문/숫자 형태의 키만 입력해 주세요.")
        sys.exit(1)


def call_gemini_api(prompt, model, temperature, max_tokens, thinking_level='unspecified'):
    """Google Gemini/Gemma REST API 서버에 요청을 보내고 AI가 생성한 최종 텍스트를 반환합니다.
    
    오류 발생 시 구글 API 응답 JSON에서 code, status, message를 추출하여 상세히 출력한 뒤 프로그램을 종료합니다.
    """
    # 1. 데이터 정제 및 유효성 검사 (Early Return)
    api_key = os.environ.get("AI_API_KEY")
    validate_api_key(api_key)

    # 2. 로직 실행
    print("[INFO] AI API 요청 중...")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    
    generation_config = {
        "temperature": temperature,
        "maxOutputTokens": max_tokens
    }
    
    model_lower = model.lower()
    if "gemini" in model_lower:
        generation_config["thinkingConfig"] = {
            "thinkingBudget": 0
        }
    elif "gemma" in model_lower and thinking_level == "high":
        generation_config["thinkingConfig"] = {
            "thinkingLevel": "high"
        }

    data = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": generation_config
    }
    
    json_data = json.dumps(data).encode('utf-8')
    headers = {
        'Content-Type': 'application/json',
        'x-goog-api-key': api_key
    }
    
    req = urllib.request.Request(url, data=json_data, headers=headers, method='POST')
    
    try:
        with urllib.request.urlopen(req) as response:
            response_body = response.read().decode('utf-8')
            response_json = json.loads(response_body)
            
            if 'candidates' not in response_json or not response_json['candidates']:
                print("[ERROR] 예상치 못한 API 응답 구조입니다.")
                return "API 호출 실패 (응답 텍스트 없음)"
                
            parts = response_json['candidates'][0]['content']['parts']
            
            # 컴프리헨션 지양: 생각 과정을 제외한 텍스트 파트만 명시적 for 루프로 수집
            actual_parts = []
            for p in parts:
                if not p.get('thought'):
                    actual_parts.append(p['text'])
                    
            if actual_parts:
                return "".join(actual_parts)
                
            return parts[0]['text']
            
    except urllib.error.HTTPError as e:
        # 오류 발생 시 구글 API 응답 JSON에서 code, status, message를 추출하여 담백하게 보여줍니다.
        error_code = e.code
        error_status = "UNKNOWN_ERROR"
        error_message = e.reason
        
        try:
            error_body = e.read().decode('utf-8')
            error_json = json.loads(error_body)
            if "error" in error_json:
                err_detail = error_json["error"]
                error_code = err_detail.get("code", error_code)
                error_status = err_detail.get("status", error_status)
                error_message = err_detail.get("message", error_message)
        except Exception:
            pass
            
        print("[ERROR] API HTTP 오류가 발생하였습니다.")
        print(f"        상태 코드(Code): {error_code}")
        print(f"        에러 유형(Status): {error_status}")
        print(f"        상세 내용(Message): {error_message}")
        sys.exit(1)
        
    except urllib.error.URLError as e:
        print(f"[ERROR] API 네트워크 오류 발생: {e.reason}")
        sys.exit(1)
    except UnicodeEncodeError:
        print("[ERROR] API Key 인코딩 중 오류가 발생했습니다. 키 값에 한글이나 잘못된 문자가 포함되어 있는지 확인해 주세요.")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] 알 수 없는 오류 발생: {e}")
        sys.exit(1)

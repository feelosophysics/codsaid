"""안전 모드(safe-mode)를 지원하여 diff 결과 내 민감 정보를 마스킹하고 길이를 제한하는 모듈입니다."""

import re

def mask_secret(match):
    """정규표현식에 매칭된 비밀번호 정보 중 일부만 남기고 마스킹하기 위한 헬퍼 함수입니다.
    
    4글자 이하이면 전체 별표, 4글자 초과이면 앞 2글자만 남기고 별표 처리합니다.
    """
    key = match.group(1)
    val = match.group(2)
    
    # 삼항 연산자 지양: if-else 구문으로 가독성을 높입니다.
    if len(val) > 4:
        masked_val = val[:2] + '*' * (len(val) - 2)
    else:
        masked_val = '****'
        
    if ':' in match.group(0):
        delimiter = ':'
    else:
        delimiter = '='
        
    return f'{key}{delimiter}"{masked_val}"'


def apply_safe_mode(diff_text, max_lines=200):
    """안전 모드(safe-mode) 활성화 시, 전송 텍스트 줄 수를 제한하고 민감 정보를 마스킹합니다.
    
    이메일, API 키, IP 주소, 비밀번호 등 민감 정보를 정규표현식으로 필터링합니다.
    """
    # 1. 데이터 정제 및 유효성 검사 (Early Return)
    if not diff_text:
        return ""

    # 2. 로직 실행
    print(f"[INFO] 안전 모드(safe-mode)가 활성화되었습니다. 민감 정보를 마스킹하고 길이를 {max_lines}줄로 제한합니다.")
    
    lines = diff_text.split('\n')
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines.append(f"\n... (안전 모드로 인해 {max_lines}줄까지만 전송됩니다) ...")
        diff_text = '\n'.join(lines)
    
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    diff_text = re.sub(email_pattern, '***@***.***', diff_text)
    
    apikey_pattern = r'sk-[a-zA-Z0-9]{20,}'
    diff_text = re.sub(apikey_pattern, 'sk-***MASKED***', diff_text)
    
    bearer_pattern = r'Bearer\s+[a-zA-Z0-9\-\._~+/]+=*'
    diff_text = re.sub(bearer_pattern, 'Bearer ***MASKED***', diff_text)

    ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
    diff_text = re.sub(ip_pattern, '***.***.***.***', diff_text)

    secret_pattern = r'(?i)(password|secret|passwd|private_key)\s*[:=]\s*["\']([^"\']+)["\']'
    diff_text = re.sub(secret_pattern, mask_secret, diff_text)

    return diff_text

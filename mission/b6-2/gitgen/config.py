"""팀 내 Git 커밋 및 PR 컨벤션 설정 파일(.ai-gitgen.yml)을 로드하는 모듈입니다."""

import os
import yaml

def load_convention():
    """프로젝트 루트에 있는 .ai-gitgen.yml 파일을 로드하여 설정을 반환합니다.
    
    설정 파일이 없거나 오류 발생 시 None을 반환하여 기본 동작을 유도합니다.
    """
    config_file = 'ai-gitgen.yml'
    
    # 1. 데이터 유효성 검사 (Early Return)
    if not os.path.exists(config_file):
        return None
        
    # 2. 로직 실행
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            print("[INFO] .ai-gitgen.yml 컨벤션 파일을 성공적으로 불러왔습니다.")
            return config
    except yaml.YAMLError as exc:
        print(f"[ERROR] 컨벤션 파일 파싱 오류: {exc}")
        return None
    except Exception as exc:
        print(f"[ERROR] 설정 파일을 읽는 중 알 수 없는 오류 발생: {exc}")
        return None

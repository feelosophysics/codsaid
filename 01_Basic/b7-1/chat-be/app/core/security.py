# 비밀번호 검증과 로그인 증명서(JWT)를 담당합니다. bcrypt 해시는 비밀번호를 원문 대신 저장하는 일방향 변환입니다.
# JWT는 서버가 서명한 문자열입니다. 내용을 숨기는 암호화가 아니므로 비밀번호·AI 키를 안에 넣으면 안 됩니다.
# 서명 확인과 만료시간 확인을 모두 통과해야 다른 파일에서 로그인한 사용자로 인정합니다.
from datetime import datetime, timedelta, timezone
from typing import Optional, Any, Union
from jose import jwt, JWTError
from passlib.context import CryptContext
from app.core.config import get_settings

settings = get_settings()

# bcrypt 방식으로 비밀번호를 처리하는 도구를 만듭니다. 해시를 복원해 비밀번호를 읽는 기능은 없습니다.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """입력 비밀번호와 저장된 해시가 같은 비밀번호에서 나왔는지 확인합니다. 해시를 원래 비밀번호로 복원하는 동작은
    아닙니다.
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """비밀번호 원문 대신 DB에 저장할 해시 문자열을 만듭니다.

    해시는 원래 비밀번호로 되돌려 읽기 위한 값이 아닌 일방향 변환 결과입니다. bcrypt는 salt라는 무작위 값을
    함께 사용하므로 같은 비밀번호도 매번 다른 해시가 생길 수 있습니다. 로그인할 때는 verify_password로
    입력값과 저장된 해시의 일치 여부를 확인합니다.
    """
    # 입력 비밀번호를 해시로 바꾸고 호출한 곳에 반환합니다. 함수 선언의 str은 문자열이라는 타입 안내입니다.
    return pwd_context.hash(password)


def create_access_token(subject: Union[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """사용자 이름(sub)과 발급/만료 시각을 담고 서버 키로 서명합니다. timedelta는 시간을 더할 때 쓰는 간격
    객체입니다.
    """
    now_utc = datetime.now(timezone.utc)
    if expires_delta:
        expire = now_utc + expires_delta
    else:
        expire = now_utc + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # exp는 만료, sub는 사용자 식별, iat는 발급 시각입니다. 토큰 내용은 읽을 수 있으므로 비밀 데이터를 넣지
    # 않습니다.
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "iat": now_utc
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """토큰의 서명·만료를 확인하고 내용을 꺼냅니다. 검증에 실패하면 None(값 없음)을 돌려 로그인 거절로 이어지게
    합니다.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    # 서명이나 만료 검사가 실패한 경우입니다. raise로 오류를 밖에 넘기지 않고 None을 반환해 인증 함수가
    # 401로 처리하게 합니다.
    except JWTError:
        return None

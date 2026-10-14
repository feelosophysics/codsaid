# API 함수가 실행되기 전에 로그인 사용자를 확인하는 공통 준비 작업입니다. Depends는 FastAPI에게 필요한 준비
# 함수를 지정합니다.
# 브라우저가 보낸 토큰을 꺼내 서명·만료를 확인하고 DB의 활성 사용자까지 찾습니다. 토큰이 있다는 사실만으로 로그인 성공은
# 아닙니다.
from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.core.database import get_db
from app.core.config import get_settings
from app.core.security import decode_access_token
from app.models.user import User

settings = get_settings()


def get_token_from_request(request: Request) -> Optional[str]:
    """HTTP-only 쿠키를 먼저 확인하고 없으면 Authorization: Bearer 헤더에서 토큰을 꺼냅니다.
    현재 FE는 Bearer 방식을 사용합니다.
    """
    # 1. 쿠키의 로그인 토큰을 먼저 찾습니다.
    cookie_token = request.cookies.get(settings.COOKIE_NAME)
    if cookie_token:
        return cookie_token

    # 2. 쿠키가 없으면 Bearer 헤더에서 토큰을 찾습니다.
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ")[1].strip()

    return None


def get_current_user(
    request: Request,
    # 함수 인수를 직접 만들지 않아도 FastAPI가 get_db를 실행해 DB 작업 공간을 준비합니다. 이를 의존성
    # 주입이라고 합니다.
    db: Session = Depends(get_db)
) -> User:
    """토큰 검증 후 DB의 활성 사용자까지 확인합니다. 잘못된 토큰·없는 사용자·비활성 계정은 모두 HTTP 401로
    거절합니다.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="로그인이 필요한 서비스입니다.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = get_token_from_request(request)
    if not token:
        raise credentials_exception

    # 서버 키로 서명과 만료를 검사합니다. 브라우저가 주장한 사용자 이름을 검증 없이 믿지 않습니다.
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception

    # DB에도 실제 활성 계정이 있어야 합니다. 토큰만 유효하고 계정이 삭제/비활성화됐다면 접근을 허용하지 않습니다.
    user = db.scalar(select(User).where(User.username == username))
    if user is None or not user.is_active:
        raise credentials_exception

    return user


def get_current_user_optional(
    request: Request,
    # 함수 인수를 직접 만들지 않아도 FastAPI가 get_db를 실행해 DB 작업 공간을 준비합니다. 이를 의존성
    # 주입이라고 합니다.
    db: Session = Depends(get_db)
) -> Optional[User]:
    """로그인이 선택 사항인 화면을 위한 조회입니다. 인증이 없거나 잘못되면 예외 대신 None을 돌려줍니다.
    """
    token = get_token_from_request(request)
    if not token:
        return None

    # 서버 키로 서명과 만료를 검사합니다. 브라우저가 주장한 사용자 이름을 검증 없이 믿지 않습니다.
    payload = decode_access_token(token)
    if payload is None:
        return None

    username: str = payload.get("sub")
    if username is None:
        return None

    # DB에도 실제 활성 계정이 있어야 합니다. 토큰만 유효하고 계정이 삭제/비활성화됐다면 접근을 허용하지 않습니다.
    user = db.scalar(select(User).where(User.username == username))
    if user is None or not user.is_active:
        return None

    return user

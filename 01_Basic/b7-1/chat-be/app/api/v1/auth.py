# 회원가입·로그인·로그아웃·내 정보·비밀번호 변경의 주소와 동작을 연결합니다.
# @router.post 같은 장식자는 바로 아래 함수를 특정 HTTP 주소에 등록합니다. 요청은 스키마에서 먼저
# 검사됩니다.
# db.add는 저장 준비, commit은 저장 확정, refresh는 DB가 만든 최신 값을 다시 읽는 작업입니다.
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.core.database import get_db
from app.core.config import get_settings
from app.core.security import get_password_hash, verify_password, create_access_token
from app.models.user import User
from app.schemas.auth import UserCreate, UserLogin, UserResponse, Token, PasswordChange
from app.api.deps import get_current_user
from app.core.abuse import limit_registration, limit_login

router = APIRouter(prefix="/auth", tags=["Authentication"])
settings = get_settings()


# 장식자(@로 시작)는 바로 아래 함수를 이 HTTP 주소의 처리기로 등록합니다. dependencies는 함수보다 먼저
# 제한 검사를 실행합니다.
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(limit_registration)])
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """중복 아이디를 확인하고 비밀번호 해시를 저장합니다. 사용자 응답 스키마에는 password_hash가 없어 비밀번호
    정보는 응답에 포함되지 않습니다.
    """
    existing_user = db.scalar(select(User).where(User.username == user_in.username))
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 존재하는 아이디입니다."
        )

    new_user = User(
        username=user_in.username,
        nickname=user_in.nickname,
        # 비밀번호 원문 대신 해시를 저장합니다. 프론트의 입력 검사만 믿지 않고 서버 스키마도 길이를 검사합니다.
        password_hash=get_password_hash(user_in.password),
        is_active=True,
        is_admin=False
    )
    # DB에 넣을 객체를 작업 공간에 등록합니다. 이 줄만으로 저장이 확정되지는 않습니다.
    db.add(new_user)
    # 이 작업 공간에 준비한 변경을 DB에 확정합니다. 저장 전에 예외가 나면 확정되지 않을 수 있습니다.
    db.commit()
    db.refresh(new_user)
    return new_user


# 장식자(@로 시작)는 바로 아래 함수를 이 HTTP 주소의 처리기로 등록합니다. dependencies는 함수보다 먼저
# 제한 검사를 실행합니다.
@router.post("/login", response_model=Token, dependencies=[Depends(limit_login)])
def login(response: Response, user_in: UserLogin, db: Session = Depends(get_db)):
    """아이디·비밀번호와 활성 상태를 확인한 뒤 JWT를 발급합니다. 쿠키와 JSON 토큰을 둘 다 제공하며 현재 프론트는
    JSON 토큰을 저장합니다.
    """
    user = db.scalar(select(User).where(User.username == user_in.username))
    if not user or not verify_password(user_in.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="아이디 또는 비밀번호가 올바르지 않습니다."
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="비활성화된 계정입니다."
        )

    access_token = create_access_token(subject=user.username)

    # 브라우저의 JavaScript가 직접 읽을 수 없는 인증 쿠키를 설정합니다.
    # 쿠키는 브라우저가 보관하는 인증값입니다. httponly는 JS의 직접 읽기를 막지만, JSON으로 받은 별도
    # 토큰에는 적용되지 않습니다.
    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=access_token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        expires=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        # 운영 인증 쿠키는 HTTPS에서만 전송합니다. 현재 FE의 Bearer 인증도 그대로 지원합니다.
        secure=settings.is_production
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


# 장식자(@로 시작)는 바로 아래 함수를 이 HTTP 주소의 처리기로 등록합니다. dependencies는 함수보다 먼저
# 제한 검사를 실행합니다.
@router.post("/logout")
def logout(response: Response):
    """브라우저의 인증 쿠키를 삭제합니다. FE에 별도 저장한 Bearer 토큰은 프론트의 removeToken에서
    지웁니다.
    """
    response.delete_cookie(
        key=settings.COOKIE_NAME,
        httponly=True,
        samesite="lax",
        secure=settings.is_production
    )
    return {"message": "로그아웃되었습니다."}


# 장식자(@로 시작)는 바로 아래 함수를 이 HTTP 주소의 처리기로 등록합니다. dependencies는 함수보다 먼저
# 제한 검사를 실행합니다.
@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """인증 준비 단계에서 찾은 내 사용자 정보를 응답합니다. 요청자가 임의의 user_id를 넣어 다른 계정을 조회하는
    API가 아닙니다.
    """
    return current_user


# 장식자(@로 시작)는 바로 아래 함수를 이 HTTP 주소의 처리기로 등록합니다. dependencies는 함수보다 먼저
# 제한 검사를 실행합니다.
@router.put("/password", dependencies=[Depends(limit_login)])
def change_password(
    password_in: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """현재 비밀번호를 확인하고 새 비밀번호의 해시로 교체합니다. 요청 스키마가 새 비밀번호 길이를 먼저 검사합니다.
    """
    if not verify_password(password_in.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="현재 비밀번호가 일치하지 않습니다."
        )

    current_user.password_hash = get_password_hash(password_in.new_password)
    # 이 작업 공간에 준비한 변경을 DB에 확정합니다. 저장 전에 예외가 나면 확정되지 않을 수 있습니다.
    db.commit()
    return {"message": "비밀번호가 변경되었습니다."}

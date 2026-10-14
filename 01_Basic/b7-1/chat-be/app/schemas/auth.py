# 인증 API의 입력/출력 모양을 정합니다. DB 모델은 저장 구조, 이 스키마는 네트워크로 주고받는 데이터 구조입니다.
# Field의 길이 조건은 잘못된 입력을 거절하고, field_validator는 공백 같은 추가 조건을 검사합니다.
# Optional은 값이 없을 수도 있다는 뜻입니다. from_attributes는 DB 객체의 속성을 응답 데이터로 읽게
# 합니다.
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator


class UserCreate(BaseModel):
    """가입 요청이 반드시 보내야 할 아이디·닉네임·비밀번호의 규격입니다. 점 세 개(...)는 필수값을 뜻합니다.
    """
    username: str = Field(..., min_length=3, max_length=30, description="사용자 아이디 (3~30자)")
    nickname: str = Field(..., min_length=1, max_length=30, description="닉네임 (1~30자)")
    password: str = Field(..., min_length=8, max_length=100, description="비밀번호 (8자 이상)")

    # 지정 필드의 추가 검사를 붙입니다. @classmethod의 cls는 객체 한 개가 아닌 이 모델 클래스 자체를
    # 가리킵니다.
    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """아이디 앞뒤 공백을 없애고 빈 값이면 거절합니다. strip은 문자열의 양끝 공백을 없애는 메서드입니다.
        """
        v = v.strip()
        if not v:
            raise ValueError("아이디를 입력해주세요.")
        return v

    # 지정 필드의 추가 검사를 붙입니다. @classmethod의 cls는 객체 한 개가 아닌 이 모델 클래스 자체를
    # 가리킵니다.
    @field_validator("nickname")
    @classmethod
    def validate_nickname(cls, v: str) -> str:
        """닉네임 앞뒤 공백을 제거해 공백만 입력한 이름을 거절합니다. 정상 값은 정리한 문자열로 돌려줍니다.
        """
        v = v.strip()
        if not v:
            raise ValueError("닉네임을 입력해주세요.")
        return v

    # 지정 필드의 추가 검사를 붙입니다. @classmethod의 cls는 객체 한 개가 아닌 이 모델 클래스 자체를
    # 가리킵니다.
    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """공백을 제외한 비밀번호 길이가 8자 이상인지 검사합니다. 실제 반환값은 원문이므로 사용자가 넣은 비밀번호를
        임의로 바꾸지 않습니다.
        """
        if not v or len(v.strip()) < 8:
            raise ValueError("비밀번호는 최소 8자 이상이어야 합니다.")
        return v


class UserLogin(BaseModel):
    """로그인 요청의 아이디·비밀번호 규격입니다. 인증 성공 여부는 이 검사 이후 API에서 DB와 비교합니다.
    """
    username: str = Field(..., description="사용자 아이디")
    password: str = Field(..., description="비밀번호")


class UserResponse(BaseModel):
    """사용자에게 돌려줄 공개 필드만 고릅니다. DB에 있는 password_hash는 여기에 없어 응답으로 나가지
    않습니다.
    """
    id: int
    username: str
    nickname: str
    is_active: bool
    is_admin: bool
    created_at: datetime

    # DB 모델 객체에서 공개 응답 필드만 읽을 수 있게 합니다. DB의 모든 열을 자동 공개하는 설정이 아닙니다.
    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    """로그인 성공 응답입니다. access_token은 이후 요청에 붙일 증명서이고 user는 화면 표시용 사용자
    정보입니다.
    """
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenData(BaseModel):
    """토큰에서 꺼낸 사용자 정보를 표현할 수 있는 보조 규격입니다. 현재 인증 로직은 해독한 dict를 직접 읽습니다.
    """
    user_id: Optional[int] = None
    username: Optional[str] = None


class PasswordChange(BaseModel):
    """현재 비밀번호 확인과 새 비밀번호 변경에 필요한 입력입니다. 새 비밀번호는 가입과 같은 길이 조건을 적용합니다.
    """
    current_password: str = Field(..., description="현재 비밀번호")
    new_password: str = Field(..., min_length=8, max_length=100, description="새 비밀번호 (8자 이상)")

    # 지정 필드의 추가 검사를 붙입니다. @classmethod의 cls는 객체 한 개가 아닌 이 모델 클래스 자체를
    # 가리킵니다.
    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """새 비밀번호에도 가입과 같은 최소 길이 조건을 적용합니다. ValueError는 입력 오류를 API의 422
        응답으로 연결합니다.
        """
        if not v or len(v.strip()) < 8:
            raise ValueError("비밀번호는 최소 8자 이상이어야 합니다.")
        return v

# 백엔드의 출발점입니다. 브라우저가 보내는 HTTP 요청을 FastAPI가 받아 인증·채팅·기록 담당 파일로 연결합니다.
# 요청은 주소와 데이터로 이루어지고 응답은 JSON(이름:값 형태의 데이터) 또는 SSE(답변 조각을 계속 보내는
# 연결)입니다.
# 아래 코드는 설정 읽기 → DB 준비 → 공통 처리 등록 → 주소별 처리 등록 순서로 실행됩니다.
import os
import sys

# 직접 실행할 때도 프로젝트의 app 패키지를 찾을 수 있게 경로를 추가합니다.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from app.core.config import get_settings
from app.core.database import init_db
from app.core.logging import logger
from app.core.middlewares import RequestIDMiddleware
from app.core.abuse import ChatLeaseMiddleware

# 주소별 인증·채팅·기록 담당 처리기입니다.
from app.api.v1.auth import router as auth_router
from app.api.v1.chat import router as chat_router
from app.api.v1.logs import router as logs_router

settings = get_settings()

# 앱을 불러올 때 없는 표를 준비합니다. 따라서 시험에서는 import 전에 임시 DB 환경을 지정합니다.
# 모델 파일의 표 설계를 등록하고 없는 표만 만듭니다. 기존 데이터 삭제나 열 변경은 하지 않습니다.
init_db()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """서버 시작 시 초기화하고 종료 시 로그를 남깁니다. yield 앞은 시작, 뒤는 종료 단계이며 연결을 기다리는 동안
    서버가 동작합니다.
    """
    logger.info(f"Starting {settings.APP_NAME} in {settings.APP_ENV} mode...")
    # 모델 파일의 표 설계를 등록하고 없는 표만 만듭니다. 기존 데이터 삭제나 열 변경은 하지 않습니다.
    init_db()
    logger.info("SQLite Database initialized successfully.")
    yield
    logger.info("Shutting down application...")


app = FastAPI(
    title=settings.APP_NAME,
    description="FastAPI Web Backend for AI Chatbot Service (AI/SW Basic)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# 1. 요청 앞뒤의 공통 처리를 등록합니다.
# 이 처리기는 API 앞뒤에 공통으로 적용됩니다. API마다 같은 인증/로그 코드를 복사하지 않게 역할을 나눕니다.
app.add_middleware(RequestIDMiddleware)
# 이 처리기는 API 앞뒤에 공통으로 적용됩니다. API마다 같은 인증/로그 코드를 복사하지 않게 역할을 나눕니다.
app.add_middleware(ChatLeaseMiddleware)
# 이 처리기는 API 앞뒤에 공통으로 적용됩니다. API마다 같은 인증/로그 코드를 복사하지 않게 역할을 나눕니다.
app.add_middleware(
    CORSMiddleware,
    # CORS는 허용 목록의 프론트만 브라우저에서 응답을 읽게 합니다. API 인증은 별도로 검사합니다.
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["Retry-After", "X-Request-ID"],
)

# 2. 오류 응답을 만드는 공통 처리기를 등록합니다.
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """입력 형식이 잘못되면 HTTP 422 JSON으로 알려 줍니다. Python 예외 객체는 JSON으로 그대로 보낼
    수 없어 필요한 필드만 골라냅니다.
    """
    errors = exc.errors()
    msg = errors[0].get("msg", "입력값 검증에 실패했습니다.") if errors else "입력값 검증 오류"
    safe_errors = [
        {"type": e.get("type"), "loc": e.get("loc"), "msg": e.get("msg"), "input": e.get("input")}
        for e in errors
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder({"detail": msg, "errors": safe_errors})
    )

# 3. 서버 생존 상태를 확인하는 주소입니다.
@app.get("/", tags=["Health"])
def root():
    """서버의 생존 상태와 API 주소를 돌려줍니다. healthy는 웹 서버 응답 확인이며 AI 호출 성공이나 모든 보안
    조건의 증거는 아닙니다.
    """
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": "1.0.0",
        "environment": settings.APP_ENV,
        "docs_url": "/docs",
        "api_v1_endpoints": {
            "auth": "/api/v1/auth",
            "chat": "/api/v1/chat",
            "logs": "/api/v1/logs"
        }
    }

# 4. 주소별 처리기를 공통 /api/v1 아래에 연결합니다.
# 분리한 주소 처리기를 앱에 등록합니다. prefix는 주소 앞에 공통으로 붙는 /api/v1 경로입니다.
app.include_router(auth_router, prefix="/api/v1")
# 분리한 주소 처리기를 앱에 등록합니다. prefix는 주소 앞에 공통으로 붙는 /api/v1 경로입니다.
app.include_router(chat_router, prefix="/api/v1")
# 분리한 주소 처리기를 앱에 등록합니다. prefix는 주소 앞에 공통으로 붙는 /api/v1 경로입니다.
app.include_router(logs_router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)

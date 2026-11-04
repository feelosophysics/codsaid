# 대화 목록과 채팅 요청을 처리합니다. 대화 묶음은 ChatSession, 각 질문/답변은 ChatMessage로
# 저장합니다.
# 사용자 질문을 먼저 저장한 뒤 AI를 호출합니다. SSE는 연결을 유지하며 text 조각과 마지막 done 사건을 보내는
# 방식입니다.
# async/await는 기다리는 동안 다른 요청도 처리하게 하고, yield는 한 조각을 호출자에게 건네고 나중에 이어서
# 실행하게 합니다.
import json
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from sqlalchemy.exc import SQLAlchemyError
from app.core.database import get_db, SessionLocal
from app.core.abuse import admit_chat
from app.core.logging import (
    log_request_received,
    log_db_save_success,
    log_db_save_failed,
    logger
)
from app.models.user import User
from app.models.chat import ChatSession, ChatMessage
from app.schemas.chat import (
    ChatStreamRequest,
    ChatSessionCreate,
    ChatSessionResponse,
    ChatMessageResponse
)
from app.api.deps import get_current_user
from app.services.gemini_service import gemini_service
from app.core.ai_models import MODEL_CHOICES, THINKING_LEVELS

router = APIRouter(prefix="/chat", tags=["Chat & Sessions"])
DB_SAVE_ERROR_DETAIL = "대화를 저장하지 못했습니다. 잠시 후 다시 시도해 주세요."


@router.get("/models")
def get_models(current_user: User = Depends(get_current_user)):
    """로그인 사용자에게 선택 목록과 서버 기본값을 제공합니다. 실제 AI를 호출하거나 키를 노출하지 않습니다."""
    return {
        "models": MODEL_CHOICES,
        "default_model": gemini_service.model_name,
        "search_enabled": gemini_service.search_enabled,
    }


@router.get("/sessions", response_model=List[ChatSessionResponse])
def get_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """로그인 사용자의 대화만 최근 수정 순으로 가져옵니다. 내부 번호는 사용자마다 1부터 다시 시작하는 순번이 아닙니다.
    """
    sessions = db.scalars(
        select(ChatSession)
        # 현재 사용자의 대화만 조회합니다. 다른 사용자의 대화가 목록에 섞이지 않게 하는 조건입니다.
        .where(ChatSession.user_id == current_user.id)
        .order_by(desc(ChatSession.updated_at))
    ).all()
    return sessions


@router.post("/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    session_in: ChatSessionCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """빈 대화 묶음을 만듭니다. flush로 내부 번호를 받은 뒤 응답 값을 준비하고 commit으로 저장 확정합니다.
    실패 시 rollback으로 취소합니다.
    """
    user_id = current_user.id
    request_id = getattr(request.state, "request_id", "req-unknown")
    log_request_received(user_id=user_id, path="/api/v1/chat/sessions", request_id=request_id)
    try:
        session = ChatSession(user_id=user_id, title=session_in.title or "새 대화")
        db.add(session)
        # 준비한 변경을 DB에 보내 내부 ID를 받습니다. 아직 commit 전이므로 같은 트랜잭션의 실패 시 함께
        # 취소할 수 있습니다.
        db.flush()
        # commit 뒤에는 ORM 속성이 만료되어 DB 재조회가 필요할 수 있으므로 응답값을 먼저 복사합니다.
        # 이미 확정한 저장을 이후 재조회 실패 때문에 취소된 것처럼 보고하지 않기 위한 순서입니다.
        response = ChatSessionResponse(
            id=session.id, user_id=user_id, title=session.title,
            created_at=session.created_at, updated_at=session.updated_at,
            messages=[]
        )
        # 빈 대화 생성만 확정합니다. 이 API는 질문을 저장하거나 AI를 호출하지 않습니다.
        db.commit()
    except SQLAlchemyError as error:
        # 빈 대화 생성에 실패하면 미확정 변경을 취소하고 DB 작업 공간을 다시 사용할 수 있게 합니다.
        db.rollback()
        log_db_save_failed(
            user_id=user_id, error=type(error).__name__,
            request_id=request_id, entity="session"
        )
        raise HTTPException(status_code=500, detail=DB_SAVE_ERROR_DETAIL) from None
    log_db_save_success(
        user_id=user_id, session_id=response.id,
        request_id=request_id, entity="session"
    )
    return response


@router.delete("/sessions/{session_id}", status_code=status.HTTP_200_OK)
def delete_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """내 소유의 대화인지 먼저 확인한 뒤 삭제합니다. 관계 설정의 cascade에 따라 그 대화의 메시지도 함께
    지워집니다.
    """
    session = db.scalar(
        select(ChatSession)
        # 대화 번호와 현재 사용자 번호를 함께 조건에 넣습니다. 남의 내부 번호를 아는 것만으로 조회/삭제할 수 없게
        # 합니다.
        .where(ChatSession.id == session_id, ChatSession.user_id == current_user.id)
    )
    if not session:
        raise HTTPException(status_code=404, detail="대화 세션을 찾을 수 없습니다.")

    db.delete(session)
    # 대화 삭제를 확정합니다. 모델의 관계 설정에 따라 연결된 메시지도 함께 삭제됩니다.
    db.commit()
    return {"message": "대화 세션이 삭제되었습니다.", "session_id": session_id}


@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessageResponse])
def get_session_messages(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """내 대화인지 검사하고 메시지를 시간순으로 읽습니다. 번호를 아는 것만으로 다른 사람의 대화에 접근할 수 없습니다.
    """
    session = db.scalar(
        select(ChatSession)
        # 대화 번호와 현재 사용자 번호를 함께 조건에 넣습니다. 남의 내부 번호를 아는 것만으로 조회/삭제할 수 없게
        # 합니다.
        .where(ChatSession.id == session_id, ChatSession.user_id == current_user.id)
    )
    if not session:
        raise HTTPException(status_code=404, detail="대화 세션을 찾을 수 없습니다.")

    messages = db.scalars(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
    ).all()
    return messages


@router.post("/stream")
async def stream_chat(
    request: Request,
    payload: ChatStreamRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """질문을 저장한 뒤 AI 답변을 스트림으로 보내는 채팅 API입니다.

    입력 payload는 요청 스키마에서 검사한 질문/대화 번호이고 current_user는 인증 준비 함수가 찾은
    사용자입니다. 처리 순서는 요청 허용 → 대화/질문 저장 → 문맥 확보 → AI 응답 → 답변 저장입니다.

    async def는 기다리는 동안 다른 요청을 처리할 수 있는 함수를 정의합니다. StreamingResponse는
    아래 생성기가 만드는 조각을 순서대로 전송합니다.
    """
    request_id = getattr(request.state, "request_id", "req-unknown")
    user_id = current_user.id
    # 화면을 거치지 않은 요청도 검사합니다. 잘못된 옵션은 DB 저장·AI 호출 전에 거절합니다.
    selected_model = payload.model or gemini_service.model_name
    if payload.thinking_level and payload.thinking_level not in THINKING_LEVELS.get(selected_model, []):
        raise HTTPException(status_code=422, detail="선택한 모델이 지원하지 않는 추론 수준입니다.")
    retry_seconds = gemini_service.cooldown_seconds(selected_model)
    if retry_seconds:
        raise HTTPException(status_code=429, detail="이 모델은 사용량 제한으로 잠시 대기 중입니다. 다른 모델을 선택하거나 대기 후 다시 시도해 주세요.", headers={"Retry-After": str(retry_seconds)})
    admit_chat(request, user_id)
    log_request_received(user_id=user_id, path="/api/v1/chat/stream", request_id=request_id)

    # 1. 세션·질문을 한 저장 묶음으로 준비하고 문맥도 확보합니다.
    # 질문 저장이 실패하면 함께 만든 새 대화도 rollback으로 취소합니다.
    session_id = payload.session_id
    save_entity = "session"
    try:
        session = db.scalar(
            select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user_id)
        ) if session_id else None
        # 내 대화를 찾지 못하면 새 대화를 만듭니다. 다른 사람의 대화 번호를 전달해도 그 사람의 대화를 이어받지는
        # 않습니다.
        new_session = session is None
        if new_session:
            session = ChatSession(user_id=user_id, title=payload.message[:30])
            db.add(session)
            # 준비한 변경을 DB에 보내 내부 ID를 받습니다. 아직 commit 전이므로 같은 트랜잭션의 실패 시
            # 함께 취소할 수 있습니다.
            db.flush()
            session_id = session.id

        # 2. 질문 저장과 대화 수정 시각 변경을 함께 준비합니다.
        save_entity = "user_message"
        user_msg = ChatMessage(
            session_id=session_id, user_id=user_id, role="user",
            content=payload.message, status="success"
        )
        db.add(user_msg)
        session.updated_at = datetime.now(timezone.utc)
        # 준비한 변경을 DB에 보내 내부 ID를 받습니다. 아직 commit 전이므로 같은 트랜잭션의 실패 시 함께
        # 취소할 수 있습니다.
        db.flush()
        user_message_id = user_msg.id
        session_title = session.title

        # 3. commit 뒤 재조회 없이 쓸 수 있도록 문맥과 응답값을 먼저 복사합니다.
        past_messages = db.scalars(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id, ChatMessage.id != user_message_id)
            .order_by(ChatMessage.created_at)
        ).all()
        # 목록 안의 for는 여러 행을 한 번에 새 목록으로 바꾸는 문법입니다. ORM 객체 대신 역할/본문만 미리
        # 복사해 AI에 전달합니다.
        history_context = [{"role": m.role, "content": m.content, "status": m.status} for m in past_messages]
        # 트랜잭션(함께 성공/실패해야 할 저장 묶음)을 확정합니다. 첫 채팅에서는 세션과 질문을 같이 저장한 뒤
        # AI를 호출합니다.
        db.commit()
    except SQLAlchemyError as error:
        # 실패한 저장 묶음을 되돌립니다. 새 대화만 남고 질문이 없는 불완전한 초기 저장을 막습니다.
        db.rollback()
        # DB 예외 원문은 SQL과 입력값을 포함할 수 있어 예외 종류만 기록합니다.
        log_db_save_failed(
            user_id=user_id, error=type(error).__name__,
            request_id=request_id, entity=save_entity
        )
        raise HTTPException(status_code=500, detail=DB_SAVE_ERROR_DETAIL) from None

    if new_session:
        log_db_save_success(
            user_id=user_id, session_id=session_id,
            request_id=request_id, entity="session"
        )
    log_db_save_success(
        user_id=user_id, chat_id=user_message_id, session_id=session_id,
        request_id=request_id, entity="user_message"
    )

    # 4. 답변 사건을 조금씩 만들어 보내는 생성기를 정의합니다.
    async def sse_event_stream():
        """meta는 대화 정보, 일반 data는 답변 조각, done은 저장 완료 상태를 보냅니다.
        json.dumps는 Python 데이터를 전송할 문자열로 바꿉니다.
        """
        # 스트림 내부의 답변 저장에는 별도 DB 작업 공간을 사용합니다.
        # 긴 응답 스트림의 답변 저장에는 별도 DB 작업 공간을 씁니다. 앞에서 확정한 질문은 AI 실패 때문에
        # 지워지지 않습니다.
        gen_db = SessionLocal()
        full_assistant_reply = ""
        latency_ms = 0
        error_type = None
        search_info, search_suggestions = None, ""

        try:
            # 대화 연결용 meta 사건을 먼저 보냅니다.
            init_event = {
                "session_id": session_id,
                "session_title": session_title,
                "user_message_id": user_message_id,
                "request_id": request_id
            }
            # SSE는 문자열 사건을 빈 줄 두 개로 구분합니다. ensure_ascii=False는 한글을 읽기
            # 쉬운 형태로 보내며 JSON 형식은 유지합니다.
            yield f"event: meta\ndata: {json.dumps(init_event, ensure_ascii=False)}\n\n"

            # AI 서비스에서 받은 답변 조각을 SSE 사건으로 전송합니다.
            # 답변 조각이 올 때마다 기다렸다가 처리합니다. 전체 답변을 기다린 후 한 번에 출력하는 방식이
            # 아닙니다.
            async for chunk in gemini_service.stream_chat_response(
                user_id=user_id,
                request_id=request_id,
                history=history_context,
                current_question=payload.message,
                **({"model_name": payload.model} if payload.model is not None else {}),
                **({"search_enabled": payload.search_enabled} if payload.search_enabled is not None else {}),
                **({"temperature": payload.temperature} if payload.temperature is not None else {}),
                **({"thinking_level": payload.thinking_level} if payload.thinking_level is not None else {})
            ):
                if not chunk["done"]:
                    # SSE는 문자열 사건을 빈 줄 두 개로 구분합니다. ensure_ascii=False는
                    # 한글을 읽기 쉬운 형태로 보내며 JSON 형식은 유지합니다.
                    yield f"data: {json.dumps({'text': chunk['text']}, ensure_ascii=False)}\n\n"
                else:
                    full_assistant_reply = chunk.get("full_text", "")
                    latency_ms = chunk.get("latency_ms", 0)
                    error_type = chunk.get("error")
                    search_info = chunk.get("search")
                    search_suggestions = chunk.get("search_suggestions", "")

            # 5. AI 전체 답변과 상태·시간을 DB에 저장합니다.
            msg_status = "error" if error_type else "success"
            assistant_msg = ChatMessage(
                session_id=session_id,
                user_id=user_id,
                role="assistant",
                content=full_assistant_reply or ("Error: " + (error_type or "Unknown")),
                latency_ms=latency_ms,
                status=msg_status,
                error_message=error_type
            )
            gen_db.add(assistant_msg)
            # AI가 끝난 뒤 답변을 별도 단계로 확정합니다. 오류 답변도 상태와 오류 종류를 함께 남깁니다.
            gen_db.commit()
            gen_db.refresh(assistant_msg)

            log_db_save_success(
                user_id=user_id, chat_id=assistant_msg.id, session_id=session_id,
                request_id=request_id, entity="assistant_message"
            )

            # DB 답변 저장 후 마지막 done 사건을 보냅니다.
            final_data = {
                "done": True,
                "message_id": assistant_msg.id,
                "latency_ms": latency_ms,
                "status": msg_status,
                "error": error_type,
                "search": search_info,
                "search_suggestions": search_suggestions
            }
            # SSE는 문자열 사건을 빈 줄 두 개로 구분합니다. ensure_ascii=False는 한글을 읽기
            # 쉬운 형태로 보내며 JSON 형식은 유지합니다.
            yield f"event: done\ndata: {json.dumps(final_data, ensure_ascii=False)}\n\n"

        # 답변 저장/전송 중 실패한 경우입니다. 이 경로에서 원본 SQL이나 사용자 입력을 로그로 내보내지 않습니다.
        except Exception as e:
            gen_db.rollback()
            log_db_save_failed(
                user_id=user_id, error=type(e).__name__,
                request_id=request_id, entity="assistant_message"
            )
            logger.error("Error in SSE stream loop: %s request_id=%s", type(e).__name__, request_id)
            err_data = {
                "done": True,
                "error": "SERVER_ERROR",
                "message": "서버 처리 중 오류가 발생했습니다."
            }
            # SSE는 문자열 사건을 빈 줄 두 개로 구분합니다. ensure_ascii=False는 한글을 읽기
            # 쉬운 형태로 보내며 JSON 형식은 유지합니다.
            yield f"event: error\ndata: {json.dumps(err_data, ensure_ascii=False)}\n\n"
        finally:
            gen_db.close()

    return StreamingResponse(
        sse_event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

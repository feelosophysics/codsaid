# 저장된 질문/답변 목록과 통계를 읽는 API입니다. DB 기록을 읽을 뿐 새로운 AI 질문을 보내지는 않습니다.
# select는 읽을 데이터를 정하고 where는 조건, join은 두 표 연결, limit/offset은 한 페이지의
# 개수/건너뛸 개수입니다.
# 일반 사용자의 조회는 자신의 user_id로 제한합니다. 관리자에게만 다른 사용자 조회를 허용합니다.
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, desc, func, case
from app.core.database import get_db
from app.models.chat import ChatMessage, ChatSession
from app.models.user import User
from app.schemas.chat import ChatLogsResponse, ChatLogItem, ChatStatsResponse
from app.api.deps import get_current_user

router = APIRouter(prefix="/logs", tags=["Logs & Evaluation"])


@router.get("", response_model=ChatLogsResponse)
def get_chat_logs(
    user_id: Optional[int] = Query(None, description="특정 사용자 ID로 필터링"),
    session_id: Optional[int] = Query(None, description="특정 세션 ID로 필터링"),
    status: Optional[str] = Query(None, description="상태(success, error, timeout) 필터링"),
    limit: int = Query(50, ge=1, le=200, description="조회할 개수"),
    offset: int = Query(0, ge=0, description="오프셋"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """현재 사용자 권한과 필터를 적용한 기록 한 페이지를 읽습니다. total은 조건에 맞는 전체 개수이고 items는
    이번 페이지의 내용입니다.
    """
    query = select(ChatMessage, User.username).join(User, ChatMessage.user_id == User.id)
    count_query = select(func.count(ChatMessage.id))

    # 관리자가 아니면 자신의 기록으로만 조회 범위를 제한합니다.
    # 일반 사용자에게 자신의 기록만 보여 주는 핵심 조건입니다. 브라우저에 ID를 숨기는 것과 서버 접근 권한 검사는
    # 별개입니다.
    if not current_user.is_admin:
        query = query.where(ChatMessage.user_id == current_user.id)
        count_query = count_query.where(ChatMessage.user_id == current_user.id)
    elif user_id:
        query = query.where(ChatMessage.user_id == user_id)
        count_query = count_query.where(ChatMessage.user_id == user_id)

    if session_id:
        query = query.where(ChatMessage.session_id == session_id)
        count_query = count_query.where(ChatMessage.session_id == session_id)
    if status:
        query = query.where(ChatMessage.status == status)
        count_query = count_query.where(ChatMessage.status == status)

    # 페이지를 자르기 전 전체 개수를 구합니다. 이번 items 개수와 구분해야 다음 페이지 버튼을 정확히 표시할 수
    # 있습니다.
    total = db.scalar(count_query) or 0
    query = query.order_by(desc(ChatMessage.created_at))

    # 전체 목록 중 이번 페이지 범위만 조회합니다.
    # offset개를 건너뛰고 limit개만 읽습니다. 전체 기록을 매번 내려받지 않아 전송량을 줄입니다.
    results = db.execute(query.offset(offset).limit(limit)).all()
    
    items = []
    for msg, username in results:
        items.append(ChatLogItem(
            id=msg.id,
            user_id=msg.user_id,
            username=username,
            session_id=msg.session_id,
            role=msg.role,
            content=msg.content,
            latency_ms=msg.latency_ms or 0,
            status=msg.status,
            error_message=msg.error_message,
            created_at=msg.created_at
        ))

    return ChatLogsResponse(
        total=total,
        items=items
    )


@router.get("/stats", response_model=ChatStatsResponse)
def get_chat_stats(
    user_id: Optional[int] = Query(None, description="특정 사용자 ID 통계 (관리자 전용)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """질문·답변·대화 수와 성공 답변의 평균시간을 계산합니다. 질문이 없으면 0으로 나누지 않도록 기본 성공률을
    사용합니다.
    """
    # 조건식 A if 조건 else B를 중첩한 표현입니다. 일반 사용자는 자기 번호, 관리자는 지정 사용자 또는 전체
    # 범위를 선택합니다.
    target_user_id = user_id if (current_user.is_admin and user_id) else (None if (current_user.is_admin and not user_id) else current_user.id)

    # 질문/답변 본문을 읽지 않고 DB에서 개수와 평균만 계산합니다.
    successful = (ChatMessage.role == "assistant") & (ChatMessage.status == "success")
    msg_query = select(
        func.count(ChatMessage.id),
        func.count(case((ChatMessage.role == "user", 1))),
        func.count(case((ChatMessage.role == "assistant", 1))),
        func.count(case((successful, 1))),
        func.avg(case((successful & (ChatMessage.latency_ms != 0), ChatMessage.latency_ms))),
    )
    sess_query = select(func.count(ChatSession.id))

    if target_user_id:
        msg_query = msg_query.where(ChatMessage.user_id == target_user_id)
        sess_query = sess_query.where(ChatSession.user_id == target_user_id)

    total_messages, total_questions, total_answers, total_success, latency = db.execute(msg_query).one()
    total_sessions = db.scalar(sess_query) or 0
    avg_latency = int(latency) if latency is not None else 0

    success_rate = (
        round((total_success / total_questions) * 100, 1)
        if total_questions
        else 100.0
    )

    return ChatStatsResponse(
        total_messages=total_messages,
        total_questions=total_questions,
        total_answers=total_answers,
        total_sessions=total_sessions,
        avg_latency_ms=avg_latency,
        success_rate_percent=success_rate
    )


"""짧은 시간에 너무 많은 요청이 오거나 AI 답변이 동시에 몰리는 것을 제한합니다.
최근 60초의 요청 시각을 deque(앞쪽 항목을 빨리 빼는 목록)에 담고, Lock으로 동시에 숫자를 바꾸는 충돌을
막습니다.
이 정보는 서버 프로세스의 메모리에만 있습니다. 재시작하면 초기화되며 여러 worker 사이에는 공유되지 않습니다.
"""
import math
import time
from collections import OrderedDict, deque
from threading import Lock

from fastapi import HTTPException, Request

from app.core.config import get_settings
from app.core.logging import logger


class LimitExceeded(Exception):
    """요청 제한을 초과했을 때 이유와 재시도 대기시간을 전달하는 전용 예외입니다. 이후 HTTP 429로 바뀝니다.
    """
    def __init__(self, reason: str, retry_after: int):
        """거절 이유와 기다릴 시간을 예외 객체에 담습니다. self는 현재 만들어진 객체 자신을 가리킵니다.
        """
        self.reason = reason
        self.retry_after = retry_after


class ChatLease:
    """진행 중인 채팅 한 개가 점유한 슬롯의 표식입니다. owner는 제한기이고 released는 이미 반환했는지
    나타냅니다.
    """
    def __init__(self, owner, user_id: int):
        """슬롯을 관리하는 제한기와 사용자 번호, 아직 반환하지 않았다는 상태를 저장합니다.
        """
        self.owner = owner
        self.user_id = user_id
        self.released = False

    def release(self) -> None:
        """사용을 마친 동시 실행 슬롯을 반환합니다. 이미 반환했는지 확인해 중복 정리로 실행 수가 음수가 되는 것을
        막습니다.
        """
        self.owner.release(self)


class RequestGuard:
    """최근 요청 시각과 동시 채팅 수를 기억합니다. 시계 함수는 시험에서 가짜로 바꿀 수 있도록 매개변수로 받습니다.
    """
    WINDOW_SECONDS = 60

    def __init__(self, clock=time.monotonic, max_buckets: int = 10000):
        """시계·상한·잠금·요청 목록·진행 수를 준비합니다. monotonic 시계는 시스템 시각 보정에 영향을 받지
        않는 시간 간격용 시계입니다.
        """
        self.clock = clock
        self.max_buckets = max_buckets
        self.lock = Lock()
        self.windows = OrderedDict()
        self.active_users = {}
        self.active_total = 0

    def _record(self, limits, now: float) -> None:
        """최근 60초의 요청 예산을 검사하고 허용된 요청만 기록합니다.

        limits는 (식별 키, 최대 횟수)의 목록입니다. 개인/전체 예산을 모두 먼저 확인하고 하나라도 부족하면
        예외를 발생시킵니다. 확인을 끝낸 뒤에만 시각을 기록하므로 거절된 요청이 다른 예산까지 소비하지 않습니다.
        """
        # 현재 시각에서 60초를 뺀 경계입니다. 이 시각 이전의 요청은 이번 예산에 포함하지 않습니다.
        cutoff = now - self.WINDOW_SECONDS
        # 마지막 허용 요청 시각 순서로 보관해 만료된 식별자를 앞쪽부터 제거합니다.
        # 매 요청마다 모든 활성 식별자를 훑지 않아도 오래된 정보를 정리할 수 있습니다.
        # OrderedDict는 순서를 기억하는 사전입니다. 마지막 요청이 오래된 항목부터 빼고 살아 있는 항목에
        # 도달하면 멈춥니다.
        while self.windows:
            key, window = next(iter(self.windows.items()))
            if window[-1] > cutoff:
                break
            self.windows.pop(key)
        missing = 0
        for key, limit in limits:
            window = self.windows.get(key)
            if window is None:
                missing += 1
                continue
            # deque의 왼쪽은 가장 오래된 시각입니다. popleft로 만료된 요청을 제거해 최근 요청만
            # 셉니다.
            while window and window[0] <= cutoff:
                window.popleft()
            if len(window) >= limit:
                raise LimitExceeded("rate_limit", max(1, math.ceil(window[0] + self.WINDOW_SECONDS - now)))
        # 접속자가 계속 바뀌어도 추적 목록이 무한히 커지지 않게 상한을 둡니다. 이 경우도 요청을 거절합니다.
        if len(self.windows) + missing > self.max_buckets:
            raise LimitExceeded("limiter_capacity", self.WINDOW_SECONDS)
        # 모든 조건을 통과한 요청만 개인/전체 예산에 함께 기록합니다.
        # 밑줄은 이 값은 쓰지 않는다는 관례입니다. 모든 조건을 통과한 후 개인/전체 예산에 같은 요청을 함께
        # 기록합니다.
        for key, _ in limits:
            window = self.windows.setdefault(key, deque())
            window.append(now)
            self.windows.move_to_end(key)

    def admit_auth(self, kind: str, client: str, limit: int) -> None:
        """가입/로그인 종류와 접속 IP를 묶어 요청 횟수를 검사합니다. with lock은 검사와 기록을 한 번에 한
        실행 흐름만 하게 합니다.
        """
        # 잠금 구역에서는 한 실행 흐름만 숫자를 검사/변경합니다. 동시에 두 요청이 빈 슬롯 하나를 얻는 충돌을
        # 막습니다.
        with self.lock:
            self._record([((kind, client), limit)], self.clock())

    def admit_chat(self, user_id: int, settings) -> ChatLease:
        """채팅 횟수와 동시 실행 수를 검사하고 진행 중 슬롯을 확보합니다. 반환한 lease는 답변 연결이 끝날 때
        슬롯을 돌려주는 표식입니다.
        """
        # 잠금 구역에서는 한 실행 흐름만 숫자를 검사/변경합니다. 동시에 두 요청이 빈 슬롯 하나를 얻는 충돌을
        # 막습니다.
        with self.lock:
            if self.active_users.get(user_id, 0) >= settings.CHAT_USER_CONCURRENCY:
                raise LimitExceeded("user_concurrency", 1)
            if self.active_total >= settings.CHAT_GLOBAL_CONCURRENCY:
                raise LimitExceeded("global_concurrency", 1)
            self._record([
                (("chat_user", user_id), settings.CHAT_REQUESTS_PER_MINUTE),
                (("chat_global", "all"), settings.CHAT_GLOBAL_REQUESTS_PER_MINUTE),
            ], self.clock())
            self.active_users[user_id] = self.active_users.get(user_id, 0) + 1
            self.active_total += 1
            return ChatLease(self, user_id)

    def release(self, lease: ChatLease) -> None:
        """사용을 마친 동시 실행 슬롯을 반환합니다. 이미 반환했는지 확인해 중복 정리로 실행 수가 음수가 되는 것을
        막습니다.
        """
        # 잠금 구역에서는 한 실행 흐름만 숫자를 검사/변경합니다. 동시에 두 요청이 빈 슬롯 하나를 얻는 충돌을
        # 막습니다.
        with self.lock:
            # 정리가 여러 경로에서 두 번 불려도 한 번만 반환합니다. 이 동작을 멱등성이라고 부릅니다.
            if lease.released:
                return
            lease.released = True
            self.active_total -= 1
            remaining = self.active_users[lease.user_id] - 1
            if remaining:
                self.active_users[lease.user_id] = remaining
            else:
                self.active_users.pop(lease.user_id)


guard = RequestGuard()


def _reject(request: Request, error: LimitExceeded, kind: str) -> None:
    """제한 초과를 HTTP 429로 알려 줍니다. Retry-After 헤더는 다시 시도하기까지 기다릴 초 단위
    시간입니다.
    """
    request_id = getattr(request.state, "request_id", "req-unknown")
    logger.warning("request_rejected request_id=%s kind=%s reason=%s", request_id, kind, error.reason)
    message = (
        "답변 처리 중입니다. 잠시 후 다시 시도해 주세요."
        if "concurrency" in error.reason else "요청이 너무 많습니다. 잠시 후 다시 시도해 주세요."
    )
    raise HTTPException(status_code=429, detail=message, headers={"Retry-After": str(error.retry_after)})


async def limit_registration(request: Request) -> None:
    """가입 요청의 IP별 제한을 적용합니다. 비밀번호 해시나 사용자 저장보다 먼저 실행되어 과도한 요청의 작업을
    줄입니다.
    """
    client = request.client.host if request.client else "unknown"
    try:
        guard.admit_auth("register", client, get_settings().REGISTER_REQUESTS_PER_MINUTE)
    except LimitExceeded as error:
        _reject(request, error, "register")


async def limit_login(request: Request) -> None:
    """로그인과 비밀번호 변경의 IP별 예산을 공유합니다. 사용자 임의 헤더 대신 서버가 신뢰한 request.client
    주소를 사용합니다.
    """
    # 사용자가 임의로 보낸 전달 헤더 대신 ASGI의 검증된 접속 주소를 사용합니다.
    # Uvicorn은 기존 loopback Caddy만 프록시로 신뢰해야 합니다.
    client = request.client.host if request.client else "unknown"
    try:
        guard.admit_auth("login", client, get_settings().LOGIN_REQUESTS_PER_MINUTE)
    except LimitExceeded as error:
        _reject(request, error, "login")


def admit_chat(request: Request, user_id: int) -> None:
    """채팅 횟수와 동시 실행 수를 검사하고 진행 중 슬롯을 확보합니다. 반환한 lease는 답변 연결이 끝날 때 슬롯을
    돌려주는 표식입니다.
    """
    try:
        # 현재 HTTP 요청에만 슬롯 표식을 저장합니다. 미들웨어가 마지막 전송/취소 뒤 이 표식을 찾아 해제합니다.
        request.state.chat_lease = guard.admit_chat(user_id, get_settings())
    except LimitExceeded as error:
        _reject(request, error, "chat")


class ChatLeaseMiddleware:
    """응답 전송의 시작부터 끝까지 감싸 채팅 슬롯을 유지합니다. 정상 종료뿐 아니라 취소·예외에서도 반환합니다.
    """
    def __init__(self, app):
        """다음 ASGI 앱을 기억해 요청을 넘길 준비를 합니다. ASGI는 비동기 웹 서버와 앱이 데이터를 주고받는
        규칙입니다.
        """
        self.app = app

    async def __call__(self, scope, receive, send):
        """실제 HTTP 응답 전송까지 감싸고 finally에서 슬롯을 해제합니다. SSE는 오래 연결되므로 함수가
        응답 객체를 만든 직후 해제하면 안 됩니다.
        """
        try:
            await self.app(scope, receive, send)
        # AI 실패·DB 실패·연결 취소에도 슬롯을 돌려줘야 다음 채팅이 막히지 않습니다.
        finally:
            if scope["type"] == "http":
                lease = scope.get("state", {}).pop("chat_lease", None)
                if lease is not None:
                    lease.release()

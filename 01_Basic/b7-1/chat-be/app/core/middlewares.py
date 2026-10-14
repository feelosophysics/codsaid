# 미들웨어는 각 API 앞뒤에서 공통 작업을 하는 중간 처리기입니다. 여기서는 요청 식별번호와 처리시간을 붙입니다.
# 한 요청의 로그들을 같은 request_id로 찾을 수 있습니다. 측정시간은 응답 객체를 만들 때까지이며 SSE 전체
# 완료시간과 다릅니다.
import time
import uuid
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.logging import logger


class RequestIDMiddleware(BaseHTTPMiddleware):
    """요청마다 공통 식별번호와 시간 헤더를 붙이는 처리기를 정의합니다. 클래스로 한 객체의 동작과 상태를 묶습니다.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """요청에 번호를 붙이고 다음 처리기를 기다린 뒤 응답 헤더에 번호·측정시간을 넣습니다. call_next는
        다음 API 처리로 넘기는 함수입니다.
        """
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())[:8]
        request.state.request_id = request_id

        start_time = time.perf_counter()
        
        # 다음 처리기에서 실제 요청을 처리하도록 넘깁니다.
        response: Response = await call_next(request)
        
        process_time_ms = int((time.perf_counter() - start_time) * 1000)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time-Ms"] = str(process_time_ms)

        return response

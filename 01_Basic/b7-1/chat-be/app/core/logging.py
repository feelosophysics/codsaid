# 로그는 서버에서 어떤 단계가 성공·실패했는지 남기는 실행 기록입니다. DB의 질문/답변 내용 저장과는 별개입니다.
# logging은 Python 표준 기록 도구이고 handler는 기록을 보낼 곳(콘솔·파일)을 정합니다.
# request_id로 관련 사건을 연결합니다.
# 로그를 쓰는 함수가 비밀을 자동으로 가려 주지는 않습니다. 호출하는 쪽에서 키·비밀번호·원본 예외 등을 넘기지 않아야
# 합니다.
import logging
import sys
import os
from datetime import datetime

# 로그 파일을 만들 수 있도록 logs 폴더를 준비합니다.
os.makedirs("logs", exist_ok=True)

# 로그의 시각·등급·이름·내용 표시를 한 형식으로 맞춥니다.
class CustomLogFormatter(logging.Formatter):
    """로그 한 건의 출력 모양을 정의합니다. logging.Formatter를 상속해 기본 기능을 재사용하고
    format만 보완합니다.
    """
    def format(self, record: logging.LogRecord) -> str:
        """기록 한 건을 시각·등급·이름·내용 순서의 문자열로 만듭니다. f 문자열의 중괄호에는 변수 값이 들어갑니다.
        """
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
        log_level = record.levelname
        msg = super().format(record)
        return f"[{timestamp}] {log_level:<5} {record.name}: {msg}"


def setup_logger(name: str = "chatbot") -> logging.Logger:
    """콘솔과 파일에 같은 형식의 로그를 보내도록 설정합니다. 이미 handler가 있으면 재사용하여 같은 기록이 중복
    출력되지 않게 합니다.
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    # 터미널로 로그를 보내는 출력 경로입니다.
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(CustomLogFormatter())
    logger.addHandler(console_handler)

    # UTF-8 로그 파일로 기록을 보내는 출력 경로입니다.
    file_handler = logging.FileHandler("logs/server.log", encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(CustomLogFormatter())
    logger.addHandler(file_handler)

    logger.propagate = False
    return logger


logger = setup_logger("chatbot.server")


# 요청·AI·DB 사건의 이름과 필드를 맞추는 공통 기록 함수입니다.
def log_request_received(user_id: str | int, path: str, request_id: str = "") -> None:
    """누가 어떤 API를 호출했는지 사건을 남깁니다. 질문 본문 대신 요청 식별번호로 다른 단계의 로그와 연결합니다.
    """
    logger.info(f"request_received user_id={user_id} path={path} request_id={request_id}")


def log_ai_call_start(user_id: str | int, request_id: str, model: str = "") -> None:
    """AI 요청이 시작됐다는 사건을 기록합니다. 모델 이름을 통해 어떤 설정으로 실행했는지 구분합니다.
    """
    logger.info(f"ai_call_start user_id={user_id} request_id={request_id} model={model}")


def log_ai_call_success(request_id: str, latency_ms: int) -> None:
    """AI 처리 완료와 소요시간(ms)을 기록합니다. 1,000ms는 1초입니다. 실제 AI/Demo 여부는 호출 경로를
    함께 봐야 합니다.
    """
    logger.info(f"ai_call_success request_id={request_id} latency_ms={latency_ms}")


def log_ai_call_failed(request_id: str, error: str, latency_ms: int = 0) -> None:
    """AI 실패의 종류와 시간을 기록합니다. 전달받은 error를 그대로 출력하므로 호출하는 쪽이 비밀 없는 값만 넘겨야
    합니다.
    """
    logger.error(f"ai_call_failed request_id={request_id} error=\"{error}\" latency_ms={latency_ms}")


def log_db_save_success(
    user_id: str | int, chat_id: str | int = "", session_id: str | int = "",
    request_id: str = "", entity: str = "message"
) -> None:
    """저장 확정 뒤 성공 사건을 기록합니다. entity가 세션/질문/답변 중 무엇을 저장했는지 구분합니다.
    """
    logger.info(
        f"db_save_success user_id={user_id} chat_id={chat_id} session_id={session_id} "
        f"request_id={request_id} entity={entity}"
    )


def log_db_save_failed(
    user_id: str | int, error: str, request_id: str = "", entity: str = "message"
) -> None:
    """DB 저장 실패를 기록합니다. DB 예외 원문에 SQL·입력값이 있을 수 있으므로 호출하는 쪽에서는 예외의 종류만
    넘깁니다.
    """
    logger.error(
        f"db_save_failed user_id={user_id} error=\"{error}\" "
        f"request_id={request_id} entity={entity}"
    )

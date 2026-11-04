"""이미 실행 중인 서버 PID(운영체제의 프로세스 번호)를 기준으로 보안 최소 조건을 참/거짓만 보고합니다.
서버 앱·DB·AI 서비스는 불러오지 않습니다. /proc는 Linux가 프로세스 정보를 제공하는 경로입니다.
환경값은 내부에서 읽되 키 원문·해시·전체 환경을 출력하지 않습니다. 길이 검사는 키의 랜덤성을 증명하지 않습니다.
"""
import argparse
import json
import os
from pathlib import Path
import sys


def main() -> int:
    """대상 PID의 작업 폴더·환경을 사용해 최소 조건을 확인합니다. 조건 미달은 종료코드 1, 확인 불가는 2, 통과는
    0입니다.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, help="Existing Linux service PID, to reuse its cwd and process environment")
    args = parser.parse_args()
    try:
        repo = Path(__file__).resolve().parents[1]
        if args.pid is not None:
            if args.pid <= 0:
                raise ValueError
            process = Path("/proc") / str(args.pid)
            environment = {}
            # Linux 프로세스 환경은 널 바이트로 구분된 이름=값 목록입니다. 내부에서 해석하되 전체 목록을
            # 출력하지 않습니다.
            for item in (process / "environ").read_bytes().split(b"\0"):
                if b"=" in item:
                    name, value = item.split(b"=", 1)
                    environment[name.decode("utf-8", "surrogateescape")] = value.decode("utf-8", "surrogateescape")
            os.chdir((process / "cwd").resolve(strict=True))
            # 점검 도구 자체의 환경과 섞이지 않게 대상 서비스 환경으로 대체합니다. 실행 중 서비스의 환경을
            # 수정하는 동작은 아닙니다.
            os.environ.clear()
            os.environ.update(environment)
        sys.path.insert(0, str(repo))
        from app.core.config import Settings, DEVELOPMENT_SECRET_KEY

        settings = Settings()
        secret = settings.SECRET_KEY.strip()
        checks = {
            "production_mode": settings.APP_ENV.strip().lower() in {"production", "prod"},
            "key_present": bool(secret),
            "key_not_default": secret != DEVELOPMENT_SECRET_KEY,
            "key_min_length": len(secret.encode("utf-8")) >= 32,
        }
        env_file = Path(".env")
        report = {
            "checks": checks,
            "baseline_passed": all(checks.values()),
            "env_file_present": env_file.is_file(),
            # 0o077은 소유자 외 그룹/다른 사용자 권한 비트를 뜻합니다. 비트 AND(&) 결과가 0이면 이
            # 권한들이 없습니다.
            "env_private_permissions": (env_file.stat().st_mode & 0o077 == 0) if env_file.is_file() else None,
            "aws_static_credentials_in_process": any(
                bool(os.environ.get(name)) for name in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN")
            ),
        }
        print(json.dumps(report))
        return 0 if report["baseline_passed"] else 1
    # 예외 원문에는 입력 설정이 포함될 수 있어 오류의 클래스 이름만 반환합니다. 실제 비밀값은 출력하지 않습니다.
    except Exception as error:
        # 설정 오류의 원문에는 비밀 입력이 섞일 수 있어 예외 종류만 출력합니다.
        # 예외 추적·전체 환경·키의 원문이나 지문은 출력하지 않습니다.
        print(json.dumps({"status": "unverified", "reason": type(error).__name__}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

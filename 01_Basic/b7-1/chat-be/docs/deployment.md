# Vercel + EC2 최소 배포

Vercel은 정적 프론트, EC2 한 대는 FastAPI와 SQLite를 실행합니다. 신규 설치와 코드 업데이트 절차를 구분합니다.

서비스 주소와 주요 설정은 [README](../README.md)를 참고하세요. 기존 서비스 업데이트에서는 .env와 앱 외부의 SQLite 파일을 유지하고 검증한 커밋을 반영한 뒤 서비스를 재시작합니다.

## 1. 계정과 브랜치

- AWS 플랜·크레딧 적용 범위를 한 번 확인합니다. Free plan과 크레딧 만료일은 서로 다릅니다. 배포 전 적용요금과 크레딧 조건을 확인합니다. [AWS FAQ](https://aws.amazon.com/free/free-tier-faqs/).
- GitHub의 main/develop 중 어떤 브랜치든 배포할 수 있습니다. 팀의 기본 기준은 검증된 main입니다.
- 두 레포는 공개된 GitHub 조직 레포입니다. 조직 비공개 레포에 대한 Hobby 제한은 해당하지 않습니다. Vercel 계정은 GitHub로 가입하고 Hobby를 사용하며 연결 권한은 해당 프론트 레포로 제한합니다. [Vercel Git 설명](https://vercel.com/docs/git).

AWS IAM 사용자는 같은 AWS 계정 안의 작업용 신원이며 별도 요금 계정이 아닙니다. EC2 생성에 기술적으로 새 IAM 사용자가 필수인 것은 아니지만 AWS는 root를 일상 작업에 사용하지 않도록 권장합니다. 이번처럼 반복해서 서버를 관리하거나 브라우저 에이전트에 맡긴다면 작업용 로그인 하나를 분리하고 EC2 작업 권한을 부여하는 방법을 권장합니다. CLI 액세스 키·별도 AWS 계정·Organizations를 만들 필요는 없습니다. [AWS root 권장사항](https://docs.aws.amazon.com/IAM/latest/UserGuide/root-user-best-practices.html).

## 2. EC2 한 대

기존 서버가 없다면 EC2 콘솔에서 다음을 선택합니다:

| 설정 | 선택 |
|---|---|
| 리전 | 팀 지정 리전, 미지정이면 서울 ap-northeast-2 |
| OS | Canonical Ubuntu Server 24.04 LTS, x86_64 |
| 유형 / 개수 | 크레딧 조건에 맞는 작은 x86 유형, 예: t3.micro 한 대 |
| CPU 크레딧 | t3이면 Standard |
| 디스크 | gp3 8 GiB, 기본 IOPS/처리량 |
| 네트워크 | 기본 VPC의 퍼블릭 서브넷, 자동 퍼블릭 IPv4 |
| 보안 그룹 | 80/443 외부 허용, SSH 22는 접속 소스로 제한, 8000 외부 비허용 |
| 키 페어 | 개인 PC에 안전하게 보관, Git에 추가하지 않음 |

이 구성에는 별도DB서버나 로드밸런서가 필요하지 않습니다. EC2/디스크/IP는 접속자가 없어도 사용량이 생기며 적용 크레딧을 소비합니다.

EC2 콘솔의 Connect로 접속하거나 개인 PC에서 `ssh -i <키파일> ubuntu@<퍼블릭IP>`로 접속합니다. 콘솔 Instance Connect는 내 PC My IP 규칙과 별개로 해당 리전의 Instance Connect 소스가 허용되어야 합니다. [연결 조건](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-connect-methods.html).

## 3. 백엔드 설치·환경 설정

다음은 **PR 병합·검증 후 main을 배포하는 예시**입니다. 아직 병합 전이고 develop을 시험하기로 했다면 clone의 브랜치만 develop으로 선택합니다. 배포는 로컬 main/develop을 수정하는 작업이 아닙니다.

```bash
sudo apt update
sudo apt install -y git python3-venv python3-pip curl
mkdir -p /home/ubuntu/apps
git clone --branch main --single-branch https://github.com/cocoa7-1/chat-be.git /home/ubuntu/apps/chat-be
cd /home/ubuntu/apps/chat-be
git rev-parse HEAD
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
mkdir -p /home/ubuntu/chat-data
chmod 700 /home/ubuntu/chat-data
cp .env.example .env
chmod 600 .env
nano .env
```

`.env` 설정:

```ini
APP_ENV=production
DEBUG=false
CORS_ALLOWED_ORIGINS=["https://b7-1-chat-fe.vercel.app"]
SECRET_KEY=서버에서_생성한_실제_랜덤키로_교체
ALGORITHM=HS256
DATABASE_URL=sqlite:////home/ubuntu/chat-data/chatbot.db
GEMINI_API_KEY=
GEMINI_MODEL_NAME=gemma-4-26b-a4b-it
AI_TIMEOUT_SECONDS=60
AI_SEARCH_TIMEOUT_SECONDS=90
GEMINI_SEARCH_ENABLED=True
MAX_HISTORY_MESSAGES=10
```

SECRET_KEY는 서버에서 `.venv/bin/python -c 'import secrets; print(secrets.token_hex(32))'`로 생성합니다. 키를 프론트/Vercel/Git에 넣지 않습니다. 처음에는 GEMINI_API_KEY를 비워 Mock로 연결 확인 후 실제 AI 키·모델·요금제를 확인합니다.

`DATABASE_URL`은 앱 폴더 밖의 절대 경로를 사용합니다. 코드 재배포 때 기존 DB를 지우지 않습니다. 테스트나 모델 변경은 운영 DB에서 바로 실행하지 않습니다.

## 4. 계속 실행하기

`sudo nano /etc/systemd/system/chat-be.service`:

```ini
[Unit]
Description=B7-1 FastAPI backend
After=network-online.target
Wants=network-online.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/apps/chat-be
ExecStart=/home/ubuntu/apps/chat-be/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
Restart=on-failure
RestartSec=5
UMask=0077

[Install]
WantedBy=multi-user.target
```

Pydantic이 WorkingDirectory의 .env를 읽습니다. 배포에는 --reload를 사용하지 않습니다.

단일 worker를 유지합니다. 메모리 요청 제한은 여러 worker 사이에서 공유되지 않습니다. 현재 Caddy는 `127.0.0.1:8000`으로 전달하며, Uvicorn은 기본으로 프록시 헤더 처리를 켜고 loopback을 신뢰합니다(버전에 따라 `127.0.0.1` 또는 `127.0.0.1,::1`). `FORWARDED_ALLOW_IPS`로 기본값을 덮어쓰지 않았는지 확인하세요. 명시하려면 같은 ExecStart에 `--proxy-headers --forwarded-allow-ips=127.0.0.1`을 붙입니다. `*`로 모든 클라이언트의 전달 헤더를 신뢰하지 않습니다. [Uvicorn 설정](https://uvicorn.dev/settings/#http).

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now chat-be
curl http://127.0.0.1:8000/
sudo journalctl -u chat-be -n 50 --no-pager
```

## 5. HTTPS와 프론트 연결

Vercel HTTPS 화면에서 HTTP API를 직접 호출하면 혼합 콘텐츠로 차단될 수 있습니다. 팀 도메인 또는 무료 하위 도메인(예: Duck DNS)을 EC2 IP에 연결하고, [공식 Ubuntu 설치 방법](https://caddyserver.com/docs/install)으로 Caddy를 설치합니다.

`/etc/caddy/Caddyfile`을 실제 도메인으로 설정합니다:

```caddyfile
your-backend.example.com {
    reverse_proxy 127.0.0.1:8000
}
```

```bash
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

DNS와 80/443 접근이 준비되면 Caddy가 HTTPS 인증서를 관리합니다. 외부에서 백엔드 HTTPS `/`가 열리는지 확인합니다. SSE는 Caddy의 기본 처리로 전달할 수 있습니다.

프론트 `js/config.js`는 로컬 localhost와 배포 주소를 분리하도록 수정했습니다. `DEPLOYED_API_BASE_URL`에 실제 백엔드 HTTPS 주소를 넣습니다. `/api/v1` 경로는 붙이지 않습니다. 빌드 없는 JS이므로 Vercel 환경 변수만 입력해서는 값이 바뀌지 않습니다.

Vercel: GitHub로 로그인 → Add New / Project → chat-fe Import → Framework Other → 루트 디렉토리 → 빌드 없음, Output 루트 `.` → 배포 브랜치 지정. FE main에 필요한 수정이 아직 없으면 먼저 FE 작업 PR을 반영하거나 검증된 FE develop으로 시험합니다. 공개 사이트의 실제 커밋을 확인합니다.

API CORS는 `CORS_ALLOWED_ORIGINS`의 JSON 배열로 제한합니다. 운영은 실제 Vercel Origin 한 곳, 개발은 `.env.example`의 로컬 Origin을 사용합니다. 미설정 기본값은 `https://b7-1-chat-fe.vercel.app`입니다. Origin에는 경로나 마지막 `/`를 넣지 않습니다. Preview URL은 Production과 다른 출처이며 필요할 때만 명시적으로 추가합니다. 변경 후 백엔드를 재시작합니다.

운영(`APP_ENV=production/prod`) 로그인 쿠키에는 `Secure`가 적용됩니다. 현재 Vercel 프론트는 Bearer 인증을 사용하므로 쿠키 인증 전환이나 `SameSite` 변경은 필요하지 않습니다.

## 6. 완료 확인과 종료

회원가입 → 로그인 → 질문·스트리밍 → 로그 조회를 한 번 실행하고, 재시작 후 데이터가 유지되는지 확인합니다. 평가 전에는 실제 AI 호출·연속 질문 문맥·오류 안내를 별도로 확인합니다. README에 외부 접속 URL·배포 커밋을 적습니다.

재배포는 검증된 커밋을 서버에 반영하고 `sudo systemctl restart chat-be`로 시작합니다. 의존성 변경 시 requirements를 다시 설치하며 DB 모델 변경은 별도 반영 방법을 검토합니다. DB는 그대로 보존합니다.

실습 종료 시 Stop은 EC2 실행을 멈추지만 EBS가 남습니다. Terminate는 루트 디스크 삭제 설정에 따라 DB도 지울 수 있으므로 필요한 데이터를 먼저 보관합니다. 자동 IP는 Stop/Start 후 바뀔 수 있어 DNS 갱신이 필요합니다. 다른 팀 리소스는 삭제하지 않습니다.

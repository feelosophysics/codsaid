# 📋 미션 수행 단계별 가이드

> 이 문서를 따라 순서대로 진행하세요. 각 단계 완료 후 ✅ 체크하며 나아갑니다.

---

## 🖥️ 1단계: UTM으로 Ubuntu 22.04 VM 설치 (Mac에서 진행)

### 1-1. UTM 설치

1. [https://mac.getutm.app/](https://mac.getutm.app/) 접속
2. **Download** 클릭 → `.dmg` 파일 다운로드
3. `.dmg` 열고 Applications에 드래그 설치

> **또는 Homebrew로 설치:**
> ```bash
> brew install --cask utm
> ```

---

### 1-2. Ubuntu 22.04 ISO 다운로드

아래 링크에서 다운로드 (Server 버전 권장 - 용량이 작고 실습 목적에 적합):

```
https://releases.ubuntu.com/22.04/ubuntu-22.04.5-live-server-amd64.iso
```

> ⚠️ **Mac이 Apple Silicon(M1/M2/M3)이면** `amd64`가 아닌 `arm64` ISO를 받아야 합니다:
> ```
> https://cdimage.ubuntu.com/releases/22.04/release/ubuntu-22.04.5-live-server-arm64.iso
> ```
> (agent-app 바이너리는 x86-64이므로 ARM VM에서 실행이 안 됩니다 → 아래 별도 안내 참고)

---

### 1-3. UTM에서 VM 생성

1. UTM 실행 → **"새 가상 머신 만들기"** 클릭
2. **"가상화"** 선택 (에뮬레이션보다 빠름, ARM Mac은 "에뮬레이션" 선택 필요)
3. **Linux** 선택
4. **"Browse"** 클릭 → 다운로드한 ISO 파일 선택
5. 설정값:
   - **메모리**: 2048 MB (2GB)
   - **CPU 코어**: 2
   - **디스크 크기**: 20 GB
6. **"저장"** 클릭

---

### 1-4. Ubuntu 설치

1. VM 실행 → Ubuntu 설치 마법사 진행
2. 설치 옵션:
   - **언어**: English (권장)
   - **네트워크**: 기본값 유지 (DHCP)
   - **설치 타입**: Ubuntu Server (minimized 말고 일반)
   - **OpenSSH 설치**: ✅ **반드시 체크**
   - **추가 패키지**: 선택 안 해도 됨
3. 계정 설정:
   - 이름: 자유
   - 서버 이름: `ubuntu-agent`
   - 사용자명: `ubuntu` (또는 원하는 이름)
   - 비밀번호: 기억하기 쉬운 것
4. 설치 완료 후 **Reboot** → ISO 자동으로 제거됨

---

### 1-5. 기본 패키지 설치 (VM 안에서 실행)

VM 부팅 후 로그인하고 아래를 실행하세요:

```bash
# 패키지 목록 업데이트
sudo apt update && sudo apt upgrade -y

# 필수 패키지 설치
sudo apt install -y ufw openssh-server acl net-tools curl wget vim
```

---

### 1-6. agent-app 파일을 VM으로 전송 (Mac에서 실행)

VM의 IP 주소 확인 (VM 안에서):
```bash
ip addr show | grep "inet "
# 예시 출력: inet 192.168.64.5/24 → IP는 192.168.64.5
```

Mac 터미널에서 전송:
```bash
# Mac에서 실행 (VM_IP는 위에서 확인한 IP로 교체)
scp /Users/f22losophysics1091/Desktop/gravity/agent-app ubuntu@<VM_IP>:~/agent-app

# scripts 폴더도 전송
scp -r /Users/f22losophysics1091/Desktop/gravity/scripts ubuntu@<VM_IP>:~/scripts
```

---

## 🔒 2단계: 기본 보안 및 네트워크 설정 (VM 안에서 실행)

### 2-1. SSH 포트 변경 및 Root 로그인 차단

```bash
# sshd 설정 파일 편집
sudo vim /etc/ssh/sshd_config

# 아래 항목을 찾아서 수정 (vim에서 / 로 검색):
# #Port 22  →  Port 20022
# #PermitRootLogin prohibit-password  →  PermitRootLogin no
```

> **vim 기본 사용법:**
> - `i` 키: 입력 모드 진입
> - `/Port` 입력 후 Enter: "Port" 검색
> - 수정 후 `Esc` → `:wq` Enter: 저장 후 종료

또는 sed 명령으로 한 번에:
```bash
sudo sed -i 's/^#\?Port .*/Port 20022/' /etc/ssh/sshd_config
sudo sed -i 's/^#\?PermitRootLogin .*/PermitRootLogin no/' /etc/ssh/sshd_config

# 설정 확인
grep -E "^Port|^PermitRootLogin" /etc/ssh/sshd_config

# SSH 재시작
sudo systemctl restart sshd

# 포트 리슨 확인
ss -tulnp | grep sshd
```

> ⚠️ **주의**: SSH 포트 변경 후에는 접속 시 `-p 20022` 옵션을 붙여야 합니다.
> ```bash
> ssh -p 20022 ubuntu@<VM_IP>
> ```

---

### 2-2. 방화벽 설정 (UFW)

```bash
# UFW 기본 정책 설정
sudo ufw default deny incoming
sudo ufw default allow outgoing

# 필요 포트만 허용
sudo ufw allow 20022/tcp    # SSH
sudo ufw allow 15034/tcp    # App

# UFW 활성화
sudo ufw enable
# "Command may disrupt existing ssh connections. Proceed with operation (y|n)?" → y

# 상태 확인 (📸 캡처)
sudo ufw status verbose
```

---

## 👥 3단계: 계정/그룹/권한 설정 (VM 안에서 실행)

```bash
# ── 그룹 생성 ──────────────────────────────────────────────
sudo groupadd agent-common
sudo groupadd agent-core

# ── 계정 생성 ──────────────────────────────────────────────
sudo useradd -m -s /bin/bash agent-admin
sudo useradd -m -s /bin/bash agent-dev
sudo useradd -m -s /bin/bash agent-test

# 비밀번호 설정 (필요한 경우)
sudo passwd agent-admin
sudo passwd agent-dev
sudo passwd agent-test

# ── 그룹 할당 ──────────────────────────────────────────────
# agent-common: 전원 포함
sudo usermod -aG agent-common agent-admin
sudo usermod -aG agent-common agent-dev
sudo usermod -aG agent-common agent-test

# agent-core: admin, dev만
sudo usermod -aG agent-core agent-admin
sudo usermod -aG agent-core agent-dev

# ── 확인 (📸 캡처) ─────────────────────────────────────────
id agent-admin
id agent-dev
id agent-test
```

```bash
# ── 디렉토리 구조 생성 ─────────────────────────────────────
AGENT_HOME=/home/agent-admin/agent-app

sudo mkdir -p $AGENT_HOME/upload_files
sudo mkdir -p $AGENT_HOME/api_keys
sudo mkdir -p $AGENT_HOME/bin
sudo mkdir -p /var/log/agent-app

# ── 권한 설정 ──────────────────────────────────────────────
# AGENT_HOME
sudo chown agent-admin:agent-core $AGENT_HOME
sudo chmod 750 $AGENT_HOME

# upload_files: agent-common R/W
sudo chown agent-admin:agent-common $AGENT_HOME/upload_files
sudo chmod 2770 $AGENT_HOME/upload_files   # setgid 비트 포함

# api_keys: agent-core ONLY
sudo chown agent-admin:agent-core $AGENT_HOME/api_keys
sudo chmod 2770 $AGENT_HOME/api_keys

# /var/log/agent-app: agent-core ONLY
sudo chown agent-admin:agent-core /var/log/agent-app
sudo chmod 2770 /var/log/agent-app

# ── ACL 설정 (더 세밀한 제어) ──────────────────────────────
sudo setfacl -m g:agent-common:rwx $AGENT_HOME/upload_files
sudo setfacl -d -m g:agent-common:rwx $AGENT_HOME/upload_files   # 기본 ACL

sudo setfacl -m g:agent-core:rwx $AGENT_HOME/api_keys
sudo setfacl -d -m g:agent-core:rwx $AGENT_HOME/api_keys

sudo setfacl -m g:agent-core:rwx /var/log/agent-app
sudo setfacl -d -m g:agent-core:rwx /var/log/agent-app

# ── 확인 (📸 캡처) ─────────────────────────────────────────
ls -la $AGENT_HOME
getfacl $AGENT_HOME/upload_files
getfacl $AGENT_HOME/api_keys
```

---

## 🚀 4단계: 애플리케이션 실행 환경 구성

### 4-1. 환경 변수 설정

```bash
# agent-admin의 .bashrc에 환경 변수 추가
sudo bash -c 'cat >> /home/agent-admin/.bashrc << "ENVEOF"

# ===== Agent App Environment =====
export AGENT_HOME=/home/agent-admin/agent-app
export AGENT_PORT=15034
export AGENT_UPLOAD_DIR=\$AGENT_HOME/upload_files
export AGENT_KEY_PATH=\$AGENT_HOME/api_keys/t_secret.key
export AGENT_LOG_DIR=/var/log/agent-app
# =================================
ENVEOF'

# /etc/environment에도 추가 (cron 실행 시 환경변수 적용을 위해)
sudo bash -c 'cat >> /etc/environment << "ENVEOF"
AGENT_HOME=/home/agent-admin/agent-app
AGENT_PORT=15034
AGENT_UPLOAD_DIR=/home/agent-admin/agent-app/upload_files
AGENT_KEY_PATH=/home/agent-admin/agent-app/api_keys/t_secret.key
AGENT_LOG_DIR=/var/log/agent-app
ENVEOF'
```

### 4-2. 키 파일 생성

```bash
echo "agent_api_key_test" | sudo tee /home/agent-admin/agent-app/api_keys/t_secret.key
sudo chown agent-admin:agent-core /home/agent-admin/agent-app/api_keys/t_secret.key
sudo chmod 640 /home/agent-admin/agent-app/api_keys/t_secret.key
```

### 4-3. agent-app 파일 배치 및 실행

```bash
# Mac에서 전송한 agent-app을 배치
sudo cp ~/agent-app /home/agent-admin/agent-app/agent-app
sudo chown agent-admin:agent-core /home/agent-admin/agent-app/agent-app
sudo chmod 750 /home/agent-admin/agent-app/agent-app

# agent-admin으로 전환 후 앱 실행
sudo -u agent-admin bash -l -c '
  cd $AGENT_HOME
  ./agent-app
'
```

> 💡 Boot Sequence 5단계가 모두 `[OK]`이고 `Agent READY`가 출력되면 성공!
> 📸 이 화면을 캡처하세요.

---

## 📊 5단계: 모니터링 자동화

### 5-1. 스크립트 파일 배치

```bash
# Mac에서 전송한 scripts를 배치
sudo cp ~/scripts/monitor.sh /home/agent-admin/agent-app/bin/monitor.sh
sudo cp ~/scripts/report.sh  /home/agent-admin/agent-app/bin/report.sh
sudo cp ~/scripts/archive.sh /home/agent-admin/agent-app/bin/archive.sh

# 권한 설정 (과제 요구사항)
sudo chown agent-dev:agent-core /home/agent-admin/agent-app/bin/monitor.sh
sudo chown agent-dev:agent-core /home/agent-admin/agent-app/bin/report.sh
sudo chown agent-dev:agent-core /home/agent-admin/agent-app/bin/archive.sh
sudo chmod 750 /home/agent-admin/agent-app/bin/monitor.sh
sudo chmod 750 /home/agent-admin/agent-app/bin/report.sh
sudo chmod 750 /home/agent-admin/agent-app/bin/archive.sh

# 확인 (📸 캡처)
ls -la /home/agent-admin/agent-app/bin/
```

### 5-2. monitor.sh 수동 실행 테스트

```bash
# agent-app이 실행 중인 상태에서 (별도 터미널에서 앱 실행 후):
sudo -u agent-admin bash -l -c '/home/agent-admin/agent-app/bin/monitor.sh'

# 로그 확인
cat /var/log/agent-app/monitor.log
```

> 📸 콘솔 출력과 monitor.log 내용을 캡처하세요.

### 5-3. cron 등록

```bash
# agent-admin의 crontab 편집
sudo -u agent-admin crontab -e
```

편집기가 열리면 아래 줄 추가:
```
* * * * * /bin/bash -l -c '. /etc/environment; /home/agent-admin/agent-app/bin/monitor.sh'
```

```bash
# crontab 등록 확인
sudo -u agent-admin crontab -l

# 1~2분 후 로그 자동 누적 확인 (📸 캡처)
tail -f /var/log/agent-app/monitor.log
```

---

## 📝 산출물 정리

### 체크리스트

| 항목 | 확인 명령어 | 상태 |
|------|------------|------|
| SSH 포트 20022 변경 | `grep "^Port" /etc/ssh/sshd_config` | ⬜ |
| Root 원격 접속 차단 | `grep "^PermitRootLogin" /etc/ssh/sshd_config` | ⬜ |
| SSH 포트 리슨 상태 | `ss -tulnp \| grep sshd` | ⬜ |
| UFW 활성화 | `sudo ufw status verbose` | ⬜ |
| 계정 생성 확인 | `id agent-admin && id agent-dev && id agent-test` | ⬜ |
| 디렉토리/권한 확인 | `ls -la /home/agent-admin/agent-app/` | ⬜ |
| ACL 확인 | `getfacl /home/agent-admin/agent-app/upload_files` | ⬜ |
| Boot Sequence [OK] | 앱 실행 후 직접 확인 | ⬜ |
| 앱 포트 리슨 | `ss -tulnp \| grep 15034` | ⬜ |
| monitor.sh 실행 결과 | 수동 실행 후 출력 확인 | ⬜ |
| monitor.log 누적 | `cat /var/log/agent-app/monitor.log` | ⬜ |
| cron 등록 확인 | `sudo -u agent-admin crontab -l` | ⬜ |
| cron 자동 실행 확인 | 1~2분 후 `tail /var/log/agent-app/monitor.log` | ⬜ |

---

## ⚠️ Apple Silicon(M1/M2/M3) Mac 사용자를 위한 특별 안내

`agent-app`은 **x86-64 바이너리**입니다. Apple Silicon Mac의 UTM은 기본적으로 ARM Ubuntu를 실행하므로, 바이너리 실행이 안 됩니다.

**해결 방법:**
1. UTM에서 **"에뮬레이션"** 방식으로 VM 생성 (속도가 느리지만 x86-64 실행 가능)
2. 또는 ARM Ubuntu 환경에서 `qemu-user-static`으로 x86-64 바이너리 에뮬레이션:
   ```bash
   sudo apt install qemu-user-static binfmt-support
   # 이후 ./agent-app 으로 실행
   ```

---

## 다음 액션

**지금 바로 시작할 것:**
1. UTM 다운로드 및 설치
2. Mac 칩 확인: Apple 메뉴 → "이 Mac에 관하여" → 칩 확인 (Intel / Apple M시리즈)
3. 알려주시면 그에 맞는 ISO 링크 안내드립니다!

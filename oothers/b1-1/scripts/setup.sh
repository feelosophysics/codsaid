#!/bin/bash
# =============================================================================
# setup.sh - 미션 전체 환경 자동 구성 스크립트
# VM 내부에서 sudo로 실행
# =============================================================================
# set -e 제거: ls 권한 오류로 중단되지 않도록

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   Agent Mission - Auto Setup Script      ║"
echo "╚══════════════════════════════════════════╝"
echo ""

AGENT_HOME=/home/agent-admin/agent-app

# ──────────────────────────────────────────────────────────────────────────────
echo "▶ [2단계] SSH 보안 설정..."
# Port 변경
sudo sed -i 's/^#\?\s*Port .*/Port 20022/' /etc/ssh/sshd_config
# Root 로그인 차단
sudo sed -i 's/^#\?\s*PermitRootLogin .*/PermitRootLogin no/' /etc/ssh/sshd_config
# 설정 확인
echo "   SSH 설정 확인:"
grep -E "^Port|^PermitRootLogin" /etc/ssh/sshd_config
# SSH 재시작
sudo systemctl restart ssh 2>/dev/null || sudo systemctl restart sshd 2>/dev/null || true
echo "   SSH 포트 리슨 상태:"
ss -tulnp | grep -E "sshd|ssh" || true
echo "   ✅ SSH 설정 완료"
echo ""

# ──────────────────────────────────────────────────────────────────────────────
echo "▶ [2단계] 방화벽(UFW) 설정..."
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 20022/tcp comment 'SSH'
sudo ufw allow 15034/tcp comment 'APP'
sudo ufw --force enable
echo "   UFW 상태:"
sudo ufw status verbose
echo "   ✅ UFW 설정 완료"
echo ""

# ──────────────────────────────────────────────────────────────────────────────
echo "▶ [3단계] 그룹 생성..."
sudo groupadd -f agent-common
sudo groupadd -f agent-core
echo "   생성된 그룹:"
grep -E "^agent-" /etc/group
echo "   ✅ 그룹 생성 완료"
echo ""

echo "▶ [3단계] 계정 생성..."
# agent-admin
if ! id agent-admin &>/dev/null; then
    sudo useradd -m -s /bin/bash agent-admin
    echo "agent-admin:agent-admin123!" | sudo chpasswd
fi
# agent-dev
if ! id agent-dev &>/dev/null; then
    sudo useradd -m -s /bin/bash agent-dev
    echo "agent-dev:agent-dev123!" | sudo chpasswd
fi
# agent-test
if ! id agent-test &>/dev/null; then
    sudo useradd -m -s /bin/bash agent-test
    echo "agent-test:agent-test123!" | sudo chpasswd
fi

# 그룹 할당 (agent-common: 전원)
sudo usermod -aG agent-common agent-admin
sudo usermod -aG agent-common agent-dev
sudo usermod -aG agent-common agent-test

# 그룹 할당 (agent-core: admin, dev)
sudo usermod -aG agent-core agent-admin
sudo usermod -aG agent-core agent-dev

echo "   계정 확인:"
id agent-admin
id agent-dev
id agent-test
echo "   ✅ 계정/그룹 설정 완료"
echo ""

# ──────────────────────────────────────────────────────────────────────────────
echo "▶ [3단계] 디렉토리 구조 및 권한 설정..."
sudo mkdir -p $AGENT_HOME/upload_files
sudo mkdir -p $AGENT_HOME/api_keys
sudo mkdir -p $AGENT_HOME/bin
sudo mkdir -p /var/log/agent-app

# 소유권/권한
sudo chown agent-admin:agent-core  $AGENT_HOME
sudo chmod 750                     $AGENT_HOME

sudo chown agent-admin:agent-common $AGENT_HOME/upload_files
sudo chmod 2770                     $AGENT_HOME/upload_files

sudo chown agent-admin:agent-core  $AGENT_HOME/api_keys
sudo chmod 2770                    $AGENT_HOME/api_keys

sudo chown agent-admin:agent-core  /var/log/agent-app
sudo chmod 2770                    /var/log/agent-app

# ACL 설정
sudo setfacl -m  g:agent-common:rwx $AGENT_HOME/upload_files
sudo setfacl -d  -m g:agent-common:rwx $AGENT_HOME/upload_files
sudo setfacl -m  g:agent-core:rwx  $AGENT_HOME/api_keys
sudo setfacl -d  -m g:agent-core:rwx  $AGENT_HOME/api_keys
sudo setfacl -m  g:agent-core:rwx  /var/log/agent-app
sudo setfacl -d  -m g:agent-core:rwx  /var/log/agent-app

echo "   디렉토리 확인:"
sudo ls -la $AGENT_HOME
echo "   ✅ 디렉토리/권한/ACL 설정 완료"
echo ""

# ──────────────────────────────────────────────────────────────────────────────
echo "▶ [4단계] 환경 변수 설정..."
# agent-admin .bashrc
sudo bash -c "cat >> /home/agent-admin/.bashrc << 'ENVEOF'

# ===== Agent App Environment =====
export AGENT_HOME=/home/agent-admin/agent-app
export AGENT_PORT=15034
export AGENT_UPLOAD_DIR=\$AGENT_HOME/upload_files
export AGENT_KEY_PATH=\$AGENT_HOME/api_keys/t_secret.key
export AGENT_LOG_DIR=/var/log/agent-app
# =================================
ENVEOF"

# /etc/environment (cron용)
sudo bash -c "cat >> /etc/environment << 'ENVEOF'
AGENT_HOME=/home/agent-admin/agent-app
AGENT_PORT=15034
AGENT_UPLOAD_DIR=/home/agent-admin/agent-app/upload_files
AGENT_KEY_PATH=/home/agent-admin/agent-app/api_keys/t_secret.key
AGENT_LOG_DIR=/var/log/agent-app
ENVEOF"

echo "   환경 변수 확인 (/etc/environment):"
grep AGENT /etc/environment
echo "   ✅ 환경 변수 설정 완료"
echo ""

# ──────────────────────────────────────────────────────────────────────────────
echo "▶ [4단계] 키 파일 생성..."
echo "agent_api_key_test" | sudo tee $AGENT_HOME/api_keys/t_secret.key > /dev/null
sudo chown agent-admin:agent-core  $AGENT_HOME/api_keys/t_secret.key
sudo chmod 640                     $AGENT_HOME/api_keys/t_secret.key
echo "   키 파일 확인:"
sudo ls -la $AGENT_HOME/api_keys/
cat $AGENT_HOME/api_keys/t_secret.key
echo "   ✅ 키 파일 생성 완료"
echo ""

# ──────────────────────────────────────────────────────────────────────────────
echo "▶ [4단계] agent-app 배치..."
sudo cp /tmp/agent-app $AGENT_HOME/agent-app
sudo chown agent-admin:agent-core $AGENT_HOME/agent-app
sudo chmod 750                    $AGENT_HOME/agent-app
echo "   agent-app 확인:"
sudo ls -la $AGENT_HOME/agent-app
file $AGENT_HOME/agent-app
echo "   ✅ agent-app 배치 완료"
echo ""

# ──────────────────────────────────────────────────────────────────────────────
echo "▶ [5단계] 스크립트 배치..."
sudo cp /tmp/scripts/monitor.sh $AGENT_HOME/bin/monitor.sh
sudo cp /tmp/scripts/report.sh  $AGENT_HOME/bin/report.sh
sudo cp /tmp/scripts/archive.sh $AGENT_HOME/bin/archive.sh

sudo chown agent-dev:agent-core $AGENT_HOME/bin/monitor.sh
sudo chown agent-dev:agent-core $AGENT_HOME/bin/report.sh
sudo chown agent-dev:agent-core $AGENT_HOME/bin/archive.sh
sudo chmod 750 $AGENT_HOME/bin/monitor.sh
sudo chmod 750 $AGENT_HOME/bin/report.sh
sudo chmod 750 $AGENT_HOME/bin/archive.sh

echo "   스크립트 확인:"
sudo ls -la $AGENT_HOME/bin/
echo "   ✅ 스크립트 배치 완료"
echo ""

# ──────────────────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   ✅ 자동 설정 완료! 다음 단계 안내     ║"
echo "╚══════════════════════════════════════════╝"
echo ""
echo "【남은 수동 작업】"
echo "1. agent-app 실행:"
echo "   sudo -u agent-admin bash -l -c 'cd \$AGENT_HOME && ./agent-app'"
echo ""
echo "2. monitor.sh 수동 테스트 (agent-app 실행 중인 상태에서):"
echo "   sudo -u agent-admin bash -l -c '$AGENT_HOME/bin/monitor.sh'"
echo ""
echo "3. cron 등록:"
echo "   sudo -u agent-admin crontab -e"
echo "   추가할 내용: * * * * * . /etc/environment; $AGENT_HOME/bin/monitor.sh >> /tmp/cron.log 2>&1"
echo ""

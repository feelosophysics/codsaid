#!/bin/bash
# =============================================================================
# setup.sh - 미션 전체 환경 자동 구성 스크립트
# VM 내부에서 sudo로 실행
# =============================================================================
# set -e 제거: ls 권한 오류로 중단되지 않도록

# 1. 쉬뱅(Shebang, #!)에 대하여
# 다른 특별한 규칙이 또 있나요?
# 스크립트 파일 안에서 첫 번째 줄에 오직 #!로 시작하는 것만이 시스템이 "아, 이 프로그램으로 이 파일을 읽어라!"라고 인식하는 유일한 특수 규칙입니다. 그 외의 모든 줄에서 #은 그냥 무시되는 주석입니다.
# 반드시 첫 번째 줄이어야 하나요? 네! 만약 두 번째 줄에 쉬뱅을 쓰면 리눅스는 그걸 그냥 일반 주석으로 생각하고 무시해 버립니다.
# 쉬뱅의 종류는 여러 가지인가요?
# 매우 많습니다! 어떤 '통역사'를 부를지에 따라 달라집니다.
#!/bin/bash: Bash 쉘로 실행해줘 (가장 흔함)
#!/bin/sh: 가장 기본적인 Shell로 실행해줘 (기능은 적지만 빠름)
#!/usr/bin/python3: 파이썬으로 이 파일을 실행해줘
#!/usr/bin/perl: 펄이라는 언어로 실행해줘

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
sudo ufw default deny incoming # 외부에서 서버로 들어오는 모든 접속을 일단 거부
sudo ufw default allow outgoing
sudo ufw allow 20022/tcp comment 'SSH'
sudo ufw allow 15034/tcp comment 'APP'
sudo ufw --force enable
echo "   UFW 상태:"
sudo ufw status verbose # 현재 방화벽이 잘 켜졌는지, 어떤 포트가 열려 있는지 상세하게(verbose) 출력해서 눈으로 확인시켜 줍니다.
echo "   ✅ UFW 설정 완료"
echo ""

# ──────────────────────────────────────────────────────────────────────────────
echo "▶ [3단계] 그룹 생성..."
sudo groupadd -f agent-common
sudo groupadd -f agent-core
echo "   생성된 그룹:"
grep -E "^agent-" /etc/group # /etc/group은 리눅스의 모든 그룹이 적힌 명부입니다. 여기서 agent-로 시작하는 줄만 찾아서 잘 만들어졌는지 확인시켜 줍니다.
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

# upload_files	agent-common	"공용 게시판" - 개발자, 관리자, 테스터 모두가 파일을 올리고 지울 수 있음.
# api_keys	agent-core	"비밀 금고" - 관리자와 개발자만 볼 수 있음. 테스터는 접근 불가.
# /var/log/...	agent-core	"작업 일지" - 시스템 로그이므로 핵심 인력만 관리함.

# 소유권/권한
sudo chown agent-admin:agent-core  $AGENT_HOME
sudo chmod 750                     $AGENT_HOME

sudo chown agent-admin:agent-common $AGENT_HOME/upload_files
sudo chmod 2770                     $AGENT_HOME/upload_files
# 앞에 붙은 **2**가 아주 똑똑한 녀석입니다. 이를 SetGID라고 부릅니다.
# 의미: "이 폴더 안에서 새로 만들어지는 모든 파일은, 누가 만들었든 상관없이 이 폴더의 그룹(agent-core 등)을 그대로 물려받아라!"라는 뜻입니다.
# 왜 쓰나요? 여러 사람이 협업할 때, 내가 만든 파일을 동료가 못 읽는 불상사를 막기 위해 "우리 팀 공용 폴더 규칙"을 강제로 적용하는 것입니다.
# 770: 주인과 그룹은 모든 권한(rwx)을 갖고, 외부인은 차단합니다.

# 왜 하필 2770의 2인가요? (1, 3, 4도 있나요?)
# 네, 아주 똑똑한 질문입니다! 이 첫 번째 자리는 **'특수 권한'**을 나타내는 스위치입니다.
# 4 (SUID): 누가 실행하든 '주인' 권한으로 실행해라.
# 2 (SGID): 이 폴더에 새로 생기는 파일은 무조건 **'이 폴더의 그룹'**을 물려받아라. (우리가 쓴 것!)
# 1 (Sticky Bit): 누구나 파일을 만들 순 있지만, **'자기가 만든 것'**만 지울 수 있게 해라. (공용 쓰레기통 같은 /tmp 폴더에 씀)
# 3, 5, 6, 7도 있나요? 네! 이 숫자들을 더하면 됩니다. 예를 들어 4(SUID)와 2(SGID)를 동시에 쓰고 싶으면 6을 씁니다. (2 + 4 = 6)


sudo chown agent-admin:agent-core  $AGENT_HOME/api_keys
sudo chmod 2770                    $AGENT_HOME/api_keys

sudo chown agent-admin:agent-core  /var/log/agent-app
sudo chmod 2770                    /var/log/agent-app

# ACL 설정
sudo setfacl -m  g:agent-common:rwx $AGENT_HOME/upload_files
# -m g:agent-common:rwx: agent-common 그룹에게 이 폴더에 대해 읽기(r), 쓰기(w), 실행(x) 권한을 추가로 부여해라.
sudo setfacl -d  -m g:agent-common:rwx $AGENT_HOME/upload_files
# -d (Default - 매우 중요!): **"앞으로 생길 파일들에게도 똑같이 적용해!"**라는 뜻입니다.
# 지금 당장 있는 폴더뿐만 아니라, 나중에 누군가 이 안에 파일을 새로 만들어도 자동으로 이 권한 규칙이 적용되도록 대물림 설정을 하는 것입니다.
sudo setfacl -m  g:agent-core:rwx  $AGENT_HOME/api_keys
sudo setfacl -d  -m g:agent-core:rwx  $AGENT_HOME/api_keys
sudo setfacl -m  g:agent-core:rwx  /var/log/agent-app
sudo setfacl -d  -m g:agent-core:rwx  /var/log/agent-app

# set: 설정하다
# f: file (파일)
# acl: Access Control List (접속 제어 목록)
# **즉, setfacl = "파일의 접속 제어 목록을 설정(Set)하라"**는 뜻입니다.
# 참고로, 설정된 걸 확인하는 명령어는 getfacl입니다. (get = 가져오다/확인하다)

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

# .bashrc와 /etc/environment의 차이
# .bashrc: agent-admin 사용자가 직접 로그인했을 때 읽는 메모장입니다.
# /etc/environment: 시스템 전체가 쓰는 메모장입니다. 나중에 **크론탭(cron)**처럼 사람이 로그인하지 않고 혼자 실행되는 프로그램들이 참고하기 위해 여기에 적어둡니다.
# export : 환경변수를 쉘이 꺼질 때까지 유지한다. -> 그럼 그 경우를 방지하는 법 : bashrc

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
# tee: 파이프(|)로 전달받은 내용을 파일에도 저장하고 화면에도 보여주는 명령어입니다. (T자형 배관처럼 양쪽으로 흘려보낸다고 해서 tee입니다.)
# > /dev/null: "화면에 보여주는 건 필요 없으니까 버려줘!"라는 뜻입니다. (비밀번호가 화면에 노출되지 않게 하려는 배려입니다.)
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
# sudo -u agent-admin: "나는 지금 root(왕)지만, 이 프로그램만큼은 agent-admin이라는 일반 관리자 계정의 이름으로 실행하겠다"는 뜻입니다. (보안상 root로 앱을 돌리는 건 금기이기 때문입니다.)
# bash -l: **로그인 쉘(Login Shell)**을 열라는 뜻입니다. 그래야 아까 우리가 .bashrc에 적어둔 AGENT_HOME 같은 환경 변수를 앱이 읽을 수 있습니다.
# -c '...': 뒤에 따옴표 안에 있는 명령어들을 한꺼번에 실행하라는 뜻입니다.
# cd $AGENT_HOME && ./agent-app: 앱이 있는 폴더로 들어가서(cd), 성공하면(&&) 앱을 실행(./)해라!

echo "2. monitor.sh 수동 테스트 (agent-app 실행 중인 상태에서):"
echo "   sudo -u agent-admin bash -l -c '$AGENT_HOME/bin/monitor.sh'"
# 왜 하나요? 자동화(cron)를 시키기 전에, 우리가 짠 감시 스크립트가 실제로 잘 돌아가는지 운영자가 직접 한 번 확인해보는 과정입니다.
# 체크포인트: 실행했을 때 [OK] 메시지들이 뜨는지, 그리고 /var/log/agent-app/monitor.log 파일에 새로운 한 줄이 추가되었는지 확인해야 합니다.

echo ""
echo "3. cron 등록:"
echo "   sudo -u agent-admin crontab -e"
echo "   추가할 내용: * * * * * . /etc/environment; $AGENT_HOME/bin/monitor.sh >> /tmp/cron.log 2>&1"
echo ""
crontab -e: agent-admin 사용자의 **자동 작업 스케줄러**를 엽니다.
# 추가할 내용 해석:
# * * * * *: "매분 1분마다 무조건 실행해!"
# . /etc/environment;: "환경 변수가 적힌 파일을 먼저 읽어들여서 준비해!"
# $AGENT_HOME/bin/monitor.sh: "준비됐으면 이 감시 스크립트를 실행해!"
# >> /tmp/cron.log 2>&1: "정상 기록도, 에러 비명 소리도 모두 이 로그 파일에 차곡차곡 쌓아줘!"
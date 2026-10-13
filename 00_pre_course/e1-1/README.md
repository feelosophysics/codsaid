# 개발 환경 이해하기

## 1. 프로젝트 개요

본 미션은 개발을 시작하기 위한 기본 환경을 직접 구축하고, 그 과정을 통해 개발 도구의 원리와 구조를 이해하는 것을 목표로 한다.
터미널 기반의 작업 환경 구성, Docker를 활용한 컨테이너 실행 및 관리, Git/GitHub를 통한 버전 관리까지 포함한 전체 개발 흐름을 경험한다.
특히 다음과 같은 핵심 개념을 직접 실습하고 검증한다

- 로컬 개발 환경 구성 및 CLI 활용
- Docker 기반 컨테이너 실행 구조 이해
- 이미지와 컨테이너의 분리 개념
- 포트 매핑을 통한 외부 접근 구조
- 바인드 마운트와 볼륨을 통한 데이터 관리
- Git과 GitHub를 통한 협업 기반 코드 관리

또한 동일한 환경을 반복적으로 재현할 수 있는 개발 방식에 대해 학습한다.

---

## 2. 실행 환경

- OS: macOS 15.7.4
- Shell: zsh 5.9 (x86_64-apple-darwin24.0)
- Docker: OrbStack 내 Docker Engine(version 28.5.2)
- Git: git version 2.53.0

#### 실행 환경을 확인하는 터미널 명령어
```
$ sw_vers
ProductName:		macOS
ProductVersion:		15.7.4
BuildVersion:		24G517

$ echo $SHELL
/bin/zsh

$ zsh --version
zsh 5.9 (x86_64-apple-darwin24.0)

$ docker --version
Docker version 28.5.2, build ecc6942

$ git --version
git version 2.53.0
```

## 수행 항목 체크리스트

- [x] 터미널 기본 조작 및 폴더 구성
- [x] 권한 변경 실습
- [x] Docker 설치 및 점검
- [x] hello-world 및 기본 컨테이너 실행 실습
- [x] Dockerfile 커스텀 이미지 빌드 및 실행
- [x] 포트 매핑 및 브라우저 접속 검증
- [x] 바인드 마운트를 통한 파일 변경 반영 검증
- [x] Docker 볼륨 생성 및 데이터 영속성 검증
- [x] Git 사용자 설정 및 로컬 저장소 초기화
- [x] VSCode와 GitHub 연동 및 푸시 완료
- [x] (보너스) Docker Compose를 활용한 자동화 환경 구성

---

## 3. 터미널 기본 조작 로그

### 현재 위치 및 파일 확인

```zsh
$ pwd # 참고로, 명령어 pwd의 뜻은 print working directory이다.
/Users/user


$ ls -la
total 0
drwxr-xr-x  5 user  staff  160 Apr  1 10:00 .
drwxr-xr-x  3 root  admin   96 Apr  1 09:00 ..

# ls = list (파일 목록 출력)
# -l = long format (권한, 소유자, 크기 등 상세 정보 표시)
# -a = all (숨김 파일 포함)
```

### 디렉토리 생성 및 이동

```zsh
$ mkdir -p workspace/docker-practice # mkdir = make directory / # -p = 경로에 필요한 모든 디렉토리를 한 번에 생성하는 옵션
$ cd workspace/docker-practice # cd = change directory
$ pwd
/Users/user/workspace/docker-practice
```

### 파일 생성 및 복사/이동

```zsh
$ touch test.txt
$ cp test.txt copy.txt # cp = copy
$ mv copy.txt moved.txt # mv = move
$ ls
test.txt moved.txt
```

### 파일 내용 확인

```zsh
$ echo "hello world" > test.txt
$ cat test.txt
hello world
```

### 파일 삭제

```zsh
$ rm moved.txt
$ ls
test.txt
```

---

## 4. 파일 권한 실습

### 권한 확인

```zsh
$ ls -l
-rw-r--r--  1 user  staff  0 Apr  1 10:10 test.txt

# 상세 분석: - / rw- / r-- / r--
# 1. 파일 타입 (-): 일반 파일임을 의미 (d이면 디렉토리)
# 2. 소유자 권한 (rw-): 읽기(r), 쓰기(w) 가능 / 실행(-) 불가 -> (4+2+0 = 6)
# 3. 그룹 권한 (r--): 읽기(r)만 가능 / 쓰기(-), 실행(-) 불가 -> (4+0+0 = 4)
# 4. 기타 사용자 권한 (r--): 읽기(r)만 가능 / 쓰기(-), 실행(-) 불가 -> (4+0+0 = 4)
# 결과적으로 이 파일의 숫지 권한은 644입니다.
```
### 파일 권한 변경하기
```
$ chmod 755 test.txt
# chmod: 'change mode'의 약자로 권한을 변경하는 명령어
# 755의 의미:
#   7 (소유자): rwx (4+2+1) -> 읽고 쓰고 실행하는 모든 권한
#   5 (그룹): r-x (4+0+1) -> 읽고 실행만 가능 (수정 불가)
#   5 (기타): r-x (4+0+1) -> 읽고 실행만 가능 (수정 불가)

$ ls -l
-rwxr-xr-x  1 user  staff  0 Apr  1 10:10 test.txt
# 변경 후: 소유자는 실행(x) 권한이 추가되었고, 그룹/기타 사용자도 실행(x) 권한이 생김
```

### 디렉토리 권한 변경

```zsh
# 1. 디렉토리 생성 및 상태 확인
$ mkdir my_project
$ ls -ld my_project
drwxr-xr-x  2 user  staff  64 Apr  1 10:15 my_project
# 기본적으로 디렉토리는 실행(x) 권한이 있어야 '진입(cd)'이 가능합니다.

# 2. 디렉토리 권한 변경 (소유자 외에는 아무것도 못하게 설정)
$ chmod 700 my_project
# 700: 소유자(rwx), 그룹(---), 기타(---)

# 3. 변경 결과 확인
$ ls -ld my_project
drwx------  2 user  staff  64 Apr  1 10:15 my_project
# 이제 소유자 본인만 이 디렉토리에 들어가거나 파일을 만들 수 있습니다.
```

### ls '-d' 옵션이란?
ls -ld 옵션에서 **d**는 Directory를 의미.
보통 ls 명령어에 디렉토리 이름을 넣으면 그 디렉토리 안에 있는 파일들을 보여주지만, -d 옵션을 붙이면 디렉토리 그 자체의 정보를 보여달라는 뜻.

##### 1. -l만 썼을 때 (디렉토리 내부 확인)
만약 my_folder라는 디렉토리가 있고 그 안에 file1.txt가 있다면:
```Zsh
$ ls -l my_folder
-rw-r--r--  1 user  staff  0 Apr  1 10:10 file1.txt
# 결과: 폴더 '안'에 들어있는 파일의 정보를 보여줍니다.
```

##### 2. -ld를 썼을 때 (디렉토리 자체 확인)
폴더 자체의 권한이나 생성일을 알고 싶을 때 사용.
```Zsh
$ ls -ld my_folder
drwxr-xr-x  2 user  staff  64 Apr  1 10:10 my_folder
# 결과: 'my_folder'라는 폴더 자체의 권한과 정보를 보여줍니다.
```

##### 왜 -ld를 같이 쓰나?
폴더 권한 확인: 내가 이 폴더에 파일을 만들 권한(w)이 있는지, 이 폴더로 들어갈 권한(x)이 있는지 확인하려면 폴더 내부가 아니라 폴더 자체의 권한을 봐야 하기 때문.

요약하자면:
-l: 상세 정보를 보여줘 (Long format)
-d: 안을 들여다보지 말고, 그 디렉토리(Directory) 자체를 보여줘

그래서 -ld는 **"디렉토리 자체의 상세 정보를 보여줘"**라는 뜻!

---

## 5. Docker 설치 및 점검

```zsh
$ docker --version
Docker version 28.5.2, build ecc6942

$ docker info
Client:
 Version:    28.5.2 # 현재 사용 중인 Docker CLI 버전
 Context:    orbstack # 어떤 Docker 환경에 연결되어 있는지(OrbStack)
 Debug Mode: false # 디버깅 로그 출력 여부 (false -> 일반 모드)
 Plugins:
  buildx: Docker Buildx (Docker Inc.) # Docker 이미지 빌드 확장 도구 / 멀티 플랫폼 빌드 가능(예: amd64, arm64)
    Version:  v0.29.1
    Path:     /Users/f22losophysics1091/.docker/cli-plugins/docker-buildx
  compose: Docker Compose (Docker Inc.) # compose : 여러 컨테이너를 한 번에 관리하는 도구 / 서비스 단위 실행 가능
    Version:  v2.40.3
    Path:     /Users/f22losophysics1091/.docker/cli-plugins/docker-compose

Server: # 실제 컨테이너를 실행하는 핵심 엔진
 Containers: 0 # 이하 현재 컨테이너 상태(하나도 없음.)
  Running: 0
  Paused: 0
  Stopped: 0
 Images: 0 # 다운로드 된 Docker 이미지 없음.
 Server Version: 28.5.2 # Docker 엔진 버전(Client와 동일)
 Storage Driver: overlay2 # 파일 저장 방식(컨테이너 파일 시스템 구현 방식), 여러 레이어를 겹쳐서 사용하는 구조(이미지 + 변경사항)
  Backing Filesystem: btrfs # 실제 디스크 파일 시스템
  Supports d_type: true # 파일 타입 정보 지원 여부 (성능/안정성 관련)
  Using metacopy: false
  Native Overlay Diff: true # 레이어 간 변경사항 비교 최적화 기능
  userxattr: false
 Logging Driver: json-file # 컨테이너 로그를 JSON 파일로 저장
 Cgroup Driver: cgroupfs
 Cgroup Version: 2
 Plugins: # Docker 기능 플러그인
  Volume: local # 기본 볼륨 저장 방식
  Network: bridge host ipvlan macvlan null overlay # 사용 가능한 네트워크 모드(bridge: 기본 네트워크 (컨테이너 간 통신), host: 호스트와 동일 네트워크, overlay: 여러 서버 간 네트워크 (클러스터), ...)
  Log: awslogs fluentd gcplogs gelf journald json-file local splunk syslog # 다양한 로그 전송 방식 지원
 CDI spec directories:
  /etc/cdi
  /var/run/cdi
 Swarm: inactive # Docker 클러스터 기능(현재 비활성화)
 Runtimes: io.containerd.runc.v2 runc # 실제로 컨테이너를 실행하는 저수준 엔진
 Default Runtime: runc
 Init Binary: docker-init
 containerd version: 1c4457e00facac03ce1d75f7b6777a7a851e5c41 # Docker 내부 구성 요소 버전
 runc version: d842d7719497cc3b774fd71620278ac9e17710e0
 init version: de40ad0
 Security Options: # 보안 설정
  seccomp # 위험한 시스템 호출 제한
   Profile: builtin
  cgroupns # 컨테이너 간 자원 격리
 Kernel Version: 6.17.8-orbstack-00308-g8f9c941121b1
 Operating System: OrbStack
 OSType: linux # macOS 위에서 Linux 커널이 실행됨 (OrbStack 내부)
 Architecture: x86_64 # CPU 아키텍처
 CPUs: 6
 Total Memory: 15.67GiB # 도커에 할당된 자원
 Name: orbstack
 ID: 575f344e-dd26-4577-8090-d43a3600d00d
 Docker Root Dir: /var/lib/docker # 이미지, 컨테이너 데이터 저장 위치
 Debug Mode: false
 Experimental: false
 Insecure Registries: # 인증 없이 접근 가능한 레지스트리
  ::1/128
  127.0.0.0/8
 Live Restore Enabled: false # Docker 재시작 시 컨테이너 유지 여부
 Product License: Community Engine
 Default Address Pools: # Docker가 내부 네트워크 생성할 때 사용하는 IP 범위
   Base: 192.168.97.0/24, Size: 24
   Base: 192.168.107.0/24, Size: 24
   Base: 192.168.117.0/24, Size: 24
   Base: 192.168.147.0/24, Size: 24
   Base: 192.168.148.0/24, Size: 24
   Base: 192.168.155.0/24, Size: 24
   Base: 192.168.156.0/24, Size: 24
   Base: 192.168.158.0/24, Size: 24
   Base: 192.168.163.0/24, Size: 24
   Base: 192.168.164.0/24, Size: 24
   Base: 192.168.165.0/24, Size: 24
   Base: 192.168.166.0/24, Size: 24
   Base: 192.168.167.0/24, Size: 24
   Base: 192.168.171.0/24, Size: 24
   Base: 192.168.172.0/24, Size: 24
   Base: 192.168.181.0/24, Size: 24
   Base: 192.168.183.0/24, Size: 24
   Base: 192.168.186.0/24, Size: 24
   Base: 192.168.207.0/24, Size: 24
   Base: 192.168.214.0/24, Size: 24
   Base: 192.168.215.0/24, Size: 24
   Base: 192.168.216.0/24, Size: 24
   Base: 192.168.223.0/24, Size: 24
   Base: 192.168.227.0/24, Size: 24
   Base: 192.168.228.0/24, Size: 24
   Base: 192.168.229.0/24, Size: 24
   Base: 192.168.237.0/24, Size: 24
   Base: 192.168.239.0/24, Size: 24
   Base: 192.168.242.0/24, Size: 24
   Base: 192.168.247.0/24, Size: 24
   Base: fd07:b51a:cc66:d000::/56, Size: 64

WARNING: DOCKER_INSECURE_NO_IPTABLES_RAW is set # 네트워크 보안 관련 경고, iptables 일부 기능 비활성화 상태
```

---

## 6. Docker 기본 명령어 실행

### 이미지 확인

```zsh
$ docker images # 내 로컬에 저장되어 있는 도커 이미지들의 목록을 보여주는 명령어
REPOSITORY   TAG       IMAGE ID
```

### hello-world 실행

```zsh
$ docker run hello-world
Unable to find image 'hello-world:latest' locally # 해당 Docker image가 없어서 공식 저장소인 인터넷(Docker Hub)에서 다운(pull).
latest: Pulling from library/hello-world
4f55086f7dd0: Pull complete
Digest: sha256:452a468a4bf985040037cb6d5392410206e47db9bf5b7278d281f94d1c2d0931
Status: Downloaded newer image for hello-world:latest # 이미지를 다 내려받았고, 그 이미지를 기반으로 컨테이너를 생성해서Create 실행Run 했음.

Hello from Docker! # 컨테이너 내부에서 실행된 프로그램이 출력한 결과물.
This message shows that your installation appears to be working correctly.

To generate this message, Docker took the following steps:
 1. The Docker client contacted the Docker daemon.
 2. The Docker daemon pulled the "hello-world" image from the Docker Hub.
    (amd64)
 3. The Docker daemon created a new container from that image which runs the
    executable that produces the output you are currently reading.
 4. The Docker daemon streamed that output to the Docker client, which sent it
    to your terminal.

# Docker Client: 우리가 터미널에 입력한 docker run 명령어를 받습니다.
# Docker Daemon: 클라이언트의 명령을 실제로 수행하는 '일꾼'입니다. 이미지가 없으면 Docker Hub에서 가져옵니다.
# Container 생성: 가져온 이미지(붕어빵 틀)를 가지고 컨테이너(붕어빵)를 만듭니다.
# 출력 전달: 컨테이너 안에서 프로그램이 실행되고, 그 결과를 다시 우리 터미널 화면으로 보여줍니다.

To try something more ambitious, you can run an Ubuntu container with:
 $ docker run -it ubuntu bash

Share images, automate workflows, and more with a free Docker ID:
 https://hub.docker.com/

For more examples and ideas, visit:
 https://docs.docker.com/get-started/
```

### Ubuntu 컨테이너 실행 및 접속

```zsh
$ docker run -it ubuntu zsh
Unable to find image 'ubuntu:latest' locally # 로컬에 우분투 이미지가 없어서 Docker Hub에서 다운로드
latest: Pulling from library/ubuntu
817807f3c64e: Pull complete 
Digest: sha256:186072bba1b2f436cbb91ef2567abca677337cfc786c86e107d25b7072feef0c
Status: Downloaded newer image for ubuntu:latest # 최신 이미지를 성공적으로 내려받음.
docker: Error response from daemon: failed to create task for container: failed to create shim task: OCI runtime create failed: runc create failed: unable to start container process: error during container init: exec: "zsh": executable file not found in $PATH # 컨테이너 내부의 환경 변수($PATH)를 다 뒤져봐도 zsh라는 실행 파일을 찾을 수 없다. ubuntu:latest라는 공식 이미지는 아주 가벼운 기본 상태로 제공된다. 이 기본 이미지 안에는 우리가 흔히 사용하는 bash 쉘은 포함되어 있지만, zsh는 기본적으로 설치되어 있지 않기 때문에 실행할 수 없는 것.

Run 'docker run --help' for more information

$ ls
Desktop		Downloads	Movies		OrbStack	Public
Documents	Library		Music		Pictures

$ echo hello
hello # echo 명령어는 터미널에서 **"입력한 문자열이나 변수의 값을 화면에 그대로 출력하라"**는 명령

# echo 활용 예시
# test.txt라는 파일을 만들고, 그 안에 'Hello'라는 내용을 넣음
# $ echo "Hello" > test.txt

# 기존 파일 내용에 이어 붙이기 (>>)
# $ echo "World" >> test.txt
```

컨테이너는 하나의 프로세스를 실행하는 환경이다.
즉, 컨테이너가 종료되는 이유는 "프로세스가 종료되었기 때문"이다.
```
예:
docker run ubuntu → 실행할 프로세스 없음 → 즉시 종료
docker run nginx → nginx 프로세스 실행 → 계속 유지됨
```

---

## 7. 컨테이너 운영 명령

```zsh
$ docker ps # 현재 실행 중인 컨테이너들의 목록만 보여줍니다.
CONTAINER ID   IMAGE     COMMAND   CREATED   STATUS    PORTS     NAMES

$ docker ps -a # 옵션 a(=all) 실행 중인 컨테이너뿐만 아니라, 중지되었거나(Exited) 오류로 종료된 컨테이너까지 포함하여 모든 컨테이너의 목록을 보여줍니다. 내가 이전에 실행했다가 꺼버린 컨테이너들은 어디로 갔을까요? 사라진 게 아니라 도커 내부에 기록으로 남아 있습니다. 이 명령어를 쓰면 그 기록까지 전부 볼 수 있습니다.
CONTAINER ID   IMAGE         COMMAND    CREATED          STATUS                      PORTS     NAMES
eb1998fa94bb   ubuntu        "zsh"      18 minutes ago   Created                               funny_boyd
bf26a4b6348d   hello-world   "/hello"   25 minutes ago   Exited (0) 25 minutes ago             hungry_chatterjee

$ docker logs <container_id> # 특정 컨테이너 안에서 생성된 출력(로그) 기록을 가져옵니다. 컨테이너 안에서 무슨 일이 일어나고 있는지 확인하는 '블랙박스'와 같습니다.
$ docker logs hungry_chatterjee
Hello from Docker!
This message shows that your installation appears to be working correctly.

To generate this message, Docker took the following steps:
 1. The Docker client contacted the Docker daemon.
 2. The Docker daemon pulled the "hello-world" image from the Docker Hub.
    (amd64)
 3. The Docker daemon created a new container from that image which runs the
    executable that produces the output you are currently reading.
 4. The Docker daemon streamed that output to the Docker client, which sent it
    to your terminal.

To try something more ambitious, you can run an Ubuntu container with:
 $ docker run -it ubuntu bash

Share images, automate workflows, and more with a free Docker ID:
 https://hub.docker.com/

For more examples and ideas, visit:
 https://docs.docker.com/get-started/


$ docker stats 실행 중인 모든 컨테이너가 **현재 사용하고 있는 시스템 자원(CPU, 메모리, 네트워크 등)**을 실시간으로 보여줍니다.
Last login: Wed Apr  1 14:49:29 on console
f22losophysics1091@c6r5s4 ~ % docker images
REPOSITORY   TAG       IMAGE ID   CREATED   SIZE
f22losophysics1091@c6r5s4 ~ % docker run hello-world
Unable to find image 'hello-world:latest' locally
latest: Pulling from library/hello-world
4f55086f7dd0: Pull complete 
Digest: sha256:452a468a4bf985040037cb6d5392410206e47db9bf5b7278d281f94d1c2d0931
Status: Downloaded newer image for hello-world:latest

Hello from Docker!
This message shows that your installation appears to be working correctly.

To generate this message, Docker took the following steps:
 1. The Docker client contacted the Docker daemon.
 2. The Docker daemon pulled the "hello-world" image from the Docker Hub.
    (amd64)
 3. The Docker daemon created a new container from that image which runs the
    executable that produces the output you are currently reading.
 4. The Docker daemon streamed that output to the Docker client, which sent it
    to your terminal.

To try something more ambitious, you can run an Ubuntu container with:
 $ docker run -it ubuntu bash

CONTAINER ID   NAME      CPU %     MEM USAGE / LIMIT   MEM %     NET I/O   BLOCK I/O   PIDS 
```

---

## 8. Dockerfile 기반 커스텀 이미지

### Dockerfile
Dockerfile : "컨테이너를 만드는 설명서(레시피)", 어떤 OS를 쓸지, 어떤 프로그램을 설치할지, 어떻게 실행할지를 '위에서 아래로 순서대로 적는 파일'
즉, "환경 + 코드 + 실행방법"을 순서대로 쌓아 만든 이미지 설계서

이미지 : 도커파일로 완성된 실행 파일(읽기 전용)(스냅샷:어느 시점의 상태를 그대로 저장한 것)
컨테이너 : (실제로 실행된 상태)기존 OS 위에서 프로세스만 격리(같은 컴퓨터 안에서 '독립된 앱 박스' 여러 개)
기본 구조 : 레이어 구조. 레이어(스냅샷)가 쌓인 이미지. 그래서 특징은 중간 단계 캐싱됨(속도 빠름), 일부 수정해도 나머지는 재사용.

(1) 시작점
FROM(Docker 예약어이므로 관례적으로 대문자, 소문자도 동작함.) : 베이스 이미지 선택(거의 필수)

(2) 작업 환경
WORKDIR : 작업 디렉토리 설정, 이후 명령어 기준 위치

(3) 파일 넣기
COPY : 그냥 복사(기본) → “내 코드 넣자”
ADD : 압축 해제, URL가능 (잘 안 씀)

(4) 실행(빌드 시)
RUN : 이미지 만들 때 실행 / 패키지 설치, 설정 작업

(5) 실행(컨테이너 시작 시)
CMD : 기본 실행 명령(간단할 때)
ENTRYPOINT : "고정 실행"(강제 실행)

(6) 기타 중요
ENV : 환경 변수 설정
EXPOSE : 포트 선언 안내문(실제로 포트를 열지 않음, "이 컨테이너는 3000 포트를 사용할 예정"이라고 알려주는 메타 정보)

예시
```dockerfile
FROM node:18           # 시작 환경

WORKDIR /app           # 작업 폴더

COPY package.json .    # 의존성 파일 먼저 복사
RUN npm install        # 설치

COPY . .               # 나머지 코드 복사

CMD ["node", "app.js"] # 실행
```
👉 여기서 중요한 설계 포인트:
왜 COPY package.json을 먼저 할까?
→ 캐싱 최적화
→ 코드만 바뀌면 npm install 다시 안 하려고

초보가 꼭 잡아야 할 3가지
1. Dockerfile은 위에서 아래로 실행된다
2. 각 줄은 레이어(스냅샷)로 저장된다
3. RUN vs CMD는 완전히 다른 시점이다

```dockerfile
FROM nginx:alpine

LABEL description="custom nginx for practice"

COPY index.html /usr/share/nginx/html/index.html

EXPOSE 80
```

### Dockerfile 연습 디렉토리 구조

```
project/
 ├── Dockerfile
 └── index.html
```

### index.html

```html
<<h1>Hello Docker</h1>
```

### 이미지 빌드

```zsh
docker build -t my-nginx .
```
-t my-nginx: 생성될 이미지의 이름(태그)을 my-nginx로 지정합니다.
.: 현재 디렉토리(Current Directory)에 있는 Dockerfile을 사용하여 빌드하라는 뜻입니다.

```
[+] Building 2.7s (7/7) FINISHED                                                     docker:orbstack # 전체 빌드 과정이 2.7초 만에 끝났으며, 총 7개의 단계를 모두 성공적으로 완료했다는 뜻입니다.
 => [internal] load build definition from Dockerfile                                            0.1s # 작성하신 Dockerfile 파일을 읽어와서 어떤 작업을 할지 파악하는 단계입니다.
 => => transferring dockerfile: 162B                                                            0.0s
 => [internal] load metadata for docker.io/library/nginx:alpine                                 1.6s # 베이스 이미지인 nginx:alpine에 대한 최신 정보를 도커 허브(Docker Hub)에서 확인하는 과정입니다.
 => [internal] load .dockerignore                                                               0.1s
 => => transferring context: 2B                                                                 0.0s
 => [internal] load build context                                                               0.2s
 => => transferring context: 42B                                                                0.0s
 => CACHED [1/2] FROM docker.io/library/nginx:alpine@sha256:e7257f1ef28ba17cf7c248cb8ccf6f0c6e  0.0s # 이전에 이 이미지를 다운로드한 적이 있어서, 다시 받지 않고 컴퓨터에 저장된 것을 그대로 사용했다는 뜻입니다. (시간 절약)
 => [2/2] COPY index.html /usr/share/nginx/html/index.html                                      0.2s # 가장 중요한 단계입니다! 사용자의 컴퓨터에 있는 index.html 파일을 이미지 내부의 웹 서버 경로로 복사했습니다. 이제 이 이미지를 실행하면 본인이 만든 페이지가 뜨게 됩니다.
 => exporting to image                                                                          0.2s # 빌드된 각 단계(레이어)를 하나로 묶어 최종 이미지 파일로 만드는 과정입니다.
 => => exporting layers                                                                         0.2s
 => => writing image sha256:3635fa6d7c46d765695963621518d46105869cc953f024e095280bbd2008c06a    0.0s # 생성된 이미지에 고유한 주민등록번호 같은 ID(sha256...)를 부여했습니다.
 => => naming to docker.io/library/my-nginx # 이미지의 이름을 처음에 명령하신 대로 my-nginx라고 붙였습니다.
```

##### 이미지 vs 컨테이너 (빌드/실행/변경) 관점에서의 차이

스크린샷
<img width="655" height="244" alt="image" src="https://github.com/user-attachments/assets/d9dfb6a1-49d0-4fa0-8052-89bacd1a5c2d" />

흐름으로 이해
1. Dockerfile → build → 이미지 생성
2. 이미지 → run → 컨테이너 생성
3. 컨테이너 내부 변경 → 일시적 (삭제 시 사라짐)

### 컨테이너 실행

```zsh
$ docker run -d -p 8080:80 --name web1 my-nginx
71f9f8bb3798d856d88d6e9de876ad452b6acb6354da50ae486c451d9ad52ace
```
-d: 백그라운드에서 실행
-p 8080:80: 내 컴퓨터의 8080번 포트를 컨테이너의 80번 포트와 연결

컨테이너는 기본적으로 독립된 네트워크 공간(네임스페이스)을 가진다. 컨테이너 내부 포트는 외부에서 직접 접근할 수 없기 때문에 포트 매핑을 통해 접근 경로를 만들어야 한다.
즉 : 컨테이너 내부의 80 포트는 내 컴퓨터(localhost)의 80 포트와 다르다.
그래서 : -p 8080:80 → 호스트 8080 → 컨테이너 80으로 연결

### 접속 확인

```zsh
$ curl http://localhost:8080
Hello Docker
```
<img width="331" height="170" alt="image" src="https://github.com/user-attachments/assets/cb238540-eb17-4dc8-b7ea-2da745423cd2" />

---

## 9. 포트 매핑 검증

```zsh
$ docker run -d -p 8081:80 --name web2 my-nginx
$ curl http://localhost:8081
Hello Docker
```

포트 매핑을 통해 동일한 컨테이너 이미지를 서로 다른 포트로 접근 가능함을 확인하였다.

##### 호스트 매핑 실패 시 진단 순서
1. 컨테이너 실행 여부와 포트 매핑 여부를 체크
```
docker ps
```
PORTS 컬럼 체크

2. 내부 서버 실행 여부
```
docker logs <container>
```

3. 컨테이너 내부 동작 확인
```
docker exec -it <container> sh
```

4. 포트 충돌 여부
```
lsof -i :8080
# lsof = list open files(현재 열려 있는 파일들 전부 보여줘)
# -i = internet
# 리눅스/유닉스에서는 "네트워크 소켓(포트)도 파일로 취급"
```

순서대로 확인하면 대부분의 문제 해결 가능

* 프로세스 강제 종료
```
$ kill -9 <PID>
```


---

## 10. 바인드 마운트 실습

```zsh
$ docker run -d -p 8081:80 \
  -v $(pwd)/app:/usr/share/nginx/html \
  --name bind-test nginx:alpine
```

*바인드 마운트(-v) 사용 시 주의사항*
형식: [호스트 경로]:[컨테이너 내부 경로]
주의: 콜론(:) 앞뒤에 공백이 있으면 안 됨.
작동 원리: 호스트(내 컴퓨터)의 폴더를 컨테이너 폴더에 '덮어쓰기' 함.
따라서 현재 $(pwd)(내 폴더)에 index.html이 없다면, 컨테이너 안의 기존 index.html도 사라지고 빈 폴더처럼 보일 수 있음. (반드시 index.html이 있는 곳에서 실행할 것!)

수정한 코드가 컨테이너에 즉시 반영되기 때문에 재빌드가 필요 없다. 실시간 동기화(디버깅, 실험 등)가 필요할 때 쓴다.

바인드 마운트는 호스트 환경에 강하게 의존한다.
예:
- 경로가 다르면 동작 안 함
- OS 차이 (Mac / Linux / Windows) 문제 발생 가능
반면 볼륨은:
- Docker가 관리 → 이식성 높음
- 운영 환경에 적합

따라서, 바인드 마운트는 개발 환경에 적합하고, 볼륨은 운영 환경에 적합하다.

### 파일 수정 전

```zsh
$ curl http://localhost:8081
Hello Docker
```

### 파일 수정

```zsh
$ echo "Hello bindmount!" > index.html
```

### 수정 후

```zsh
$ curl http://localhost:8082
Hello bindmount!
```

<img width="445" height="99" alt="image" src="https://github.com/user-attachments/assets/50945a3a-d000-43c8-9c21-cbcda6a5d285" />

---

## 11. Docker 볼륨 영속성 실습 및 검증
개념 이해: "컨테이너는 죽어도 데이터는 살아야 한다"

바인드 마운트 (이전 단계): 내 컴퓨터의 특정 폴더를 컨테이너에 연결 (개발자가 소스 코드 수정할 때 주로 사용)
볼륨 (이번 단계): 도커가 관리하는 별도의 저장 공간을 컨테이너에 연결 (데이터베이스 데이터, 로그 등 중요한 데이터를 보관할 때 사용)
영속성(Persistence): 컨테이너를 삭제(docker rm)해도 도커 볼륨 안에 저장된 데이터는 사라지지 않고 유지되는 성질.

### 1단계: 도커 볼륨 생성
먼저 데이터를 저장할 '가상의 저장 장치'를 만듭니다.
```zsh
$ docker volume create my-data-vol
```

확인: docker volume ls를 입력하면 목록에 my-data-vol이 보입니다.
```
$ docker volume ls
DRIVER    VOLUME NAME
local     my-data-vol
```

### 2단계: 첫 번째 컨테이너에서 데이터 생성
볼륨을 컨테이너의 /app/data 폴더에 연결하고, 그 안에 파일을 하나 만들어 보겠습니다.
```
# ubuntu 이미지를 사용해 컨테이너 실행 (볼륨 연결)
$ docker run -d --name helper-1 -v my-data-vol:/app/data ubuntu sleep infinity

# 컨테이너 내부에 텍스트 파일 생성
$ docker exec helper-1 bash -c "echo 'This data is permanent' > /app/data/hello.txt"
```

*sleep infinity는 무엇인가요?*
도커 컨테이너의 아주 중요한 특징입니다: "컨테이너는 실행 중인 프로세스가 없으면 즉시 종료된다."

Nginx 컨테이너: 웹 서버가 백그라운드에서 계속 돌아가고 있기 때문에 가만히 놔둬도 종료되지 않습니다.

Ubuntu 컨테이너: 기본적으로 실행할 프로그램이 지정되어 있지 않습니다. 그래서 docker run ubuntu만 하면, "안녕? 나 실행됐어. 근데 할 일 없네? 그럼 종료할게!" 하고 0.1초 만에 꺼져버립니다.

sleep infinity: 컨테이너에게 **"영원히(infinity) 잠자고(sleep) 있어라"**라는 명령을 내리는 것입니다.

이렇게 하면 컨테이너가 죽지 않고 계속 살아있게 되어, 우리가 docker exec 명령어를 써서 컨테이너 안으로 들어가 파일을 확인하거나 내용을 수정할 수 있는 시간을 벌어줍니다.

### 3단계: 컨테이너 삭제 (데이터 유실 위기!)
이제 데이터를 만들었던 컨테이너를 강제로 삭제해 봅니다. 일반적인 컨테이너라면 내부 데이터도 다 날아갑니다.
```
$ docker rm -f helper-1
```

### 4단계: 새로운 컨테이너에서 데이터 확인
완전 새로운 컨테이너(helper-2)를 만들어서 아까 그 볼륨을 다시 연결해 봅니다.
```
# 새 컨테이너 실행 (같은 볼륨 연결)
$ docker run -d --name helper-2 -v my-data-vol:/app/data ubuntu sleep infinity

# 데이터가 남아있는지 확인
$ docker exec helper-2 cat /app/data/hello.txt
This data is permanent
```

<img width="631" height="167" alt="image" src="https://github.com/user-attachments/assets/63f2c142-ad8a-4658-ab54-3a36c3cd6d0a" />

<img width="891" height="170" alt="image" src="https://github.com/user-attachments/assets/2b48ddd1-d2cb-4b59-a65f-e684738ca5e3" />

```
$ docker volume inspect my-data-vol
[
    {
        "CreatedAt": "2026-04-03T01:53:38+09:00",
        "Driver": "local",
        "Labels": null,
        "Mountpoint": "/var/lib/docker/volumes/my-data-vol/_data",
        "Name": "my-data-vol",
        "Options": null,
        "Scope": "local"
    }
]
```

### Docker 실행/운영 실습

실습
```
$ docker run -d -p 8080:80 --name test-nginx nginx
```

로그 보기
```
$ docker logs test-nginx
/docker-entrypoint.sh: /docker-entrypoint.d/ is not empty, will attempt to perform configuration
/docker-entrypoint.sh: Looking for shell scripts in /docker-entrypoint.d/
/docker-entrypoint.sh: Launching /docker-entrypoint.d/10-listen-on-ipv6-by-default.sh
10-listen-on-ipv6-by-default.sh: info: Getting the checksum of /etc/nginx/conf.d/default.conf
10-listen-on-ipv6-by-default.sh: info: Enabled listen on IPv6 in /etc/nginx/conf.d/default.conf
/docker-entrypoint.sh: Sourcing /docker-entrypoint.d/15-local-resolvers.envsh
/docker-entrypoint.sh: Launching /docker-entrypoint.d/20-envsubst-on-templates.sh
/docker-entrypoint.sh: Launching /docker-entrypoint.d/30-tune-worker-processes.sh
/docker-entrypoint.sh: Configuration complete; ready for start up
2026/04/02 17:21:20 [notice] 1#1: using the "epoll" event method
2026/04/02 17:21:20 [notice] 1#1: nginx/1.29.7
2026/04/02 17:21:20 [notice] 1#1: built by gcc 15.2.0 (Alpine 15.2.0) 
2026/04/02 17:21:20 [notice] 1#1: OS: Linux 6.17.8-orbstack-00308-g8f9c941121b1
2026/04/02 17:21:20 [notice] 1#1: getrlimit(RLIMIT_NOFILE): 20480:1048576
2026/04/02 17:21:20 [notice] 1#1: start worker processes
2026/04/02 17:21:20 [notice] 1#1: start worker process 30
2026/04/02 17:21:20 [notice] 1#1: start worker process 31
2026/04/02 17:21:20 [notice] 1#1: start worker process 32
2026/04/02 17:21:20 [notice] 1#1: start worker process 33
2026/04/02 17:21:20 [notice] 1#1: start worker process 34
2026/04/02 17:21:20 [notice] 1#1: start worker process 35
```

내부 들어가기
```
docker exec -it test-nginx sh
```
-it 옵션은 "컨테이너 내부로 들어가서 직접 명령어를 입력하고 결과를 실시간으로 보고 싶을 때" 사용하는 필수 세트 옵션.

중지/재시작
```
docker stop test-nginx
docker start test-nginx
```

컨테이너 내부 상태 확인을 위해 docker exec를 사용하였고,
실행 로그 확인을 위해 docker logs를 활용하였다.

## 12. Docker Compose

<img width="253" height="205" alt="image" src="https://github.com/user-attachments/assets/48de3f5c-ab1e-443e-a9fe-33f362e157f0" />

Docker Compose 개념 : 환경(포트, 볼륨, 컨테이너 설정)을 코드로 저장하여 "어디서든 동일한 환경을 재현" 가능하게 한다. 지금까지 하나하나 명령어로 입력했던 docker run 방식이 **"수동 조리"**라면, Docker Compose는 미리 작성된 **"자동 요리 레시피"**

docker-compose.yml
```YAML
version: "3" # Docker Compose 파일의 버전을 의미합니다. 현재는 보통 3.x 버전을 가장 많이 쓰며, 도커 엔진이 이 파일을 어떻게 해석할지 결정하는 기준이 됩니다.
services: # 실행할 컨테이너들 목록 : 여기서부터 "내가 실행할 컨테이너들을 정의하겠다"는 선언입니다. 이 아래에 여러 개의 서비스를 적으면 한 번에 여러 컨테이너를 띄울 수 있습니다.
  web:    # 이 컨테이너의 서비스 이름(컨테이너 별명)입니다. 도커 네트워크 안에서 다른 컨테이너들이 이 이름을 통해 서로를 찾을 수 있습니다. (예: DB 컨테이너가 Web 컨테이너를 찾을 때 web이라는 이름을 사용)
    image: nginx:alpine # 사용할 이미지
    ports: # 포트 매핑 설정, 항상 동일한 포트로 접근 가능할 수 있도록 한다.(환경 재현 가능)
      - "8085:80" # [호스트 포트]:[컨테이너 포트] 호스트 8085 포트를 컨에티너 80 포트와 연결
```

이 YAML 파일은 아래의 명령어를 파일 하나로 정리한 것과 완전히 똑같다.
```
docker run -d -p 8085:80 --name [프로젝트명]_web nginx:alpine
```

(Docker Compose의 장점)
1. 명령어가 길어지지 않음: -p, -v, --name, -e 등 복잡한 옵션을 매번 타이핑할 필요가 없습니다.
2. 문서화: 이 파일만 있으면 어떤 설정을 사용했는지 누구나 알 수 있고, 나중에도 똑같은 환경을 만들 수 있습니다.
3. 협업: 팀원에게 docker-compose.yml 파일만 전달하면, 팀원도 똑같은 환경을 즉시 실행할 수 있습니다.
4. 한꺼번에 실행: 나중에 web뿐만 아니라 db, redis 등 여러 컨테이너를 정의하면 명령어 한 줄로 다 같이 켜고 끌 수 있습니다.

실행
```
$ docker compose up -d
WARN[0000] /Users/f22losophysics1091/Desktop/mis1/docker-compose.yml: the attribute `version` is obsolete, it will be ignored, please remove it to avoid potential confusion 
[+] Running 9/9
 ✔ web Pulled                                                                                                      4.2s 
   ✔ 589002ba0eae Already exists                                                                                   0.0s 
   ✔ 8892f80f46a0 Already exists                                                                                   0.0s 
   ✔ 91d1c9c22f2c Already exists                                                                                   0.0s 
   ✔ cf1159c696ee Already exists                                                                                   0.0s 
   ✔ 3f4ad4352d4f Already exists                                                                                   0.0s 
   ✔ c2bd5ab17727 Already exists                                                                                   0.0s 
   ✔ 4d9d41f3822d Already exists                                                                                   0.0s 
   ✔ 3370263bc02a Already exists                                                                                   0.0s 
[+] Running 2/2
 ✔ Network mis1_default  Created                                                                                   0.1s 
 ✔ Container mis1-web-1  Started                                                                                   0.4s
```

<img width="582" height="261" alt="image" src="https://github.com/user-attachments/assets/89164503-a4b3-4f89-9631-b1c001183891" />

종료
```
$ docker compose down
WARN[0000] /Users/f22losophysics1091/Desktop/mis1/docker-compose.yml: the attribute `version` is obsolete, it will be ignored, please remove it to avoid potential confusion 
[+] Running 2/2
 ✔ Container mis1-web-1  Removed                                                                                   0.3s 
 ✔ Network mis1_default  Removed                                                                                   0.1s
```

docker run 명령을 반복하지 않고,
docker-compose.yml을 통해 실행 환경을 코드로 관리하였다.

---

## 13. Git + GitHub

### Git 설정
Git: 로컬 버전 관리
GitHub: 원격 저장소 (협업 플랫폼)

설정 및 초기화 (내 컴퓨터에 깃 저장소 만들기)
```
git init
# 현재 폴더를 Git 저장소로 초기화합니다.
# 이 폴더에 **'전용 CCTV'**를 설치하는 것과 같습니다. 이제부터 파일이 생기거나 지워지는 것을 Git이 감시하기 시작합니다.

git config --global user.name [이름]
git config --global user.email [이메일]
# 의미: 누가 코드를 짰는지 이름표를 설정하는 것입니다.
# 중요성: 나중에 협업할 때 "이 코드는 누가 수정했지?"를 확인하기 위해 처음에 한 번만 설정하면 됩니다.
```

이름과 이메일이 잘 들어갔다.
```
$ git config --list
credential.helper=osxkeychain
init.defaultbranch=main
user.name=charlie # 이름
user.email=f22losophysics@gmail.com # 이메일
core.repositoryformatversion=0
core.filemode=true
core.bare=false
core.logallrefupdates=true
core.ignorecase=true
core.precomposeunicode=true
remote.origin.url=https://github.com/feelosophysics/guy
remote.origin.fetch=+refs/heads/*:refs/remotes/origin/*
```

현재 상황 확인
```
git status
```
이 명령어를 치면 Git이 현재 폴더를 슥 훑어보고 다음 세 부류로 나누어 리포트를 해줍니다.
 ① "너 이거 새로 만들었니? (Untracked files)" - 보통 빨간색
  의미: 새로 만든 파일인데, 아직 Git이 관리하라고 명령(git add)하지 않은 파일들입니다.
  상태: Git의 감시망 밖에 있는 상태입니다.
 ② "수정은 했는데, 장바구니에 안 담았네? (Changes not staged for commit)" - 보통 빨간색
  의미: 원래 있던 파일인데 내용이 바뀌었습니다. 하지만 아직 저장할 목록(git add)에는 올리지 않은 상태입니다.
 ③ "저장할 준비 완료! (Changes to be committed)" - 보통 초록색
  의미: git add를 마쳐서 **장바구니(Staging Area)**에 예쁘게 담긴 상태입니다.
  상태: 이제 git commit만 하면 사진(버전)이 찍히는 단계입니다.
<img width="552" height="573" alt="image" src="https://github.com/user-attachments/assets/651cfcb7-2e13-4204-8f3a-47b1b7103e94" />

변경사항 저장하기 (스냅샷 찍기)
```
git add .
# 의미: 현재 폴더 내의 모든 변경된 파일들을 **'장바구니(Staging Area)'**에 담습니다.
# 비유: 사진을 찍기 전에 "자, 이 물건들 찍을 거니까 여기 모여!"라고 정렬시키는 단계입니다.
git commit -m "init"
# 의미: 장바구니에 담긴 파일들을 확정 지어 **하나의 버전(Snapshot)**으로 저장합니다.
# -m "init": 이 버전에 대한 짧은 메모입니다.
# 비유: 정렬된 물건들의 셔터를 눌러 사진을 찍고, 사진 뒤에 "첫 번째 기록"이라고 날짜와 이름을 적어 앨범에 끼워 넣는 것과 같습니다.
```

내 컴퓨터(로컬)에 있는 앨범을 인터넷(GitHub)에 백업
```
git remote add origin <repo>
# 의미: 내 컴퓨터의 Git과 인터넷상의 GitHub 저장소(repo_url)를 연결합니다.
# origin: 이 연결 통로의 이름입니다. 관례적으로 '기본 원격 저장소'라는 뜻으로 origin이라고 부릅니다.

git push -u origin main
# 의미: 내 컴퓨터에 저장된 버전들(main 브랜치)을 GitHub(origin)으로 업로드합니다.
# -u: 처음 한 번만 해주면, 다음부터는 그냥 git push만 쳐도 자동으로 이 주소로 올라가게 기억시키는 옵션입니다.
```

<img width="695" height="199" alt="image" src="https://github.com/user-attachments/assets/5b47d791-c9fc-48fb-98ad-0e52b51da19e" />


---

## 14. 트러블슈팅

### 문제 1: git 초기 설정 방법을 찾다가, git config --global user.name을 보고, 실습에서 임의로 해석하여 git config --global charlie라고 적었는데 에러 발생.

* 원인 가설: 내가 학습한 자료가 틀렸나..? 아니면 다른 뭐가 잘못 되었을까?
* 확인: user.name은 "이름 설정을 바꾸겠다"는 일종의 '항목 이름(Key)'이기 때문에 반드시 써야 하는 것이었다.
* 해결: git config --global user.name "charlie"

---

### 문제 2: nginx:alpine에서 bash와 zsh 실행 불가
<img width="853" height="58" alt="image" src="https://github.com/user-attachments/assets/55e22d18-a3a4-4a2d-9b29-c67156d976fe" />

* 원인 가설: exec 명령어가 뭐가 잘 안 맞나?
* 확인: ubuntu:alpine은 경량화된 이미지라, 기본 이미지에 bash와 zsh 없음.
* 해결: 기본적으로 sh 있어서 해결.
<img width="443" height="143" alt="image" src="https://github.com/user-attachments/assets/139bac74-e99b-436d-a941-4cc52d34ad4a" />

---

## 15. 핵심 개념 정리

### 절대 경로 vs 상대 경로

* 절대 경로: `/Users/user/workspace` 항상 동일한 위치, 안정적, 스크립트/운영 환경에 적합
* 상대 경로: `./workspace` 현재 위치 기준, 이동 가능, 개발 환경에 유리

### 파일 권한

* r: read
* w: write
* x: execute

예:

* 755 → rwxr-xr-x
* 644 → rw-r--r--

### Docker 구조

* 이미지: 앱을 실행하는 데 필요한 모든 것(OS, 코드, 설정)을 담은 '압축 파일'이자 '설계도'
* 컨테이너: 이미지를 바탕으로 컴퓨터 메모리 위에서 '실제로 살아 움직이는 상태' (실행체)

### 포트 매핑

* 외부 → 컨테이너 내부 연결
* 예: 8080:80

### 볼륨

* 컨테이너 외부에 데이터 저장
* 삭제 후에도 유지됨

### Git vs GitHub

* Git: 로컬 버전 관리
* GitHub: 원격 저장소 및 협업 플랫폼

---

## 16. 결론

본 미션을 통해 개발 환경 구축부터 컨테이너 기반 실행, 데이터 관리, 협업 도구 활용까지의 전체 흐름을 경험하였다.
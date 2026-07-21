# macOS VS Code 실행 실패 (에러 -54) 진단 및 해결 가이드

이 문서는 macOS 환경에서 VS Code가 정상적으로 켜지지 않고, 실행 시 Launch Services 에러 `-54`가 발생하는 문제의 원인, 재현 방법, 진단 단계 및 해결 절차를 설명합니다.

---

## 1. 문제 상황 및 증상 (Symptom)

- **일반적인 터미널 명령어 실행 시 (`code .`)**: 에러 메시지조차 출력되지 않고 **아무런 반응 없이 즉시 명령줄 프롬프트가 복귀**합니다. 겉보기에는 에러 없이 끝난 것 같지만 실제 VS Code 창은 전혀 열리지 않습니다.
- **수동 실행 혹은 `open` 명령 사용 시 (`open -a "Visual Studio Code"`)**: 터미널에 아래와 같은 Launch Services 관련 에러 메시지가 상세 출력됩니다.
  ```bash
  _LSOpenURLsWithCompletionHandler() failed for the application /Applications/Visual Studio Code.app with error -54.
  ```
- **GUI 실행 시 증상**: Dock 이나 Finder에서 VS Code 아이콘을 클릭해도 아무런 반응이 없으며 무반응 상태가 유지됩니다.

---

## 2. 발생 원인 (Root Cause)

1. **자동 로그아웃/세션 끊김에 의한 좀비 프로세스 생성:** 
   학습용 PC나 공용 PC에서 로그인 후 1시간 이상 비활성 상태로 방치되어 **자동 로그아웃**이 수행될 때, VS Code가 안전하게 닫히지 못하고 백그라운드에서 **좀비(Frozen) 프로세스**로 남게 됩니다.
2. **락(Lock) 파일의 잔존:** 
   종료되지 못한 이전 세션의 프로세스가 `~/Library/Application Support/Code/code.lock` 파일과 통신 소켓 파일(`*.sock`)을 여전히 점유하고(Locked) 있습니다.
3. **Launch Services 충돌 (-54):** 
   다시 로그인한 후 새 VS Code를 실행(혹은 `code .` 입력)하려고 할 때, macOS Launch Services가 이 락 파일과 기존 프로세스를 발견하여 충돌로 인식하고 **에러 -54 (권한/소프트웨어 락 오류)**를 반환합니다.

---

## 3. 문제 재현 방법 (How to Reproduce)

1. VS Code를 정상 실행합니다.
2. 시스템 설정의 화면 보호기 또는 에너지 절약 설정에 의해 **1시간 비활성 자동 로그아웃**을 발생시키거나, 사용자 세션을 강제로 비정상 종료(Disconnect)시킵니다.
3. 다시 로그인한 후, 터미널을 열고 `code .` 명령을 실행합니다.
4. Launch Services가 기존 락 파일 점유를 감지하여 실행이 거부되고 `-54` 에러가 출력되는 것을 확인합니다.

---

## 4. 자가 진단 방법 (Diagnosis Steps)

문제가 발생했을 때 다음 명령어로 상태를 진단할 수 있습니다.

### ① 백그라운드 꼬임 프로세스 조회
현재 본인의 계정($USER)으로 실행 중인 VS Code 프로세스를 조회하기 위해 다음 명령어를 사용합니다. 
(참고: VS Code가 정상 작동 중일 때는 무수히 많은 관련 백그라운드 프로세스가 조회되는 것이 정상입니다. **이 진단은 '화면에 VS Code 창이 전혀 켜져 있지 않음에도 불구하고 백그라운드에 프로세스가 구동 중인지'를 점검하기 위한 목적**입니다.)

```bash
# 본인 계정의 VS Code 메인 프로세스 조회
pgrep -u $USER -lf "Visual Studio Code"

# 또는 꼬이기 쉬운 백그라운드 헬퍼 프로세스 조회
pgrep -u $USER -lf "Code Helper"
```

**[정상 상태(VS Code를 완전히 종료한 상태) 출력 예시]**
VS Code 앱을 정상적으로 끈 상태라면, 터미널에 입력했을 때 아무런 결과도 출력되지 않아야 합니다.

**[좀비/오류 상태 출력 예시]**
사용자 화면에는 VS Code 창이 전혀 켜져 있지 않음에도 불구하고 아래와 같이 여러 프로세스 목록이 조회된다면 프로세스가 좀비 상태로 잔존하고 있는 것입니다.
```text
87061 /Applications/Visual Studio Code.app/Contents/MacOS/Code
87077 /Applications/Visual Studio Code.app/Contents/Frameworks/Code Helper.app/Contents/MacOS/Code Helper ...
87079 /Applications/Visual Studio Code.app/Contents/Frameworks/Code Helper (Renderer).app/Contents/MacOS/Code Helper ...
87109 /Applications/Visual Studio Code.app/Contents/Frameworks/Code Helper.app/Contents/MacOS/Code Helper ...
```

### ② 락 파일 점유 상태 확인
VS Code의 다중 실행을 방지하기 위해 생성되는 락 파일의 존재 여부와 생성 시각을 조회합니다.
```bash
ls -la "$HOME/Library/Application Support/Code/code.lock"
```

**[출력 예시]**
```text
-rw-r--r--  1 f22losophysics1091  f22losophysics1091  5 Jun 25 11:46 /Users/f22losophysics1091/Library/Application Support/Code/code.lock
```
파일 크기가 5바이트로 아주 작게 생성되어 있는 것을 볼 수 있습니다. 이 파일의 내용을 열면 락을 선점하고 있는 프로세스의 ID(PID)가 적혀 있습니다.

```bash
cat "$HOME/Library/Application Support/Code/code.lock"
```

**[출력 예시]**
```text
87061
```
*이 값은 위 ①번 진단에서 조회된 메인 프로세스 ID(`87061`)와 일치하게 되며, 이 좀비 프로세스가 종료되지 않아 락이 계속 묶여 있음을 증명합니다.*

---

## 5. 수동 해결 단계 (Manual Solution)

자동 스크립트 없이 수동으로 해결하고 싶을 때는 아래 3단계를 순서대로 실행하세요.

### 1단계: 좀비 프로세스 강제 종료
```bash
pkill -9 -f "Visual Studio Code"
killall -9 "Code Helper" 2>/dev/null
killall -9 "Visual Studio Code" 2>/dev/null
killall -9 Code 2>/dev/null
```

### 2단계: 락 및 소켓 파일 강제 제거
```bash
rm -f "$HOME/Library/Application Support/Code/code.lock"
rm -f "$HOME/Library/Application Support/Code/"*.sock
```

### 3단계: VS Code 다시 시작
```bash
code .
```

---

## 6. 통합 해결 스크립트 코드 (Integrated Fix Script)

이 문서 하나만 보관하여 간편하게 해결할 수 있도록, 위 3단계를 수행하는 쉘 스크립트 코드 전체를 첨부합니다.

필요할 때 언제든 이 코드를 복사하여 `fix_vscode.sh` 같은 파일로 저장하여 실행하시거나, 터미널에 직접 복사-붙여넣기 하실 수 있습니다.

```bash
#!/bin/bash

echo "=== VS Code 충돌 및 프로세스 꼬임 해결 스크립트 ==="

echo "1. 현재 남아있는 VS Code 프로세스 확인 및 강제 종료..."
pkill -9 -f "Visual Studio Code"
killall -9 "Code Helper" 2>/dev/null
killall -9 "Visual Studio Code" 2>/dev/null
killall -9 Code 2>/dev/null

echo "2. VS Code 락(lock) 및 소켓 파일 제거..."
rm -f "$HOME/Library/Application Support/Code/code.lock"
rm -f "$HOME/Library/Application Support/Code/"*.sock

echo "3. VS Code 정상 실행 시도..."
code .

echo "=== 프로세스 정리 및 재실행 완료! ==="
```

> [!TIP]
> 스크립트 코드를 파일로 만들어 실행할 때 아래 두 가지 방법 중 편한 방식으로 실행할 수 있습니다.
> 
> **방법 A: 권한 설정 없이 bash 셸로 실행 (권장)**
> 실행 권한을 줄 필요 없이 곧바로 실행기를 통해 실행합니다.
> ```bash
> bash fix_vscode.sh
> ```
> 
> **방법 B: 실행 권한(+x)을 부여한 후 직접 실행**
> 파일 자체를 독자적인 실행 파일로 바꾸어 실행합니다.
> ```bash
> chmod +x fix_vscode.sh
> ./fix_vscode.sh
> ```

---

## 7. 자주 묻는 질문 (FAQ) 및 기술적 설명

### Q1. 왜 하필 `-9` 옵션을 사용하여 종료하나요?
- **답변:** 유닉스 계열(macOS 포함) 시스템에서 프로세스 종료 신호 중 `-15` (SIGTERM, 기본값)은 프로세스에게 "정상적으로 리소스를 정리하고 종료하라"고 요청하는 신호입니다.
- 하지만 자동 로그아웃 등으로 인해 이미 먹통(Frozen/좀비)이 된 프로세스들은 이 정상적인 종료 요청 신호를 수신하거나 처리하지 못합니다.
- **`-9` (SIGKILL)** 옵션은 프로세스의 수신 상태와 상관없이 **OS 커널이 대상 프로세스를 즉각 강제 종료**시키기 때문에, 확실한 프로세스 정리를 위해 사용됩니다.

### Q2. 동료의 Mac이나 다른 PC 환경에서도 그대로 쓸 수 있나요? (하드코딩 여부)
- **답변:** **네, 완벽하게 그대로 공유하여 사용하셔도 됩니다.** 본 스크립트와 가이드는 동적으로 환경을 인지하도록 설계되어 있습니다.
  1. **동적 프로세스 매칭 (No PID Hardcoding):** 특정 프로세스 번호(PID)가 아닌, 프로세스 **이름**(`"Visual Studio Code"`, `"Code Helper"`)을 탐색하여 대상을 종료하므로 실행할 때마다 변하는 PID 값과 무관하게 작동합니다.
  2. **환경변수 사용 (No User Hardcoding):** 특정 사용자의 경로가 아닌 **`$HOME`** 환경변수를 사용합니다. 각 사용자의 환경에 따라 `/Users/본인계정` 경로로 자동 치환되므로 다른 동료 PC에서도 오류 없이 실행됩니다.

### Q3. 증상의 디테일이 조금 달라져도 이 스크립트가 유효한가요?
- **답변:** macOS 환경에서 "VS Code가 켜지지 않고 터미널/GUI에서 무반응이거나 에러가 나는 경우"라면 대부분 이 좀비 프로세스와 락 파일 꼬임이 원인이므로 스크립트 수정 없이 해결됩니다. 단, Windows나 Linux 환경은 디렉토리 구조와 프로세스 관리 방식이 다르므로 본 스크립트(macOS 전용)가 호환되지 않습니다. macOS를 사용하는 팀 동료들에게는 이 문서를 안심하고 공유하셔도 좋습니다.

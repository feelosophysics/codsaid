
.venv/bin/pip install pyyaml python-dotenv
.venv/bin/python main.py commit


## 궁금

- 레포 새로, 완성본 말고, 추적용 유틸 따로?

---

## 미션
1. AI API를 호출하는 python 코드를 기반으로, git diff를 입력값으로 받아 커밋 메시지와 PR 설명을 자동 생성하는 CLI 도구를 개발. 단순 호출에 그치지 않고, API 파라미터와 컨텍스트(Commit/PR 양식, 변경 이유, 요구사항)를 설계해 원하는 품질의 결과가 나오도록 프롬프트를 최적화
2. 또한 Git 명령 실행 결과를 프로그램에 연결하고, 생성된 결과물을 실제 커밋/PR 작성 흐름에 적용하며 연동·검증·자동화를 하나의 흐름으로 구현

## 결과물
1. 단일 실행으로 자동화 흐름
2. GitHub repo
3. README.md: 설치 방법, 환경변수(API Key) 설정 방법, 실행 예시, 커밋/PR 생성 결과 예시, 주의사항(또는 운영 관점)이 포함되어 있어 사용자는 문서만 보고 도구를 실행할 수 있다.


---


## 희수님 memo
- REST API 이용해서 통신 -> commit, PR
- subprocess LIB: 파이썬 코드 안에서 운영체제(OS)의 명령어(쉘 명령어)나 다른 외부 프로그램을 직접 실행하고 제어할 수 있게 해주는 표준 모듈
- gem 2.5 flash, max_toeknizer ~500 무료
- diff, commit 후 변경사항 확인(커밋 후? 전 아니고?), AI 응답하기 전에
- 정규표현식 보는 눈 / {20, }: 20자 이상
- get: URL 정보 노출, post: URL 암호화? 좀 안전? / request: 응답 보내기, repost: 응답 받기
- safe mode: 마스킹, 정규표현식
- cadidate: 후보자, 지원자, 수험생
    -  IT 및 소프트웨어 (Release Candidate): 릴리스 후보 (Release Candidate, RC): 소프트웨어 개발 단계 중 하나로, 정식 버전으로 출시되기 전 출시가 가능한 수준으로 완성된 베타 버전

- 평가 항목, 예외처리: API key 누락, 네트워크 오류 등 대처 어떻게?
- 길이/형식을 재생성or후처리 중 선택 이유
- bonus는 토큰 많이 필요하다?---

# 🚀 남은 수동 작업 (Manual Action Guide)

현재 AI 프로그램 코드와 파일 구조는 완벽히 구축해두었습니다. 하지만 저(AI)의 권한이나 환경 제약상 **사용자님께서 직접 마무리해주셔야 하는 작업**이 몇 가지 있습니다. 아래 단계들을 따라 완료해 주세요.

## 1. Gemini API 발급 및 적용 (필수)
이 프로그램이 AI와 통신하려면 API Key가 필요합니다.
1. [Google AI Studio](https://aistudio.google.com/) 에 접속하여 `Create API Key` 버튼을 눌러 발급받습니다. (무료입니다)
2. 터미널을 열고 다음 명령어를 쳐서 컴퓨터에 환경변수로 등록합니다.
   `export AI_API_KEY="방금 발급받은 키 값"`
3. 잘 등록되었는지 `echo $AI_API_KEY` 로 확인해 봅니다.

## 2. Bonus 5.1 (실제 PR 작성하기) 과제 수행 방법
제가 직접 다른 리포지토리에 접근해서 PR을 날려드릴 순 없기 때문에, 이 프로그램으로 결과물을 뽑아 직접 PR을 올리셔야 합니다.
1. 터미널에서 사용자님이 진행하셨던 **예전 미션 폴더(리포지토리)**로 이동합니다. (`cd 예전_미션_폴더`)
2. 코드를 수정하고, `git add` 를 합니다. (변경 사항 만들기)
3. 이 프로그램(`main.py`와 `.ai-gitgen.yml`)을 그 예전 미션 폴더에 복사하거나, 경로를 지정하여 실행합니다.
4. 화면에 출력된 마크다운 결과물을 복사합니다.
5. GitHub 홈페이지로 가서 평소처럼 **New Pull Request** 버튼을 누르고, 복사해둔 내용을 붙여넣기 하여 완료합니다.

---

# 🧠 초심자를 위한 코드 핵심 설명 
나중에 다른 사람에게 설명하실 수 있도록 요약해 드립니다!

- **`subprocess` 란?**
  파이썬 코드 안에서 터미널 명령어(예: `git status`)를 칠 수 있게 해주는 도구입니다. 이 프로그램에서는 `get_git_diff()` 함수 안에 사용되어 변경된 코드를 문자열로 끌어옵니다.
  
- **API 예외처리 (API key 누락, 네트워크 오류)**
  `os.environ.get("AI_API_KEY")`로 키가 있는지 먼저 확인하고, 없으면 프로그램이 강제 종료(`sys.exit(1)`)되도록 막았습니다. 또한 `urllib.request.urlopen` 부분을 `try ~ except` 문으로 감싸서, 인터넷이 끊기거나(URLError) 구글 서버가 뻗었을 때(HTTPError) 에러 원인을 터미널에 예쁘게 띄워주고 종료하도록 "예외처리"를 했습니다.

- **길이/형식 적용을 후처리 대신 '프롬프트'로 선택한 이유**
  생성된 텍스트를 후처리로 자르면(예: 문자열 인덱싱 `text[:50]`) 단어가 반토막 나거나 문맥이 끊기는 등 결과가 어색해집니다. 따라서 차라리 프롬프트(명령어)에 "반드시 50자 이내로 써줘"라고 규칙을 줘서, AI가 애초에 문맥에 맞게 요약해서 만들어내도록 유도하는 것이 자연스럽고 좋은 결과를 냅니다.

- **안전 모드 (Safe Mode)**
  정규표현식(`re` 모듈)을 썼습니다. `re.sub(패턴, 바꿀글자, 원본텍스트)` 함수를 이용해서 `[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}` 처럼 생긴 이메일을 찾아내고 `***@***.***` 로 바꿔치기(마스킹)해서 구글 서버로 정보를 보내기 전에 안전하게 차단했습니다.

---

Ran command: `git push`
Ran command: `git status`
Ran command: `git add .`
Ran command: `git commit -m 'del'`
Ran command: `git push`
Viewed venv_guide.md:1-75
Listed directory check

원인을 찾았습니다! 

터미널에서 `pip` 명령어가 시스템 파이썬 경로인 `$PYTHON_HOME/bin/pip3.12`로 **별칭(alias) 설정**되어 있기 때문에 발생한 문제입니다.

### 🔍 원인 분석
가상환경(`source .venv/bin/activate`)을 활성화하면 터미널의 `PATH` 환경 변수가 가상환경 내부를 가리키도록 변경됩니다. 하지만 **셸 별칭(alias)은 `PATH`보다 우선순위가 높습니다.** 
따라서 `(.venv)` 상태임에도 불구하고 `pip`를 입력했을 때 가상환경 내부의 `pip` 대신 시스템 전역 `pip`가 강제로 실행되었고, 이로 인해 `externally-managed-environment` 에러가 발생한 것입니다.

---

### 🛠️ 해결 방법 (아래 방법 중 하나를 선택해서 실행해 보세요)

#### 방법 1. 가상환경 내부의 pip 직접 실행하기 (가장 확실하고 추천하는 방법)
별칭(alias)을 무시하고 가상환경 폴더 내부에 있는 `pip` 실행 파일을 상대 경로로 직접 지정하여 설치합니다.
```bash
.venv/bin/pip install pyyaml python-dotenv
```

#### 방법 2. 현재 터미널 세션에서 pip 별칭 일시적으로 해제하기
현재 터미널 창에서만 `pip` 별칭 설정을 해제한 후 설치를 진행합니다.
```bash
unalias pip
pip install pyyaml python-dotenv
```
*(이 방법은 현재 열려 있는 터미널 창에서만 유효하며, 새 터미널 창을 열면 다시 별칭이 적용됩니다.)*

#### 방법 3. python 명령어로 실행하기 (python 별칭이 없을 때 가능)
만약 `python` 명령어에는 별칭이 걸려있지 않다면, 아래와 같이 모듈 호출 방식으로 설치할 수도 있습니다.
```bash
python -m pip install pyyaml python-dotenv
```

---

### 작업 완료 후 실행할 때도 주의할 점
프로그램을 실행하실 때도 `python main.py commit`을 입력했을 때 동일하게 시스템 파이썬이 실행된다면, 가상환경 내부의 파이썬을 직접 지정하여 실행해 주세요.
```bash
.venv/bin/python main.py commit
```
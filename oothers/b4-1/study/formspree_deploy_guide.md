# 포트폴리오 외부 연동 및 GitHub Pages 배포 가이드

이 가이드는 포트폴리오 웹사이트를 완성한 후, **Formspree**를 활용한 Contact Form 메일 연동과 **GitHub Pages**를 활용한 웹사이트 무료 호스팅(배포) 단계를 상세히 안내합니다.

---

## 1부: Formspree 이메일 연동 (Contact Form)

사용자가 문의를 제출했을 때 본인의 실제 이메일로 알림을 수신할 수 있도록 외부 서비스인 **Formspree**를 연동합니다. (무료 플랜 기준 **월 50건** 수신 가능)

### Step 1. Formspree 가입 및 로그인
1. 웹 브라우저를 열고 [Formspree 공식 사이트](https://formspree.io)에 접속합니다.
2. 우측 상단의 **[Get Started]** 또는 **[Sign Up]** 버튼을 클릭하여 회원가입을 진행합니다.
   * 포트폴리오 메시지를 직접 받아볼 **실제 사용 중인 이메일 주소**로 가입하는 것을 권장합니다.
3. 가입 후 메일함에 발송된 인증 메일 링크를 클릭하여 인증을 마친 뒤 로그인합니다.

### Step 2. 새 폼(New Form) 생성
1. Formspree 대시보드 화면에서 **[+ New Form]** 버튼을 클릭합니다.
2. 설정 창에서 다음과 같이 입력합니다.
   * **Project Name (프로젝트 이름):** 자유롭게 작성 (예: `My Portfolio`)
   * **Form Name (폼 이름):** 폼의 이름을 작성 (예: `Contact Form`)
   * **Send emails to (수신할 이메일):** 알림을 받아볼 이메일 주소(본인 계정 메일)를 선택합니다.
3. 입력이 끝났다면 **[Create Form]** 버튼을 클릭합니다.

### Step 3. API 엔드포인트 URL 복사
1. 폼 생성이 완료되면 가이드 페이지로 이동합니다.
2. 화면 중앙의 **Integration** 탭 또는 **Endpoint** 항목 아래에 표시된 주소를 복사합니다.
   * 예: `https://formspree.io/f/xanyqwyj` (끝부분의 영어/숫자 혼합 키가 본인의 고유 Form ID입니다.)

### Step 4. HTML 파일에 적용
1. 작업 중인 웹프로젝트의 [portfolio/index.html](file:///Users/f22losophysics1091/Desktop/glad/portfolio/index.html) 파일을 엽니다.
2. 139번째 라인 근처에 있는 `<form>` 태그의 `action` 값을 복사한 주소로 변경하고 저장합니다.
   ```html
   <form id="contact-form" class="contact__form" action="https://formspree.io/f/복사한_고유_ID" method="POST">
   ```

### Step 5. 로컬 테스트
1. Live Server 환경에서 문의 작성 후 **[Send Message]**를 눌러봅니다.
2. 제출 성공 시 피드백 메시지가 나타나며, 본인 이메일로 수신된 알림 메일을 확인해 봅니다. (최초 1회 전송 시 이메일 소유 확인 브라우저 창이 뜰 수 있으며, 동의하고 진행하면 됩니다.)

---

## 2부: GitHub Pages 웹 배포 가이드

완성한 코드를 전 세계 누구나 접속할 수 있도록 GitHub의 무료 정적 웹 호스팅 서비스인 **GitHub Pages**에 올리는 방법입니다.

### Step 1. 최신 코드 GitHub에 커밋 & 푸시 (Commit & Push)
GitHub Pages는 원격 저장소(GitHub)의 코드를 기준으로 배포를 수행하므로, 먼저 로컬의 모든 변경 사항을 업로드해야 합니다.

1. VS Code 터미널을 열고 다음 명령어를 순서대로 입력합니다.
   ```bash
   git add .
   git commit -m "feat: complete portfolio site and integration"
   git push origin main
   ```
   *(저장소 브랜치 명이 `master`인 경우 `git push origin master`로 입력합니다.)*

### Step 2. GitHub 저장소에서 Pages 활성화
1. 본인의 GitHub 원격 저장소 페이지(`https://github.com/feelosophysics/glad`)에 접속합니다.
2. 상단 메뉴 탭 중에서 **[Settings] (설정)** 톱니바퀴 아이콘을 클릭합니다.
3. 왼쪽 사이드바 메뉴 중 **[Code and automation]** 섹션 아래에 있는 **[Pages]** 메뉴를 선택합니다.
4. **Build and deployment** 항목의 설정을 다음과 같이 구성합니다.
   * **Source (소스):** `Deploy from a branch` 선택
   * **Branch (브랜치):** `main` (혹은 배포할 기본 브랜치 명)으로 지정하고 옆의 폴더 경로는 `/ (root)`로 둔 상태에서 **[Save]** 버튼을 누릅니다.

### Step 3. 배포 진행 상황 확인 및 주소 확인
1. **[Save]** 버튼을 누르면 GitHub 내부에서 사이트 빌드 및 배포 작업이 시작됩니다. (약 1~2분 소요)
2. 대략 1분 뒤에 Settings > Pages 화면을 새로고침하면 상단에 다음과 같은 문구가 생겨납니다.
   > 🌐 **"Your site is live at https://feelosophysics.github.io/glad/"**
3. **⚠️ 주의 (중요한 경로 추가):**
   * 현재 프로젝트 폴더 구조상 `index.html`이 루트가 아닌 `portfolio/` 하위 폴더에 들어있습니다.
   * 따라서 GitHub에서 안내해 준 기본 주소 뒤에 반드시 **/portfolio/**를 붙여서 접속해야 합니다.
   * **실제 접속 주소:** `https://feelosophysics.github.io/glad/portfolio/`

### Step 4. 배포 완료 후 마무리 작업
1. 실전 주소(`https://feelosophysics.github.io/glad/portfolio/`)로 스마트폰이나 다른 컴퓨터에서 접속해 봅니다.
2. 모든 인터랙션(다크 모드, 햄버거 메뉴, 스크롤 애니메이션, Projects GitHub API 연동 등)이 정상 작동하는지 점검합니다.
3. 배포가 최종 성공하면 [README.md](file:///Users/f22losophysics1091/Desktop/glad/README.md) 파일의 배포 주소 및 스크린샷 영역을 채워 넣고 마무리합니다.

# 📖 BookLog 개발 완료 워크스루

React 핵심 개념 실습 미션인 **BookLog (독서 기록 SPA 서비스)** 개발을 완료했습니다! 미션의 모든 필수 요구사항과 **보너스 과제 3개(Context 전역 상태, 컴포넌트 최적화, Supabase Auth)**를 모두 성공적으로 구현했습니다.

## ✅ 구현 완료된 내용

### 1. 라우팅 & 기반 구조
- **React Router**를 사용하여 총 9개의 페이지(6개 메인 기능, 인증, 404)를 구성했습니다.
- `App.jsx`에서 `BrowserRouter`와 2개의 `Provider`(Theme, Auth)를 설정하여 전역 상태를 앱 전체에 주입했습니다.

### 2. 재사용 컴포넌트 설계
미션 요구사항(최소 8개)을 초과하는 **12개의 재사용 UI 컴포넌트**를 개발했습니다.
- **범용 UI**: `Button`, `Input`, `Card`, `Modal`
- **상태 처리 UI**: `Loading`, `EmptyState`, `ErrorState` (앱 전체에서 일관된 UX 제공)
- **도메인 UI**: `BookCard`, `BookForm`, `StarRating`
- **레이아웃/특수**: `Navbar`, `ThemeToggle`, `ProtectedRoute`

### 3. 상태 관리와 최적화 흐름
- **Controlled Input**: `BookForm`에서 모든 입력값을 React 상태로 제어하고 유효성 검증을 수행합니다.
- **Custom Hooks**: API 호출 로직을 `useBooks`, `useBookDetail`로 분리하여 컴포넌트를 순수하게 유지했습니다.
- **이벤트 렌더링**: `StarRating` 클릭, `ThemeToggle` 토글 등 상태 변화가 즉시 렌더링으로 이어지는 흐름을 구축했습니다.
- **성능 최적화 (보너스 5.2)**: 
  - `BookCard`에 `React.memo` 적용
  - 검색 필터링에 `useMemo` 적용
  - 이벤트 핸들러에 `useCallback` 적용

### 4. 전역 상태와 인증
- **다크/라이트 모드 (보너스 5.1)**: `ThemeContext`를 만들어 앱 전체의 테마를 관리하고, CSS 변수와 연동하여 부드러운 전환을 구현했습니다.
- **인증 시스템 (보너스 5.3)**: `AuthContext`와 Supabase Auth를 연동하여 로그인/회원가입 및 라우트 보호(`ProtectedRoute`)를 구현했습니다.

### 5. 보안 및 정합성 검토 보완 (추가 완료)
- **보안 패치**: `.gitignore` 파일에 `.env` 및 관련 로컬 환경변수 예외 처리가 누락된 문제를 발견하여 즉각 패치했습니다. Supabase API Key 등 민감한 자격 증명이 노출되지 않도록 조치했습니다.
- **문서-코드 동기화**: `study_guide.md` 내 예시 코드와 실제 비즈니스 로직(AuthContext의 로그인/회원가입 등 API, useBooks의 삭제 및 에러 처리 훅)이 간소화에 머물지 않고 실제 파일 소스 코드와 100% 동기화되도록 보완했습니다.
- **기술 사양 일치**: `package.json`의 실사양(React 19, Vite 8, React Router v7)이 `README.md`에 잘못 명시(React 18, React Router v6)되어 있던 버그를 발견하여 맥락을 완전히 정렬했습니다.

## 🛠️ 남은 작업 (사용자 수동 진행)

제가 접근할 수 없는 **Supabase 클라우드 설정과 배포는 직접 진행해 주셔야 합니다.** 이를 돕기 위해 상세한 가이드 문서를 프로젝트 내에 생성해 두었습니다.

> [!IMPORTANT]
> **순서대로 진행해 주세요!**
> 1. `supabase_setup_guide.md` 파일을 열고, 안내에 따라 Supabase 프로젝트와 테이블(`books`)을 생성하세요.
> 2. 가이드에 따라 발급받은 URL과 Anon Key를 복사합니다.
> 3. 프로젝트 루트에 `.env` 파일을 만들고 키를 붙여넣습니다. (`.env.example` 파일 참고)
> 4. 터미널에서 `npm run dev`를 실행하여 회원가입과 데이터 저장이 잘 되는지 로컬에서 먼저 테스트합니다.
> 5. 코드를 본인의 GitHub 저장소에 푸시(Push)합니다.
> 6. `deploy_guide.md` 가이드에 따라 Vercel에 배포합니다. (환경변수 설정 주의!)

## 📚 코드 학습 추천

모든 파일에는 초보 학습자의 눈높이에 맞춘 **상세한 한국어 주석**이 달려 있습니다. 특히 다음 파일들의 주석을 읽어보시면 React 데이터 흐름을 이해하는 데 큰 도움이 될 것입니다.

- `src/components/BookForm.jsx`: 폼 상태 관리와 유효성 검증
- `src/hooks/useBooks.js`: 비동기 데이터 로딩과 커스텀 훅의 분리
- `src/contexts/ThemeContext.jsx`: Context API를 활용한 전역 상태 패턴

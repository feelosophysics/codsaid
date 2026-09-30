# 📖 BookLog (독서 기록 서비스)

본 프로젝트는 React의 핵심 개념(컴포넌트 설계, 상태 관리, 라우팅, 비동기 흐름)을 학습하고 실습하기 위해 만들어진 단일 페이지 애플리케이션(SPA)입니다.

## 🚀 기능 소개
- **회원가입/로그인**: Supabase Auth를 통한 이메일 기반 사용자 인증 (보너스 과제 5.3)
- **독서 기록 CRUD**: Supabase Database를 연동하여 독서 기록을 생성, 조회, 수정, 삭제
- **테마 전환**: 전역 상태(Context)를 활용한 라이트/다크 모드 지원 (보너스 과제 5.1)
- **성능 최적화**: `React.memo`, `useMemo`, `useCallback`을 활용한 불필요한 리렌더링 방지 (보너스 과제 5.2)

## 🛠️ 기술 스택
- **프레임워크**: React 19 (Vite 8)
- **언어**: JavaScript
- **라우팅**: React Router v7 (SPA 라우팅 및 보호 라우트 구현)
- **상태 관리**: React Hooks (`useState`, `useEffect`, `useCallback`, `useMemo`, `Context API`)
- **스타일링**: Vanilla CSS (CSS Variables를 활용한 테마 시스템 구현)
- **백엔드/BaaS**: Supabase (PostgreSQL + Auth)


## 📁 주요 폴더 구조
```
src/
├── components/   # 재사용 가능한 UI 컴포넌트 (Button, Input, Card 등)
├── contexts/     # 전역 상태 관리를 위한 Context (AuthContext, ThemeContext)
├── hooks/        # 커스텀 훅 (useBooks, useBookDetail)
├── lib/          # 유틸리티 (Supabase 클라이언트 초기화)
├── pages/        # 라우트 단위 페이지 컴포넌트
├── App.jsx       # 라우팅 및 Provider 설정
└── index.css     # 글로벌 CSS 및 CSS 변수(디자인 토큰)
```

## ⚙️ 로컬 실행 방법

1. **저장소 클론 및 패키지 설치**
   ```bash
   npm install
   ```

2. **환경변수 설정**
   루트 디렉토리에 `.env` 파일을 생성하고, Supabase 프로젝트 정보를 입력합니다. (자세한 설정 방법은 `supabase_setup_guide.md`를 참고하세요)
   ```env
   VITE_SUPABASE_URL=https://your-project.supabase.co
   VITE_SUPABASE_ANON_KEY=your-anon-key-here
   ```

3. **개발 서버 실행**
   ```bash
   npm run dev
   ```

## 📚 학습 주안점

- **컴포넌트 분리**: UI와 페이지 컴포넌트를 명확히 분리하고, 재사용 가능한 형태로 `props`를 설계했습니다.
- **상태 흐름**: 하향식(Top-down) 데이터 흐름과, `Controlled Input` 패턴을 활용하여 상태를 제어했습니다.
- **일관된 UI 처리**: 로딩 중, 에러 발생, 데이터 없음 상태를 각각의 재사용 컴포넌트(`Loading`, `ErrorState`, `EmptyState`)로 분리하여 앱 전체에서 일관된 사용자 경험을 제공하도록 설계했습니다.
- **비동기 처리 최적화**: API 호출 로직을 커스텀 훅(`useBooks`, `useBookDetail`)으로 추상화하여 페이지 컴포넌트를 가볍게 유지했습니다.

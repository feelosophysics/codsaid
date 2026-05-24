# 🚀 Vercel 배포 가이드

이 문서에서는 완성된 React(Vite) 앱을 Vercel을 사용하여 외부에 배포하는 방법을 안내합니다.

> **사전 준비**: 
> 1. 프로젝트 코드가 GitHub 레포지토리에 푸시(Push)되어 있어야 합니다.
> 2. `supabase_setup_guide.md`에 따라 Supabase 설정이 완료되어 있어야 합니다.

---

## 1. Vercel 로그인 및 새 프로젝트 시작

1. [Vercel 공식 홈페이지](https://vercel.com/)에 접속하여 GitHub 계정으로 가입/로그인합니다.
2. 대시보드 우측 상단의 **[Add New...]** 버튼을 누르고 **[Project]**를 선택합니다.

## 2. GitHub 레포지토리 연결

1. **Import Git Repository** 화면에서, 방금 코드를 올린 GitHub 레포지토리를 찾아 **[Import]** 버튼을 클릭합니다.
2. (만약 보이지 않는다면, Vercel 앱이 레포지토리에 접근할 수 있도록 권한을 설정해 주세요.)

## 3. 프로젝트 설정 및 환경 변수 추가

1. **Project Name**: 원하는 이름으로 설정합니다.
2. **Framework Preset**: Vercel이 자동으로 `Vite`를 인식합니다. 그대로 둡니다.
3. **Build and Output Settings**: 기본값 그대로 둡니다. (`npm run build`, `dist` 폴더 등)
4. ⭐️ **Environment Variables (환경 변수)** 섹션을 클릭하여 펼칩니다.
   - Name과 Value 폼에 아래 2개의 변수를 각각 추가(Add)합니다.
   - 로컬 `.env` 파일에 있는 값과 똑같이 입력해야 합니다.

| Name | Value |
|------|-------|
| `VITE_SUPABASE_URL` | https://...supabase.co (본인 프로젝트 URL) |
| `VITE_SUPABASE_ANON_KEY` | 본인의 anon key (ey...) |

## 4. 배포 실행!

1. 모든 설정을 마쳤다면 하단의 파란색 **[Deploy]** 버튼을 클릭합니다.
2. Vercel이 코드를 가져와 빌드를 시작합니다. (약 1~2분 소요)
3. 팡파레 효과와 함께 **"Congratulations!"** 화면이 뜨면 배포 성공입니다!

## 5. 배포 확인

- 제공된 Vercel URL(예: `https://booklog-app.vercel.app`)을 클릭하여 접속합니다.
- 회원가입, 로그인, 글쓰기가 로컬 환경처럼 정상적으로 동작하는지 확인합니다.
- (만약 동작하지 않는다면, 환경변수(`VITE_...`) 입력에 오타가 없는지 확인하고 재배포하세요.)

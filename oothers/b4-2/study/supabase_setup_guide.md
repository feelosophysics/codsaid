# 🗄️ Supabase 수동 설정 가이드

이 프로젝트는 백엔드로 **Supabase**를 사용합니다. 데이터베이스 테이블과 인증 시스템이 설정되어 있어야 앱이 정상적으로 동작합니다. 아래 순서에 따라 Supabase 프로젝트를 설정해 주세요.

---

## 1. 계정 및 프로젝트 생성

1. [Supabase 공식 홈페이지](https://supabase.com/)에 접속하여 회원가입(Sign up) 또는 로그인합니다.
2. 대시보드에서 **[New Project]** 버튼을 클릭합니다.
3. 소속될 Organization을 선택하고, **Name**(예: `booklog-app`), **Database Password**(기억해두세요), **Region**(가장 가까운 `Seoul` 추천)을 입력합니다.
4. **[Create new project]**를 클릭하고, 데이터베이스가 세팅될 때까지 몇 분 정도 기다립니다.

---

## 2. 데이터베이스 테이블 생성 (SQL Editor 사용)

프로젝트 세팅이 완료되면, 좌측 메뉴에서 **SQL Editor**를 클릭합니다. 
새 쿼리(New Query)를 열고 아래 SQL 코드를 붙여넣은 뒤, **[Run]** 버튼을 클릭하여 테이블을 생성합니다.

```sql
-- 1. books 테이블 생성
create table public.books (
  id uuid not null default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  title text not null,
  author text not null,
  content text null,
  rating integer null,
  read_date date null,
  created_at timestamp with time zone not null default now(),
  updated_at timestamp with time zone not null default now(),
  constraint books_pkey primary key (id)
);

-- 2. Row Level Security (RLS) 활성화
-- 이 설정을 해야 사용자가 "자신의 기록만" 볼 수 있게 제어할 수 있습니다.
alter table public.books enable row level security;

-- 3. RLS 정책(Policy) 추가
-- 로그인한 사용자는 자신의 기록만 조회(SELECT), 추가(INSERT), 수정(UPDATE), 삭제(DELETE) 가능
create policy "사용자는 자신의 기록만 볼 수 있습니다." on public.books
  for select using (auth.uid() = user_id);

create policy "사용자는 자신의 기록만 추가할 수 있습니다." on public.books
  for insert with check (auth.uid() = user_id);

create policy "사용자는 자신의 기록만 수정할 수 있습니다." on public.books
  for update using (auth.uid() = user_id);

create policy "사용자는 자신의 기록만 삭제할 수 있습니다." on public.books
  for delete using (auth.uid() = user_id);
```

> **성공 확인**: 좌측 메뉴의 **Table Editor**로 이동했을 때 `books` 테이블이 보인다면 성공입니다!

---

## 3. 인증 (Authentication) 설정

이메일/비밀번호 로그인을 사용하기 위해, 기본적인 이메일 인증 절차를 테스트 기간 동안 꺼두는 것이 편합니다.

1. 좌측 메뉴에서 **Authentication** → **Providers**로 이동합니다.
2. **Email** 제공자(Provider)를 클릭하여 엽니다.
3. `Confirm email` (이메일 확인 활성화) 설정이 켜져있다면, **꺼줍니다(Disable)**.
4. **[Save]** 버튼을 눌러 저장합니다.
*(실제 상용 서비스에서는 켜두는 것이 안전하지만, 테스트 시에는 번거로울 수 있습니다.)*

---

## 4. 환경 변수(API Keys) 가져오기 및 코드 연동

앱 코드와 Supabase를 연결하려면 URL과 Anon Key가 필요합니다.

1. 좌측 최하단의 **Project Settings** (톱니바퀴 아이콘)을 클릭합니다.
2. **API** 메뉴로 이동합니다.
3. 화면에 보이는 **Project URL**과 **Project API Keys**의 `anon` `public` 키를 복사합니다.
4. 로컬 PC의 프로젝트 루트(가장 바깥 폴더)에 **`.env`** 파일을 만들고 아래와 같이 복사한 값을 붙여넣습니다.

```env
# .env 파일 내용
VITE_SUPABASE_URL=당신의_프로젝트_URL
VITE_SUPABASE_ANON_KEY=당신의_ANON_KEY
```

> **주의**: `.env` 파일은 절대 Github에 올리면 안 됩니다! (기본적으로 `.gitignore`에 설정되어 있습니다.)

---

## 🎉 모든 준비가 끝났습니다!
이제 터미널에서 `npm run dev`를 실행하여 회원가입을 시도해 보세요. 에러 없이 회원가입 및 독서 기록 저장이 동작한다면 완벽합니다!

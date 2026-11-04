/**
 * ============================================================
 * AuthContext.jsx — 인증(로그인) 전역 상태 관리
 * ============================================================
 * 
 * [보너스 과제 5.1 — 전역 상태 도입 + 5.3 — 인증 추가]
 * 
 * 이 파일이 하는 일:
 *   1. Supabase Auth를 사용하여 사용자의 로그인/로그아웃 상태를 추적합니다.
 *   2. 로그인한 사용자 정보를 Context로 전역에서 공유합니다.
 *   3. 회원가입, 로그인, 로그아웃 함수를 제공합니다.
 *   4. 인증 상태가 변경되면(로그인/로그아웃) 자동으로 감지합니다.
 * 
 * Supabase Auth란?
 *   → Supabase가 제공하는 인증 서비스로, 이메일/비밀번호 기반
 *     회원가입, 로그인, 로그아웃을 쉽게 구현할 수 있습니다.
 *   → JWT(JSON Web Token) 기반으로 동작하며, 세션 관리도 자동으로 해줍니다.
 */

import { createContext, useContext, useState, useEffect } from 'react';
import { supabase } from '../lib/supabase';

// ============================================================
// 1. Context 생성
// ============================================================
const AuthContext = createContext();

// ============================================================
// 2. AuthProvider — 인증 상태를 관리하는 컴포넌트
// ============================================================
export function AuthProvider({ children }) {
  // --------------------------------------------------------
  // 상태 정의
  // --------------------------------------------------------
  // user: 현재 로그인한 사용자 정보 (null이면 비로그인 상태)
  const [user, setUser] = useState(null);
  // loading: 초기 인증 상태를 확인 중인지 여부
  // → 앱이 처음 로드될 때 Supabase에 "지금 로그인된 사용자가 있나요?"를
  //   물어보는 동안 true로 설정됩니다.
  const [loading, setLoading] = useState(true);

  // --------------------------------------------------------
  // useEffect: 앱 시작 시 인증 상태 확인 + 변경 감지
  // --------------------------------------------------------
  // 의존성 배열이 빈 배열 [] → 컴포넌트가 처음 마운트될 때 1번만 실행
  useEffect(() => {
    // --- (1) 현재 세션(로그인 상태) 확인 ---
    // getSession() → Supabase에 저장된 세션 정보를 가져옵니다.
    // 세션이 있다면 사용자가 이전에 로그인했다는 뜻입니다.
    supabase.auth.getSession().then(({ data: { session } }) => {
      // session이 있으면 session.user에 사용자 정보가 있음
      setUser(session?.user ?? null);
      // 초기 확인 완료 → loading을 false로
      setLoading(false);
    });

    // --- (2) 인증 상태 변경 리스너 등록 ---
    // onAuthStateChange: 로그인/로그아웃/토큰갱신 등이 발생할 때
    //                    자동으로 호출되는 콜백(이벤트 리스너)을 등록합니다.
    // _event: 이벤트 종류 (SIGNED_IN, SIGNED_OUT 등) — 여기서는 사용 안 함
    // session: 변경된 세션 정보
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, session) => {
        setUser(session?.user ?? null);
        setLoading(false);
      }
    );

    // --- (3) 클린업 함수 ---
    // 컴포넌트가 언마운트(화면에서 사라질 때)되면
    // 이벤트 리스너를 해제하여 메모리 누수를 방지합니다.
    return () => subscription.unsubscribe();
  }, []); // ← 빈 배열: 처음 마운트 시 1번만 실행

  // --------------------------------------------------------
  // 회원가입 함수
  // --------------------------------------------------------
  // email, password를 받아 Supabase Auth에 새 계정을 등록합니다.
  // async/await: 비동기 작업(서버 요청)이 끝날 때까지 기다리는 문법.
  const signUp = async (email, password) => {
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
    });
    // error가 있으면 Error 객체를 던져서 호출하는 쪽에서 catch할 수 있게 합니다.
    if (error) throw error;
    return data;
  };

  // --------------------------------------------------------
  // 로그인 함수
  // --------------------------------------------------------
  // email, password로 기존 계정에 로그인합니다.
  const signIn = async (email, password) => {
    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });
    if (error) throw error;
    return data;
  };

  // --------------------------------------------------------
  // 로그아웃 함수
  // --------------------------------------------------------
  // 현재 세션을 종료하고 사용자를 로그아웃시킵니다.
  const signOut = async () => {
    const { error } = await supabase.auth.signOut();
    if (error) throw error;
  };

  // --------------------------------------------------------
  // Context에 값을 제공
  // --------------------------------------------------------
  // 자식 컴포넌트들이 useAuth()로 접근할 수 있는 값들:
  //   - user: 현재 로그인한 사용자 정보 (null이면 비로그인)
  //   - loading: 인증 상태 확인 중 여부
  //   - signUp: 회원가입 함수
  //   - signIn: 로그인 함수
  //   - signOut: 로그아웃 함수
  return (
    <AuthContext.Provider value={{ user, loading, signUp, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

// ============================================================
// 3. useAuth — Context를 쉽게 사용하기 위한 커스텀 훅
// ============================================================
// 사용 예: const { user, signIn, signOut } = useAuth();
export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth는 AuthProvider 안에서만 사용할 수 있습니다.');
  }
  return context;
}

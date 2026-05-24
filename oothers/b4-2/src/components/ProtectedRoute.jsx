/**
 * ============================================================
 * ProtectedRoute.jsx — 인증 보호 라우트 컴포넌트
 * ============================================================
 * 
 * [보너스 5.3 — 인증 추가 / 보호 라우트]
 * 
 * 보호 라우트(Protected Route)란?
 *   → 로그인한 사용자만 접근할 수 있는 페이지를 만드는 것.
 *   → 로그인하지 않은 사용자가 보호된 페이지에 접근하면
 *     자동으로 로그인 페이지(/login)로 이동시킵니다.
 * 
 * 작동 원리:
 *   1. AuthContext에서 user와 loading 상태를 확인합니다.
 *   2. loading 중이면 → 로딩 스피너 표시
 *   3. user가 없으면(비로그인) → /login으로 리다이렉트
 *   4. user가 있으면(로그인됨) → 자식 컴포넌트(페이지)를 정상 렌더링
 * 
 * Navigate란?
 *   → React Router의 컴포넌트로, 렌더링되면 지정된 경로로 이동합니다.
 *   → replace 옵션을 사용하면 브라우저 히스토리에 현재 페이지가 남지 않아
 *     뒤로 가기를 눌러도 보호된 페이지로 돌아오지 않습니다.
 */

import { Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import Loading from './Loading';

export default function ProtectedRoute({ children }) {
  // AuthContext에서 현재 사용자와 로딩 상태를 가져옵니다.
  const { user, loading } = useAuth();

  // 인증 상태를 확인하는 중이면 로딩 표시
  if (loading) {
    return <Loading message="인증 확인 중..." />;
  }

  // 로그인하지 않은 사용자 → 로그인 페이지로 리다이렉트
  if (!user) {
    return <Navigate to="/login" replace />;
  }

  // 로그인된 사용자 → 자식 컴포넌트(실제 페이지)를 정상 렌더링
  return children;
}

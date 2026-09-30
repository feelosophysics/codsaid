/**
 * ============================================================
 * Navbar.jsx — 네비게이션 바 컴포넌트
 * ============================================================
 * 
 * 앱의 상단에 고정되어 주요 페이지로 이동할 수 있는 링크를 제공합니다.
 * 
 * [미션 요구사항 4.1]
 *   "공통 레이아웃(헤더/네비게이션)이 주요 페이지에 적용되어야 한다"
 * 
 * [미션 요구사항 4.2]
 *   "네비게이션을 통해 주요 라우트로 이동 가능한 링크가 제공되어야 한다"
 * 
 * React Router의 Link와 NavLink:
 *   - Link: HTML의 <a> 태그 대신 사용. 페이지 새로고침 없이 이동합니다.
 *   - NavLink: Link와 동일하지만, 현재 경로와 일치하면
 *     자동으로 'active' 클래스가 추가됩니다.
 *     → 현재 페이지 링크를 시각적으로 강조할 수 있습니다.
 */

import { NavLink } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import ThemeToggle from './ThemeToggle';
import './Navbar.css';

export default function Navbar() {
  // 현재 로그인한 사용자 정보를 가져옵니다.
  const { user } = useAuth();

  return (
    <nav className="navbar">
      <div className="navbar-inner">
        {/* ======== 로고 / 브랜드 ======== */}
        <NavLink to="/" className="navbar-logo">
          📖 BookLog
        </NavLink>

        {/* ======== 네비게이션 링크 ======== */}
        <div className="navbar-links">
          {/* 
            로그인한 사용자에게만 표시되는 링크들
            user가 있을 때(truthy)만 렌더링됩니다.
            이것이 "조건부 렌더링"의 또 다른 예입니다.
          */}
          {user && (
            <>
              {/* NavLink의 className 함수: { isActive }를 받아 동적 클래스 적용 */}
              <NavLink
                to="/books"
                className={({ isActive }) =>
                  `navbar-link ${isActive ? 'navbar-link-active' : ''}`
                }
              >
                내 기록
              </NavLink>
              <NavLink
                to="/books/new"
                className={({ isActive }) =>
                  `navbar-link ${isActive ? 'navbar-link-active' : ''}`
                }
              >
                새 기록
              </NavLink>
              <NavLink
                to="/profile"
                className={({ isActive }) =>
                  `navbar-link ${isActive ? 'navbar-link-active' : ''}`
                }
              >
                프로필
              </NavLink>
            </>
          )}

          {/* 비로그인 사용자에게 표시되는 링크 */}
          {!user && (
            <>
              <NavLink
                to="/login"
                className={({ isActive }) =>
                  `navbar-link ${isActive ? 'navbar-link-active' : ''}`
                }
              >
                로그인
              </NavLink>
              <NavLink
                to="/signup"
                className={({ isActive }) =>
                  `navbar-link ${isActive ? 'navbar-link-active' : ''}`
                }
              >
                회원가입
              </NavLink>
            </>
          )}

          {/* 테마 토글 버튼 — 항상 표시 */}
          <ThemeToggle />
        </div>
      </div>
    </nav>
  );
}

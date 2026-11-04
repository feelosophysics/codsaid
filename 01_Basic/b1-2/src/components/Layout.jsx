/**
 * ============================================================
 * Layout.jsx — 공통 레이아웃 컴포넌트
 * ============================================================
 * 
 * 모든 페이지에 공통으로 적용되는 레이아웃입니다.
 * Navbar를 포함하고, 페이지 콘텐츠가 들어갈 영역을 제공합니다.
 * 
 * React Router의 Outlet:
 *   → 중첩 라우트(nested route)에서 자식 라우트의 컴포넌트가
 *     렌더링될 위치를 지정합니다.
 *   → Layout 안에 <Outlet />을 넣으면, URL에 따라 해당 페이지 컴포넌트가
 *     이 위치에 렌더링됩니다.
 */

import { Outlet } from 'react-router-dom';
import Navbar from './Navbar';
import './Layout.css';

export default function Layout() {
  return (
    <div className="layout">
      {/* 상단 네비게이션 바 — 모든 페이지에 공통 표시 */}
      <Navbar />
      {/* 메인 콘텐츠 영역 — 각 페이지 컴포넌트가 여기에 렌더링됨 */}
      <main className="layout-main">
        {/* Outlet: React Router가 현재 URL에 맞는 페이지를 여기에 렌더링 */}
        <Outlet />
      </main>
    </div>
  );
}

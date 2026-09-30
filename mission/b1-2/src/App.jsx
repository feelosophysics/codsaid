/**
 * ============================================================
 * App.jsx — 앱의 루트 컴포넌트 (라우터 + Context Provider)
 * ============================================================
 * 
 * 이 파일이 하는 일:
 *   1. React Router로 URL 경로별 페이지를 매핑합니다.
 *   2. ThemeProvider로 전체 앱의 테마 상태를 관리합니다.
 *   3. AuthProvider로 전체 앱의 인증 상태를 관리합니다.
 *   4. Layout으로 공통 네비게이션 바를 적용합니다.
 *   5. ProtectedRoute로 인증이 필요한 페이지를 보호합니다.
 * 
 * BrowserRouter란?
 *   → HTML5 History API를 사용하는 라우터.
 *   → URL 경로(/books, /login 등)에 따라 다른 컴포넌트를 렌더링합니다.
 *   → 페이지 새로고침 없이 URL만 변경하여 SPA를 구현합니다.
 * 
 * Routes / Route란?
 *   → Routes: Route들을 감싸는 컨테이너. URL과 매칭되는 Route를 찾습니다.
 *   → Route: 특정 경로(path)와 컴포넌트(element)를 연결합니다.
 *     예: <Route path="/login" element={<LoginPage />} />
 *         → URL이 /login이면 LoginPage를 렌더링합니다.
 */

import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ThemeProvider } from './contexts/ThemeContext';
import { AuthProvider } from './contexts/AuthContext';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';

// 페이지 컴포넌트 임포트
import HomePage from './pages/HomePage';
import LoginPage from './pages/LoginPage';
import SignUpPage from './pages/SignUpPage';
import BooksPage from './pages/BooksPage';
import BookDetailPage from './pages/BookDetailPage';
import BookNewPage from './pages/BookNewPage';
import BookEditPage from './pages/BookEditPage';
import ProfilePage from './pages/ProfilePage';
import NotFoundPage from './pages/NotFoundPage';

export default function App() {
  return (
    // ============================================================
    // Provider 래핑 순서 (바깥 → 안쪽):
    // ThemeProvider → AuthProvider → BrowserRouter → Routes
    // 
    // 왜 이 순서인가?
    //   → ThemeProvider가 가장 바깥에 있어서, 모든 컴포넌트가
    //     테마 정보에 접근할 수 있습니다.
    //   → AuthProvider가 BrowserRouter 안에 있을 필요는 없지만,
    //     AuthProvider 안의 컴포넌트가 Router의 기능(navigate 등)을
    //     사용하지 않으므로 바깥에 놓아도 괜찮습니다.
    // ============================================================
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            {/* 
              Layout을 부모 Route로 설정하면,
              모든 자식 Route에 Navbar가 공통으로 적용됩니다.
              Outlet 위치에 자식 Route의 컴포넌트가 렌더링됩니다.
            */}
            <Route element={<Layout />}>
              {/* ===== 공개 라우트 (로그인 불필요) ===== */}
              
              {/* index: 부모 경로(/)에서 렌더링되는 기본 페이지 */}
              <Route index element={<HomePage />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/signup" element={<SignUpPage />} />

              {/* ===== 보호 라우트 (로그인 필요) ===== */}
              {/* ProtectedRoute로 감싸면 비로그인 사용자는 /login으로 리다이렉트 */}
              
              <Route path="/books" element={
                <ProtectedRoute><BooksPage /></ProtectedRoute>
              } />
              {/* 
                주의: /books/new가 /books/:id보다 먼저 와야 합니다!
                그렇지 않으면 "new"가 :id로 인식됩니다.
              */}
              <Route path="/books/new" element={
                <ProtectedRoute><BookNewPage /></ProtectedRoute>
              } />
              <Route path="/books/:id" element={
                <ProtectedRoute><BookDetailPage /></ProtectedRoute>
              } />
              <Route path="/books/:id/edit" element={
                <ProtectedRoute><BookEditPage /></ProtectedRoute>
              } />
              <Route path="/profile" element={
                <ProtectedRoute><ProfilePage /></ProtectedRoute>
              } />

              {/* ===== 404 페이지 ===== */}
              {/* path="*": 위의 어떤 경로에도 매칭되지 않을 때 */}
              <Route path="*" element={<NotFoundPage />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
}

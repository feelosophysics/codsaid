/**
 * ============================================================
 * main.jsx — React 앱의 진입점(Entry Point)
 * ============================================================
 * 
 * Vite가 가장 먼저 실행하는 JavaScript 파일입니다.
 * HTML의 <div id="root">에 React 앱(App.jsx)을 렌더링합니다.
 */

import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.jsx';
// 글로벌 CSS(디자인 토큰, 테마 설정 등)를 여기서 불러옵니다.
import './index.css';

// ReactDOM.createRoot(): React 18의 새로운 렌더링 방식
ReactDOM.createRoot(document.getElementById('root')).render(
  // StrictMode: 개발 환경에서 잠재적인 문제를 찾기 위해
  // 컴포넌트를 두 번씩 렌더링하는 React의 기능입니다.
  // (실제 배포 시에는 한 번만 렌더링됩니다)
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

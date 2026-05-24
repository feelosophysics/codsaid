/**
 * ============================================================
 * ThemeToggle.jsx — 다크/라이트 모드 전환 버튼
 * ============================================================
 * 
 * [보너스 5.1 — 전역 상태 도입]
 * 
 * ThemeContext에서 제공하는 theme과 toggleTheme을 사용하여
 * 다크 모드 ↔ 라이트 모드를 전환합니다.
 * 
 * [이벤트 → 상태 → 렌더링 흐름]
 *   버튼 클릭(이벤트) → toggleTheme() 호출(상태 변경) 
 *   → Context 값 변경 → 전체 앱 테마 변경(렌더링)
 *   이것은 전역 상태 변경이 전체 UI에 영향을 미치는 좋은 예입니다.
 */

import { useTheme } from '../contexts/ThemeContext';
import './ThemeToggle.css';

export default function ThemeToggle() {
  // useTheme() 커스텀 훅으로 ThemeContext의 값을 가져옵니다.
  // theme: 현재 테마 ('light' 또는 'dark')
  // toggleTheme: 테마를 전환하는 함수
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      className="theme-toggle"
      onClick={toggleTheme}
      // aria-label: 스크린 리더가 읽어줄 버튼 설명
      aria-label={theme === 'light' ? '다크 모드로 전환' : '라이트 모드로 전환'}
      title={theme === 'light' ? '다크 모드' : '라이트 모드'}
    >
      {/* 테마에 따라 아이콘 변경: 라이트 → 🌙, 다크 → ☀️ */}
      <span className="theme-toggle-icon">
        {theme === 'light' ? '🌙' : '☀️'}
      </span>
    </button>
  );
}

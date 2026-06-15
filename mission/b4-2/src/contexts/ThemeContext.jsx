/**
 * ============================================================
 * ThemeContext.jsx — 테마(다크/라이트 모드) 전역 상태 관리
 * ============================================================
 * 
 * [보너스 과제 5.1 — 전역 상태 도입]
 * 
 * Context란?
 *   → React에서 여러 컴포넌트가 같은 데이터를 공유할 때 사용합니다.
 *   → 일반적으로 데이터는 부모 → 자식으로 props를 통해 전달하지만,
 *     깊이가 깊어지면 일일이 전달하기 번거롭습니다(prop drilling).
 *   → Context를 사용하면 어디서든 useContext()로 바로 접근 가능합니다.
 * 
 * 이 파일이 하는 일:
 *   1. ThemeContext 생성 — 테마 정보를 담는 그릇
 *   2. ThemeProvider 컴포넌트 — 테마 상태를 관리하고 자식에게 제공
 *   3. useTheme 커스텀 훅 — Context를 쉽게 사용하기 위한 단축 훅
 */

import { createContext, useContext, useState, useEffect } from 'react';

// ============================================================
// 1. Context 생성
// ============================================================
// createContext() → 새로운 Context 객체를 만듭니다.
// 이 Context를 통해 테마 정보를 전역에서 공유합니다.
const ThemeContext = createContext();

// ============================================================
// 2. ThemeProvider — 테마 상태를 관리하는 컴포넌트
// ============================================================
// Provider란? → Context의 값을 자식 컴포넌트들에게 "제공"하는 역할.
// App.jsx에서 <ThemeProvider>로 전체 앱을 감싸면,
// 앱 어디서든 useTheme()으로 테마 정보에 접근할 수 있습니다.
export function ThemeProvider({ children }) {
  // --------------------------------------------------------
  // 상태: 현재 테마 ('light' 또는 'dark')
  // --------------------------------------------------------
  // localStorage에서 저장된 테마를 읽어옵니다.
  // localStorage → 브라우저에 데이터를 영구 저장하는 저장소.
  //                새로고침하거나 브라우저를 닫아도 값이 유지됩니다.
  // 저장된 값이 없으면 기본값 'light'를 사용합니다.
  const [theme, setTheme] = useState(() => {
    // localStorage.getItem('theme') → 'theme' 키로 저장된 값을 읽기
    const savedTheme = localStorage.getItem('theme');
    return savedTheme || 'light'; // 저장된 값이 없으면 'light'
  });

  // --------------------------------------------------------
  // useEffect: 테마가 바뀔 때마다 실행되는 부수효과
  // --------------------------------------------------------
  // useEffect란?
  //   → 컴포넌트가 렌더링된 후 실행되는 코드를 담는 곳.
  //   → 두 번째 인자 [theme]는 "의존성 배열"로,
  //     theme 값이 바뀔 때마다 이 함수가 다시 실행됩니다.
  useEffect(() => {
    // HTML 문서의 <html> 태그에 data-theme 속성을 설정합니다.
    // 이 속성값에 따라 index.css의 CSS 변수가 전환됩니다.
    document.documentElement.setAttribute('data-theme', theme);
    
    // 변경된 테마를 localStorage에 저장하여,
    // 다음에 접속할 때도 같은 테마가 적용되게 합니다.
    localStorage.setItem('theme', theme);
  }, [theme]); // ← theme이 바뀔 때만 실행

  // --------------------------------------------------------
  // 테마 전환 함수
  // --------------------------------------------------------
  // 현재 'light'이면 'dark'로, 'dark'이면 'light'로 전환합니다.
  const toggleTheme = () => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light');
  };

  // --------------------------------------------------------
  // Context에 값을 제공
  // --------------------------------------------------------
  // value={{ theme, toggleTheme }}
  //   → 자식 컴포넌트들이 useTheme()으로 이 값들을 가져갈 수 있습니다.
  // {children} → ThemeProvider로 감싼 하위 컴포넌트들을 그대로 렌더링
  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

// ============================================================
// 3. useTheme — Context를 쉽게 사용하기 위한 커스텀 훅
// ============================================================
// 사용 예: const { theme, toggleTheme } = useTheme();
// 이렇게 하면 ThemeContext.Provider의 value에 접근할 수 있습니다.
export function useTheme() {
  // useContext(ThemeContext) → ThemeContext.Provider의 value를 가져옴
  const context = useContext(ThemeContext);
  
  // 만약 ThemeProvider 바깥에서 useTheme()을 호출하면 에러를 던집니다.
  // 이는 개발 중 실수를 빨리 발견하기 위한 안전장치입니다.
  if (!context) {
    throw new Error('useTheme은 ThemeProvider 안에서만 사용할 수 있습니다.');
  }
  
  return context;
}

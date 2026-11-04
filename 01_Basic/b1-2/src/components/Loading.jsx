/**
 * ============================================================
 * Loading.jsx — 로딩 상태 표시 컴포넌트
 * ============================================================
 * 
 * 데이터를 서버에서 불러오는 동안 사용자에게 "로딩 중"임을 알려주는
 * 컴포넌트입니다. 회전하는 스피너 아이콘과 메시지를 표시합니다.
 * 
 * 비동기(async) 작업에서의 로딩 상태:
 *   → 서버에 데이터를 요청하면 응답이 올 때까지 시간이 걸립니다.
 *   → 그 시간 동안 빈 화면 대신 로딩 스피너를 보여주면
 *     사용자가 "아직 처리 중"임을 알 수 있습니다.
 */

import './Loading.css';

export default function Loading({
  message = '불러오는 중...',  // 로딩 메시지 (기본값 제공)
}) {
  return (
    <div className="loading-container center-screen">
      {/* 회전하는 스피너 */}
      <div className="loading-spinner" />
      {/* 로딩 메시지 */}
      <p className="loading-message">{message}</p>
    </div>
  );
}

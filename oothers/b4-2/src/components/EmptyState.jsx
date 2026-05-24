/**
 * ============================================================
 * EmptyState.jsx — 빈 데이터 상태 표시 컴포넌트
 * ============================================================
 * 
 * 데이터가 없을 때 빈 화면 대신 "아직 데이터가 없어요" 같은 
 * 안내 메시지를 표시합니다. 이모지 아이콘도 함께 보여줍니다.
 * 
 * 미션 요구사항 4.4:
 *   "빈 상태가 모든 핵심 화면에서 일관된 방식으로 처리되어야 한다"
 *   → 이 컴포넌트를 재사용하여 모든 페이지에서 동일한 빈 상태 UI를 보여줍니다.
 */

import './EmptyState.css';

export default function EmptyState({
  title = '데이터가 없습니다',     // 제목
  message = '표시할 데이터가 없습니다.', // 설명 메시지
  icon = '📭',                     // 이모지 아이콘
}) {
  return (
    <div className="empty-state center-screen">
      {/* 큰 이모지 아이콘 */}
      <span className="empty-state-icon">{icon}</span>
      {/* 제목 */}
      <h3 className="empty-state-title">{title}</h3>
      {/* 설명 메시지 */}
      <p className="empty-state-message">{message}</p>
    </div>
  );
}

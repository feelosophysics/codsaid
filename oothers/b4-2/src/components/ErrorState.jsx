/**
 * ============================================================
 * ErrorState.jsx — 에러 상태 표시 컴포넌트
 * ============================================================
 * 
 * 서버 요청이 실패했을 때 사용자에게 에러 메시지를 보여주고,
 * "다시 시도" 버튼을 제공합니다.
 * 
 * 미션 요구사항 4.4:
 *   "에러 상태가 모든 핵심 화면에서 일관된 방식으로 처리되어야 한다"
 *   → EmptyState와 마찬가지로, 에러 표시도 재사용 컴포넌트로 통일합니다.
 * 
 * 미션 요구사항 4.6:
 *   "요청 실패 시 사용자에게 실패 사실이 화면에 표시되어야 한다"
 */

import Button from './Button';
import './ErrorState.css';

export default function ErrorState({
  message = '요청에 실패했습니다. 다시 시도해 주세요.',  // 에러 메시지
  onRetry,  // 재시도 버튼 클릭 시 호출되는 함수
}) {
  return (
    <div className="error-state center-screen">
      {/* 에러 아이콘 */}
      <span className="error-state-icon">⚠️</span>
      {/* 에러 제목 */}
      <h3 className="error-state-title">오류가 발생했습니다</h3>
      {/* 에러 메시지 */}
      <p className="error-state-message">{message}</p>
      {/* 재시도 버튼 — onRetry 함수가 있을 때만 표시 */}
      {onRetry && (
        <Button variant="secondary" onClick={onRetry}>
          다시 시도
        </Button>
      )}
    </div>
  );
}

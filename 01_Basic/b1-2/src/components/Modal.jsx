/**
 * ============================================================
 * Modal.jsx — 확인 모달 컴포넌트
 * ============================================================
 * 
 * 모달(Modal)이란?
 *   → 화면 위에 뜨는 작은 팝업 창입니다.
 *   → 중요한 동작(예: 삭제) 전에 "정말로 삭제하시겠습니까?" 같은
 *     확인을 받을 때 사용합니다.
 *   → 모달이 열리면 뒤쪽 화면이 어두워지고(오버레이), 
 *     모달 바깥을 클릭하면 닫힙니다.
 * 
 * [상태 → 렌더링 흐름]
 *   isOpen(상태)이 true이면 모달이 화면에 렌더링되고,
 *   false이면 렌더링되지 않습니다(화면에서 사라짐).
 */

import Button from './Button';
import './Modal.css';

export default function Modal({
  isOpen,        // 모달이 열려있는지 (true/false)
  onClose,       // 모달을 닫는 함수
  onConfirm,     // 확인 버튼 클릭 시 실행되는 함수
  title,         // 모달 제목 (예: "삭제 확인")
  message,       // 모달 메시지 (예: "정말 삭제하시겠습니까?")
  confirmText = '확인',    // 확인 버튼 텍스트
  cancelText = '취소',     // 취소 버튼 텍스트
  variant = 'danger',      // 확인 버튼 스타일 (삭제 시 빨간색)
  loading = false,          // 확인 작업 진행 중인지
}) {
  // isOpen이 false이면 아무것도 렌더링하지 않습니다.
  // 이것이 "조건부 렌더링" — React에서 특정 조건일 때만 UI를 표시하는 방법입니다.
  if (!isOpen) return null;

  return (
    // 오버레이: 모달 뒤의 반투명 어두운 배경
    // 오버레이를 클릭하면 모달이 닫힙니다.
    <div className="modal-overlay" onClick={onClose}>
      {/* 
        모달 본체
        e.stopPropagation() → 이벤트 버블링 방지
        모달 안쪽을 클릭해도 onClose가 호출되지 않게 합니다.
        (이벤트가 부모인 overlay로 전파되는 것을 막음)
      */}
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        {/* 모달 제목 */}
        <h3 className="modal-title">{title}</h3>
        {/* 모달 메시지 */}
        <p className="modal-message">{message}</p>
        {/* 버튼 영역 */}
        <div className="modal-actions">
          {/* 취소 버튼 — 모달을 닫음 */}
          <Button variant="ghost" onClick={onClose} disabled={loading}>
            {cancelText}
          </Button>
          {/* 확인 버튼 — onConfirm 실행 */}
          <Button variant={variant} onClick={onConfirm} loading={loading}>
            {confirmText}
          </Button>
        </div>
      </div>
    </div>
  );
}

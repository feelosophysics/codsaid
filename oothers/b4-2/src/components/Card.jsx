/**
 * ============================================================
 * Card.jsx — 카드형 컨테이너 컴포넌트
 * ============================================================
 * 
 * 콘텐츠를 카드(박스) 형태로 감싸는 범용 컴포넌트입니다.
 * - 둥근 모서리, 그림자, 배경색이 적용됩니다.
 * - onClick이 있으면 클릭 가능한 카드가 됩니다(호버 효과 포함).
 * - className으로 추가 스타일을 적용할 수 있습니다.
 */

import './Card.css';

export default function Card({
  children,            // 카드 안에 들어갈 내용
  onClick,             // 클릭 이벤트 핸들러 (있으면 클릭 가능)
  className = '',      // 추가 CSS 클래스
  hover = false,       // 호버 효과 강제 적용 여부
  ...rest
}) {
  return (
    <div
      // 클래스를 동적으로 조합합니다:
      // 'card' — 기본 카드 스타일
      // 'card-clickable' — onClick이 있거나 hover가 true이면 호버 효과 추가
      className={`card ${onClick || hover ? 'card-clickable' : ''} ${className}`}
      onClick={onClick}
      // onClick이 있으면 role="button"을 추가하여 접근성(A11y)을 향상시킵니다.
      // 스크린 리더 등 보조 기술이 이 요소를 버튼으로 인식합니다.
      role={onClick ? 'button' : undefined}
      // tabIndex: 키보드 탭으로 이 요소에 포커스할 수 있게 합니다.
      tabIndex={onClick ? 0 : undefined}
      {...rest}
    >
      {children}
    </div>
  );
}

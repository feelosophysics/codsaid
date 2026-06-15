/**
 * ============================================================
 * Button.jsx — 범용 버튼 컴포넌트
 * ============================================================
 * 
 * 재사용 컴포넌트란?
 *   → 앱 여러 곳에서 반복 사용되는 UI를 하나의 컴포넌트로 만들어,
 *     같은 코드를 복붙하지 않고 import해서 쓰는 것입니다.
 * 
 * props(속성)란?
 *   → 부모 컴포넌트가 자식 컴포넌트에 전달하는 데이터.
 *   → <Button variant="primary" size="large"> 처럼 사용하면
 *     Button 컴포넌트 안에서 props.variant, props.size로 접근 가능.
 * 
 * 이 Button 컴포넌트의 특징:
 *   - variant: 버튼 스타일 종류 (primary, secondary, danger, ghost)
 *   - size: 크기 (small, medium, large)
 *   - loading: 로딩 중이면 스피너 표시 + 클릭 불가
 *   - disabled: 비활성화 상태
 *   - fullWidth: 부모 너비에 꽉 차게
 */

import './Button.css';

// ============================================================
// Button 컴포넌트 정의
// ============================================================
// { ... } = props → 구조 분해 할당(destructuring)으로 props를 꺼냄
// = 'medium' 같은 것은 기본값(default value) — props가 없을 때 사용됨
export default function Button({
  children,         // 버튼 안의 내용 (텍스트, 아이콘 등)
  variant = 'primary', // 스타일 종류: 'primary' | 'secondary' | 'danger' | 'ghost'
  size = 'medium',     // 크기: 'small' | 'medium' | 'large'
  loading = false,     // 로딩 상태인지
  disabled = false,    // 비활성화 상태인지
  fullWidth = false,   // 부모 너비에 꽉 차게 할지
  type = 'button',     // HTML button의 type 속성 ('button', 'submit')
  onClick,             // 클릭 이벤트 핸들러 (함수)
  ...rest              // 나머지 HTML 속성들 (예: id, className 등)
}) {
  return (
    <button
      // className: CSS 클래스를 동적으로 조합합니다.
      // `btn btn-${variant}` → variant가 'primary'이면 'btn btn-primary'가 됩니다.
      // 조건부 클래스: loading이 true이면 'btn-loading' 클래스를 추가합니다.
      className={`btn btn-${variant} btn-${size} ${fullWidth ? 'btn-full' : ''} ${loading ? 'btn-loading' : ''}`}
      // disabled: loading 중이거나 disabled가 true이면 버튼을 비활성화
      disabled={disabled || loading}
      type={type}
      onClick={onClick}
      {...rest}  // 나머지 속성들을 그대로 전달 (스프레드 연산자)
    >
      {/* loading 중이면 스피너 아이콘을 표시합니다 */}
      {loading && <span className="btn-spinner" />}
      {/* 버튼 안의 내용을 렌더링 */}
      <span className="btn-content">{children}</span>
    </button>
  );
}

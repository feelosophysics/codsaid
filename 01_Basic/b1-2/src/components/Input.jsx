/**
 * ============================================================
 * Input.jsx — 범용 입력 필드 컴포넌트
 * ============================================================
 * 
 * HTML의 <input>과 <textarea>를 래핑한 재사용 컴포넌트입니다.
 * - 라벨(label) 표시
 * - 에러 메시지 표시 (폼 유효성 검증 결과)
 * - 필수 필드 표시 (*)
 * - <textarea> 지원 (multiline prop)
 * 
 * Controlled Input(제어 컴포넌트)란?
 *   → React의 state가 입력 필드의 값을 "제어"하는 방식.
 *   → value를 state로 관리하고, onChange로 state를 업데이트합니다.
 *   → 예: const [name, setName] = useState('');
 *          <Input value={name} onChange={(e) => setName(e.target.value)} />
 */

import './Input.css';

export default function Input({
  label,            // 라벨 텍스트 (예: "책 제목")
  type = 'text',    // 입력 타입: 'text', 'email', 'password', 'date' 등
  value,            // 현재 입력값 (state에서 가져옴)
  onChange,         // 값이 바뀔 때 호출되는 함수 (state 업데이트)
  error,            // 에러 메시지 문자열 (없으면 에러 표시 안 함)
  placeholder,      // 입력 힌트 텍스트 (연한 글씨로 보이는 것)
  required = false, // 필수 입력 여부
  multiline = false, // true이면 <textarea>로 렌더링
  rows = 4,         // textarea의 줄 수
  disabled = false, // 비활성화 여부
  ...rest           // 나머지 HTML 속성
}) {
  return (
    // 입력 필드 전체를 감싸는 컨테이너
    // error가 있으면 'input-group-error' 클래스를 추가하여 빨간 테두리를 표시
    <div className={`input-group ${error ? 'input-group-error' : ''}`}>
      {/* 라벨이 있을 때만 표시 */}
      {label && (
        <label className="input-label">
          {label}
          {/* 필수 입력이면 빨간 * 표시 */}
          {required && <span className="input-required">*</span>}
        </label>
      )}

      {/* multiline이 true이면 textarea, 아니면 input을 렌더링 */}
      {multiline ? (
        <textarea
          className="input-field input-textarea"
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          required={required}
          rows={rows}
          disabled={disabled}
          {...rest}
        />
      ) : (
        <input
          className="input-field"
          type={type}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          required={required}
          disabled={disabled}
          {...rest}
        />
      )}

      {/* 에러 메시지가 있을 때만 표시 */}
      {error && <span className="input-error">{error}</span>}
    </div>
  );
}

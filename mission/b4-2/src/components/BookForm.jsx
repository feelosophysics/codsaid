/**
 * ============================================================
 * BookForm.jsx — 독서 기록 등록/수정 폼 컴포넌트
 * ============================================================
 * 
 * 독서 기록을 등록하거나 수정하는 폼(양식)입니다.
 * 등록과 수정 모두에서 재사용됩니다.
 * 
 * [미션 요구사항 4.3 — 재사용 컴포넌트]
 *   등록 폼과 수정 폼의 UI가 동일하므로 하나의 컴포넌트로 통합합니다.
 *   initialData가 있으면 수정 모드, 없으면 등록 모드로 동작합니다.
 * 
 * [미션 요구사항 4.5 — 폼 UX]
 *   - 필수값 검증: 제목/저자가 비어있으면 제출 불가
 *   - 에러 메시지: 입력 필드 근처에 표시
 *   - 제출 중 상태: 버튼 비활성화 + 스피너
 *   - 요청 실패 시: 에러 메시지 표시
 * 
 * [미션 요구사항 4.4 — Controlled Input]
 *   모든 입력 필드는 React의 state로 제어됩니다.
 *   입력값이 바뀌면 state가 업데이트되고, state가 바뀌면 UI가 갱신됩니다.
 */

import { useState, useEffect } from 'react';
import Input from './Input';
import Button from './Button';
import StarRating from './StarRating';
import './BookForm.css';

export default function BookForm({
  initialData = null,   // 수정 모드일 때 기존 데이터 (null이면 등록 모드)
  onSubmit,             // 폼 제출 시 호출되는 함수 (부모 → 서버 요청 처리)
  isSubmitting = false, // 제출 중인지 (서버 요청 진행 중)
  submitError = '',     // 서버 요청 실패 시 에러 메시지
}) {
  // ============================================================
  // 폼 입력 상태 (Controlled Input)
  // ============================================================
  // 각 입력 필드의 값을 state로 관리합니다.
  // 사용자가 입력할 때마다 setState가 호출되어 값이 업데이트됩니다.
  const [title, setTitle] = useState('');
  const [author, setAuthor] = useState('');
  const [content, setContent] = useState('');
  const [rating, setRating] = useState(0);
  const [readDate, setReadDate] = useState('');

  // ============================================================
  // 유효성 검증 에러 상태
  // ============================================================
  // errors 객체에 각 필드별 에러 메시지를 저장합니다.
  // 예: { title: '제목을 입력해 주세요', author: '' }
  const [errors, setErrors] = useState({});

  // ============================================================
  // useEffect: 수정 모드일 때 기존 데이터로 폼 초기화
  // ============================================================
  // initialData가 전달되면(수정 모드) 기존 값을 폼에 채워넣습니다.
  // 의존성 배열 [initialData] → initialData가 바뀔 때만 실행
  useEffect(() => {
    if (initialData) {
      setTitle(initialData.title || '');
      setAuthor(initialData.author || '');
      setContent(initialData.content || '');
      setRating(initialData.rating || 0);
      setReadDate(initialData.read_date || '');
    }
  }, [initialData]);

  // ============================================================
  // 유효성 검증 함수
  // ============================================================
  // 제출 전에 필수 필드가 입력되었는지 확인합니다.
  // 에러가 있으면 errors 상태에 저장하고, false를 반환합니다.
  const validate = () => {
    const newErrors = {};

    // .trim() → 앞뒤 공백을 제거한 후 빈 문자열인지 확인
    if (!title.trim()) {
      newErrors.title = '제목을 입력해 주세요.';
    }
    if (!author.trim()) {
      newErrors.author = '저자를 입력해 주세요.';
    }
    if (rating === 0) {
      newErrors.rating = '별점을 선택해 주세요.';
    }

    setErrors(newErrors);
    // Object.keys(obj).length === 0 → 에러가 하나도 없다는 뜻
    return Object.keys(newErrors).length === 0;
  };

  // ============================================================
  // 폼 제출 핸들러
  // ============================================================
  // <form>의 onSubmit 이벤트가 발생하면 호출됩니다.
  const handleSubmit = (e) => {
    // e.preventDefault() → 폼의 기본 동작(페이지 새로고침)을 막습니다.
    // SPA에서는 페이지를 새로고침하지 않고 JavaScript로 처리합니다.
    e.preventDefault();

    // 유효성 검증 실패 시 제출하지 않음
    if (!validate()) return;

    // 부모 컴포넌트가 전달한 onSubmit 함수 호출
    // 폼에 입력된 데이터를 객체로 묶어서 전달합니다.
    onSubmit({
      title: title.trim(),
      author: author.trim(),
      content: content.trim(),
      rating,
      read_date: readDate || null,
    });
  };

  return (
    <form className="book-form" onSubmit={handleSubmit}>
      {/* 서버 에러 메시지가 있으면 상단에 표시 */}
      {submitError && (
        <div className="book-form-error">
          ⚠️ {submitError}
        </div>
      )}

      {/* 제목 입력 */}
      <Input
        label="책 제목"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        error={errors.title}
        placeholder="읽은 책의 제목을 입력하세요"
        required
        disabled={isSubmitting}
      />

      {/* 저자 입력 */}
      <Input
        label="저자"
        value={author}
        onChange={(e) => setAuthor(e.target.value)}
        error={errors.author}
        placeholder="책의 저자를 입력하세요"
        required
        disabled={isSubmitting}
      />

      {/* 별점 선택 */}
      <div className="input-group">
        <label className="input-label">
          별점
          <span className="input-required">*</span>
        </label>
        <StarRating
          value={rating}
          onChange={setRating}
          size="large"
        />
        {errors.rating && (
          <span className="input-error">{errors.rating}</span>
        )}
      </div>

      {/* 읽은 날짜 */}
      <Input
        label="읽은 날짜"
        type="date"
        value={readDate}
        onChange={(e) => setReadDate(e.target.value)}
        disabled={isSubmitting}
      />

      {/* 감상문 (여러 줄 입력) */}
      <Input
        label="감상문"
        multiline
        rows={6}
        value={content}
        onChange={(e) => setContent(e.target.value)}
        placeholder="책을 읽고 느낀 점을 자유롭게 작성하세요"
        disabled={isSubmitting}
      />

      {/* 제출 버튼 */}
      <Button
        type="submit"
        variant="primary"
        size="large"
        fullWidth
        loading={isSubmitting}
        disabled={isSubmitting}
      >
        {/* initialData가 있으면 수정, 없으면 등록 */}
        {initialData ? '수정 완료' : '기록 등록'}
      </Button>
    </form>
  );
}

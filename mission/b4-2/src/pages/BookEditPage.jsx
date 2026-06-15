/**
 * ============================================================
 * BookEditPage.jsx — 독서 기록 수정 페이지
 * ============================================================
 * 
 * 경로: /books/:id/edit (보호 라우트)
 * 기존 기록을 불러와서 BookForm에 초기값으로 전달하고,
 * 수정된 내용을 Supabase에 업데이트합니다.
 * 
 * [미션 요구사항 4.5]
 *   "수정: 폼 입력 → 제출 → 성공 시 이동/갱신 흐름이 존재한다"
 */

import { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { supabase } from '../lib/supabase';
import useBookDetail from '../hooks/useBookDetail';
import BookForm from '../components/BookForm';
import Loading from '../components/Loading';
import ErrorState from '../components/ErrorState';
import './BookNewPage.css'; // 같은 스타일을 공유합니다

export default function BookEditPage() {
  const { id } = useParams();      // URL에서 id 추출
  const navigate = useNavigate();

  // 기존 데이터를 커스텀 훅으로 불러옵니다.
  const { book, loading, error } = useBookDetail(id);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');

  // ============================================================
  // 수정 처리 함수
  // ============================================================
  const handleSubmit = async (formData) => {
    try {
      setIsSubmitting(true);
      setSubmitError('');

      // Supabase에서 해당 기록을 업데이트
      // .update(): 기존 행의 값을 변경하는 쿼리
      // .eq('id', id): id가 일치하는 행만 업데이트
      const { error: updateError } = await supabase
        .from('books')
        .update({
          ...formData,
          updated_at: new Date().toISOString(), // 수정 시각 갱신
        })
        .eq('id', id);

      if (updateError) throw updateError;

      // 성공 시 상세 페이지로 이동
      navigate(`/books/${id}`);
    } catch (err) {
      setSubmitError(err.message || '수정에 실패했습니다. 다시 시도해 주세요.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // 로딩/에러 상태 처리
  if (loading) return <Loading message="기록을 불러오는 중..." />;
  if (error) return <ErrorState message={error} />;
  if (!book) return <ErrorState message="기록을 찾을 수 없습니다." />;

  return (
    <div className="page-container book-form-page">
      <Link to={`/books/${id}`} className="back-link">
        ← 상세로 돌아가기
      </Link>
      <h1 className="page-title">기록 수정</h1>
      <p className="page-subtitle">"{book.title}"의 내용을 수정합니다.</p>

      {/* BookForm에 initialData를 전달하면 수정 모드로 동작 */}
      <BookForm
        initialData={book}
        onSubmit={handleSubmit}
        isSubmitting={isSubmitting}
        submitError={submitError}
      />
    </div>
  );
}

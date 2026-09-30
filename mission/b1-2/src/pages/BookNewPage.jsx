/**
 * ============================================================
 * BookNewPage.jsx — 새 독서 기록 등록 페이지
 * ============================================================
 * 
 * 경로: /books/new (보호 라우트)
 * BookForm 컴포넌트를 사용하여 새 독서 기록을 등록합니다.
 * 
 * [미션 요구사항 4.5]
 *   "등록: 폼 입력 → 제출 → 성공 시 이동/갱신 흐름이 존재한다"
 */

import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { supabase } from '../lib/supabase';
import { useAuth } from '../contexts/AuthContext';
import BookForm from '../components/BookForm';
import './BookNewPage.css';

export default function BookNewPage() {
  const navigate = useNavigate();
  const { user } = useAuth();

  // 제출 중 상태와 에러 상태
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');

  // ============================================================
  // 등록 처리 함수
  // ============================================================
  // BookForm에서 폼 데이터를 받아 Supabase에 저장합니다.
  const handleSubmit = async (formData) => {
    try {
      setIsSubmitting(true);
      setSubmitError('');

      // Supabase에 새 기록 삽입
      // .insert(): 새 행을 추가하는 쿼리
      // user_id: 현재 로그인한 사용자의 ID를 함께 저장
      const { data, error } = await supabase
        .from('books')
        .insert([{
          ...formData,           // 폼 데이터 (title, author, content, rating, read_date)
          user_id: user.id,      // 현재 사용자 ID
        }])
        .select()    // 삽입된 데이터를 반환받음
        .single();   // 단일 객체로 반환

      if (error) throw error;

      // 성공 시 상세 페이지로 이동
      navigate(`/books/${data.id}`);
    } catch (err) {
      setSubmitError(err.message || '등록에 실패했습니다. 다시 시도해 주세요.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="page-container book-form-page">
      <Link to="/books" className="back-link">
        ← 목록으로 돌아가기
      </Link>
      <h1 className="page-title">새 독서 기록</h1>
      <p className="page-subtitle">읽은 책의 정보와 감상을 기록해 보세요.</p>

      {/* BookForm — 재사용 컴포넌트 */}
      <BookForm
        onSubmit={handleSubmit}
        isSubmitting={isSubmitting}
        submitError={submitError}
      />
    </div>
  );
}

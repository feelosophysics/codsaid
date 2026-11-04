/**
 * ============================================================
 * BookDetailPage.jsx — 독서 기록 상세 페이지
 * ============================================================
 * 
 * 경로: /books/:id (보호 라우트)
 * URL 파라미터에서 id를 추출하여 해당 기록의 상세 정보를 표시합니다.
 * 수정/삭제 버튼을 제공합니다.
 * 
 * [미션 요구사항]
 *   4.2: 라우트 파라미터로 특정 데이터를 불러와 렌더링
 *   4.5: 상세 조회 + 삭제 후 목록 갱신/이동 흐름
 * 
 * useParams란?
 *   → React Router가 제공하는 훅으로, URL 경로의 동적 부분(:id)을 읽습니다.
 *   → 예: /books/abc-123 → useParams() = { id: 'abc-123' }
 */

import { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import useBookDetail from '../hooks/useBookDetail';
import { supabase } from '../lib/supabase';
import Loading from '../components/Loading';
import ErrorState from '../components/ErrorState';
import StarRating from '../components/StarRating';
import Button from '../components/Button';
import Modal from '../components/Modal';
import './BookDetailPage.css';

export default function BookDetailPage() {
  // URL에서 id 파라미터를 추출합니다.
  const { id } = useParams();
  const navigate = useNavigate();

  // 커스텀 훅으로 상세 데이터를 가져옵니다.
  const { book, loading, error } = useBookDetail(id);

  // 삭제 모달 상태
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // ============================================================
  // 삭제 핸들러
  // ============================================================
  const handleDelete = async () => {
    try {
      setDeleting(true);
      // Supabase에서 해당 기록 삭제
      const { error: deleteError } = await supabase
        .from('books')
        .delete()
        .eq('id', id);

      if (deleteError) throw deleteError;

      // 삭제 성공 → 목록 페이지로 이동
      navigate('/books');
    } catch (err) {
      alert('삭제에 실패했습니다: ' + err.message);
      setDeleting(false);
    }
  };

  // 로딩 중
  if (loading) return <Loading message="기록을 불러오는 중..." />;
  // 에러 발생
  if (error) return <ErrorState message={error} onRetry={() => navigate(0)} />;
  // 데이터 없음
  if (!book) return <ErrorState message="기록을 찾을 수 없습니다." />;

  return (
    <div className="page-container book-detail-page">
      {/* 뒤로 가기 링크 */}
      <Link to="/books" className="back-link">
        ← 목록으로 돌아가기
      </Link>

      {/* 상세 카드 */}
      <article className="detail-card">
        {/* 헤더: 제목 + 저자 */}
        <header className="detail-header">
          <h1 className="detail-title">{book.title}</h1>
          <p className="detail-author">저자: {book.author}</p>
        </header>

        {/* 메타 정보: 별점 + 읽은 날짜 */}
        <div className="detail-meta">
          <div className="detail-meta-item">
            <span className="detail-meta-label">별점</span>
            <StarRating value={book.rating} readOnly size="medium" />
          </div>
          {book.read_date && (
            <div className="detail-meta-item">
              <span className="detail-meta-label">읽은 날짜</span>
              <span className="detail-meta-value">📅 {book.read_date}</span>
            </div>
          )}
        </div>

        {/* 감상문 */}
        {book.content && (
          <section className="detail-content">
            <h2 className="detail-content-title">감상문</h2>
            <p className="detail-content-text">{book.content}</p>
          </section>
        )}

        {/* 등록일/수정일 */}
        <div className="detail-dates">
          <span>등록: {new Date(book.created_at).toLocaleDateString('ko-KR')}</span>
          {book.updated_at && book.updated_at !== book.created_at && (
            <span>수정: {new Date(book.updated_at).toLocaleDateString('ko-KR')}</span>
          )}
        </div>

        {/* 액션 버튼 */}
        <div className="detail-actions">
          <Button
            variant="secondary"
            onClick={() => navigate(`/books/${id}/edit`)}
          >
            ✏️ 수정하기
          </Button>
          <Button
            variant="danger"
            onClick={() => setShowDeleteModal(true)}
          >
            🗑️ 삭제하기
          </Button>
        </div>
      </article>

      {/* 삭제 확인 모달 */}
      <Modal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        onConfirm={handleDelete}
        title="기록 삭제"
        message={`"${book.title}" 기록을 정말 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.`}
        confirmText="삭제"
        variant="danger"
        loading={deleting}
      />
    </div>
  );
}

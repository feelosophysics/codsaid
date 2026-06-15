/**
 * ============================================================
 * BooksPage.jsx — 독서 기록 목록 페이지
 * ============================================================
 * 
 * 경로: /books (보호 라우트)
 * 로그인한 사용자의 독서 기록을 카드 목록으로 표시합니다.
 * 
 * [미션 요구사항]
 *   4.3: 로딩/에러/빈 상태가 재사용 컴포넌트로 통일
 *   4.4: 커스텀 훅(useBooks)으로 데이터 흐름 분리
 *   4.5: 목록 조회 — 리스트 UI가 렌더링
 * 
 * [보너스 5.2 — useMemo 적용]
 *   검색 키워드로 필터링한 결과를 useMemo로 캐싱하여
 *   불필요한 재계산을 방지합니다.
 */

import { useState, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import useBooks from '../hooks/useBooks';
import BookCard from '../components/BookCard';
import Loading from '../components/Loading';
import EmptyState from '../components/EmptyState';
import ErrorState from '../components/ErrorState';
import Button from '../components/Button';
import Input from '../components/Input';
import './BooksPage.css';

export default function BooksPage() {
  // ============================================================
  // 커스텀 훅으로 데이터 가져오기
  // ============================================================
  // useBooks()가 반환하는 값:
  //   books: 독서 기록 배열
  //   loading: 로딩 중 여부
  //   error: 에러 메시지
  //   fetchBooks: 목록 새로고침 함수
  const { books, loading, error, fetchBooks } = useBooks();

  // 검색어 상태
  const [searchQuery, setSearchQuery] = useState('');

  // useNavigate: 코드에서 페이지를 이동시키는 함수
  const navigate = useNavigate();

  // ============================================================
  // useMemo — 검색 결과 캐싱 (보너스 5.2)
  // ============================================================
  // useMemo란?
  //   → 계산 비용이 큰 값을 캐싱(메모이제이션)합니다.
  //   → 의존성(books, searchQuery)이 바뀌지 않으면 이전 결과를 재사용합니다.
  //   → 매 렌더링마다 필터링을 다시 하지 않아 성능이 향상됩니다.
  const filteredBooks = useMemo(() => {
    if (!searchQuery.trim()) return books; // 검색어가 없으면 전체 반환

    const query = searchQuery.toLowerCase(); // 대소문자 무시를 위해 소문자로 변환
    return books.filter(book =>
      // 제목 또는 저자에 검색어가 포함되어 있는지 확인
      book.title.toLowerCase().includes(query) ||
      book.author.toLowerCase().includes(query)
    );
  }, [books, searchQuery]); // ← books나 searchQuery가 바뀔 때만 재계산

  // ============================================================
  // 카드 클릭 핸들러 — useCallback으로 최적화 (보너스 5.2)
  // ============================================================
  // useCallback란?
  //   → 함수를 캐싱합니다. 의존성이 바뀌지 않으면 같은 함수 참조를 유지.
  //   → 자식 컴포넌트(BookCard)에 전달할 때, 불필요한 리렌더링을 방지.
  const handleCardClick = useCallback((bookId) => {
    navigate(`/books/${bookId}`);
  }, [navigate]);

  // ============================================================
  // 조건부 렌더링: 로딩/에러/빈 상태
  // ============================================================
  // 로딩 중이면 Loading 컴포넌트 표시
  if (loading) return <Loading message="독서 기록을 불러오는 중..." />;
  // 에러가 있으면 ErrorState 컴포넌트 표시 (재시도 버튼 포함)
  if (error) return <ErrorState message={error} onRetry={fetchBooks} />;

  return (
    <div className="page-container books-page">
      {/* 페이지 헤더 */}
      <div className="books-header">
        <div>
          <h1 className="page-title">내 독서 기록</h1>
          <p className="books-count">{books.length}권의 기록</p>
        </div>
        {/* 새 기록 작성 버튼 */}
        <Button
          variant="primary"
          onClick={() => navigate('/books/new')}
        >
          + 새 기록
        </Button>
      </div>

      {/* 검색 바 — 제목/저자로 필터링 */}
      {books.length > 0 && (
        <div className="books-search">
          <Input
            placeholder="제목 또는 저자로 검색..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      )}

      {/* 콘텐츠 영역 */}
      {books.length === 0 ? (
        // 데이터가 없을 때 — 빈 상태 표시
        <EmptyState
          icon="📚"
          title="아직 독서 기록이 없습니다"
          message="첫 번째 독서 기록을 등록해 보세요!"
        />
      ) : filteredBooks.length === 0 ? (
        // 검색 결과가 없을 때
        <EmptyState
          icon="🔍"
          title="검색 결과가 없습니다"
          message={`"${searchQuery}"에 해당하는 기록을 찾을 수 없습니다.`}
        />
      ) : (
        // 카드 그리드 — 독서 기록 카드 목록
        <div className="books-grid">
          {filteredBooks.map(book => (
            <BookCard
              key={book.id}  // React에서 목록 렌더링 시 각 항목에 고유 key 필수
              book={book}
              onClick={() => handleCardClick(book.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

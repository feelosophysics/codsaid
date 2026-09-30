/**
 * ============================================================
 * BookCard.jsx — 독서 기록 카드 컴포넌트 (목록용)
 * ============================================================
 * 
 * [보너스 5.2 — 성능 최적화 / React.memo 적용]
 * 
 * 독서 기록 목록(BooksPage)에서 각 항목을 카드 형태로 보여주는 컴포넌트입니다.
 * 
 * React.memo란?
 *   → 컴포넌트를 "메모이제이션"하는 고차 함수(Higher Order Component).
 *   → props가 변경되지 않으면 컴포넌트를 다시 렌더링하지 않습니다.
 *   → 목록에서 수십 개의 카드가 있을 때, 하나의 카드만 변경되어도
 *     모든 카드가 다시 렌더링되는 것을 방지합니다.
 *   → 이것을 "불필요한 리렌더링을 줄이는 성능 최적화"라고 합니다.
 */

import { memo } from 'react';
import Card from './Card';
import StarRating from './StarRating';
import './BookCard.css';

// memo()로 감싸서 props가 바뀌지 않으면 리렌더링을 건너뜁니다.
const BookCard = memo(function BookCard({
  book,       // 독서 기록 데이터 객체 { id, title, author, rating, read_date, content }
  onClick,    // 카드 클릭 시 실행 (상세 페이지로 이동)
}) {
  return (
    <Card onClick={onClick} className="book-card">
      {/* 카드 상단: 제목과 저자 */}
      <div className="book-card-header">
        <h3 className="book-card-title">{book.title}</h3>
        <p className="book-card-author">{book.author}</p>
      </div>

      {/* 카드 중간: 별점 */}
      <div className="book-card-rating">
        <StarRating value={book.rating} readOnly size="small" />
      </div>

      {/* 카드 하단: 감상문 미리보기 + 읽은 날짜 */}
      <div className="book-card-footer">
        {/* 감상문이 있으면 앞 80자만 미리보기로 보여줍니다 */}
        {book.content && (
          <p className="book-card-preview">
            {book.content.length > 80
              ? book.content.substring(0, 80) + '...'
              : book.content}
          </p>
        )}
        {/* 읽은 날짜 */}
        {book.read_date && (
          <span className="book-card-date">
            📅 {book.read_date}
          </span>
        )}
      </div>
    </Card>
  );
});

// export default를 별도로 하여 memo()가 적용된 컴포넌트를 내보냅니다.
export default BookCard;

/**
 * ============================================================
 * NotFoundPage.jsx — 404 에러 페이지
 * ============================================================
 * 
 * 경로: * (와일드카드 — 위에 정의된 어떤 경로에도 매칭되지 않을 때)
 * 
 * [미션 요구사항 4.2]
 *   "잘못된 주소 접근 시 Not Found 페이지가 있어야 한다"
 */

import { Link } from 'react-router-dom';
import Button from '../components/Button';
import './NotFoundPage.css';

export default function NotFoundPage() {
  return (
    <div className="notfound-page center-screen">
      {/* 큰 404 텍스트 */}
      <span className="notfound-code">404</span>
      {/* 아이콘 */}
      <span className="notfound-icon">🔍</span>
      {/* 제목 */}
      <h1 className="notfound-title">페이지를 찾을 수 없습니다</h1>
      {/* 설명 */}
      <p className="notfound-message">
        요청하신 페이지가 존재하지 않거나, 이동되었을 수 있습니다.
      </p>
      {/* 홈으로 돌아가기 버튼 */}
      <Link to="/">
        <Button variant="primary">홈으로 돌아가기</Button>
      </Link>
    </div>
  );
}

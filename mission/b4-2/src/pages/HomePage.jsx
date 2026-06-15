/**
 * ============================================================
 * HomePage.jsx — 메인(랜딩) 페이지
 * ============================================================
 * 
 * 경로: /
 * 서비스를 소개하고, 로그인/회원가입/내 기록으로 안내합니다.
 * 로그인 여부에 따라 다른 CTA(Call To Action) 버튼을 표시합니다.
 */

import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import Button from '../components/Button';
import './HomePage.css';

export default function HomePage() {
  // 현재 로그인한 사용자 정보
  const { user } = useAuth();

  return (
    <div className="home-page">
      {/* ======== 히어로 섹션 — 메인 소개 영역 ======== */}
      <section className="hero">
        {/* 배경 장식 요소 (CSS로 애니메이션) */}
        <div className="hero-bg-decoration" />

        <div className="hero-content">
          <span className="hero-badge">📖 독서 기록 서비스</span>
          <h1 className="hero-title">
            당신의 독서 여정을
            <br />
            <span className="hero-title-accent">기록하세요</span>
          </h1>
          <p className="hero-description">
            읽은 책의 감상을 기록하고, 별점을 매기고, 나만의 독서 리스트를 만들어 보세요.
            BookLog와 함께 의미 있는 독서 습관을 만들어 갑니다.
          </p>

          {/* CTA 버튼 — 로그인 여부에 따라 다른 버튼 표시 */}
          <div className="hero-actions">
            {user ? (
              // 로그인된 사용자 → "내 기록 보기" 버튼
              <Link to="/books">
                <Button variant="primary" size="large">
                  내 기록 보기 →
                </Button>
              </Link>
            ) : (
              // 비로그인 사용자 → 시작하기 + 로그인 버튼
              <>
                <Link to="/signup">
                  <Button variant="primary" size="large">
                    시작하기 →
                  </Button>
                </Link>
                <Link to="/login">
                  <Button variant="secondary" size="large">
                    로그인
                  </Button>
                </Link>
              </>
            )}
          </div>
        </div>

        {/* 히어로 일러스트 — 이모지로 표현 */}
        <div className="hero-illustration">
          <div className="hero-card hero-card-1">📚</div>
          <div className="hero-card hero-card-2">✍️</div>
          <div className="hero-card hero-card-3">⭐</div>
        </div>
      </section>

      {/* ======== 기능 소개 섹션 ======== */}
      <section className="features">
        <h2 className="features-title">BookLog의 기능</h2>
        <div className="features-grid">
          <div className="feature-item">
            <span className="feature-icon">📝</span>
            <h3 className="feature-name">독서 기록</h3>
            <p className="feature-desc">읽은 책의 제목, 저자, 감상문을 간편하게 기록하세요.</p>
          </div>
          <div className="feature-item">
            <span className="feature-icon">⭐</span>
            <h3 className="feature-name">별점 평가</h3>
            <p className="feature-desc">1~5점까지 별점을 매겨 나만의 평가를 남기세요.</p>
          </div>
          <div className="feature-item">
            <span className="feature-icon">📊</span>
            <h3 className="feature-name">한눈에 관리</h3>
            <p className="feature-desc">내 독서 기록을 목록으로 한눈에 확인하고 관리하세요.</p>
          </div>
        </div>
      </section>
    </div>
  );
}

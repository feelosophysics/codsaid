/**
 * ============================================================
 * ProfilePage.jsx — 사용자 프로필 페이지
 * ============================================================
 * 
 * 경로: /profile (보호 라우트)
 * 현재 로그인한 사용자의 정보를 표시하고, 로그아웃 기능을 제공합니다.
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import Button from '../components/Button';
import './ProfilePage.css';

export default function ProfilePage() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const [loggingOut, setLoggingOut] = useState(false);

  // ============================================================
  // 로그아웃 핸들러
  // ============================================================
  const handleSignOut = async () => {
    try {
      setLoggingOut(true);
      await signOut();
      // 로그아웃 후 홈으로 이동
      navigate('/');
    } catch (err) {
      alert('로그아웃에 실패했습니다: ' + err.message);
      setLoggingOut(false);
    }
  };

  return (
    <div className="page-container profile-page">
      <h1 className="page-title">내 프로필</h1>

      <div className="profile-card">
        {/* 프로필 아이콘 */}
        <div className="profile-avatar">
          <span className="profile-avatar-emoji">👤</span>
        </div>

        {/* 사용자 정보 */}
        <div className="profile-info">
          <div className="profile-field">
            <span className="profile-label">이메일</span>
            <span className="profile-value">{user?.email}</span>
          </div>
          <div className="profile-field">
            <span className="profile-label">가입일</span>
            <span className="profile-value">
              {user?.created_at
                ? new Date(user.created_at).toLocaleDateString('ko-KR')
                : '-'}
            </span>
          </div>
          <div className="profile-field">
            <span className="profile-label">사용자 ID</span>
            <span className="profile-value profile-id">
              {user?.id?.substring(0, 8)}...
            </span>
          </div>
        </div>

        {/* 로그아웃 버튼 */}
        <div className="profile-actions">
          <Button
            variant="danger"
            onClick={handleSignOut}
            loading={loggingOut}
          >
            로그아웃
          </Button>
        </div>
      </div>
    </div>
  );
}

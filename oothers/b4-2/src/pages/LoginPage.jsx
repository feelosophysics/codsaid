/**
 * ============================================================
 * LoginPage.jsx — 로그인 페이지
 * ============================================================
 * 
 * 경로: /login
 * 이메일/비밀번호로 Supabase Auth 로그인을 수행합니다.
 * 
 * [이벤트 → 상태 → 렌더링 흐름]
 *   입력(이벤트) → state 업데이트(상태) → 화면 갱신(렌더링)
 *   제출(이벤트) → loading true(상태) → 스피너 표시(렌더링)
 *   에러(이벤트) → error state(상태) → 에러 메시지 표시(렌더링)
 */

import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import Input from '../components/Input';
import Button from '../components/Button';
import './LoginPage.css';

export default function LoginPage() {
  // ============================================================
  // 상태 정의
  // ============================================================
  const [email, setEmail] = useState('');         // 이메일 입력값
  const [password, setPassword] = useState('');   // 비밀번호 입력값
  const [error, setError] = useState('');          // 에러 메시지
  const [loading, setLoading] = useState(false);  // 제출 중 여부

  // AuthContext에서 signIn 함수를 가져옵니다.
  const { signIn } = useAuth();
  // useNavigate: 프로그래밍 방식으로 페이지를 이동하는 함수
  const navigate = useNavigate();

  // ============================================================
  // 폼 제출 핸들러
  // ============================================================
  const handleSubmit = async (e) => {
    e.preventDefault(); // 기본 동작(페이지 새로고침) 방지
    setError('');        // 이전 에러 초기화

    // 간단한 유효성 검증
    if (!email.trim() || !password) {
      setError('이메일과 비밀번호를 입력해 주세요.');
      return;
    }

    try {
      setLoading(true);
      // Supabase Auth로 로그인 시도
      await signIn(email, password);
      // 성공 시 독서 기록 목록 페이지로 이동
      navigate('/books');
    } catch (err) {
      // 실패 시 에러 메시지 표시
      setError(err.message || '로그인에 실패했습니다. 이메일과 비밀번호를 확인해 주세요.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        {/* 페이지 헤더 */}
        <div className="auth-header">
          <h1 className="auth-title">로그인</h1>
          <p className="auth-subtitle">BookLog에 돌아오신 것을 환영합니다</p>
        </div>

        {/* 로그인 폼 */}
        <form className="auth-form" onSubmit={handleSubmit}>
          {/* 에러 메시지 */}
          {error && <div className="auth-error">⚠️ {error}</div>}

          <Input
            label="이메일"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="your@email.com"
            required
            disabled={loading}
          />

          <Input
            label="비밀번호"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="비밀번호를 입력하세요"
            required
            disabled={loading}
          />

          <Button
            type="submit"
            variant="primary"
            size="large"
            fullWidth
            loading={loading}
          >
            로그인
          </Button>
        </form>

        {/* 회원가입 안내 링크 */}
        <p className="auth-footer">
          계정이 없으신가요?{' '}
          <Link to="/signup" className="auth-link">회원가입</Link>
        </p>
      </div>
    </div>
  );
}

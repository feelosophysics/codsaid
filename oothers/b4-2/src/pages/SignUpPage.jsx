/**
 * ============================================================
 * SignUpPage.jsx — 회원가입 페이지
 * ============================================================
 * 
 * 경로: /signup
 * 이메일/비밀번호로 Supabase Auth 회원가입을 수행합니다.
 * LoginPage와 구조가 유사하지만, signUp 함수를 호출합니다.
 */

import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import Input from '../components/Input';
import Button from '../components/Button';
// LoginPage.css와 같은 스타일을 공유합니다.
import './LoginPage.css';

export default function SignUpPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState(''); // 비밀번호 확인
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');   // 성공 메시지
  const [loading, setLoading] = useState(false);

  const { signUp } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    // 유효성 검증
    if (!email.trim() || !password) {
      setError('이메일과 비밀번호를 입력해 주세요.');
      return;
    }

    if (password.length < 6) {
      setError('비밀번호는 6자 이상이어야 합니다.');
      return;
    }

    // 비밀번호 확인 일치 여부
    if (password !== confirmPassword) {
      setError('비밀번호가 일치하지 않습니다.');
      return;
    }

    try {
      setLoading(true);
      await signUp(email, password);
      // 회원가입 성공 메시지 표시
      // Supabase는 이메일 확인을 요구할 수 있으므로,
      // 바로 로그인 페이지로 이동하거나 확인 안내를 표시합니다.
      setSuccess('회원가입이 완료되었습니다! 이메일을 확인해 주세요.');
      // 2초 후 로그인 페이지로 이동
      setTimeout(() => navigate('/login'), 2000);
    } catch (err) {
      setError(err.message || '회원가입에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-header">
          <h1 className="auth-title">회원가입</h1>
          <p className="auth-subtitle">BookLog에서 독서 여정을 시작하세요</p>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          {error && <div className="auth-error">⚠️ {error}</div>}
          {success && <div className="auth-success">✅ {success}</div>}

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
            placeholder="6자 이상 입력하세요"
            required
            disabled={loading}
          />

          <Input
            label="비밀번호 확인"
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder="비밀번호를 다시 입력하세요"
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
            회원가입
          </Button>
        </form>

        <p className="auth-footer">
          이미 계정이 있으신가요?{' '}
          <Link to="/login" className="auth-link">로그인</Link>
        </p>
      </div>
    </div>
  );
}

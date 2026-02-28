import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { Eye, EyeOff, User } from 'lucide-react';

export default function Login() {
  const { login, loading } = useAuth();
  const navigate = useNavigate();
  const [loginVal, setLoginVal] = useState('');
  const [password, setPassword] = useState('');
  const [showPass, setShowPass] = useState(false);
  const [error, setError] = useState('');

  const doLogin = async (loginStr, passStr) => {
    setError('');
    try {
      const u = await login(loginStr, passStr);
      if (u.role === 'admin' || u.role === 'superadmin') navigate('/admin/overview');
      else navigate('/dashboard');
    } catch (err) {
      setError(err.message || 'Неверный логин или пароль');
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!loginVal || !password) {
      setError('Заполните все поля');
      return;
    }
    doLogin(loginVal, password);
  };

  return (
    <div className="auth-page">
      <div className="auth-card" style={{ maxWidth: 440 }}>
        <div className="auth-logo">
          <div className="auth-logo-icon">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="20 6 9 17 4 12" />
            </svg>
          </div>
          <span className="auth-logo-text">В Плюсе</span>
        </div>

        <h2 style={{ textAlign: 'center', fontSize: 20, fontWeight: 700, color: 'var(--gray-900)', marginBottom: 4, marginTop: 8 }}>
          Войти в аккаунт
        </h2>
        <p style={{ textAlign: 'center', fontSize: 13, color: 'var(--gray-500)', marginBottom: 24 }}>
          Корпоративная платформа «В Плюсе»
        </p>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div className="form-group">
            <label className="form-label">Логин</label>
            <div style={{ position: 'relative' }}>
              <User size={14} style={{ position: 'absolute', left: 11, top: '50%', transform: 'translateY(-50%)', color: 'var(--gray-400)' }} />
              <input
                className="form-input"
                type="text"
                placeholder="Введите логин"
                value={loginVal}
                onChange={(e) => setLoginVal(e.target.value)}
                style={{ paddingLeft: 32 }}
                autoComplete="username"
              />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Пароль</label>
            <div style={{ position: 'relative' }}>
              <input
                className="form-input"
                type={showPass ? 'text' : 'password'}
                placeholder="Введите пароль"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                style={{ paddingRight: 40 }}
                autoComplete="current-password"
              />
              <button
                type="button"
                onClick={() => setShowPass((s) => !s)}
                style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', color: 'var(--gray-400)', cursor: 'pointer' }}
              >
                {showPass ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          {error && (
            <div style={{ background: '#FEF2F2', border: '1px solid #FECACA', borderRadius: 'var(--radius)', padding: '8px 12px', color: 'var(--danger)', fontSize: 13, textAlign: 'center' }}>
              {error}
            </div>
          )}

          <button className="btn btn-primary btn-lg w-full" type="submit" disabled={loading} style={{ justifyContent: 'center' }}>
            {loading ? 'Вход...' : 'Войти'}
          </button>
        </form>

        <div className="auth-footer">© 2025 В Плюсе. Внутренняя корпоративная платформа.</div>
      </div>
    </div>
  );
}

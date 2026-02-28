import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Mail } from 'lucide-react';

export default function ForgotPassword() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (email) setSent(true);
  };

  if (sent) return (
    <div className="auth-page">
      <div className="auth-card" style={{ textAlign: 'center' }}>
        <div className="auth-logo" style={{ marginBottom: 16 }}>
          <div className="auth-logo-icon">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="20 6 9 17 4 12" />
            </svg>
          </div>
          <span className="auth-logo-text">В Плюсе</span>
        </div>
        <div style={{ width: 56, height: 56, borderRadius: '50%', background: '#D1FAE5', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
          <Mail size={24} color="var(--success)" />
        </div>
        <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 10 }}>Проверьте входящие</h2>
        <p style={{ fontSize: 13, color: 'var(--gray-500)', marginBottom: 24, lineHeight: 1.6 }}>
          Мы отправили инструкцию по восстановлению доступа и ссылку для сброса пароля на вашу почту или телефон.
        </p>
        <button className="btn btn-primary w-full btn-lg" style={{ justifyContent: 'center' }} onClick={() => navigate('/login')}>
          Вернуться на страницу входа
        </button>
        <p style={{ marginTop: 16, fontSize: 13, color: 'var(--gray-500)' }}>
          Не пришло сообщение?{' '}
          <span style={{ color: 'var(--primary)', cursor: 'pointer' }} onClick={() => setSent(false)}>Отправить повторно</span>
        </p>
        <div className="auth-footer">© 2025 В Плюсе. Внутренняя корпоративная платформа.</div>
      </div>
    </div>
  );

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-logo">
          <div className="auth-logo-icon">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="20 6 9 17 4 12" />
            </svg>
          </div>
          <span className="auth-logo-text">В Плюсе</span>
        </div>
        <h2 style={{ textAlign: 'center', fontSize: 22, fontWeight: 700, color: 'var(--gray-900)', marginBottom: 6 }}>Восстановление пароля</h2>
        <p style={{ textAlign: 'center', fontSize: 13, color: 'var(--gray-500)', marginBottom: 28 }}>
          Введите email или телефон для получения ссылки
        </p>
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div className="form-group">
            <label className="form-label">Email или телефон</label>
            <input className="form-input" placeholder="email@vpluse.kg" value={email} onChange={e => setEmail(e.target.value)} />
          </div>
          <button className="btn btn-primary btn-lg w-full" type="submit" style={{ justifyContent: 'center', marginTop: 4 }}>
            Отправить
          </button>
          <button type="button" className="btn btn-secondary btn-lg w-full" style={{ justifyContent: 'center' }} onClick={() => navigate('/login')}>
            Назад
          </button>
        </form>
        <div className="auth-footer">© 2025 В Плюсе. Внутренняя корпоративная платформа.</div>
      </div>
    </div>
  );
}

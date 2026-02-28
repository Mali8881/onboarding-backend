import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bell, ChevronDown, LogOut, User } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useLocale } from '../../context/LocaleContext';
import {
  getNotificationsForUser,
  getUnreadCountForUser,
  markAllNotificationsRead,
} from '../../utils/notifications';

const ROLE_COLORS = {
  intern:         '#2563EB',
  employee:       '#16A34A',
  projectmanager: '#7C3AED',
  admin:          '#EA580C',
  superadmin:     '#BE123C',
};

export default function Header({ title }) {
  const { user, logout } = useAuth();
  const { locale, setLocale, t } = useLocale();
  const navigate = useNavigate();
  const [dropOpen, setDropOpen] = useState(false);
  const [notifOpen, setNotifOpen] = useState(false);
  const [notifs, setNotifs] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);

  const initials = user?.name?.split(' ').map(p => p[0]).join('').slice(0, 2).toUpperCase() || '??';
  const roleColor = ROLE_COLORS[user?.role] || '#2563EB';
  const firstName = user?.name?.split(' ')[0] || '';

  const refreshNotifications = () => {
    if (!user) return;
    setNotifs(getNotificationsForUser(user));
    setUnreadCount(getUnreadCountForUser(user));
  };

  useEffect(() => {
    refreshNotifications();
    const i = setInterval(refreshNotifications, 5000);
    return () => clearInterval(i);
  }, [user?.id, user?.role]);

  const readAllNotifications = () => {
    if (!user) return;
    markAllNotificationsRead(user.id, notifs.map(n => n.id));
    setUnreadCount(0);
  };

  return (
    <header className="header">
      <div className="header-title">{title || ''}</div>
      <div style={{ flex: 1, paddingLeft: 20, fontSize: 14, color: 'var(--gray-500)', display: 'flex', alignItems: 'center', gap: 6 }}>
        {t('header.welcome', 'Добро пожаловать')}, <b style={{ color: 'var(--gray-800)' }}>{firstName}!</b>
      </div>
      <div className="header-lang" style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
        {['ru', 'en', 'kg'].map((code, idx) => (
          <button
            key={code}
            type="button"
            onClick={() => setLocale(code)}
            style={{
              border: 'none',
              background: 'transparent',
              padding: 0,
              margin: 0,
              cursor: 'pointer',
              color: locale === code ? 'var(--primary)' : 'var(--gray-500)',
              fontWeight: locale === code ? 700 : 500,
              fontSize: 14,
            }}
          >
            {t(`lang.${code}`, code.toUpperCase())}
            {idx < 2 ? ' /' : ''}
          </button>
        ))}
      </div>
      <div className="header-notif" style={{ position: 'relative', cursor: 'pointer' }} onClick={() => { setNotifOpen(o => !o); refreshNotifications(); }}>
        <Bell size={18} color="var(--gray-500)" />
        {unreadCount > 0 && <div className="header-notif-badge" />}
        {notifOpen && (
          <div style={{ position: 'absolute', top: '100%', right: -20, marginTop: 8, width: 360, maxWidth: 'calc(100vw - 24px)', background: 'var(--white)', border: '1px solid var(--gray-200)', borderRadius: 'var(--radius-lg)', boxShadow: 'var(--shadow-lg)', zIndex: 120 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 12px', borderBottom: '1px solid var(--gray-100)' }}>
              <div style={{ fontSize: 13, fontWeight: 700 }}>{t('header.notifications', 'Уведомления')}</div>
              <button className="btn btn-secondary btn-sm" onClick={(e) => { e.stopPropagation(); readAllNotifications(); }}>
                {t('header.read', 'Прочитано')}
              </button>
            </div>
            <div style={{ maxHeight: 360, overflow: 'auto', padding: 8 }}>
              {notifs.length === 0 && (
                <div style={{ fontSize: 12, color: 'var(--gray-500)', padding: 8 }}>{t('header.noEvents', 'Новых событий нет.')}</div>
              )}
              {notifs.map(n => (
                <div key={n.id} style={{ padding: '8px 10px', borderBottom: '1px solid var(--gray-100)' }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--gray-800)' }}>{n.title}</div>
                  <div style={{ fontSize: 12, color: 'var(--gray-600)', marginTop: 2 }}>{n.text}</div>
                  {n.ts && <div style={{ fontSize: 11, color: 'var(--gray-400)', marginTop: 3 }}>{String(n.ts)}</div>}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
      <div className="header-user" onClick={() => setDropOpen(o => !o)} style={{ position: 'relative' }}>
        <div className="header-user-info">
          <div className="header-user-name">{user?.name?.split(' ').slice(0, 2).join(' ')}</div>
          <div className="header-user-role">{user?.roleLabel}</div>
        </div>
        <div className="avatar" style={{ width: 36, height: 36, background: roleColor }}>{initials}</div>
        <ChevronDown size={14} color="var(--gray-500)" />

        {dropOpen && (
          <div style={{ position: 'absolute', top: '100%', right: 0, marginTop: 6, background: 'var(--white)', border: '1px solid var(--gray-200)', borderRadius: 'var(--radius-lg)', boxShadow: 'var(--shadow-lg)', minWidth: 210, zIndex: 100, padding: '4px 0' }}>
            <div style={{ padding: '10px 14px 8px', borderBottom: '1px solid var(--gray-100)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <div style={{ width: 40, height: 40, borderRadius: '50%', background: roleColor, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 14, fontWeight: 700, color: 'white', flexShrink: 0 }}>{initials}</div>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 600 }}>{user?.name}</div>
                  <div style={{ fontSize: 11, color: 'var(--gray-500)' }}>{user?.position}</div>
                  <div style={{ fontSize: 11, marginTop: 2, display: 'inline-block', padding: '1px 6px', borderRadius: 10, background: roleColor + '20', color: roleColor, fontWeight: 600 }}>{user?.roleLabel}</div>
                </div>
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 14px', cursor: 'pointer', fontSize: 14, color: 'var(--gray-700)' }}
              onClick={() => { navigate('/profile'); setDropOpen(false); }}>
              <User size={15} /> {t('header.profile', 'Профиль')}
            </div>
            <div style={{ height: 1, background: 'var(--gray-200)', margin: '4px 0' }} />
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 14px', cursor: 'pointer', fontSize: 14, color: 'var(--danger)' }}
              onClick={() => { logout(); navigate('/login'); }}>
              <LogOut size={15} /> {t('header.logout', 'Выйти')}
            </div>
          </div>
        )}
      </div>
    </header>
  );
}

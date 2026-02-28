import { useEffect, useMemo, useState } from 'react';
import MainLayout from '../../layouts/MainLayout';
import { usersAPI } from '../../api/auth';

const ROLE_META = {
  superadmin: {
    label: 'Суперадминистратор',
    icon: '👑',
    desc: 'Полный доступ к системе, ролям и безопасности.',
    perms: ['Полный доступ', 'Управление пользователями', 'Системные настройки'],
  },
  admin: {
    label: 'Администратор',
    icon: '🛡',
    desc: 'Операционная работа с контентом и пользователями.',
    perms: ['Пользователи', 'Контент', 'Онбординг', 'Обратная связь'],
  },
  projectmanager: {
    label: 'Проект-менеджер',
    icon: '📋',
    desc: 'Управление задачами команды и процессами отдела.',
    perms: ['Задачи команды', 'Структура отдела', 'Просмотр отчетов'],
  },
  employee: {
    label: 'Сотрудник',
    icon: '👤',
    desc: 'Работа в личном кабинете, задачи, расписание.',
    perms: ['Личный кабинет', 'Задачи', 'График'],
  },
  intern: {
    label: 'Стажер',
    icon: '🎓',
    desc: 'Прохождение онбординга и сдача отчетов.',
    perms: ['Онбординг', 'Регламенты', 'Отчеты'],
  },
};

export default function AdminRoles() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError('');
      try {
        const res = await usersAPI.list();
        setUsers(Array.isArray(res.data) ? res.data : []);
      } catch (e) {
        setError(e.response?.data?.detail || 'Не удалось загрузить роли.');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const roleCards = useMemo(() => {
    const counts = users.reduce((acc, user) => {
      const key = user.role || 'employee';
      acc[key] = (acc[key] || 0) + 1;
      return acc;
    }, {});

    return Object.entries(ROLE_META).map(([id, meta]) => ({
      id,
      ...meta,
      count: counts[id] || 0,
    }));
  }, [users]);

  return (
    <MainLayout title="Управление системой">
      <div className="page-header">
        <div>
          <div className="page-title">Роли и права доступа</div>
          <div className="page-subtitle">Сводка по ролям в текущем составе пользователей</div>
        </div>
      </div>

      {error && <div className="card" style={{ marginBottom: 12 }}><div className="card-body" style={{ color: '#b91c1c' }}>{error}</div></div>}
      {loading && <div className="card"><div className="card-body">Загрузка...</div></div>}

      {!loading && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 16 }}>
          {roleCards.map((role) => (
            <div key={role.id} className="card">
              <div className="card-body">
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                  <span style={{ fontSize: 18 }}>{role.icon}</span>
                  <span style={{ fontWeight: 700, fontSize: 16 }}>{role.label}</span>
                </div>
                <p style={{ fontSize: 13, color: 'var(--gray-500)', marginBottom: 14, lineHeight: 1.5 }}>{role.desc}</p>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 14 }}>
                  {role.perms.map((perm) => (
                    <span key={perm} className="badge badge-blue" style={{ fontSize: 11 }}>{perm}</span>
                  ))}
                </div>
                <div style={{ fontSize: 12, color: 'var(--gray-500)' }}>Пользователей: {role.count}</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </MainLayout>
  );
}

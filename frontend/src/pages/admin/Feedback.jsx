import { useEffect, useMemo, useState } from 'react';
import { Eye, CheckCircle, Clock, AlertCircle } from 'lucide-react';
import MainLayout from '../../layouts/MainLayout';
import { feedbackAPI } from '../../api/content';

const STATUS_LABELS = { new: 'Новое', in_progress: 'В работе', closed: 'Закрыто' };
const STATUS_COLORS = { new: 'badge-blue', in_progress: 'badge-yellow', closed: 'badge-green' };
const STATUS_ICONS = {
  new: <AlertCircle size={14} />,
  in_progress: <Clock size={14} />,
  closed: <CheckCircle size={14} />,
};

function normalize(item) {
  return {
    id: item.id,
    type: item.type || 'review',
    text: item.text || '',
    status: item.status || 'new',
    isAnonymous: Boolean(item.is_anonymous),
    fullName: item.full_name || '',
    createdAt: item.created_at,
  };
}

export default function AdminFeedback() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState('all');
  const [selected, setSelected] = useState(null);

  const load = async () => {
    try {
      setLoading(true);
      const res = await feedbackAPI.list();
      const list = Array.isArray(res.data) ? res.data : [];
      setItems(list.map(normalize));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load().catch(() => setItems([]));
  }, []);

  const filtered = useMemo(
    () => (filterStatus === 'all' ? items : items.filter((i) => i.status === filterStatus)),
    [items, filterStatus]
  );

  const counts = useMemo(
    () => ({
      all: items.length,
      new: items.filter((i) => i.status === 'new').length,
      in_progress: items.filter((i) => i.status === 'in_progress').length,
      closed: items.filter((i) => i.status === 'closed').length,
    }),
    [items]
  );

  const setStatus = async (id, status) => {
    await feedbackAPI.reply(id, { status });
    setItems((prev) => prev.map((i) => (i.id === id ? { ...i, status } : i)));
    if (selected?.id === id) setSelected((prev) => ({ ...prev, status }));
  };

  return (
    <MainLayout title="Админ-панель · Обратная связь">
      <div className="page-header">
        <div>
          <div className="page-title">Обратная связь</div>
          <div className="page-subtitle">Список обращений из backend</div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 20 }}>
        {[
          { key: 'all', label: 'Всего' },
          { key: 'new', label: 'Новые' },
          { key: 'in_progress', label: 'В работе' },
          { key: 'closed', label: 'Закрыто' },
        ].map((s) => (
          <div key={s.key} className="card" style={{ cursor: 'pointer' }} onClick={() => setFilterStatus(s.key)}>
            <div className="card-body" style={{ padding: '14px 16px' }}>
              <div style={{ fontSize: 24, fontWeight: 700 }}>{counts[s.key] || 0}</div>
              <div style={{ fontSize: 12, color: 'var(--gray-500)', marginTop: 2 }}>{s.label}</div>
            </div>
          </div>
        ))}
      </div>

      <div className="card">
        <div className="card-body" style={{ padding: 0 }}>
          {loading ? (
            <div style={{ padding: 16 }}>Загрузка...</div>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Тип</th>
                  <th>Сообщение</th>
                  <th>Автор</th>
                  <th>Дата</th>
                  <th>Статус</th>
                  <th>Действия</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((item) => (
                  <tr key={item.id}>
                    <td><span className="badge badge-gray">{item.type}</span></td>
                    <td style={{ maxWidth: 360, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: 13 }}>{item.text}</td>
                    <td style={{ fontSize: 13 }}>{item.isAnonymous ? 'Анонимно' : (item.fullName || 'Пользователь')}</td>
                    <td style={{ fontSize: 13, color: 'var(--gray-500)' }}>{item.createdAt ? new Date(item.createdAt).toLocaleString('ru-RU') : '-'}</td>
                    <td>
                      <span className={`badge ${STATUS_COLORS[item.status] || 'badge-gray'}`} style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                        {STATUS_ICONS[item.status]} {STATUS_LABELS[item.status] || item.status}
                      </span>
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: 6 }}>
                        <button className="btn-icon" title="Посмотреть" onClick={() => setSelected(item)}><Eye size={14} /></button>
                        {item.status !== 'in_progress' ? <button className="btn btn-secondary btn-sm" onClick={() => setStatus(item.id, 'in_progress')}>В работу</button> : null}
                        {item.status !== 'closed' ? <button className="btn btn-sm" style={{ background: 'var(--success-light)', color: 'var(--success)', border: 'none' }} onClick={() => setStatus(item.id, 'closed')}>Закрыть</button> : null}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {selected ? (
        <div className="modal-overlay" onClick={() => setSelected(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title">Обращение #{selected.id}</div>
              <button className="btn btn-secondary btn-sm" onClick={() => setSelected(null)}>Закрыть</button>
            </div>
            <div className="modal-body">
              <div style={{ marginBottom: 10 }}><b>Тип:</b> {selected.type}</div>
              <div style={{ marginBottom: 10 }}><b>Статус:</b> {STATUS_LABELS[selected.status] || selected.status}</div>
              <div style={{ marginBottom: 10 }}><b>Автор:</b> {selected.isAnonymous ? 'Анонимно' : (selected.fullName || 'Пользователь')}</div>
              <div><b>Текст:</b><div style={{ marginTop: 6 }}>{selected.text}</div></div>
            </div>
          </div>
        </div>
      ) : null}
    </MainLayout>
  );
}

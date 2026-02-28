import { useEffect, useMemo, useState } from 'react';
import { CheckCircle, Eye, RotateCcw, X, XCircle } from 'lucide-react';
import MainLayout from '../../layouts/MainLayout';
import { onboardingAPI } from '../../api/content';

const STATUS = {
  DRAFT: { label: 'Черновик', cls: 'badge-gray' },
  SENT: { label: 'Отправлен', cls: 'badge-blue' },
  ACCEPTED: { label: 'Принят', cls: 'badge-green' },
  REVISION: { label: 'На доработке', cls: 'badge-yellow' },
  REJECTED: { label: 'Отклонен', cls: 'badge-red' },
};

export default function AdminOnboarding() {
  const [days, setDays] = useState([]);
  const [reports, setReports] = useState([]);
  const [selected, setSelected] = useState(null);
  const [comment, setComment] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [toast, setToast] = useState('');

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const [daysRes, reportsRes] = await Promise.all([
        onboardingAPI.listDays(),
        onboardingAPI.getReports(),
      ]);
      setDays(Array.isArray(daysRes.data) ? daysRes.data : []);
      setReports(Array.isArray(reportsRes.data) ? reportsRes.data : []);
    } catch (e) {
      setError(e.response?.data?.detail || 'Не удалось загрузить onboarding данные.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const grouped = useMemo(() => {
    const map = new Map();
    reports.forEach((r) => {
      const key = `${r.user_id}:${r.full_name || r.username || r.user_id}`;
      if (!map.has(key)) map.set(key, []);
      map.get(key).push(r);
    });
    return Array.from(map.entries()).map(([key, items]) => {
      const [userId, name] = key.split(':');
      const done = items.filter((x) => String(x.status || '').toUpperCase() === 'ACCEPTED').length;
      return { userId, name, done, total: Math.max(days.length, items.length), items };
    });
  }, [reports, days]);

  const review = async (reportId, status) => {
    try {
      await onboardingAPI.reviewReport(reportId, {
        status,
        comment,
      });
      setSelected(null);
      setComment('');
      setToast(status === 'ACCEPTED' ? 'Отчет принят' : status === 'REVISION' ? 'Отправлен на доработку' : 'Отчет отклонен');
      setTimeout(() => setToast(''), 2500);
      await load();
    } catch (e) {
      setError(e.response?.data?.detail || 'Не удалось изменить статус отчета.');
    }
  };

  return (
    <MainLayout title="Админ-панель · Онбординг / Отчеты">
      <div className="page-header">
        <div className="page-title">Онбординг / Отчеты</div>
        <div className="page-subtitle">Проверка отчетов стажеров и контроль прогресса</div>
      </div>

      {error && <div className="card" style={{ marginBottom: 12 }}><div className="card-body" style={{ color: '#b91c1c' }}>{error}</div></div>}
      {loading && <div className="card"><div className="card-body">Загрузка...</div></div>}

      {!loading && (
        <div style={{ display: 'grid', gap: 14 }}>
          <div className="card">
            <div className="card-header"><span className="card-title">Прогресс стажеров</span></div>
            <div className="card-body" style={{ display: 'grid', gap: 10 }}>
              {grouped.map((item) => {
                const percent = item.total > 0 ? Math.round((item.done / item.total) * 100) : 0;
                return (
                  <div key={item.userId} style={{ border: '1px solid var(--gray-200)', borderRadius: 'var(--radius)', padding: 12 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                      <div style={{ fontWeight: 600 }}>{item.name}</div>
                      <div style={{ fontSize: 12, color: 'var(--gray-500)' }}>{item.done}/{item.total} дней принято</div>
                    </div>
                    <div style={{ height: 7, background: 'var(--gray-200)', borderRadius: 999, overflow: 'hidden' }}>
                      <div style={{ height: '100%', width: `${percent}%`, background: percent === 100 ? '#16A34A' : '#2563EB' }} />
                    </div>
                  </div>
                );
              })}
              {grouped.length === 0 && <div style={{ color: 'var(--gray-500)' }}>Отчетов пока нет.</div>}
            </div>
          </div>

          <div className="card">
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>СТАЖЕР</th>
                    <th>ДЕНЬ</th>
                    <th>ОБНОВЛЕНО</th>
                    <th>СТАТУС</th>
                    <th>ДЕЙСТВИЯ</th>
                  </tr>
                </thead>
                <tbody>
                  {reports.map((r) => (
                    <tr key={r.id}>
                      <td>{r.full_name || r.username || r.user_id}</td>
                      <td>День {r.day_number}</td>
                      <td>{String(r.updated_at || '').slice(0, 16).replace('T', ' ')}</td>
                      <td><span className={`badge ${STATUS[r.status]?.cls || 'badge-gray'}`}>{STATUS[r.status]?.label || r.status}</span></td>
                      <td>
                        <div style={{ display: 'flex', gap: 4 }}>
                          <button className="btn-icon" onClick={() => setSelected(r)} title="Просмотр"><Eye size={14} /></button>
                          {r.status === 'SENT' && (
                            <>
                              <button className="btn-icon" style={{ color: 'var(--success)' }} onClick={() => review(r.id, 'ACCEPTED')} title="Принять"><CheckCircle size={14} /></button>
                              <button className="btn-icon" style={{ color: 'var(--warning)' }} onClick={() => setSelected(r)} title="На доработку"><RotateCcw size={14} /></button>
                              <button className="btn-icon" style={{ color: 'var(--danger)' }} onClick={() => review(r.id, 'REJECTED')} title="Отклонить"><XCircle size={14} /></button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                  {reports.length === 0 && (
                    <tr><td colSpan={5}>Отчетов пока нет.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {selected && (
        <div className="modal-overlay" onClick={() => setSelected(null)}>
          <div className="modal" style={{ width: 620 }} onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title">Отчет: {selected.full_name || selected.username} · День {selected.day_number}</div>
              <button className="btn-icon" onClick={() => setSelected(null)}><X size={18} /></button>
            </div>
            <div className="modal-body">
              <ViewBlock label="Что сделал" value={selected.did} />
              <ViewBlock label="Что буду делать" value={selected.will_do} />
              <ViewBlock label="Проблемы" value={selected.problems} />
              {selected.status === 'SENT' && (
                <div className="form-group">
                  <label className="form-label">Комментарий</label>
                  <textarea className="form-textarea" value={comment} onChange={(e) => setComment(e.target.value)} style={{ minHeight: 90 }} />
                </div>
              )}
            </div>
            {selected.status === 'SENT' && (
              <div className="modal-footer">
                <button className="btn btn-secondary" onClick={() => setSelected(null)}>Закрыть</button>
                <button className="btn btn-sm" style={{ background: '#FEF9C3', color: '#854D0E', border: '1px solid #FDE047' }} onClick={() => review(selected.id, 'REVISION')}>
                  <RotateCcw size={13} /> На доработку
                </button>
                <button className="btn btn-danger btn-sm" onClick={() => review(selected.id, 'REJECTED')}>Отклонить</button>
                <button className="btn btn-primary btn-sm" onClick={() => review(selected.id, 'ACCEPTED')}>
                  <CheckCircle size={13} /> Принять
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {toast && <div className="toast toast-success"><div><div className="toast-title">Готово</div><div className="toast-msg">{toast}</div></div></div>}
    </MainLayout>
  );
}

function ViewBlock({ label, value }) {
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 6 }}>{label}</div>
      <div style={{ fontSize: 13, color: 'var(--gray-700)', background: 'var(--gray-50)', border: '1px solid var(--gray-200)', borderRadius: 'var(--radius)', padding: '10px 14px', lineHeight: 1.5 }}>
        {value || '—'}
      </div>
    </div>
  );
}

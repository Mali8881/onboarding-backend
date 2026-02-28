import { useEffect, useMemo, useState } from 'react';
import MainLayout from '../../layouts/MainLayout';
import { usersAPI } from '../../api/auth';
import { auditAPI, feedbackAPI, onboardingAPI } from '../../api/content';

export default function AdminOverview() {
  const [users, setUsers] = useState([]);
  const [audit, setAudit] = useState([]);
  const [feedback, setFeedback] = useState([]);
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError('');
      try {
        const [usersRes, auditRes, feedbackRes, reportsRes] = await Promise.all([
          usersAPI.list(),
          auditAPI.list().catch(() => ({ data: [] })),
          feedbackAPI.list().catch(() => ({ data: [] })),
          onboardingAPI.getReports().catch(() => ({ data: [] })),
        ]);
        setUsers(Array.isArray(usersRes.data) ? usersRes.data : []);
        setAudit(Array.isArray(auditRes.data) ? auditRes.data : []);
        setFeedback(Array.isArray(feedbackRes.data) ? feedbackRes.data : []);
        setReports(Array.isArray(reportsRes.data) ? reportsRes.data : []);
      } catch (e) {
        setError(e.response?.data?.detail || 'Не удалось загрузить overview.');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const stats = useMemo(() => {
    const activeUsers = users.filter((u) => u.is_active).length;
    const interns = users.filter((u) => u.role === 'intern').length;
    const admins = users.filter((u) => u.role === 'admin' || u.role === 'superadmin').length;
    const sentReports = reports.filter((r) => String(r.status || '').toUpperCase() === 'SENT').length;
    const newFeedback = feedback.filter((f) => f.status === 'new').length;
    return { activeUsers, interns, admins, sentReports, newFeedback };
  }, [users, reports, feedback]);

  return (
    <MainLayout title="Админ-панель">
      <div className="page-header">
        <div>
          <div className="page-title">Обзор системы</div>
          <div className="page-subtitle">Ключевые показатели и последние события</div>
        </div>
      </div>

      {error && <div className="card" style={{ marginBottom: 12 }}><div className="card-body" style={{ color: '#b91c1c' }}>{error}</div></div>}
      {loading && <div className="card"><div className="card-body">Загрузка...</div></div>}

      {!loading && (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, minmax(120px, 1fr))', gap: 12, marginBottom: 20 }}>
            <Metric title="Пользователи" value={users.length} />
            <Metric title="Активные" value={stats.activeUsers} />
            <Metric title="Стажеры" value={stats.interns} />
            <Metric title="Админы" value={stats.admins} />
            <Metric title="Отчеты SENT" value={stats.sentReports} />
          </div>

          <div className="grid-2" style={{ gap: 20 }}>
            <div className="card">
              <div className="card-header"><span className="card-title">Последние события аудита</span></div>
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr><th>ВРЕМЯ</th><th>ACTOR</th><th>ACTION</th><th>LEVEL</th></tr>
                  </thead>
                  <tbody>
                    {audit.slice(0, 10).map((row) => (
                      <tr key={row.id}>
                        <td>{String(row.created_at || '').slice(0, 16).replace('T', ' ')}</td>
                        <td>{row.actor_username || '-'}</td>
                        <td>{row.action}</td>
                        <td>{row.level || '-'}</td>
                      </tr>
                    ))}
                    {audit.length === 0 && (
                      <tr><td colSpan={4}>Событий пока нет.</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="card">
              <div className="card-header"><span className="card-title">Очередь обратной связи</span></div>
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr><th>ID</th><th>ТИП</th><th>СТАТУС</th><th>СОЗДАНО</th></tr>
                  </thead>
                  <tbody>
                    {feedback.slice(0, 10).map((row) => (
                      <tr key={row.id}>
                        <td>{row.id}</td>
                        <td>{row.type}</td>
                        <td>{row.status}</td>
                        <td>{String(row.created_at || '').slice(0, 16).replace('T', ' ')}</td>
                      </tr>
                    ))}
                    {feedback.length === 0 && (
                      <tr><td colSpan={4}>Обращений пока нет.</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
              <div className="card-body" style={{ paddingTop: 0, color: 'var(--gray-500)', fontSize: 12 }}>
                Новые: {stats.newFeedback}
              </div>
            </div>
          </div>
        </>
      )}
    </MainLayout>
  );
}

function Metric({ title, value }) {
  return (
    <div className="card">
      <div className="card-body">
        <div style={{ fontSize: 12, color: 'var(--gray-500)', marginBottom: 4 }}>{title}</div>
        <div style={{ fontSize: 24, fontWeight: 800 }}>{value}</div>
      </div>
    </div>
  );
}

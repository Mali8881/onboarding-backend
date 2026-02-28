import { useEffect, useMemo, useState } from 'react';
import MainLayout from '../../layouts/MainLayout';
import { companyAPI } from '../../api/content';

const NODE_COLORS = ['#D9F99D', '#FDE68A', '#C4B5FD', '#F9A8D4', '#93C5FD', '#67E8F9', '#FCA5A5', '#FDBA74'];

export default function Company() {
  const [tab, setTab] = useState('structure');
  const [structure, setStructure] = useState(null);
  const [org, setOrg] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError('');
      try {
        const [structureRes, orgRes] = await Promise.all([
          companyAPI.structure(),
          companyAPI.org(),
        ]);
        setStructure(structureRes.data || null);
        setOrg(orgRes.data || null);
      } catch (e) {
        setError(e.response?.data?.detail || 'Не удалось загрузить данные компании.');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const employees = useMemo(() => {
    const rows = [];
    (org?.departments || []).forEach((dep) => {
      (dep.members || []).forEach((member) => {
        rows.push({
          id: member.id,
          full_name: member.full_name || member.username || `#${member.id}`,
          department: dep.name || '-',
          position: member.position || '-',
          role: member.role || '-',
        });
      });
    });
    return rows;
  }, [org]);

  return (
    <MainLayout title="Компания">
      <div className="page-header">
        <div>
          <div className="page-title">Компания</div>
          <div className="page-subtitle">Структура компании и сотрудники</div>
        </div>
      </div>

      {error && <div className="card" style={{ marginBottom: 12 }}><div className="card-body" style={{ color: '#b91c1c' }}>{error}</div></div>}
      {loading && <div className="card"><div className="card-body">Загрузка...</div></div>}

      {!loading && (
        <>
          <div className="tabs" style={{ marginBottom: 14 }}>
            <button className={`tab-btn ${tab === 'structure' ? 'active' : ''}`} onClick={() => setTab('structure')}>Структура</button>
            <button className={`tab-btn ${tab === 'employees' ? 'active' : ''}`} onClick={() => setTab('employees')}>Сотрудники</button>
          </div>

          {tab === 'structure' && (
            <div className="card">
              <div className="card-body" style={{ overflowX: 'auto' }}>
                <div style={{ minWidth: 900 }}>
                  <div style={{ textAlign: 'center', fontSize: 32, fontWeight: 700, color: 'var(--gray-900)', marginBottom: 12 }}>
                    Структура компании
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 18 }}>
                    <div style={{ background: '#A3E635', border: '1px solid #84CC16', borderRadius: 10, padding: '10px 14px', minWidth: 240, textAlign: 'center' }}>
                      <div style={{ fontSize: 13, fontWeight: 700 }}>Руководитель</div>
                      <div style={{ fontSize: 12 }}>{structure?.owner?.full_name || '—'}</div>
                    </div>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: `repeat(${Math.max(1, (structure?.departments || []).length)}, minmax(170px, 1fr))`, gap: 10 }}>
                    {(structure?.departments || []).map((dep, i) => (
                      <div key={dep.id} style={{ background: NODE_COLORS[i % NODE_COLORS.length], border: '1px solid rgba(0,0,0,0.08)', borderRadius: 10, padding: 10, minHeight: 170 }}>
                        <div style={{ fontSize: 15, fontWeight: 700, marginBottom: 4 }}>{dep.name}</div>
                        <div style={{ fontSize: 12, marginBottom: 8 }}>
                          Руководитель: {dep.head?.full_name || dep.head?.username || 'Не назначен'}
                        </div>
                        <div style={{ fontSize: 11, color: 'var(--gray-600)' }}>
                          Сотрудники: {(org?.departments || []).find((d) => d.id === dep.id)?.members?.length || 0}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {tab === 'employees' && (
            <div className="card">
              <div className="card-header"><span className="card-title">Сотрудники компании</span></div>
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr>
                      <th>СОТРУДНИК</th>
                      <th>ОТДЕЛ</th>
                      <th>ДОЛЖНОСТЬ</th>
                      <th>РОЛЬ</th>
                    </tr>
                  </thead>
                  <tbody>
                    {employees.map((u) => (
                      <tr key={`${u.id}-${u.department}`}>
                        <td>{u.full_name}</td>
                        <td>{u.department}</td>
                        <td>{u.position}</td>
                        <td>{u.role}</td>
                      </tr>
                    ))}
                    {employees.length === 0 && (
                      <tr>
                        <td colSpan={4} style={{ color: 'var(--gray-500)' }}>Данные не найдены.</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </MainLayout>
  );
}

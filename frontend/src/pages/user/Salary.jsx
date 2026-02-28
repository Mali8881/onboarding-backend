import { useEffect, useMemo, useState } from 'react';
import { Check, DollarSign, Pencil, X } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { payrollAPI } from '../../api/content';
import MainLayout from '../../layouts/MainLayout';

const fmt = (value) => `${Number(value || 0).toLocaleString('ru-RU')} KGS`;

const monthMeta = () => {
  const now = new Date();
  return { year: now.getFullYear(), month: now.getMonth() + 1 };
};

const toPayTypeLabel = (value) => {
  if (value === 'hourly') return 'Почасовая';
  if (value === 'daily') return 'Дневная';
  return 'Оклад';
};

function MySalary({ payrollEntry, loading, error }) {
  if (loading) {
    return <div className="card"><div className="card-body">Загрузка...</div></div>;
  }
  if (error) {
    return <div className="card"><div className="card-body" style={{ color: '#b91c1c' }}>{error}</div></div>;
  }
  if (!payrollEntry) {
    return (
      <div className="card">
        <div className="card-body" style={{ textAlign: 'center', padding: 60 }}>
          <DollarSign size={40} style={{ color: 'var(--gray-200)', marginBottom: 12 }} />
          <div style={{ fontSize: 16, fontWeight: 600, color: 'var(--gray-500)' }}>Расчет за месяц пока не сформирован</div>
        </div>
      </div>
    );
  }

  return (
    <>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 16, marginBottom: 20 }}>
        <div className="card" style={{ borderTop: '3px solid #16A34A' }}>
          <div className="card-body">
            <div style={{ fontSize: 12, color: 'var(--gray-500)', marginBottom: 6 }}>Итого за текущий месяц</div>
            <div style={{ fontSize: 26, fontWeight: 800 }}>{fmt(payrollEntry.total_amount)}</div>
          </div>
        </div>
        <div className="card">
          <div className="card-body">
            <div style={{ fontSize: 12, color: 'var(--gray-500)', marginBottom: 6 }}>Начисление</div>
            <div style={{ fontSize: 22, fontWeight: 700 }}>{fmt(payrollEntry.salary_amount)}</div>
            <div style={{ fontSize: 12, color: 'var(--gray-400)', marginTop: 6 }}>
              Дней: {payrollEntry.worked_days}/{payrollEntry.planned_days}
            </div>
          </div>
        </div>
        <div className="card">
          <div className="card-body">
            <div style={{ fontSize: 12, color: 'var(--gray-500)', marginBottom: 6 }}>Авансы</div>
            <div style={{ fontSize: 22, fontWeight: 700 }}>{fmt(payrollEntry.advances)}</div>
            <div style={{ fontSize: 12, color: 'var(--gray-400)', marginTop: 6 }}>Период: {payrollEntry.period?.month}/{payrollEntry.period?.year}</div>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header"><span className="card-title">Детали начисления</span></div>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr><th>ПОЛЕ</th><th>ЗНАЧЕНИЕ</th></tr>
            </thead>
            <tbody>
              <tr><td>Плановые дни</td><td>{payrollEntry.planned_days}</td></tr>
              <tr><td>Отработанные дни</td><td>{payrollEntry.worked_days}</td></tr>
              <tr><td>Начисленная сумма</td><td>{fmt(payrollEntry.salary_amount)}</td></tr>
              <tr><td>Авансы</td><td>{fmt(payrollEntry.advances)}</td></tr>
              <tr><td>К выплате</td><td style={{ fontWeight: 700 }}>{fmt(payrollEntry.total_amount)}</td></tr>
              <tr><td>Статус периода</td><td>{payrollEntry.period?.status || '-'}</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}

function TeamSalaries({ usersById, profiles, payrollRows, loading, error, onGenerate, onSaveProfile }) {
  const [modal, setModal] = useState(false);
  const [editProfile, setEditProfile] = useState(null);
  const [form, setForm] = useState({ base_salary: '', employment_type: 'fixed', currency: 'KGS', is_active: true });

  const payrollByUser = useMemo(() => {
    const map = new Map();
    payrollRows.forEach((row) => map.set(Number(row.user), row));
    return map;
  }, [payrollRows]);

  const openEdit = (profile) => {
    setEditProfile(profile);
    setForm({
      base_salary: String(profile.base_salary || 0),
      employment_type: profile.employment_type || 'fixed',
      currency: profile.currency || 'KGS',
      is_active: profile.is_active !== false,
    });
    setModal(true);
  };

  const saveProfile = async () => {
    if (!editProfile) return;
    await onSaveProfile(editProfile.id, {
      base_salary: Number(form.base_salary) || 0,
      employment_type: form.employment_type,
      currency: form.currency || 'KGS',
      is_active: !!form.is_active,
    });
    setModal(false);
  };

  return (
    <>
      {error && <div className="card" style={{ marginBottom: 12 }}><div className="card-body" style={{ color: '#b91c1c' }}>{error}</div></div>}

      <div style={{ marginBottom: 14, display: 'flex', gap: 8 }}>
        <button className="btn btn-secondary" type="button" onClick={onGenerate}>Сформировать текущий месяц</button>
      </div>

      <div className="card">
        <div className="card-header"><span className="card-title">Зарплаты сотрудников</span></div>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>СОТРУДНИК</th>
                <th>ТИП ОПЛАТЫ</th>
                <th>ПРОФИЛЬ</th>
                <th>ОТРАБОТАНО</th>
                <th>НАЧИСЛЕНО</th>
                <th>АВАНСЫ</th>
                <th>К ВЫПЛАТЕ</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr><td colSpan={8}>Загрузка...</td></tr>
              )}
              {!loading && profiles.map((profile) => {
                const row = payrollByUser.get(Number(profile.user));
                const user = usersById.get(Number(profile.user));
                return (
                  <tr key={profile.id}>
                    <td style={{ fontWeight: 600 }}>{user?.full_name || profile.username || `#${profile.user}`}</td>
                    <td>{toPayTypeLabel(profile.employment_type)}</td>
                    <td>{fmt(profile.base_salary)}</td>
                    <td>{row ? `${row.worked_days}/${row.planned_days} дн` : '-'}</td>
                    <td>{row ? fmt(row.salary_amount) : '-'}</td>
                    <td>{row ? fmt(row.advances) : '-'}</td>
                    <td style={{ fontWeight: 700 }}>{row ? fmt(row.total_amount) : '-'}</td>
                    <td><button className="btn-icon" type="button" onClick={() => openEdit(profile)}><Pencil size={13} /></button></td>
                  </tr>
                );
              })}
              {!loading && profiles.length === 0 && (
                <tr><td colSpan={8}>Профили зарплат не настроены.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {modal && (
        <div className="modal-overlay" onClick={() => setModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 520 }}>
            <div className="modal-header">
              <div className="modal-title">Настройка профиля зарплаты</div>
              <button className="btn-icon" type="button" onClick={() => setModal(false)}><X size={18} /></button>
            </div>
            <div className="modal-body">
              <div className="form-group" style={{ marginBottom: 12 }}>
                <label className="form-label">Тип оплаты</label>
                <select className="form-select" value={form.employment_type} onChange={(e) => setForm((f) => ({ ...f, employment_type: e.target.value }))}>
                  <option value="fixed">Оклад</option>
                  <option value="daily">Дневная</option>
                  <option value="hourly">Почасовая</option>
                </select>
              </div>
              <div className="form-group" style={{ marginBottom: 12 }}>
                <label className="form-label">База (KGS)</label>
                <input className="form-input" type="number" value={form.base_salary} onChange={(e) => setForm((f) => ({ ...f, base_salary: e.target.value }))} />
              </div>
              <div className="form-group" style={{ marginBottom: 12 }}>
                <label className="form-label">Валюта</label>
                <input className="form-input" value={form.currency} onChange={(e) => setForm((f) => ({ ...f, currency: e.target.value }))} />
              </div>
              <label style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <input type="checkbox" checked={form.is_active} onChange={(e) => setForm((f) => ({ ...f, is_active: e.target.checked }))} />
                Активный профиль
              </label>
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" type="button" onClick={() => setModal(false)}>Отмена</button>
              <button className="btn btn-primary" type="button" onClick={saveProfile} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <Check size={14} /> Сохранить
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export default function Salary() {
  const { user } = useAuth();
  const isAdminOrSuper = user?.role === 'superadmin' || user?.role === 'admin';
  const [view, setView] = useState('my');
  const [myEntry, setMyEntry] = useState(null);
  const [myError, setMyError] = useState('');
  const [myLoading, setMyLoading] = useState(true);
  const [teamLoading, setTeamLoading] = useState(true);
  const [teamError, setTeamError] = useState('');
  const [profiles, setProfiles] = useState([]);
  const [rows, setRows] = useState([]);
  const [usersById, setUsersById] = useState(new Map());

  const { year, month } = monthMeta();

  const loadMy = async () => {
    setMyLoading(true);
    setMyError('');
    try {
      const res = await payrollAPI.my({ year, month });
      setMyEntry(res.data || null);
    } catch (e) {
      if (e.response?.status === 404) {
        setMyEntry(null);
        setMyError('');
      } else {
        setMyError(e.response?.data?.detail || 'Не удалось загрузить мою зарплату.');
      }
    } finally {
      setMyLoading(false);
    }
  };

  const loadTeam = async () => {
    if (!isAdminOrSuper) return;
    setTeamLoading(true);
    setTeamError('');
    try {
      const [profilesRes, rowsRes] = await Promise.all([
        payrollAPI.salaryProfiles(),
        payrollAPI.adminList({ year, month }),
      ]);
      const nextProfiles = Array.isArray(profilesRes.data) ? profilesRes.data : [];
      const nextRows = Array.isArray(rowsRes.data) ? rowsRes.data : [];
      setProfiles(nextProfiles);
      setRows(nextRows);
      const map = new Map();
      nextRows.forEach((row) => map.set(Number(row.user), { full_name: row.username, username: row.username }));
      nextProfiles.forEach((profile) => {
        if (!map.has(Number(profile.user))) map.set(Number(profile.user), { full_name: profile.username, username: profile.username });
      });
      setUsersById(map);
    } catch (e) {
      setTeamError(e.response?.data?.detail || 'Не удалось загрузить зарплаты сотрудников.');
    } finally {
      setTeamLoading(false);
    }
  };

  useEffect(() => {
    loadMy();
    loadTeam();
  }, []);

  const generateMonth = async () => {
    setTeamError('');
    try {
      await payrollAPI.generate({ year, month });
      await Promise.all([loadMy(), loadTeam()]);
    } catch (e) {
      setTeamError(e.response?.data?.detail || 'Не удалось сформировать payroll.');
    }
  };

  const saveProfile = async (id, payload) => {
    setTeamError('');
    try {
      await payrollAPI.updateSalaryProfile(id, payload);
      await loadTeam();
    } catch (e) {
      setTeamError(e.response?.data?.detail || 'Не удалось сохранить профиль зарплаты.');
    }
  };

  return (
    <MainLayout title="Зарплата">
      <div className="page-header">
        <div>
          <div className="page-title">{isAdminOrSuper && view === 'team' ? 'Зарплаты сотрудников' : 'Моя зарплата'}</div>
          <div className="page-subtitle">Период: {month}/{year}</div>
        </div>
      </div>

      {isAdminOrSuper && (
        <div style={{ display: 'flex', gap: 8, marginBottom: 14 }}>
          <button type="button" className={`btn btn-sm ${view === 'my' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setView('my')}>
            Моя зарплата
          </button>
          <button type="button" className={`btn btn-sm ${view === 'team' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setView('team')}>
            Зарплаты сотрудников
          </button>
        </div>
      )}

      {isAdminOrSuper && view === 'team'
        ? <TeamSalaries usersById={usersById} profiles={profiles} payrollRows={rows} loading={teamLoading} error={teamError} onGenerate={generateMonth} onSaveProfile={saveProfile} />
        : <MySalary payrollEntry={myEntry} loading={myLoading} error={myError} />}
    </MainLayout>
  );
}

import { useEffect, useMemo, useState } from 'react';
import MainLayout from '../../layouts/MainLayout';
import { schedulesAPI } from '../../api/content';
import { usersAPI } from '../../api/auth';

const DAY_LABELS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
const STATUS_LABELS = {
  pending: 'На рассмотрении',
  clarification_requested: 'Нужна доработка',
  approved: 'Утвержден',
  rejected: 'Отклонен',
};

const emptyTemplate = {
  name: '',
  work_days: [0, 1, 2, 3, 4],
  start_time: '09:00',
  end_time: '18:00',
  break_start: '13:00',
  break_end: '14:00',
  is_default: false,
  is_active: true,
};

function mondayOf(date = new Date()) {
  const d = new Date(date);
  const day = d.getDay() || 7;
  d.setDate(d.getDate() - day + 1);
  d.setHours(0, 0, 0, 0);
  return d;
}

function isoDate(date) {
  return new Date(date).toISOString().slice(0, 10);
}

function formatDate(date) {
  return new Date(date).toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

function formatDateTime(value) {
  if (!value) return '—';
  return new Date(value).toLocaleString('ru-RU');
}

function shortTime(value) {
  if (!value) return '—';
  return String(value).slice(0, 5);
}

export default function AdminSchedules() {
  const [tab, setTab] = useState('templates');
  const [templates, setTemplates] = useState([]);
  const [requests, setRequests] = useState([]);
  const [weeklyPlans, setWeeklyPlans] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const [templateForm, setTemplateForm] = useState(emptyTemplate);
  const [editingTemplateId, setEditingTemplateId] = useState(null);

  const [assignUserId, setAssignUserId] = useState('');
  const [assignScheduleId, setAssignScheduleId] = useState('');
  const [assignApproved, setAssignApproved] = useState(true);

  const [weekFilter, setWeekFilter] = useState(isoDate(mondayOf()));
  const [decisionComment, setDecisionComment] = useState('');

  const usersMap = useMemo(() => new Map(users.map((u) => [Number(u.id), u])), [users]);

  const loadAll = async () => {
    setLoading(true);
    setError('');
    try {
      const [tplRes, reqRes, plansRes, usersRes] = await Promise.all([
        schedulesAPI.adminTemplates(),
        schedulesAPI.adminRequests(),
        schedulesAPI.weeklyPlansAdmin(),
        usersAPI.list(),
      ]);
      setTemplates(Array.isArray(tplRes.data) ? tplRes.data : []);
      setRequests(Array.isArray(reqRes.data) ? reqRes.data : []);
      setWeeklyPlans(Array.isArray(plansRes.data) ? plansRes.data : []);
      setUsers(Array.isArray(usersRes.data) ? usersRes.data : []);
    } catch (e) {
      setError(e.response?.data?.detail || 'Не удалось загрузить раздел графиков.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
  }, []);

  const pendingRequests = useMemo(() => requests.filter((r) => !r.approved), [requests]);

  const plansForWeek = useMemo(() => {
    return weeklyPlans.filter((p) => String(p.week_start) === String(weekFilter));
  }, [weeklyPlans, weekFilter]);

  const boardColumns = useMemo(() => {
    const cols = DAY_LABELS.map((label, idx) => ({ label, index: idx, entries: [] }));
    plansForWeek
      .filter((p) => p.status === 'approved')
      .forEach((plan) => {
        const name = plan.username || usersMap.get(Number(plan.user))?.full_name || `#${plan.user}`;
        (plan.days || []).forEach((day) => {
          const date = day.date ? new Date(`${day.date}T00:00:00`) : null;
          if (!date) return;
          const idx = date.getDay() === 0 ? 6 : date.getDay() - 1;
          if (day.mode === 'day_off') return;
          cols[idx].entries.push({
            id: `${plan.id}-${day.date}`,
            user: name,
            from: shortTime(day.start_time),
            to: shortTime(day.end_time),
            mode: day.mode === 'online' ? 'онлайн' : 'офис',
          });
        });
      });
    return cols;
  }, [plansForWeek, usersMap]);

  const saveTemplate = async () => {
    if (!templateForm.name.trim()) return;
    setError('');
    try {
      const payload = {
        ...templateForm,
        work_days: [...templateForm.work_days].sort((a, b) => a - b),
      };
      if (editingTemplateId) {
        await schedulesAPI.adminUpdateTemplate(editingTemplateId, payload);
      } else {
        await schedulesAPI.adminCreateTemplate(payload);
      }
      setTemplateForm(emptyTemplate);
      setEditingTemplateId(null);
      setNotice('Шаблон графика сохранен.');
      await loadAll();
    } catch (e) {
      setError(e.response?.data?.detail || 'Не удалось сохранить шаблон графика.');
    }
  };

  const deactivateTemplate = async (id) => {
    setError('');
    try {
      await schedulesAPI.adminUpdateTemplate(id, { is_active: false });
      setNotice('Шаблон деактивирован.');
      await loadAll();
    } catch (e) {
      setError(e.response?.data?.detail || 'Не удалось деактивировать шаблон.');
    }
  };

  const decideRequest = async (id, approved) => {
    setError('');
    try {
      await schedulesAPI.adminRequestDecision(id, approved);
      setNotice(approved ? 'Заявка одобрена.' : 'Заявка отклонена.');
      await loadAll();
    } catch (e) {
      setError(e.response?.data?.detail || 'Не удалось обработать заявку.');
    }
  };

  const assignSchedule = async () => {
    if (!assignUserId || !assignScheduleId) return;
    setError('');
    try {
      await schedulesAPI.adminAssign({
        user_id: Number(assignUserId),
        schedule_id: Number(assignScheduleId),
        approved: !!assignApproved,
      });
      setNotice('График назначен сотруднику.');
      await loadAll();
    } catch (e) {
      setError(e.response?.data?.detail || 'Не удалось назначить график сотруднику.');
    }
  };

  const decideWeeklyPlan = async (id, action) => {
    setError('');
    try {
      await schedulesAPI.weeklyPlanDecision(id, {
        action,
        admin_comment: decisionComment,
      });
      setNotice('Решение по недельному плану сохранено.');
      await loadAll();
    } catch (e) {
      setError(e.response?.data?.detail || 'Не удалось обработать недельный план.');
    }
  };

  const toggleWorkDay = (dayIdx) => {
    setTemplateForm((prev) => {
      const has = prev.work_days.includes(dayIdx);
      const next = has ? prev.work_days.filter((d) => d !== dayIdx) : [...prev.work_days, dayIdx];
      return { ...prev, work_days: next };
    });
  };

  return (
    <MainLayout title="Админ-панель · Графики работы">
      <div className="page-header">
        <div>
          <div className="page-title">Графики работы</div>
          <div className="page-subtitle">Шаблоны, назначения сотрудникам, заявки и недельные планы</div>
        </div>
      </div>

      {error && <div className="card" style={{ marginBottom: 12 }}><div className="card-body" style={{ color: '#b91c1c' }}>{error}</div></div>}
      {notice && <div className="card" style={{ marginBottom: 12 }}><div className="card-body" style={{ color: '#166534' }}>{notice}</div></div>}
      {loading && <div className="card"><div className="card-body">Загрузка...</div></div>}

      {!loading && (
        <>
          <div className="tabs" style={{ marginBottom: 14 }}>
            <button className={`tab-btn ${tab === 'templates' ? 'active' : ''}`} onClick={() => setTab('templates')}>Шаблоны</button>
            <button className={`tab-btn ${tab === 'requests' ? 'active' : ''}`} onClick={() => setTab('requests')}>Заявки ({pendingRequests.length})</button>
            <button className={`tab-btn ${tab === 'weekly' ? 'active' : ''}`} onClick={() => setTab('weekly')}>Недельные планы</button>
            <button className={`tab-btn ${tab === 'board' ? 'active' : ''}`} onClick={() => setTab('board')}>График недели</button>
          </div>

          {tab === 'templates' && (
            <>
              <div className="card" style={{ marginBottom: 12 }}>
                <div className="card-header"><span className="card-title">Создание / редактирование шаблона</span></div>
                <div className="card-body" style={{ display: 'grid', gap: 10 }}>
                  <input className="form-input" placeholder="Название" value={templateForm.name} onChange={(e) => setTemplateForm((f) => ({ ...f, name: e.target.value }))} />
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 8 }}>
                    <div>
                      <label className="form-label">Начало</label>
                      <input className="form-input" type="time" value={templateForm.start_time} onChange={(e) => setTemplateForm((f) => ({ ...f, start_time: e.target.value }))} />
                    </div>
                    <div>
                      <label className="form-label">Конец</label>
                      <input className="form-input" type="time" value={templateForm.end_time} onChange={(e) => setTemplateForm((f) => ({ ...f, end_time: e.target.value }))} />
                    </div>
                    <div>
                      <label className="form-label">Перерыв с</label>
                      <input className="form-input" type="time" value={templateForm.break_start || ''} onChange={(e) => setTemplateForm((f) => ({ ...f, break_start: e.target.value || null }))} />
                    </div>
                    <div>
                      <label className="form-label">Перерыв до</label>
                      <input className="form-input" type="time" value={templateForm.break_end || ''} onChange={(e) => setTemplateForm((f) => ({ ...f, break_end: e.target.value || null }))} />
                    </div>
                  </div>
                  <div>
                    <label className="form-label">Рабочие дни</label>
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                      {DAY_LABELS.map((label, idx) => {
                        const active = templateForm.work_days.includes(idx);
                        return (
                          <button
                            key={label}
                            type="button"
                            className={`btn btn-sm ${active ? 'btn-primary' : 'btn-secondary'}`}
                            onClick={() => toggleWorkDay(idx)}
                          >
                            {label}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                  <label style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                    <input type="checkbox" checked={templateForm.is_default} onChange={(e) => setTemplateForm((f) => ({ ...f, is_default: e.target.checked }))} />
                    Использовать как график по умолчанию
                  </label>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <button className="btn btn-primary btn-sm" onClick={saveTemplate}>{editingTemplateId ? 'Сохранить' : 'Создать'}</button>
                    {editingTemplateId && <button className="btn btn-secondary btn-sm" onClick={() => { setEditingTemplateId(null); setTemplateForm(emptyTemplate); }}>Отмена</button>}
                  </div>
                </div>
              </div>

              <div className="card" style={{ marginBottom: 12 }}>
                <div className="card-header"><span className="card-title">Назначить график сотруднику</span></div>
                <div className="card-body" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr auto auto', gap: 8, alignItems: 'end' }}>
                  <div>
                    <label className="form-label">Сотрудник</label>
                    <select className="form-select" value={assignUserId} onChange={(e) => setAssignUserId(e.target.value)}>
                      <option value="">Выберите</option>
                      {users.map((u) => (
                        <option key={u.id} value={u.id}>{u.full_name || u.username}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="form-label">Шаблон</label>
                    <select className="form-select" value={assignScheduleId} onChange={(e) => setAssignScheduleId(e.target.value)}>
                      <option value="">Выберите</option>
                      {templates.filter((s) => s.is_active).map((s) => (
                        <option key={s.id} value={s.id}>{s.name}</option>
                      ))}
                    </select>
                  </div>
                  <label style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 8 }}>
                    <input type="checkbox" checked={assignApproved} onChange={(e) => setAssignApproved(e.target.checked)} />
                    Сразу утвердить
                  </label>
                  <button className="btn btn-primary btn-sm" onClick={assignSchedule} disabled={!assignUserId || !assignScheduleId}>Назначить</button>
                </div>
              </div>

              <div className="card">
                <div className="card-header"><span className="card-title">Шаблоны графиков</span></div>
                <div className="table-wrap">
                  <table className="table">
                    <thead>
                      <tr><th>ID</th><th>Название</th><th>Дни</th><th>Время</th><th>Перерыв</th><th>Default</th><th>Активен</th><th>Пользователей</th><th>Действия</th></tr>
                    </thead>
                    <tbody>
                      {templates.map((t) => (
                        <tr key={t.id}>
                          <td>{t.id}</td>
                          <td>{t.name}</td>
                          <td>{(t.work_days || []).map((i) => DAY_LABELS[i]).join(', ') || '—'}</td>
                          <td>{shortTime(t.start_time)} - {shortTime(t.end_time)}</td>
                          <td>{t.break_start && t.break_end ? `${shortTime(t.break_start)} - ${shortTime(t.break_end)}` : '—'}</td>
                          <td>{t.is_default ? 'Да' : 'Нет'}</td>
                          <td>{t.is_active ? 'Да' : 'Нет'}</td>
                          <td>{t.users_count ?? 0}</td>
                          <td>
                            <div style={{ display: 'flex', gap: 6 }}>
                              <button className="btn btn-secondary btn-sm" onClick={() => {
                                setEditingTemplateId(t.id);
                                setTemplateForm({
                                  name: t.name,
                                  work_days: Array.isArray(t.work_days) ? t.work_days : [],
                                  start_time: shortTime(t.start_time),
                                  end_time: shortTime(t.end_time),
                                  break_start: t.break_start ? shortTime(t.break_start) : null,
                                  break_end: t.break_end ? shortTime(t.break_end) : null,
                                  is_default: !!t.is_default,
                                  is_active: !!t.is_active,
                                });
                              }}>Изменить</button>
                              {t.is_active && <button className="btn btn-secondary btn-sm" onClick={() => deactivateTemplate(t.id)}>Деактивировать</button>}
                            </div>
                          </td>
                        </tr>
                      ))}
                      {templates.length === 0 && <tr><td colSpan={9}>Шаблоны не найдены.</td></tr>}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}

          {tab === 'requests' && (
            <div className="card">
              <div className="card-header"><span className="card-title">Заявки сотрудников на смену графика</span></div>
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr><th>ID</th><th>Сотрудник</th><th>Шаблон</th><th>Запрошено</th><th>Статус</th><th>Действия</th></tr>
                  </thead>
                  <tbody>
                    {requests.map((r) => {
                      const u = usersMap.get(Number(r.user));
                      return (
                        <tr key={r.id}>
                          <td>{r.id}</td>
                          <td>{u?.full_name || u?.username || `#${r.user}`}</td>
                          <td>{r.schedule_name}</td>
                          <td>{formatDateTime(r.requested_at)}</td>
                          <td>{r.approved ? 'Утверждено' : 'Ожидает'}</td>
                          <td>
                            {!r.approved ? (
                              <div style={{ display: 'flex', gap: 6 }}>
                                <button className="btn btn-primary btn-sm" onClick={() => decideRequest(r.id, true)}>Одобрить</button>
                                <button className="btn btn-secondary btn-sm" onClick={() => decideRequest(r.id, false)}>Отклонить</button>
                              </div>
                            ) : '—'}
                          </td>
                        </tr>
                      );
                    })}
                    {requests.length === 0 && <tr><td colSpan={6}>Заявок нет.</td></tr>}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {tab === 'weekly' && (
            <div className="card">
              <div className="card-header" style={{ display: 'flex', gap: 8, alignItems: 'end' }}>
                <div>
                  <label className="form-label">Неделя (понедельник)</label>
                  <input className="form-input" type="date" value={weekFilter} onChange={(e) => setWeekFilter(e.target.value)} />
                </div>
                <div style={{ flex: 1 }}>
                  <label className="form-label">Комментарий администратора</label>
                  <input className="form-input" value={decisionComment} onChange={(e) => setDecisionComment(e.target.value)} placeholder="Комментарий для доработки/отклонения" />
                </div>
              </div>
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr><th>ID</th><th>Сотрудник</th><th>Неделя</th><th>Офис</th><th>Онлайн</th><th>Статус</th><th>Обновлен</th><th>Действия</th></tr>
                  </thead>
                  <tbody>
                    {plansForWeek.map((p) => (
                      <tr key={p.id}>
                        <td>{p.id}</td>
                        <td>{p.username || usersMap.get(Number(p.user))?.full_name || `#${p.user}`}</td>
                        <td>{p.week_start}</td>
                        <td>{p.office_hours} ч</td>
                        <td>{p.online_hours} ч</td>
                        <td>{STATUS_LABELS[p.status] || p.status}</td>
                        <td>{formatDateTime(p.updated_at)}</td>
                        <td>
                          {p.status !== 'approved' && (
                            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                              <button className="btn btn-primary btn-sm" onClick={() => decideWeeklyPlan(p.id, 'approve')}>Утвердить</button>
                              <button className="btn btn-secondary btn-sm" onClick={() => decideWeeklyPlan(p.id, 'request_clarification')}>На доработку</button>
                              <button className="btn btn-secondary btn-sm" onClick={() => decideWeeklyPlan(p.id, 'reject')}>Отклонить</button>
                            </div>
                          )}
                        </td>
                      </tr>
                    ))}
                    {plansForWeek.length === 0 && <tr><td colSpan={8}>На выбранную неделю планов нет.</td></tr>}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {tab === 'board' && (
            <div className="card">
              <div className="card-header" style={{ display: 'flex', gap: 8, alignItems: 'end' }}>
                <div>
                  <label className="form-label">Неделя (понедельник)</label>
                  <input className="form-input" type="date" value={weekFilter} onChange={(e) => setWeekFilter(e.target.value)} />
                </div>
                <div style={{ color: 'var(--gray-500)', fontSize: 13 }}>Показываются только утвержденные реальные смены сотрудников</div>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, minmax(170px, 1fr))', borderTop: '1px solid var(--gray-200)', overflowX: 'auto' }}>
                {boardColumns.map((col, idx) => (
                  <div key={col.label} style={{ minHeight: 360, borderRight: idx < 6 ? '1px solid var(--gray-200)' : 'none' }}>
                    <div style={{ background: '#0B1C46', color: 'white', padding: '10px 12px' }}>
                      <div style={{ fontWeight: 700 }}>{col.label}</div>
                      <div style={{ fontSize: 12, opacity: 0.9 }}>{formatDate(new Date(new Date(weekFilter).getTime() + idx * 86400000))}</div>
                    </div>
                    <div style={{ padding: 8, display: 'grid', gap: 8 }}>
                      {col.entries.length === 0 && <div style={{ color: 'var(--gray-400)', fontSize: 12 }}>Нет смен</div>}
                      {col.entries.map((entry) => (
                        <div key={entry.id} style={{ border: '1px solid #BBF7D0', borderRadius: 8, background: '#F0FDF4', padding: '8px 10px' }}>
                          <div style={{ fontWeight: 700 }}>{entry.user}</div>
                          <div style={{ fontSize: 12, color: 'var(--gray-600)' }}>Время: {entry.from} - {entry.to}</div>
                          <div style={{ fontSize: 12, color: 'var(--gray-600)' }}>Формат: {entry.mode}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </MainLayout>
  );
}

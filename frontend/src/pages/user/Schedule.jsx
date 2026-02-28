import { useEffect, useMemo, useState } from 'react';
import MainLayout from '../../layouts/MainLayout';
import { schedulesAPI } from '../../api/content';

const DAY_LABELS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
const STATUS_LABELS = {
  pending: 'На рассмотрении',
  clarification_requested: 'Нужна доработка',
  approved: 'Утвержден',
  rejected: 'Отклонен',
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

function addDays(date, n) {
  const d = new Date(date);
  d.setDate(d.getDate() + n);
  return d;
}

function shortTime(value) {
  if (!value) return '—';
  return String(value).slice(0, 5);
}

function calcHours(from, to) {
  if (!from || !to) return 0;
  const [fh, fm] = from.split(':').map(Number);
  const [th, tm] = to.split(':').map(Number);
  const minutes = th * 60 + tm - (fh * 60 + fm);
  return Math.max(0, Math.round((minutes / 60) * 100) / 100);
}

function addMinutesHHMM(value, delta) {
  if (!value || !value.includes(':')) return '13:00';
  const [h, m] = value.split(':').map(Number);
  const total = h * 60 + m + delta;
  const hh = String(Math.floor(total / 60)).padStart(2, '0');
  const mm = String(((total % 60) + 60) % 60).padStart(2, '0');
  return `${hh}:${mm}`;
}

function extractErrorMessage(e, fallback) {
  const data = e?.response?.data;
  if (!data) return fallback;
  if (typeof data.detail === 'string') return data.detail;
  if (Array.isArray(data.detail) && data.detail.length) return String(data.detail[0]);
  if (typeof data === 'string') return data;
  if (typeof data === 'object') {
    const firstKey = Object.keys(data)[0];
    const firstVal = data[firstKey];
    if (Array.isArray(firstVal) && firstVal.length) return `${firstKey}: ${firstVal[0]}`;
    if (typeof firstVal === 'string') return `${firstKey}: ${firstVal}`;
  }
  return fallback;
}

function makeDefaultDays(weekStart) {
  const monday = new Date(`${weekStart}T00:00:00`);
  return DAY_LABELS.map((_, idx) => {
    const date = isoDate(addDays(monday, idx));
    const isWeekday = idx <= 4;
    return {
      date,
      mode: isWeekday ? 'office' : 'day_off',
      start_time: isWeekday ? '09:00' : '',
      end_time: isWeekday ? '18:00' : '',
      comment: '',
      breaks: [],
      lunch_start: '',
      lunch_end: '',
    };
  });
}

export default function Schedule() {
  const [tab, setTab] = useState('my');
  const [workSchedules, setWorkSchedules] = useState([]);
  const [mySchedule, setMySchedule] = useState(null);
  const [holidays, setHolidays] = useState([]);
  const [weeklyPlans, setWeeklyPlans] = useState([]);
  const [selectedScheduleId, setSelectedScheduleId] = useState('');
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');

  const currentYear = useMemo(() => new Date().getFullYear(), []);

  const [weekStart, setWeekStart] = useState(isoDate(mondayOf()));
  const [days, setDays] = useState(makeDefaultDays(isoDate(mondayOf())));
  const [onlineReason, setOnlineReason] = useState('');
  const [employeeComment, setEmployeeComment] = useState('');

  const officeHours = useMemo(() => days.reduce((sum, d) => sum + (d.mode === 'office' ? calcHours(d.start_time, d.end_time) : 0), 0), [days]);
  const onlineHours = useMemo(() => days.reduce((sum, d) => sum + (d.mode === 'online' ? calcHours(d.start_time, d.end_time) : 0), 0), [days]);
  const needReason = officeHours < 24 || onlineHours > 16;

  const loadAll = async () => {
    setLoading(true);
    setMessage('');
    try {
      const [templatesRes, holidaysRes, plansRes] = await Promise.all([
        schedulesAPI.getWorkSchedules(),
        schedulesAPI.getHolidays(currentYear),
        schedulesAPI.weeklyPlansMy(),
      ]);
      setWorkSchedules(Array.isArray(templatesRes.data) ? templatesRes.data : []);
      setHolidays(Array.isArray(holidaysRes.data) ? holidaysRes.data : []);
      setWeeklyPlans(Array.isArray(plansRes.data) ? plansRes.data : []);
      try {
        const myRes = await schedulesAPI.getMine();
        const mine = myRes?.data || null;
        setMySchedule(mine);
        setSelectedScheduleId(mine?.schedule || '');
      } catch {
        setMySchedule(null);
        setSelectedScheduleId('');
      }
    } catch {
      setMessage('Не удалось загрузить данные графика.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
  }, []);

  useEffect(() => {
    const monday = mondayOf(new Date(`${weekStart}T00:00:00`));
    const nextStart = isoDate(monday);
    if (nextStart !== weekStart) {
      setWeekStart(nextStart);
      return;
    }

    const existing = weeklyPlans.find((p) => String(p.week_start) === String(weekStart));
    if (existing?.days?.length === 7) {
      setDays(existing.days.map((d) => ({
        date: d.date,
        mode: d.mode,
        start_time: d.start_time || '',
        end_time: d.end_time || '',
        comment: d.comment || '',
        breaks: Array.isArray(d.breaks) ? d.breaks.map((b) => ({ start_time: b.start_time || '', end_time: b.end_time || '' })) : [],
        lunch_start: d.lunch_start || '',
        lunch_end: d.lunch_end || '',
      })));
      setOnlineReason(existing.online_reason || '');
      setEmployeeComment(existing.employee_comment || '');
    } else {
      setDays(makeDefaultDays(weekStart));
      setOnlineReason('');
      setEmployeeComment('');
    }
  }, [weekStart, weeklyPlans]);

  const submitSelection = async () => {
    if (!selectedScheduleId) return;
    try {
      await schedulesAPI.select(Number(selectedScheduleId));
      setMessage('Запрос на график отправлен. Ожидайте подтверждения администратора.');
      await loadAll();
    } catch {
      setMessage('Не удалось отправить запрос на график.');
    }
  };

  const updateDay = (idx, patch) => {
    setDays((prev) => prev.map((d, i) => (i === idx ? { ...d, ...patch } : d)));
  };

  const addBreak = (idx) => {
    setDays((prev) => prev.map((d, i) => {
      if (i !== idx) return d;
      const last = d.breaks[d.breaks.length - 1];
      const start = last?.end_time || (d.lunch_end || addMinutesHHMM(d.start_time || '13:00', 120));
      const end = addMinutesHHMM(start, 15);
      return {
        ...d,
        breaks: [...d.breaks, { start_time: start, end_time: end }],
      };
    }));
  };

  const updateBreak = (dayIdx, breakIdx, patch) => {
    setDays((prev) => prev.map((d, i) => {
      if (i !== dayIdx) return d;
      return {
        ...d,
        breaks: d.breaks.map((b, bi) => (bi === breakIdx ? { ...b, ...patch } : b)),
      };
    }));
  };

  const removeBreak = (dayIdx, breakIdx) => {
    setDays((prev) => prev.map((d, i) => {
      if (i !== dayIdx) return d;
      return {
        ...d,
        breaks: d.breaks.filter((_, bi) => bi !== breakIdx),
      };
    }));
  };

  const submitWeeklyPlan = async () => {
    const invalid = days.find((d) => d.mode !== 'day_off' && (!d.start_time || !d.end_time || !d.start_time.endsWith(':00') || !d.end_time.endsWith(':00')));
    if (invalid) {
      setMessage('Для рабочих смен укажите корректное время в полных часах (например, 09:00-18:00).');
      return;
    }
    if (needReason && !onlineReason.trim()) {
      setMessage('Нужно указать причину, когда офис < 24ч и/или онлайн > 16ч.');
      return;
    }

    try {
      await schedulesAPI.weeklyPlanSubmit({
        week_start: weekStart,
        days: days.map((d) => ({
          date: d.date,
          mode: d.mode,
          start_time: d.mode === 'day_off' ? null : d.start_time,
          end_time: d.mode === 'day_off' ? null : d.end_time,
          comment: d.comment || '',
          breaks: d.mode === 'office'
            ? d.breaks
              .filter((b) => b.start_time && b.end_time)
              .map((b) => ({ start_time: b.start_time, end_time: b.end_time }))
            : [],
          lunch_start: d.mode === 'office' && d.lunch_start ? d.lunch_start : null,
          lunch_end: d.mode === 'office' && d.lunch_end ? d.lunch_end : null,
        })),
        online_reason: onlineReason,
        employee_comment: employeeComment,
      });
      setMessage('Недельный план отправлен на согласование.');
      await loadAll();
    } catch (e) {
      setMessage(extractErrorMessage(e, 'Не удалось отправить недельный план. Проверьте заполнение полей.'));
    }
  };

  return (
    <MainLayout title="Мой график">
      <div className="page-header">
        <div>
          <div className="page-title">График работы</div>
          <div className="page-subtitle">Текущий график, заявка на шаблон и недельные планы</div>
        </div>
      </div>

      {message ? <div className="card" style={{ marginBottom: 12 }}><div className="card-body">{message}</div></div> : null}

      {loading ? (
        <div className="card"><div className="card-body">Загрузка...</div></div>
      ) : (
        <>
          <div className="tabs" style={{ marginBottom: 14 }}>
            <button className={`tab-btn ${tab === 'my' ? 'active' : ''}`} onClick={() => setTab('my')}>Мой график</button>
            <button className={`tab-btn ${tab === 'request' ? 'active' : ''}`} onClick={() => setTab('request')}>Запрос шаблона</button>
            <button className={`tab-btn ${tab === 'weekly' ? 'active' : ''}`} onClick={() => setTab('weekly')}>Недельный план</button>
            <button className={`tab-btn ${tab === 'history' ? 'active' : ''}`} onClick={() => setTab('history')}>История планов</button>
          </div>

          {tab === 'my' && (
            <div className="card">
              <div className="card-header"><span className="card-title">Текущий график</span></div>
              <div className="card-body">
                {!mySchedule ? (
                  <div style={{ color: 'var(--gray-500)' }}>График пока не назначен.</div>
                ) : (
                  <>
                    <div style={{ marginBottom: 8 }}><b>Название:</b> {mySchedule.schedule_name || '—'}</div>
                    <div style={{ marginBottom: 8 }}><b>Статус:</b> {mySchedule.status || (mySchedule.approved ? 'approved' : 'pending')}</div>
                    <div style={{ marginBottom: 8 }}><b>Запрошен:</b> {mySchedule.requested_at ? new Date(mySchedule.requested_at).toLocaleString('ru-RU') : '—'}</div>
                  </>
                )}
              </div>
            </div>
          )}

          {tab === 'request' && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
              <div className="card">
                <div className="card-header"><span className="card-title">Запросить другой шаблон графика</span></div>
                <div className="card-body">
                  <div className="form-group" style={{ marginBottom: 10 }}>
                    <label className="form-label">Шаблон графика</label>
                    <select className="form-select" value={selectedScheduleId} onChange={(e) => setSelectedScheduleId(e.target.value)}>
                      <option value="">Выберите график</option>
                      {workSchedules.map((s) => (
                        <option key={s.id} value={s.id}>
                          {s.name} ({shortTime(s.start_time)} - {shortTime(s.end_time)})
                        </option>
                      ))}
                    </select>
                  </div>
                  <button className="btn btn-primary btn-sm" onClick={submitSelection} disabled={!selectedScheduleId}>Отправить запрос</button>
                </div>
              </div>

              <div className="card">
                <div className="card-header"><span className="card-title">Праздничные дни ({currentYear})</span></div>
                <div className="card-body" style={{ maxHeight: 280, overflow: 'auto' }}>
                  {holidays.length === 0 ? (
                    <div style={{ color: 'var(--gray-500)' }}>Праздники не настроены.</div>
                  ) : (
                    <ul style={{ margin: 0, paddingLeft: 18 }}>
                      {holidays.map((h) => (
                        <li key={`${h.date}-${h.name}`} style={{ marginBottom: 6 }}>
                          {h.date} — {h.name || 'Праздник'}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            </div>
          )}

          {tab === 'weekly' && (
            <div className="card">
              <div className="card-header"><span className="card-title">Недельный план работы</span></div>
              <div className="card-body">
                <div style={{ display: 'grid', gridTemplateColumns: '240px 1fr', gap: 12, marginBottom: 10 }}>
                  <div>
                    <label className="form-label">Неделя (понедельник)</label>
                    <input className="form-input" type="date" value={weekStart} onChange={(e) => setWeekStart(e.target.value)} />
                  </div>
                  <div style={{ display: 'flex', alignItems: 'end', color: 'var(--gray-600)', fontSize: 13 }}>
                    Офис: {officeHours} ч · Онлайн: {onlineHours} ч
                  </div>
                </div>

                <div className="table-wrap" style={{ marginBottom: 12 }}>
                  <table className="table">
                    <thead>
                      <tr><th>День</th><th>Дата</th><th>Формат</th><th>Начало</th><th>Конец</th><th>Обед</th><th>Перерывы</th><th>Комментарий</th></tr>
                    </thead>
                    <tbody>
                      {days.map((d, idx) => (
                        <tr key={d.date}>
                          <td>{DAY_LABELS[idx]}</td>
                          <td>{d.date}</td>
                          <td>
                            <select className="form-select" value={d.mode} onChange={(e) => {
                              const mode = e.target.value;
                              if (mode === 'day_off') {
                                updateDay(idx, { mode, start_time: '', end_time: '', lunch_start: '', lunch_end: '', breaks: [] });
                              } else {
                                updateDay(idx, { mode, start_time: d.start_time || '09:00', end_time: d.end_time || '18:00' });
                              }
                            }}>
                              <option value="office">Офис</option>
                              <option value="online">Онлайн</option>
                              <option value="day_off">Выходной</option>
                            </select>
                          </td>
                          <td><input className="form-input" type="time" value={d.start_time} disabled={d.mode === 'day_off'} onChange={(e) => updateDay(idx, { start_time: e.target.value })} /></td>
                          <td><input className="form-input" type="time" value={d.end_time} disabled={d.mode === 'day_off'} onChange={(e) => updateDay(idx, { end_time: e.target.value })} /></td>
                          <td>
                            {d.mode === 'office' ? (
                              <div style={{ display: 'grid', gap: 4 }}>
                                <input className="form-input" type="time" value={d.lunch_start} onChange={(e) => updateDay(idx, { lunch_start: e.target.value })} />
                                <input className="form-input" type="time" value={d.lunch_end} onChange={(e) => updateDay(idx, { lunch_end: e.target.value })} />
                              </div>
                            ) : '—'}
                          </td>
                          <td style={{ minWidth: 210 }}>
                            {d.mode === 'office' ? (
                              <div style={{ display: 'grid', gap: 4 }}>
                                {d.breaks.map((b, bi) => (
                                  <div key={`${d.date}-b-${bi}`} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr auto', gap: 4 }}>
                                    <input className="form-input" type="time" value={b.start_time} onChange={(e) => updateBreak(idx, bi, { start_time: e.target.value })} />
                                    <input className="form-input" type="time" value={b.end_time} onChange={(e) => updateBreak(idx, bi, { end_time: e.target.value })} />
                                    <button className="btn btn-secondary btn-sm" type="button" onClick={() => removeBreak(idx, bi)}>×</button>
                                  </div>
                                ))}
                                <button className="btn btn-secondary btn-sm" type="button" onClick={() => addBreak(idx)} disabled={d.breaks.length >= 4}>+ перерыв</button>
                              </div>
                            ) : '—'}
                          </td>
                          <td><input className="form-input" value={d.comment} onChange={(e) => updateDay(idx, { comment: e.target.value })} /></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <div className="form-group" style={{ marginBottom: 10 }}>
                  <label className="form-label">Причина онлайн-часов (обязательно, если офис &lt; 24 и/или онлайн &gt; 16)</label>
                  <textarea className="form-textarea" value={onlineReason} required={needReason} onChange={(e) => setOnlineReason(e.target.value)} style={{ minHeight: 80 }} />
                </div>
                <div className="form-group" style={{ marginBottom: 12 }}>
                  <label className="form-label">Комментарий сотрудника</label>
                  <textarea className="form-textarea" value={employeeComment} onChange={(e) => setEmployeeComment(e.target.value)} style={{ minHeight: 80 }} />
                </div>

                <button className="btn btn-primary btn-sm" onClick={submitWeeklyPlan}>Отправить на согласование</button>
              </div>
            </div>
          )}

          {tab === 'history' && (
            <div className="card">
              <div className="card-header"><span className="card-title">История недельных планов</span></div>
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr><th>Неделя</th><th>Офис</th><th>Онлайн</th><th>Статус</th><th>Комментарий администратора</th><th>Обновлен</th></tr>
                  </thead>
                  <tbody>
                    {weeklyPlans.map((p) => (
                      <tr key={p.id}>
                        <td>{p.week_start}</td>
                        <td>{p.office_hours} ч</td>
                        <td>{p.online_hours} ч</td>
                        <td>{STATUS_LABELS[p.status] || p.status}</td>
                        <td>{p.admin_comment || '—'}</td>
                        <td>{p.updated_at ? new Date(p.updated_at).toLocaleString('ru-RU') : '—'}</td>
                      </tr>
                    ))}
                    {weeklyPlans.length === 0 && (
                      <tr><td colSpan={6}>Недельных планов пока нет.</td></tr>
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

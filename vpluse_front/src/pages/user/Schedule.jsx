import { useEffect, useMemo, useState } from 'react';
import MainLayout from '../../layouts/MainLayout';
import { attendanceAPI, schedulesAPI } from '../../api/content';

const DAY_LABELS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
const DAY_FULL_LABELS = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье'];
const STATUS_LABELS = {
  pending: 'На рассмотрении',
  clarification_requested: 'Нужна доработка',
  approved: 'Утвержден',
  rejected: 'Отклонен',
};

function mondayOf(date = new Date()) {
  const d = new Date(date);
  if (Number.isNaN(d.getTime())) {
    const now = new Date();
    const nowDay = now.getDay() || 7;
    now.setDate(now.getDate() - nowDay + 1);
    now.setHours(0, 0, 0, 0);
    return now;
  }
  const day = d.getDay() || 7;
  d.setDate(d.getDate() - day + 1);
  d.setHours(0, 0, 0, 0);
  return d;
}

function isoDate(date) {
  const d = new Date(date);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

function addDays(date, n) {
  const d = new Date(date);
  d.setDate(d.getDate() + n);
  return d;
}

function parseIsoDate(value) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(value || ''));
  if (!match) return null;
  const y = Number(match[1]);
  const m = Number(match[2]);
  const d = Number(match[3]);
  const parsed = new Date(y, m - 1, d);
  if (Number.isNaN(parsed.getTime())) return null;
  return parsed;
}

function formatWeekStartLabel(value) {
  const parsed = parseIsoDate(value);
  if (!parsed) return value || '—';
  return parsed.toLocaleDateString('ru-RU');
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

function defaultShiftByDayIndex(dayIndex) {
  // Weekdays: 09:00-18:00; weekends: 11:00-19:00 (backend constraints).
  if (dayIndex >= 5) return { start: '11:00', end: '19:00' };
  return { start: '09:00', end: '18:00' };
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
  const monday = parseIsoDate(weekStart) || mondayOf(new Date());
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

function findFirstAvailableWeekStart(plans, fromDate = new Date()) {
  const taken = new Set((Array.isArray(plans) ? plans : []).map((p) => String(p.week_start || '')));
  const startMonday = mondayOf(fromDate);
  for (let weekOffset = 0; weekOffset < 52; weekOffset += 1) {
    const candidate = isoDate(addDays(startMonday, weekOffset * 7));
    if (!taken.has(candidate)) return candidate;
  }
  return isoDate(startMonday);
}

function normalizeWeekStart(rawValue, fallbackValue) {
  if (!rawValue) return fallbackValue;
  const parsed = new Date(`${rawValue}T00:00:00`);
  if (Number.isNaN(parsed.getTime())) return fallbackValue;
  const normalized = mondayOf(parsed);
  const year = normalized.getFullYear();
  const currentMonday = mondayOf(new Date());
  if (year < 2020 || year > 2100) return fallbackValue;
  if (normalized < currentMonday) return fallbackValue;
  return isoDate(normalized);
}

function shiftWeek(weekStartValue, deltaWeeks, plans) {
  const currentMonday = mondayOf(new Date());
  const parsed = parseIsoDate(weekStartValue) || currentMonday;
  const candidate = mondayOf(addDays(parsed, deltaWeeks * 7));
  if (candidate < currentMonday) return isoDate(currentMonday);

  const taken = new Set((Array.isArray(plans) ? plans : []).map((p) => String(p.week_start || '')));
  const candidateIso = isoDate(candidate);
  if (!taken.has(candidateIso)) return candidateIso;

  const direction = deltaWeeks >= 0 ? 1 : -1;
  for (let i = 1; i <= 52; i += 1) {
    const next = mondayOf(addDays(candidate, i * 7 * direction));
    if (next < currentMonday) break;
    const nextIso = isoDate(next);
    if (!taken.has(nextIso)) return nextIso;
  }
  return candidateIso;
}

function weekdayMonBased(dateObj) {
  const jsDay = dateObj.getDay();
  return jsDay === 0 ? 6 : jsDay - 1;
}

function resolveTodayShift({ todayIso, todayWeekStart, weeklyPlans, mySchedule, workSchedules }) {
  const plansForCurrentWeek = (Array.isArray(weeklyPlans) ? weeklyPlans : []).filter(
    (plan) => String(plan.week_start) === String(todayWeekStart)
  );
  const approvedPlan = plansForCurrentWeek.find((plan) => String(plan.status).toLowerCase() === 'approved');
  const selectedPlan = approvedPlan || plansForCurrentWeek[0];
  const dayFromPlan = selectedPlan?.days?.find((item) => String(item.date) === String(todayIso));

  if (dayFromPlan) {
    return {
      mode: dayFromPlan.mode || 'day_off',
      start_time: dayFromPlan.start_time || '',
      end_time: dayFromPlan.end_time || '',
      breaks: Array.isArray(dayFromPlan.breaks) ? dayFromPlan.breaks : [],
      lunch_start: dayFromPlan.lunch_start || '',
      lunch_end: dayFromPlan.lunch_end || '',
      source: selectedPlan ? 'weekly_plan' : 'none',
    };
  }

  const assignedSchedule = (Array.isArray(workSchedules) ? workSchedules : []).find(
    (item) => String(item.id) === String(mySchedule?.schedule)
  );
  if (assignedSchedule) {
    const todayDate = parseIsoDate(todayIso) || new Date();
    const isWorkday = Array.isArray(assignedSchedule.work_days)
      && assignedSchedule.work_days.includes(weekdayMonBased(todayDate));
    return {
      mode: isWorkday ? 'office' : 'day_off',
      start_time: isWorkday ? shortTime(assignedSchedule.start_time) : '',
      end_time: isWorkday ? shortTime(assignedSchedule.end_time) : '',
      breaks: isWorkday && assignedSchedule.break_start && assignedSchedule.break_end
        ? [{ start_time: shortTime(assignedSchedule.break_start), end_time: shortTime(assignedSchedule.break_end) }]
        : [],
      lunch_start: '',
      lunch_end: '',
      source: 'template',
    };
  }

  return {
    mode: 'day_off',
    start_time: '',
    end_time: '',
    breaks: [],
    lunch_start: '',
    lunch_end: '',
    source: 'none',
  };
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
  const [selectedDayIndex, setSelectedDayIndex] = useState(0);
  const [onlineReason, setOnlineReason] = useState('');
  const [employeeComment, setEmployeeComment] = useState('');
  const [todayAttendanceMark, setTodayAttendanceMark] = useState(null);
  const [markingStart, setMarkingStart] = useState(false);

  const today = useMemo(() => new Date(), []);
  const todayIso = useMemo(() => isoDate(today), [today]);
  const todayWeekStart = useMemo(() => isoDate(mondayOf(today)), [today]);
  const todayWeekdayIndex = useMemo(() => weekdayMonBased(today), [today]);
  const todayLabel = DAY_FULL_LABELS[todayWeekdayIndex];
  const todayShift = useMemo(
    () => resolveTodayShift({ todayIso, todayWeekStart, weeklyPlans, mySchedule, workSchedules }),
    [todayIso, todayWeekStart, weeklyPlans, mySchedule, workSchedules]
  );
  const isTodayWorking = todayShift.mode === 'office' || todayShift.mode === 'online';
  const hasTodayMark = Boolean(todayAttendanceMark?.status);

  const officeHours = useMemo(() => days.reduce((sum, d) => sum + (d.mode === 'office' ? calcHours(d.start_time, d.end_time) : 0), 0), [days]);
  const onlineHours = useMemo(() => days.reduce((sum, d) => sum + (d.mode === 'online' ? calcHours(d.start_time, d.end_time) : 0), 0), [days]);
  const needReason = officeHours < 24 || onlineHours > 16;

  const loadTodayAttendanceMark = async () => {
    const attendanceRes = await attendanceAPI.getMy({
      year: today.getFullYear(),
      month: today.getMonth() + 1,
    });
    const rows = Array.isArray(attendanceRes?.data) ? attendanceRes.data : [];
    const found = rows.find((item) => String(item.date) === String(todayIso)) || null;
    setTodayAttendanceMark(found);
    return found;
  };

  const loadAll = async () => {
    setLoading(true);
    setMessage('');
    try {
      const [templatesRes, holidaysRes, plansRes] = await Promise.all([
        schedulesAPI.getWorkSchedules(),
        schedulesAPI.getHolidays(currentYear),
        schedulesAPI.weeklyPlansMy(),
      ]);
      const plans = Array.isArray(plansRes.data) ? plansRes.data : [];
      setWorkSchedules(Array.isArray(templatesRes.data) ? templatesRes.data : []);
      setHolidays(Array.isArray(holidaysRes.data) ? holidaysRes.data : []);
      setWeeklyPlans(plans);
      setWeekStart((prev) => {
        const recommended = findFirstAvailableWeekStart(plans);
        const normalized = normalizeWeekStart(prev, recommended);
        const alreadyPlanned = plans.some((p) => String(p.week_start) === String(normalized));
        return alreadyPlanned ? recommended : normalized;
      });
      try {
        const myRes = await schedulesAPI.getMine();
        const mine = myRes?.data || null;
        setMySchedule(mine);
        setSelectedScheduleId(mine?.schedule || '');
      } catch {
        setMySchedule(null);
        setSelectedScheduleId('');
      }
      try {
        await loadTodayAttendanceMark();
      } catch {
        setTodayAttendanceMark(null);
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
    const fallback = findFirstAvailableWeekStart(weeklyPlans);
    const safeWeekStart = normalizeWeekStart(weekStart, fallback);
    if (safeWeekStart !== weekStart) {
      setWeekStart(safeWeekStart);
      return;
    }

    const monday = mondayOf(parseIsoDate(safeWeekStart) || new Date());
    const nextStart = isoDate(monday);
    if (nextStart !== safeWeekStart) {
      setWeekStart(nextStart);
      return;
    }

    const existing = weeklyPlans.find((p) => String(p.week_start) === String(safeWeekStart));
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
      setDays(makeDefaultDays(safeWeekStart));
      setOnlineReason('');
      setEmployeeComment('');
    }
    setSelectedDayIndex(0);
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

  const selectedDay = days[selectedDayIndex] || null;
  const selectedDayTitle = DAY_FULL_LABELS[selectedDayIndex] || '';
  const selectedIsWorkday = !!selectedDay && selectedDay.mode !== 'day_off';

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

  const markStartOfWork = async () => {
    if (!isTodayWorking || markingStart) return;
    setMarkingStart(true);
    setMessage('');
    try {
      if (todayShift.mode === 'online') {
        await attendanceAPI.mark({
          date: todayIso,
          status: 'remote',
          comment: 'Начало работы (онлайн).',
        });
        const found = await loadTodayAttendanceMark();
        if (found?.status) {
          setMessage('Отметка о начале онлайн-работы сохранена.');
        } else {
          setMessage('Сервер не вернул отметку. Нажмите обновить страницу и проверьте еще раз.');
        }
      } else {
        const attemptOfficeCheckIn = async () => {
          if (!navigator.geolocation) {
            return attendanceAPI.officeCheckIn({});
          }
          try {
            const position = await new Promise((resolve, reject) => {
              navigator.geolocation.getCurrentPosition(resolve, reject, {
                enableHighAccuracy: true,
                timeout: 15000,
                maximumAge: 0,
              });
            });
            return attendanceAPI.officeCheckIn({
              latitude: position.coords.latitude,
              longitude: position.coords.longitude,
              accuracy_m: position.coords.accuracy,
            });
          } catch (geoError) {
            if (geoError?.code === 1 || geoError?.code === 2 || geoError?.code === 3) {
              return attendanceAPI.officeCheckIn({});
            }
            throw geoError;
          }
        };

        const response = await attemptOfficeCheckIn();
        if (!response?.data?.in_office) {
          setMessage('Офис не подтвержден. Проверьте Wi-Fi/IP офиса и повторите.');
          await loadTodayAttendanceMark();
          return;
        }
        const found = await loadTodayAttendanceMark();
        if (found?.status) {
          setMessage('Отметка о начале работы в офисе подтверждена.');
        } else {
          setMessage('Проверка офиса прошла, но отметка не найдена. Проверьте API /attendance/my.');
        }
      }
    } catch (e) {
      setMessage(extractErrorMessage(e, 'Не удалось выполнить отметку начала работы.'));
      try {
        await loadTodayAttendanceMark();
      } catch {
        // ignore refresh errors
      }
    } finally {
      setMarkingStart(false);
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

                <div style={{ margin: '14px 0', borderTop: '1px solid var(--gray-200)' }} />

                <div style={{ marginBottom: 8, fontWeight: 700 }}>
                  Сегодня ({todayLabel}, {todayIso})
                </div>
                <div style={{ marginBottom: 6 }}>
                  <b>Формат:</b> {todayShift.mode === 'office' ? 'Офис' : todayShift.mode === 'online' ? 'Онлайн' : 'Выходной'}
                </div>
                <div style={{ marginBottom: 6 }}>
                  <b>Время:</b> {todayShift.start_time && todayShift.end_time ? `${todayShift.start_time} - ${todayShift.end_time}` : '—'}
                </div>
                <div style={{ marginBottom: 6 }}>
                  <b>Перерывы:</b> {todayShift.breaks.length > 0
                    ? todayShift.breaks
                      .map((item) => `${item.start_time || '—'}-${item.end_time || '—'}`)
                      .join(', ')
                    : 'Нет'}
                </div>
                <div style={{ marginBottom: 10 }}>
                  <b>Обед:</b> {todayShift.lunch_start && todayShift.lunch_end ? `${todayShift.lunch_start}-${todayShift.lunch_end}` : 'Нет'}
                </div>
                <div style={{ marginBottom: 10 }}>
                  <b>Отметка на сегодня:</b> {todayAttendanceMark ? todayAttendanceMark.status : 'Нет'}
                </div>

                {isTodayWorking && (
                  <button
                    className={`btn btn-sm ${hasTodayMark ? 'btn-secondary' : 'btn-primary'}`}
                    type="button"
                    onClick={markStartOfWork}
                    disabled={markingStart || hasTodayMark}
                  >
                    {hasTodayMark
                      ? 'Отмечен'
                      : markingStart
                        ? 'Проверяем...'
                        : 'Отметиться о начале работы'}
                  </button>
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
                <div className="weekly-plan-toolbar">
                  <div className="weekly-plan-meta">
                    <div className="weekly-plan-label">Неделя (понедельник)</div>
                    <div className="weekly-plan-date">{formatWeekStartLabel(weekStart)}</div>
                  </div>
                  <div className="weekly-plan-hours">
                    Офис: {officeHours} ч · Онлайн: {onlineHours} ч
                  </div>
                  <div className="weekly-plan-actions">
                    <button
                      className="btn btn-secondary btn-sm"
                      type="button"
                      onClick={() => setWeekStart((prev) => shiftWeek(prev, -1, weeklyPlans))}
                    >
                      Предыдущая неделя
                    </button>
                    <button
                      className="btn btn-secondary btn-sm"
                      type="button"
                      onClick={() => setWeekStart((prev) => shiftWeek(prev, 1, weeklyPlans))}
                    >
                      Следующая неделя
                    </button>
                  </div>
                </div>

                <div className="weekly-day-tabs">
                  {days.map((d, idx) => (
                    <button
                      key={d.date}
                      type="button"
                      className={`weekly-day-tab ${selectedDayIndex === idx ? 'active' : ''}`}
                      onClick={() => setSelectedDayIndex(idx)}
                    >
                      <div className="weekly-day-tab-top">{DAY_LABELS[idx]}</div>
                      <div className="weekly-day-tab-bottom">{d.mode === 'day_off' ? 'Выходной' : 'Рабочий'}</div>
                    </button>
                  ))}
                </div>

                {selectedDay && (
                  <div className="weekly-day-editor">
                    <div className="weekly-day-editor-header">
                      <div className="weekly-day-editor-title">{selectedDayTitle}</div>
                    </div>

                    <div className="grid-2" style={{ marginBottom: 10 }}>
                      <div className="form-group">
                        <label className="form-label">Начало</label>
                        <input
                          className="form-input"
                          type="time"
                          value={selectedDay.start_time}
                          disabled={!selectedIsWorkday}
                          onChange={(e) => updateDay(selectedDayIndex, { start_time: e.target.value })}
                        />
                      </div>
                      <div className="form-group">
                        <label className="form-label">Конец</label>
                        <input
                          className="form-input"
                          type="time"
                          value={selectedDay.end_time}
                          disabled={!selectedIsWorkday}
                          onChange={(e) => updateDay(selectedDayIndex, { end_time: e.target.value })}
                        />
                      </div>
                    </div>

                    <div className="form-group" style={{ marginBottom: 10 }}>
                      <label className="form-label">Формат</label>
                      <select
                        className="form-select"
                        value={selectedDay.mode}
                        onChange={(e) => {
                          const mode = e.target.value;
                          if (mode === 'day_off') {
                            updateDay(selectedDayIndex, { mode, start_time: '', end_time: '', lunch_start: '', lunch_end: '', breaks: [] });
                          } else {
                            const defaults = defaultShiftByDayIndex(selectedDayIndex);
                            updateDay(selectedDayIndex, {
                              mode,
                              start_time: selectedDay.start_time || defaults.start,
                              end_time: selectedDay.end_time || defaults.end,
                            });
                          }
                        }}
                      >
                        <option value="office">Офис</option>
                        <option value="online">Онлайн</option>
                        <option value="day_off">Выходной</option>
                      </select>
                    </div>

                    {selectedDay.mode === 'office' && selectedIsWorkday && (
                      <>
                        <div className="grid-2" style={{ marginBottom: 10 }}>
                          <div className="form-group">
                            <label className="form-label">Обед с</label>
                            <input className="form-input" type="time" value={selectedDay.lunch_start} onChange={(e) => updateDay(selectedDayIndex, { lunch_start: e.target.value })} />
                          </div>
                          <div className="form-group">
                            <label className="form-label">Обед до</label>
                            <input className="form-input" type="time" value={selectedDay.lunch_end} onChange={(e) => updateDay(selectedDayIndex, { lunch_end: e.target.value })} />
                          </div>
                        </div>

                        <div className="form-group" style={{ marginBottom: 10 }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                            <label className="form-label">Короткие перерывы</label>
                            <button className="btn btn-secondary btn-sm" type="button" onClick={() => addBreak(selectedDayIndex)} disabled={selectedDay.breaks.length >= 4}>
                              + 15 мин
                            </button>
                          </div>
                          <div style={{ display: 'grid', gap: 6 }}>
                            {selectedDay.breaks.map((b, bi) => (
                              <div key={`${selectedDay.date}-b-${bi}`} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr auto', gap: 6 }}>
                                <input className="form-input" type="time" value={b.start_time} onChange={(e) => updateBreak(selectedDayIndex, bi, { start_time: e.target.value })} />
                                <input className="form-input" type="time" value={b.end_time} onChange={(e) => updateBreak(selectedDayIndex, bi, { end_time: e.target.value })} />
                                <button className="btn btn-secondary btn-sm" type="button" onClick={() => removeBreak(selectedDayIndex, bi)}>?</button>
                              </div>
                            ))}
                          </div>
                        </div>
                      </>
                    )}

                    <div className="form-group">
                      <label className="form-label">Комментарий</label>
                      <input className="form-input" value={selectedDay.comment} onChange={(e) => updateDay(selectedDayIndex, { comment: e.target.value })} />
                    </div>
                  </div>
                )}

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













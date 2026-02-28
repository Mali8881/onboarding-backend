import { useEffect, useMemo, useState } from 'react';
import MainLayout from '../../layouts/MainLayout';
import { onboardingAPI } from '../../api/content';
import { CheckCircle, CheckSquare, Send, Square } from 'lucide-react';

const STATUS_LABELS = {
  draft: 'Черновик',
  sent: 'Отправлен',
  accepted: 'Принят',
  rework: 'На доработке',
  rejected: 'Отклонен',
};

const normStatus = (value) => {
  const raw = String(value || '').toLowerCase();
  if (raw === 'draft') return 'draft';
  if (raw === 'sent') return 'sent';
  if (raw === 'accepted') return 'accepted';
  if (raw === 'revision') return 'rework';
  if (raw === 'rework') return 'rework';
  if (raw === 'rejected') return 'rejected';
  return 'draft';
};

const findReportByDay = (reports, dayId) => reports.find((r) => String(r.day_id) === String(dayId)) || null;

const materialToDoc = (item) => {
  const rawType = String(item.type || '').toLowerCase();
  let type = 'link';
  if (rawType === 'file') type = 'file';
  if (rawType === 'video') type = 'video';
  const content = String(item.content || '');
  return {
    id: item.id,
    title: content,
    type,
    url: content.startsWith('http') ? content : '',
  };
};

export default function Onboarding() {
  const [tab, setTab] = useState('onboarding');
  const [days, setDays] = useState([]);
  const [overview, setOverview] = useState(null);
  const [reports, setReports] = useState([]);
  const [activeDayId, setActiveDayId] = useState('');
  const [dayDetails, setDayDetails] = useState({});
  const [taskState, setTaskState] = useState({});
  const [reportData, setReportData] = useState({ did: '', will_do: '', problems: '' });
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const activeDay = useMemo(() => days.find((d) => String(d.id) === String(activeDayId)) || null, [days, activeDayId]);
  const activeDetail = activeDay ? dayDetails[String(activeDay.id)] : null;
  const activeReport = activeDay ? findReportByDay(reports, activeDay.id) : null;
  const tasks = activeDetail?.tasks || [];
  const taskMap = taskState[String(activeDay?.id)] || {};
  const doneTasks = tasks.filter((t) => taskMap[t.id]).length;
  const totalTasks = tasks.length;
  const progress = totalTasks ? Math.round((doneTasks / totalTasks) * 100) : 0;
  const reportStatus = normStatus(activeReport?.status);

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const [daysRes, myRes, reportsRes] = await Promise.all([
        onboardingAPI.listDays(),
        onboardingAPI.getMy(),
        onboardingAPI.getReports(),
      ]);
      const nextDays = Array.isArray(daysRes.data) ? daysRes.data : [];
      const nextReports = Array.isArray(reportsRes.data) ? reportsRes.data : [];
      setDays(nextDays);
      setOverview(myRes.data || null);
      setReports(nextReports);
      if (nextDays.length > 0) {
        const current = myRes.data?.current_day?.id || nextDays[0].id;
        setActiveDayId(String(current));
      }
    } catch (e) {
      setError(e.response?.data?.detail || 'Не удалось загрузить onboarding.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    if (!activeDayId) return;
    if (dayDetails[String(activeDayId)]) return;
    onboardingAPI.getDay(activeDayId)
      .then((res) => {
        const detail = res.data || {};
        setDayDetails((prev) => ({ ...prev, [String(activeDayId)]: detail }));
        const dayTasks = Array.isArray(detail.tasks) ? detail.tasks : [];
        setTaskState((prev) => ({
          ...prev,
          [String(activeDayId)]: dayTasks.reduce((acc, item) => ({ ...acc, [item.id]: item.column === 'Done' }), {}),
        }));
      })
      .catch(() => {});
  }, [activeDayId, dayDetails]);

  useEffect(() => {
    if (!activeDay) return;
    const report = findReportByDay(reports, activeDay.id);
    setReportData({
      did: report?.did || '',
      will_do: report?.will_do || '',
      problems: report?.problems || '',
    });
  }, [activeDay, reports]);

  const toggleTask = (taskId) => {
    if (!activeDay) return;
    setTaskState((prev) => ({
      ...prev,
      [String(activeDay.id)]: {
        ...(prev[String(activeDay.id)] || {}),
        [taskId]: !(prev[String(activeDay.id)] || {})[taskId],
      },
    }));
  };

  const submitReport = async () => {
    if (!activeDay) return;
    if (!reportData.did.trim() || !reportData.will_do.trim()) {
      setError('Заполните поля "Что сделал" и "Что буду делать".');
      return;
    }
    setSubmitting(true);
    setError('');
    try {
      const payload = { day_id: activeDay.id, ...reportData };
      if (activeReport?.id) {
        await onboardingAPI.updateReport(activeReport.id, reportData);
      } else {
        await onboardingAPI.submitReport(payload);
      }
      const reportsRes = await onboardingAPI.getReports();
      setReports(Array.isArray(reportsRes.data) ? reportsRes.data : []);
    } catch (e) {
      setError(e.response?.data?.detail || 'Не удалось отправить отчет.');
    } finally {
      setSubmitting(false);
    }
  };

  const completeCurrentDay = async () => {
    if (!activeDay) return;
    setSubmitting(true);
    setError('');
    try {
      await onboardingAPI.completeDay(activeDay.id);
      await load();
    } catch (e) {
      setError(e.response?.data?.detail || 'Не удалось завершить день onboarding.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <MainLayout title="Программа адаптации">
      <div className="page-header">
        <div>
          <div className="page-title">Программа адаптации</div>
          <div className="page-subtitle">Материалы, задачи и ежедневный отчет стажера</div>
        </div>
      </div>

      {error && <div className="card" style={{ marginBottom: 12 }}><div className="card-body" style={{ color: '#b91c1c' }}>{error}</div></div>}
      {loading && <div className="card"><div className="card-body">Загрузка...</div></div>}

      {!loading && (
        <>
          <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
            {days.map((day) => {
              const done = overview?.days?.find((d) => String(d.day_id) === String(day.id))?.status === 'DONE';
              return (
                <button
                  key={day.id}
                  onClick={() => setActiveDayId(String(day.id))}
                  style={{
                    padding: '8px 18px',
                    borderRadius: 'var(--radius)',
                    border: '1px solid',
                    borderColor: String(activeDayId) === String(day.id) ? 'var(--primary)' : 'var(--gray-200)',
                    background: String(activeDayId) === String(day.id) ? 'var(--primary-light)' : 'white',
                    color: String(activeDayId) === String(day.id) ? 'var(--primary)' : 'var(--gray-700)',
                    fontWeight: 600,
                    fontSize: 13,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                  }}
                >
                  День {day.day_number}
                  {done && <CheckCircle size={13} color="#16A34A" />}
                </button>
              );
            })}
          </div>

          <div className="tabs">
            <button className={`tab-btn ${tab === 'onboarding' ? 'active' : ''}`} onClick={() => setTab('onboarding')}>Онбординг</button>
            <button className={`tab-btn ${tab === 'tasks' ? 'active' : ''}`} onClick={() => setTab('tasks')}>Задачи {doneTasks}/{totalTasks}</button>
            <button className={`tab-btn ${tab === 'report' ? 'active' : ''}`} onClick={() => setTab('report')}>Отчет</button>
          </div>

          {tab === 'onboarding' && activeDay && (
            <div className="onboarding-day-card">
              <h2 style={{ fontSize: 22, fontWeight: 700, color: 'var(--gray-900)', marginBottom: 6 }}>
                День {activeDay.day_number}. {activeDay.title}
              </h2>
              <div style={{ fontSize: 13, color: 'var(--gray-500)', marginBottom: 16 }}>
                Дедлайн: {activeDay.deadline_time || 'Не задан'}
              </div>

              <div className="section-label">Цели дня</div>
              <ul style={{ paddingLeft: 20, marginBottom: 20 }}>
                {(activeDay.goals || []).map((goal, i) => (
                  <li key={i} style={{ fontSize: 14, color: 'var(--gray-700)', marginBottom: 6, lineHeight: 1.5 }}>{goal}</li>
                ))}
              </ul>

              <div className="section-label">Инструкции</div>
              <p style={{ fontSize: 14, color: 'var(--gray-700)', lineHeight: 1.7, marginBottom: 20 }}>{activeDay.instructions || activeDay.description}</p>

              <div className="section-label">Материалы</div>
              <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
                {(activeDetail?.materials || []).map((material) => {
                  const doc = materialToDoc(material);
                  return (
                    <a
                      key={doc.id}
                      className="doc-card"
                      href={doc.url || '#'}
                      target="_blank"
                      rel="noreferrer"
                      style={{ flex: '1', minWidth: 180, textDecoration: 'none', color: 'inherit' }}
                    >
                      <div style={{ flex: 1 }}>
                        <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--gray-800)' }}>{doc.title}</div>
                        <div style={{ fontSize: 11, color: 'var(--gray-400)' }}>{doc.type.toUpperCase()}</div>
                      </div>
                    </a>
                  );
                })}
              </div>

              <button className="btn btn-primary" disabled={submitting} onClick={completeCurrentDay}>
                Завершить день onboarding
              </button>
            </div>
          )}

          {tab === 'tasks' && (
            <div className="onboarding-day-card">
              <div style={{ marginBottom: 14 }}>
                <div style={{ fontSize: 17, fontWeight: 700 }}>Задачи дня</div>
                <div style={{ fontSize: 13, color: 'var(--gray-500)' }}>{activeDay?.title || ''}</div>
              </div>

              <div style={{ height: 8, background: 'var(--gray-100)', borderRadius: 4, marginBottom: 24, overflow: 'hidden' }}>
                <div style={{ height: '100%', width: `${progress}%`, background: progress === 100 ? '#16A34A' : 'var(--primary)', borderRadius: 4 }} />
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {tasks.length === 0 && <div style={{ color: 'var(--gray-500)' }}>Задачи не назначены.</div>}
                {tasks.map((task) => {
                  const done = !!taskMap[task.id];
                  return (
                    <div
                      key={task.id}
                      onClick={() => toggleTask(task.id)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 14,
                        padding: '14px 16px',
                        borderRadius: 'var(--radius)',
                        border: '1px solid',
                        borderColor: done ? '#A7F3D0' : 'var(--gray-200)',
                        background: done ? '#F0FDF4' : 'white',
                        cursor: 'pointer',
                      }}
                    >
                      <div style={{ flexShrink: 0, color: done ? '#16A34A' : 'var(--gray-300)' }}>
                        {done ? <CheckSquare size={20} /> : <Square size={20} />}
                      </div>
                      <span style={{ fontSize: 14, fontWeight: 500, color: done ? 'var(--gray-400)' : 'var(--gray-800)', textDecoration: done ? 'line-through' : 'none', flex: 1 }}>
                        {task.title}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {tab === 'report' && (
            <div className="onboarding-day-card">
              <div style={{ marginBottom: 14 }}>
                <div style={{ fontSize: 13, color: 'var(--gray-500)' }}>Статус: {STATUS_LABELS[reportStatus]}</div>
              </div>
              <div className="form-group" style={{ marginBottom: 14 }}>
                <label className="form-label">Что сделал</label>
                <textarea
                  className="form-textarea"
                  value={reportData.did}
                  onChange={(e) => setReportData((prev) => ({ ...prev, did: e.target.value }))}
                  style={{ minHeight: 120 }}
                />
              </div>
              <div className="form-group" style={{ marginBottom: 14 }}>
                <label className="form-label">Что буду делать</label>
                <textarea
                  className="form-textarea"
                  value={reportData.will_do}
                  onChange={(e) => setReportData((prev) => ({ ...prev, will_do: e.target.value }))}
                  style={{ minHeight: 120 }}
                />
              </div>
              <div className="form-group" style={{ marginBottom: 14 }}>
                <label className="form-label">Проблемы</label>
                <textarea
                  className="form-textarea"
                  value={reportData.problems}
                  onChange={(e) => setReportData((prev) => ({ ...prev, problems: e.target.value }))}
                  style={{ minHeight: 100 }}
                />
              </div>
              <button className="btn btn-primary" disabled={submitting} onClick={submitReport} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <Send size={14} /> {submitting ? 'Отправка...' : 'Сохранить отчет'}
              </button>
            </div>
          )}
        </>
      )}
    </MainLayout>
  );
}

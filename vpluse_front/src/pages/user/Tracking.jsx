import { useState, useEffect, useRef } from 'react';
import { useAuth } from '../../context/AuthContext';
import MainLayout from '../../layouts/MainLayout';
import { Play, Square, Plus, X, Clock, Calendar, BarChart2, Trash2 } from 'lucide-react';

const PROJECTS = ['Разработка платформы', 'Онбординг стажёров', 'Маркетинг', 'Внутренние задачи', 'Митинги'];

const fmtTime = (sec) => {
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = sec % 60;
  return `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
};

const fmtDur = (sec) => {
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  if (h > 0) return `${h}ч ${m}м`;
  return `${m}м`;
};

const today = () => new Date().toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' });

const INIT_LOGS = [
  { id: 1, project: 'Разработка платформы', task: 'Верстка компонентов',      date: '23.02.2026', dur: 7200  },
  { id: 2, project: 'Маркетинг',            task: 'Подготовка презентации',   date: '23.02.2026', dur: 3600  },
  { id: 3, project: 'Митинги',              task: 'Еженедельный митинг',       date: '22.02.2026', dur: 2700  },
  { id: 4, project: 'Разработка платформы', task: 'Code review',               date: '22.02.2026', dur: 5400  },
  { id: 5, project: 'Онбординг стажёров',   task: 'Проверка отчётов',         date: '21.02.2026', dur: 1800  },
];

export default function Tracking() {
  const { user } = useAuth();
  const [logs,      setLogs]    = useState(INIT_LOGS);
  const [running,   setRunning] = useState(false);
  const [elapsed,   setElapsed] = useState(0);
  const [project,   setProject] = useState(PROJECTS[0]);
  const [taskName,  setTask]    = useState('');
  const [modal,     setModal]   = useState(false);
  const [manForm,   setManForm] = useState({ project: PROJECTS[0], task: '', date: today(), hours: '', minutes: '' });
  const intervalRef = useRef(null);

  useEffect(() => {
    if (running) {
      intervalRef.current = setInterval(() => setElapsed(e => e + 1), 1000);
    } else {
      clearInterval(intervalRef.current);
    }
    return () => clearInterval(intervalRef.current);
  }, [running]);

  const startStop = () => {
    if (running) {
      // Stop — save log
      if (elapsed > 0) {
        setLogs(l => [{
          id: Date.now(),
          project,
          task: taskName || 'Без названия',
          date: today(),
          dur: elapsed,
        }, ...l]);
      }
      setElapsed(0);
      setRunning(false);
    } else {
      setRunning(true);
    }
  };

  const addManual = () => {
    const dur = (parseInt(manForm.hours) || 0) * 3600 + (parseInt(manForm.minutes) || 0) * 60;
    if (!dur || !manForm.task.trim()) return;
    setLogs(l => [{ id: Date.now(), project: manForm.project, task: manForm.task, date: manForm.date, dur }, ...l]);
    setManForm({ project: PROJECTS[0], task: '', date: today(), hours: '', minutes: '' });
    setModal(false);
  };

  const deleteLog = (id) => setLogs(l => l.filter(x => x.id !== id));

  const totalToday   = logs.filter(l => l.date === today()).reduce((s, l) => s + l.dur, 0);
  const totalWeek    = logs.reduce((s, l) => s + l.dur, 0);
  const byProject    = PROJECTS.map(p => ({ name: p, dur: logs.filter(l => l.project === p).reduce((s, l) => s + l.dur, 0) })).filter(p => p.dur > 0);
  const maxDur       = Math.max(...byProject.map(p => p.dur), 1);

  return (
    <MainLayout title="Трекинг времени">
      <div className="page-header">
        <div>
          <div className="page-title">⏱ Трекинг времени</div>
          <div className="page-subtitle">Отслеживай время работы по задачам и проектам</div>
        </div>
        <button className="btn btn-secondary" onClick={() => setModal(true)} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <Plus size={15} /> Добавить вручную
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: 20 }}>
        {/* Left column */}
        <div>
          {/* Timer card */}
          <div className="card" style={{ marginBottom: 20, borderTop: running ? '3px solid #EF4444' : '3px solid var(--primary)' }}>
            <div className="card-body">
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--gray-600)', marginBottom: 12 }}>
                {running ? '🔴 Идёт запись...' : '▶ Запустить таймер'}
              </div>

              {/* Timer display */}
              <div style={{ fontSize: 52, fontWeight: 800, letterSpacing: '-2px', color: running ? '#EF4444' : 'var(--gray-800)', marginBottom: 20, fontVariantNumeric: 'tabular-nums' }}>
                {fmtTime(elapsed)}
              </div>

              {/* Inputs */}
              <div style={{ display: 'flex', gap: 10, marginBottom: 16, flexWrap: 'wrap' }}>
                <input className="form-input" placeholder="Название задачи..." value={taskName}
                  onChange={e => setTask(e.target.value)} disabled={running}
                  style={{ flex: 1, minWidth: 200 }} />
                <select className="form-select" value={project} onChange={e => setProject(e.target.value)}
                  disabled={running} style={{ width: 200 }}>
                  {PROJECTS.map(p => <option key={p}>{p}</option>)}
                </select>
              </div>

              <button
                onClick={startStop}
                style={{
                  display: 'flex', alignItems: 'center', gap: 8, padding: '10px 24px',
                  borderRadius: 'var(--radius)', border: 'none', cursor: 'pointer', fontWeight: 700, fontSize: 14,
                  background: running ? '#EF4444' : 'var(--primary)', color: 'white',
                  transition: 'all 0.15s',
                }}>
                {running ? <><Square size={16} fill="white" /> Стоп — сохранить</> : <><Play size={16} fill="white" /> Старт</>}
              </button>
            </div>
          </div>

          {/* Log table */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">История записей</span>
              <span style={{ fontSize: 12, color: 'var(--gray-400)' }}>{logs.length} записей</span>
            </div>
            {logs.length === 0 ? (
              <div className="card-body" style={{ textAlign: 'center', padding: 40, color: 'var(--gray-400)' }}>
                <Clock size={32} style={{ marginBottom: 8, opacity: 0.3 }} />
                <div>Записей пока нет</div>
              </div>
            ) : (
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr><th>ДАТА</th><th>ПРОЕКТ</th><th>ЗАДАЧА</th><th>ВРЕМЯ</th><th></th></tr>
                  </thead>
                  <tbody>
                    {logs.map(log => (
                      <tr key={log.id}>
                        <td style={{ fontSize: 12, color: 'var(--gray-400)', whiteSpace: 'nowrap' }}>{log.date}</td>
                        <td>
                          <span style={{ fontSize: 12, fontWeight: 600, padding: '2px 8px', borderRadius: 20, background: 'var(--primary-light)', color: 'var(--primary)' }}>
                            {log.project}
                          </span>
                        </td>
                        <td style={{ fontSize: 13 }}>{log.task}</td>
                        <td style={{ fontWeight: 700, fontSize: 13, whiteSpace: 'nowrap' }}>
                          <Clock size={11} style={{ marginRight: 4, verticalAlign: 'middle', color: 'var(--gray-400)' }} />
                          {fmtDur(log.dur)}
                        </td>
                        <td>
                          <button className="btn-icon" onClick={() => deleteLog(log.id)} style={{ color: 'var(--danger)' }}>
                            <Trash2 size={13} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        {/* Right column — stats */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Stats cards */}
          <div className="card">
            <div className="card-header"><span className="card-title">📊 Статистика</span></div>
            <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {[
                { label: 'Сегодня',          val: fmtDur(totalToday),            color: '#2563EB', icon: '📅' },
                { label: 'За неделю',        val: fmtDur(totalWeek),             color: '#7C3AED', icon: '📆' },
                { label: 'Всего записей',    val: String(logs.length),           color: '#16A34A', icon: '📝' },
                { label: 'Среднее в день',   val: fmtDur(Math.round(totalWeek / 5)), color: '#EA580C', icon: '⚡' },
              ].map(s => (
                <div key={s.label} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid var(--gray-100)' }}>
                  <div style={{ fontSize: 13, color: 'var(--gray-600)' }}>{s.icon} {s.label}</div>
                  <div style={{ fontSize: 15, fontWeight: 700, color: s.color }}>{s.val}</div>
                </div>
              ))}
            </div>
          </div>

          {/* By project */}
          {byProject.length > 0 && (
            <div className="card">
              <div className="card-header"><span className="card-title">По проектам</span></div>
              <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {byProject.sort((a,b) => b.dur - a.dur).map(p => (
                  <div key={p.name}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
                      <span style={{ color: 'var(--gray-700)', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 180 }}>{p.name}</span>
                      <span style={{ color: 'var(--gray-500)', flexShrink: 0, marginLeft: 8 }}>{fmtDur(p.dur)}</span>
                    </div>
                    <div style={{ height: 6, background: 'var(--gray-100)', borderRadius: 3, overflow: 'hidden' }}>
                      <div style={{ height: '100%', width: `${(p.dur / maxDur) * 100}%`, background: 'var(--primary)', borderRadius: 3, transition: 'width 0.3s' }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Manual add modal */}
      {modal && (
        <div className="modal-overlay" onClick={() => setModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 420 }}>
            <div className="modal-header">
              <div className="modal-title">Добавить время вручную</div>
              <button className="btn-icon" onClick={() => setModal(false)}><X size={18} /></button>
            </div>
            <div className="modal-body">
              <div className="form-group" style={{ marginBottom: 14 }}>
                <label className="form-label">Задача</label>
                <input className="form-input" placeholder="Название задачи" value={manForm.task}
                  onChange={e => setManForm(f => ({ ...f, task: e.target.value }))} />
              </div>
              <div className="form-group" style={{ marginBottom: 14 }}>
                <label className="form-label">Проект</label>
                <select className="form-select" value={manForm.project}
                  onChange={e => setManForm(f => ({ ...f, project: e.target.value }))}>
                  {PROJECTS.map(p => <option key={p}>{p}</option>)}
                </select>
              </div>
              <div className="grid-2" style={{ marginBottom: 14 }}>
                <div className="form-group">
                  <label className="form-label">Часы</label>
                  <input className="form-input" type="number" min="0" max="23" placeholder="0"
                    value={manForm.hours} onChange={e => setManForm(f => ({ ...f, hours: e.target.value }))} />
                </div>
                <div className="form-group">
                  <label className="form-label">Минуты</label>
                  <input className="form-input" type="number" min="0" max="59" placeholder="30"
                    value={manForm.minutes} onChange={e => setManForm(f => ({ ...f, minutes: e.target.value }))} />
                </div>
              </div>
              <div className="form-group">
                <label className="form-label">Дата</label>
                <input className="form-input" type="date" value={manForm.date.split('.').reverse().join('-')}
                  onChange={e => {
                    const d = e.target.value.split('-').reverse().join('.');
                    setManForm(f => ({ ...f, date: d }));
                  }} />
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setModal(false)}>Отмена</button>
              <button className="btn btn-primary" onClick={addManual} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <Plus size={14} /> Добавить
              </button>
            </div>
          </div>
        </div>
      )}
    </MainLayout>
  );
}

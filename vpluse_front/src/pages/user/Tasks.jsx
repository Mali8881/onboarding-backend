import { useEffect, useMemo, useState } from 'react';
import { Plus, X } from 'lucide-react';
import MainLayout from '../../layouts/MainLayout';
import { useAuth } from '../../context/AuthContext';
import { tasksAPI } from '../../api/content';
import { usersAPI } from '../../api/auth';

const PRIORITY_LABELS = {
  high: 'Высокий',
  medium: 'Средний',
  low: 'Низкий',
};

const DEFAULT_COLUMN_ORDERS = [1, 2, 3, 4];
const DEFAULT_COLUMN_NAMES = {
  1: 'Новые',
  2: 'В работе',
  3: 'На проверке',
  4: 'Завершенные',
};

function todayISO() {
  return new Date().toISOString().slice(0, 10);
}

function normalizeTask(raw) {
  return {
    id: raw.id,
    title: raw.title || '',
    description: raw.description || '',
    assigneeId: raw.assignee,
    assigneeName: raw.assignee_username || `ID ${raw.assignee}`,
    reporterName: raw.reporter_username || '',
    dueDate: raw.due_date || null,
    priority: raw.priority || 'medium',
    columnId: raw.column,
    columnOrder: Number(raw.column_order || 0),
    columnName: raw.column_name || '',
    boardColumns: Array.isArray(raw.board_columns) ? raw.board_columns : [],
    updatedAt: raw.updated_at,
  };
}

function normalizeReport(raw) {
  return {
    id: raw.id,
    username: raw.user_full_name || raw.username || '-',
    date: raw.report_date,
    started: raw.started_tasks || '',
    taken: raw.taken_tasks || '',
    completed: raw.completed_tasks || '',
    blockers: raw.blockers || '',
    summary: raw.summary || '',
  };
}

export default function Tasks() {
  const { user } = useAuth();
  const role = user?.role;
  const isManager = ['department_head', 'admin', 'superadmin', 'projectmanager'].includes(role);
  const canSwitchTaskSections = !['employee', 'intern'].includes(role);
  const canSeeOwnTasksSection = canSwitchTaskSections && role !== 'superadmin';
  const canSeeTeamTasksSection = canSwitchTaskSections;
  const [taskSection, setTaskSection] = useState(role === 'superadmin' ? 'team' : 'my');
  const canSubmitDaily = ['employee', 'projectmanager'].includes(user?.role);
  const canViewDaily = ['department_head', 'admin', 'superadmin', 'projectmanager'].includes(user?.role);

  const [tasks, setTasks] = useState([]);
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [error, setError] = useState('');
  const [assigneeOptions, setAssigneeOptions] = useState([]);
  const [movingTaskId, setMovingTaskId] = useState(null);
  const [reportDate, setReportDate] = useState(todayISO());

  const [form, setForm] = useState({
    title: '',
    description: '',
    priority: 'medium',
    due_date: '',
    assignee_id: '',
  });

  const [dailyForm, setDailyForm] = useState({
    started_tasks: '',
    taken_tasks: '',
    completed_tasks: '',
    blockers: '',
  });

  const loadAll = async () => {
    setLoading(true);
    setError('');
    try {
      const [myRes, teamRes, reportsRes] = await Promise.all([
        canSeeOwnTasksSection ? tasksAPI.my().catch(() => ({ data: [] })) : Promise.resolve({ data: [] }),
        canSeeTeamTasksSection ? tasksAPI.team().catch(() => ({ data: [] })) : Promise.resolve({ data: [] }),
        tasksAPI.dailyReports({ date: reportDate }).catch(() => ({ data: [] })),
      ]);

      const myTasks = Array.isArray(myRes.data) ? myRes.data : [];
      const teamTasks = Array.isArray(teamRes.data) ? teamRes.data : [];
      const selectedTasks = taskSection === 'team' ? teamTasks : myTasks;
      const byId = new Map();
      selectedTasks.forEach((t) => byId.set(t.id, normalizeTask(t)));
      setTasks(Array.from(byId.values()).sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt)));

      const reportRows = Array.isArray(reportsRes.data) ? reportsRes.data : [];
      setReports(reportRows.map(normalizeReport));
    } catch {
      setError('Не удалось загрузить задачи или отчеты.');
    } finally {
      setLoading(false);
    }
  };

  const loadAssignees = async () => {
    if (!isManager) return;
    try {
      const res = await usersAPI.list();
      const list = Array.isArray(res.data) ? res.data : [];
      setAssigneeOptions(
        list.map((u) => ({
          id: u.id,
          name: u.full_name || u.username || `ID ${u.id}`,
        }))
      );
    } catch {
      // fallback: derive from tasks
    }
  };

  useEffect(() => {
    loadAll();
    loadAssignees();
  }, []);

  useEffect(() => {
    setTaskSection(role === 'superadmin' ? 'team' : 'my');
  }, [role]);

  useEffect(() => {
    if (!showModal) return;
    setForm((prev) => ({
      ...prev,
      assignee_id: prev.assignee_id || user?.id || '',
    }));
  }, [showModal, user?.id]);

  useEffect(() => {
    loadAll();
  }, [reportDate, taskSection]);

  const columns = useMemo(() => {
    const map = new Map();
    DEFAULT_COLUMN_ORDERS.forEach((order) => {
      map.set(order, {
        order,
        id: null,
        name: DEFAULT_COLUMN_NAMES[order],
        items: [],
      });
    });

    tasks.forEach((task) => {
      const order = task.columnOrder || 1;
      if (!map.has(order)) {
        map.set(order, {
          order,
          id: task.columnId,
          name: task.columnName || `Колонка ${order}`,
          items: [],
        });
      }
      const col = map.get(order);
      if (!col.id) col.id = task.columnId;
      if (task.columnName) col.name = task.columnName;
      col.items.push(task);
    });

    return Array.from(map.values()).sort((a, b) => a.order - b.order);
  }, [tasks]);

  const createTask = async () => {
    const title = form.title.trim();
    if (!title) return;
    try {
      const assigneeId = Number(form.assignee_id || user?.id);
      await tasksAPI.create({
        title,
        description: form.description.trim(),
        assignee_id: assigneeId,
        due_date: form.due_date || null,
        priority: form.priority,
      });
      setShowModal(false);
      setForm({
        title: '',
        description: '',
        priority: 'medium',
        due_date: '',
        assignee_id: '',
      });
      await loadAll();
    } catch {
      setError('Не удалось создать задачу.');
    }
  };

  const moveTask = async (task, targetOrder) => {
    if (!task || targetOrder === task.columnOrder) return;
    const target = task.boardColumns.find((c) => Number(c.order) === Number(targetOrder));
    if (!target?.id) return;
    try {
      setMovingTaskId(task.id);
      await tasksAPI.move(task.id, target.id);
      await loadAll();
    } catch {
      setError('Не удалось изменить статус задачи.');
    } finally {
      setMovingTaskId(null);
    }
  };

  const submitDailyReport = async () => {
    if (!canSubmitDaily) return;
    try {
      await tasksAPI.submitDailyReport({
        report_date: reportDate,
        ...dailyForm,
      });
      setDailyForm({ started_tasks: '', taken_tasks: '', completed_tasks: '', blockers: '' });
      await loadAll();
    } catch {
      setError('Не удалось отправить ежедневный отчет.');
    }
  };

  return (
    <MainLayout title="Задачи">
      <div className="page-header">
        <div>
          <div className="page-title">Трекер задач</div>
          <div className="page-subtitle">Канбан доска: новые, в работе, на проверке, завершенные</div>
        </div>
        <button className="btn btn-primary" onClick={() => setShowModal(true)}><Plus size={15} /> Новая задача</button>
      </div>

      {canSwitchTaskSections && (
        <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
          {canSeeOwnTasksSection && (
            <button
              type="button"
              className={`btn btn-sm ${taskSection === 'my' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setTaskSection('my')}
            >
              Мои задачи
            </button>
          )}
          {canSeeTeamTasksSection && (
            <button
              type="button"
              className={`btn btn-sm ${taskSection === 'team' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setTaskSection('team')}
            >
              Задачи сотрудников
            </button>
          )}
        </div>
      )}

      {error ? <div className="card" style={{ marginBottom: 12 }}><div className="card-body" style={{ color: 'var(--danger)' }}>{error}</div></div> : null}

      {loading ? (
        <div className="card"><div className="card-body">Загрузка...</div></div>
      ) : (
        <>
          <div className="kanban-board">
            {columns.map((column) => (
              <div key={column.order} className="kanban-col">
                <div className="kanban-col-header">
                  <span className="kanban-col-title">{column.name}</span>
                  <span className="badge badge-blue">{column.items.length}</span>
                </div>
                {column.items.map((task) => (
                  <div key={task.id} className="kanban-card">
                    <div className="kanban-card-title">{task.title}</div>
                    <div style={{ fontSize: 12, color: 'var(--gray-500)', marginBottom: 8 }}>{task.description || 'Без описания'}</div>
                    <div style={{ fontSize: 12, color: 'var(--gray-600)' }}>Исполнитель: {task.assigneeName}</div>
                    <div style={{ fontSize: 12, color: 'var(--gray-600)' }}>Постановщик: {task.reporterName || '-'}</div>
                    <div style={{ fontSize: 12, color: 'var(--gray-600)' }}>Приоритет: {PRIORITY_LABELS[task.priority] || task.priority}</div>
                    <div style={{ fontSize: 12, color: 'var(--gray-600)' }}>Срок: {task.dueDate || '—'}</div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 8 }}>
                      {DEFAULT_COLUMN_ORDERS.map((order) => (
                        <button
                          key={`${task.id}-${order}`}
                          className="btn btn-secondary btn-sm"
                          type="button"
                          onClick={() => moveTask(task, order)}
                          disabled={movingTaskId === task.id || order === task.columnOrder}
                        >
                          {DEFAULT_COLUMN_NAMES[order]}
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            ))}
          </div>

          {canSubmitDaily && (!canSwitchTaskSections || taskSection === 'my') && (
            <div className="card" style={{ marginTop: 16 }}>
              <div className="card-body" style={{ display: 'grid', gap: 10 }}>
                <div style={{ fontWeight: 700 }}>Ежедневный отчет</div>
                <div className="grid-2">
                  <div className="form-group">
                    <label className="form-label">Дата</label>
                    <input className="form-input" type="date" value={reportDate} onChange={(e) => setReportDate(e.target.value)} />
                  </div>
                </div>
                <textarea className="form-textarea" placeholder="Что начал" value={dailyForm.started_tasks} onChange={(e) => setDailyForm((p) => ({ ...p, started_tasks: e.target.value }))} />
                <textarea className="form-textarea" placeholder="Что взял в работу" value={dailyForm.taken_tasks} onChange={(e) => setDailyForm((p) => ({ ...p, taken_tasks: e.target.value }))} />
                <textarea className="form-textarea" placeholder="Что завершил" value={dailyForm.completed_tasks} onChange={(e) => setDailyForm((p) => ({ ...p, completed_tasks: e.target.value }))} />
                <textarea className="form-textarea" placeholder="Проблемы / блокеры" value={dailyForm.blockers} onChange={(e) => setDailyForm((p) => ({ ...p, blockers: e.target.value }))} />
                <div>
                  <button className="btn btn-primary" onClick={submitDailyReport}>Отправить отчет</button>
                </div>
              </div>
            </div>
          )}

          {canViewDaily && canSwitchTaskSections && taskSection === 'team' && (
            <div className="card" style={{ marginTop: 16 }}>
              <div className="card-body">
                <div style={{ fontWeight: 700, marginBottom: 10 }}>Отчеты сотрудников за {reportDate}</div>
                <div className="table-wrap">
                  <table className="table">
                    <thead>
                      <tr>
                        <th>Сотрудник</th>
                        <th>Начал</th>
                        <th>Взял в работу</th>
                        <th>Завершил</th>
                        <th>Блокеры</th>
                      </tr>
                    </thead>
                    <tbody>
                      {reports.map((r) => (
                        <tr key={r.id}>
                          <td>{r.username}</td>
                          <td>{r.started || '-'}</td>
                          <td>{r.taken || '-'}</td>
                          <td>{r.completed || '-'}</td>
                          <td>{r.blockers || '-'}</td>
                        </tr>
                      ))}
                      {reports.length === 0 && (
                        <tr><td colSpan={5}>Отчетов за этот день пока нет.</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </>
      )}

      {showModal ? (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 560 }}>
            <div className="modal-header">
              <div className="modal-title">Новая задача</div>
              <button className="btn-icon" onClick={() => setShowModal(false)}><X size={18} /></button>
            </div>
            <div className="modal-body">
              <div className="form-group" style={{ marginBottom: 12 }}>
                <label className="form-label">Название</label>
                <input className="form-input" value={form.title} onChange={(e) => setForm((prev) => ({ ...prev, title: e.target.value }))} />
              </div>
              <div className="form-group" style={{ marginBottom: 12 }}>
                <label className="form-label">Описание</label>
                <textarea className="form-textarea" style={{ minHeight: 80 }} value={form.description} onChange={(e) => setForm((prev) => ({ ...prev, description: e.target.value }))} />
              </div>
              <div className="grid-2" style={{ marginBottom: 12 }}>
                {isManager ? (
                  <div className="form-group">
                    <label className="form-label">Исполнитель</label>
                    <select className="form-select" value={form.assignee_id || user?.id || ''} onChange={(e) => setForm((prev) => ({ ...prev, assignee_id: e.target.value }))}>
                      {assigneeOptions.length === 0 ? <option value={user?.id || ''}>Я</option> : null}
                      {assigneeOptions.map((opt) => (
                        <option key={opt.id} value={opt.id}>{opt.name}</option>
                      ))}
                    </select>
                  </div>
                ) : (
                  <div className="form-group">
                    <label className="form-label">Исполнитель</label>
                    <input className="form-input" value={user?.name || user?.username || 'Я'} disabled />
                  </div>
                )}
                <div className="form-group">
                  <label className="form-label">Приоритет</label>
                  <select className="form-select" value={form.priority} onChange={(e) => setForm((prev) => ({ ...prev, priority: e.target.value }))}>
                    <option value="high">Высокий</option>
                    <option value="medium">Средний</option>
                    <option value="low">Низкий</option>
                  </select>
                </div>
              </div>
              <div className="form-group">
                <label className="form-label">Срок</label>
                <input className="form-input" type="date" value={form.due_date} onChange={(e) => setForm((prev) => ({ ...prev, due_date: e.target.value }))} />
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setShowModal(false)}>Отмена</button>
              <button className="btn btn-primary" onClick={createTask}>Создать</button>
            </div>
          </div>
        </div>
      ) : null}
    </MainLayout>
  );
}

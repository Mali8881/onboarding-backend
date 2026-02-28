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
    column: raw.column,
    updatedAt: raw.updated_at,
  };
}

export default function Tasks() {
  const { user } = useAuth();
  const isManager = ['admin', 'superadmin', 'projectmanager'].includes(user?.role);
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [error, setError] = useState('');
  const [assigneeOptions, setAssigneeOptions] = useState([]);
  const [form, setForm] = useState({
    title: '',
    description: '',
    priority: 'medium',
    due_date: '',
    assignee_id: '',
  });

  const loadTasks = async () => {
    setLoading(true);
    setError('');
    try {
      const [myRes, teamRes] = await Promise.all([
        tasksAPI.my(),
        isManager ? tasksAPI.team().catch(() => ({ data: [] })) : Promise.resolve({ data: [] }),
      ]);
      const merged = [...(Array.isArray(myRes.data) ? myRes.data : []), ...(Array.isArray(teamRes.data) ? teamRes.data : [])];
      const byId = new Map();
      merged.forEach((t) => byId.set(t.id, normalizeTask(t)));
      const normalized = Array.from(byId.values()).sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt));
      setTasks(normalized);
      if (isManager) {
        const derived = new Map();
        normalized.forEach((t) => {
          if (t.assigneeId) derived.set(String(t.assigneeId), { id: t.assigneeId, name: t.assigneeName });
        });
        if (user?.id) derived.set(String(user.id), { id: user.id, name: user.name || user.username || `ID ${user.id}` });
        if (derived.size > 0) setAssigneeOptions(Array.from(derived.values()));
      }
    } catch {
      setError('Не удалось загрузить задачи.');
    } finally {
      setLoading(false);
    }
  };

  const loadAssignees = async () => {
    if (!isManager) return;
    try {
      const res = await usersAPI.list();
      const list = Array.isArray(res.data) ? res.data : [];
      const options = list.map((u) => ({
        id: u.id,
        name: u.full_name || u.username || `ID ${u.id}`,
      }));
      setAssigneeOptions(options);
    } catch {
      // Keep derived assignees from loaded tasks if users endpoint is not available for this role.
    }
  };

  useEffect(() => {
    loadTasks();
    loadAssignees();
  }, []);

  useEffect(() => {
    if (!showModal) return;
    setForm((prev) => ({
      ...prev,
      assignee_id: prev.assignee_id || user?.id || '',
    }));
  }, [showModal, user?.id]);

  const byColumn = useMemo(() => {
    const groups = new Map();
    tasks.forEach((t) => {
      const key = String(t.column ?? '0');
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(t);
    });
    return Array.from(groups.entries())
      .map(([columnId, items]) => ({ columnId, items }))
      .sort((a, b) => Number(a.columnId) - Number(b.columnId));
  }, [tasks]);

  const createTask = async () => {
    if (!isManager) return;
    const title = form.title.trim();
    if (!title) return;
    try {
      await tasksAPI.create({
        title,
        description: form.description.trim(),
        assignee_id: Number(form.assignee_id || user?.id),
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
      await loadTasks();
    } catch {
      setError('Не удалось создать задачу.');
    }
  };

  return (
    <MainLayout title="Задачи">
      <div className="page-header">
        <div>
          <div className="page-title">Задачи</div>
          <div className="page-subtitle">Список задач из backend</div>
        </div>
        {isManager ? <button className="btn btn-primary" onClick={() => setShowModal(true)}><Plus size={15} /> Новая задача</button> : null}
      </div>

      {error ? <div className="card" style={{ marginBottom: 12 }}><div className="card-body" style={{ color: 'var(--danger)' }}>{error}</div></div> : null}

      {loading ? (
        <div className="card"><div className="card-body">Загрузка...</div></div>
      ) : (
        <div className="kanban-board">
          {byColumn.map((column) => (
            <div key={column.columnId} className="kanban-col">
              <div className="kanban-col-header">
                <span className="kanban-col-title">Колонка #{column.columnId}</span>
                <span className="badge badge-blue">{column.items.length}</span>
              </div>
              {column.items.map((task) => (
                <div key={task.id} className="kanban-card">
                  <div className="kanban-card-title">{task.title}</div>
                  <div style={{ fontSize: 12, color: 'var(--gray-500)', marginBottom: 8 }}>{task.description || 'Без описания'}</div>
                  <div style={{ fontSize: 12, color: 'var(--gray-600)' }}>Исполнитель: {task.assigneeName}</div>
                  <div style={{ fontSize: 12, color: 'var(--gray-600)' }}>Приоритет: {PRIORITY_LABELS[task.priority] || task.priority}</div>
                  <div style={{ fontSize: 12, color: 'var(--gray-600)' }}>Срок: {task.dueDate || '—'}</div>
                </div>
              ))}
            </div>
          ))}
          {byColumn.length === 0 ? <div className="card"><div className="card-body">Задач пока нет.</div></div> : null}
        </div>
      )}

      {showModal && isManager ? (
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
                <div className="form-group">
                  <label className="form-label">Исполнитель</label>
                  <select className="form-select" value={form.assignee_id || user?.id || ''} onChange={(e) => setForm((prev) => ({ ...prev, assignee_id: e.target.value }))}>
                    {assigneeOptions.length === 0 ? <option value={user?.id || ''}>Я</option> : null}
                    {assigneeOptions.map((opt) => (
                      <option key={opt.id} value={opt.id}>{opt.name}</option>
                    ))}
                  </select>
                </div>
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

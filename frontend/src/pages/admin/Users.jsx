import { useEffect, useMemo, useState } from 'react';
import { Plus, Search, Pencil, Lock, Send, Check, Ban, X } from 'lucide-react';
import MainLayout from '../../layouts/MainLayout';
import { useAuth } from '../../context/AuthContext';
import {
  usersAPI,
  departmentsAPI,
  positionsAPI,
  promotionRequestsAPI,
} from '../../api/auth';

const ROLE_LABELS = {
  intern: 'Стажёр',
  employee: 'Сотрудник',
  projectmanager: 'Проект-менеджер',
  admin: 'Администратор',
  superadmin: 'Суперадмин',
};

const EMPTY_FORM = {
  name: '',
  email: '',
  department: '',
  position: '',
  role: 'intern',
  password: '',
};

function splitName(fullName) {
  const parts = String(fullName || '').trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return { first_name: '', last_name: '' };
  if (parts.length === 1) return { first_name: parts[0], last_name: '' };
  return { first_name: parts[0], last_name: parts.slice(1).join(' ') };
}

function mapUser(raw) {
  return {
    id: raw.id,
    name: raw.full_name || raw.username,
    email: raw.email || '',
    role: raw.role || 'intern',
    department: raw.department_name || '',
    departmentId: raw.department || null,
    position: raw.position_name || '',
    positionId: raw.position || null,
    status: raw.is_active ? 'active' : 'blocked',
  };
}

export default function AdminUsers() {
  const { user, isSuperAdmin } = useAuth();
  const [users, setUsers] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [positions, setPositions] = useState([]);
  const [promotionRequests, setPromotionRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [editUser, setEditUser] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState('');

  const isAdminOrSuper = isSuperAdmin || user?.role === 'admin';

  const loadAll = async () => {
    setLoading(true);
    setError('');
    try {
      const [usersRes, depRes, posRes, promotionRes] = await Promise.all([
        usersAPI.list(),
        departmentsAPI.list(),
        positionsAPI.list(),
        promotionRequestsAPI.list(),
      ]);
      setUsers((Array.isArray(usersRes.data) ? usersRes.data : []).map(mapUser));
      setDepartments(Array.isArray(depRes.data) ? depRes.data : []);
      setPositions(Array.isArray(posRes.data) ? posRes.data : []);
      setPromotionRequests(Array.isArray(promotionRes.data) ? promotionRes.data : []);
    } catch {
      setError('Не удалось загрузить данные.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
  }, []);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return users;
    return users.filter(
      (u) =>
        u.name.toLowerCase().includes(q) ||
        u.email.toLowerCase().includes(q) ||
        u.department.toLowerCase().includes(q) ||
        u.position.toLowerCase().includes(q)
    );
  }, [users, search]);

  const pending = useMemo(
    () => promotionRequests.filter((r) => r.status === 'pending'),
    [promotionRequests]
  );

  const openAdd = () => {
    setEditUser(null);
    setForm(EMPTY_FORM);
    setShowModal(true);
  };

  const openEdit = (target) => {
    setEditUser(target);
    setForm({
      name: target.name,
      email: target.email,
      department: target.departmentId || '',
      position: target.positionId || '',
      role: target.role || 'intern',
      password: '',
    });
    setShowModal(true);
  };

  const saveUser = async () => {
    if (!form.name || !form.email) return;
    const name = splitName(form.name);
    const payload = {
      username: form.email,
      email: form.email,
      first_name: name.first_name,
      last_name: name.last_name,
      department: form.department || null,
      position: form.position || null,
      role: form.role,
    };
    if (form.password) payload.password = form.password;
    try {
      if (editUser) await usersAPI.update(editUser.id, payload);
      else await usersAPI.create(payload);
      setShowModal(false);
      await loadAll();
    } catch {
      setError('Не удалось сохранить пользователя.');
    }
  };

  const toggleStatus = async (id) => {
    try {
      await usersAPI.toggleStatus(id);
      await loadAll();
    } catch {
      setError('Не удалось изменить статус.');
    }
  };

  const sendPromotion = async (targetUser) => {
    try {
      await promotionRequestsAPI.create({
        user_id: targetUser.id,
        requested_role: 'employee',
        reason: 'Заявка на перевод стажёра в сотрудники.',
      });
      await loadAll();
    } catch {
      setError('Не удалось отправить заявку.');
    }
  };

  const handleApprove = async (id) => {
    try {
      await promotionRequestsAPI.approve(id, { comment: 'Одобрено' });
      await loadAll();
    } catch {
      setError('Не удалось одобрить заявку.');
    }
  };

  const handleReject = async (id) => {
    try {
      await promotionRequestsAPI.reject(id, { comment: 'Отклонено' });
      await loadAll();
    } catch {
      setError('Не удалось отклонить заявку.');
    }
  };

  return (
    <MainLayout title="Админ-панель · Пользователи">
      <div className="page-header">
        <div>
          <div className="page-title">Пользователи</div>
          <div className="page-subtitle">Управление сотрудниками через backend API</div>
        </div>
        <button className="btn btn-primary" onClick={openAdd}><Plus size={15} /> Добавить</button>
      </div>

      {error ? <div className="card" style={{ marginBottom: 12 }}><div className="card-body" style={{ color: 'var(--danger)' }}>{error}</div></div> : null}

      {isSuperAdmin ? (
        <div className="card" style={{ marginBottom: 16 }}>
          <div className="card-header">
            <span className="card-title">Заявки на перевод</span>
            <span className="badge badge-blue">{pending.length}</span>
          </div>
          <div className="card-body">
            {pending.length === 0 ? <div style={{ fontSize: 13, color: 'var(--gray-500)' }}>Новых заявок нет.</div> : null}
            {pending.map((req) => (
              <div key={req.id} style={{ display: 'flex', justifyContent: 'space-between', gap: 12, marginBottom: 8 }}>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 14 }}>{req.username}</div>
                  <div style={{ fontSize: 12, color: 'var(--gray-500)' }}>{req.reason || 'Без комментария'}</div>
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                  <button className="btn btn-primary btn-sm" onClick={() => handleApprove(req.id)}><Check size={14} /> Одобрить</button>
                  <button className="btn btn-secondary btn-sm" onClick={() => handleReject(req.id)}><Ban size={14} /> Отклонить</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      <div className="card" style={{ marginBottom: 12 }}>
        <div className="card-body" style={{ padding: '14px 20px' }}>
          <div style={{ position: 'relative' }}>
            <Search size={14} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--gray-400)' }} />
            <input
              className="form-input"
              style={{ paddingLeft: 32 }}
              placeholder="Поиск..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </div>
      </div>

      <div className="card">
        <div className="table-wrap">
          {loading ? (
            <div style={{ padding: 16 }}>Загрузка...</div>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Пользователь</th>
                  <th>Должность</th>
                  <th>Отдел</th>
                  <th>Роль</th>
                  <th>Статус</th>
                  <th>Действия</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((u) => (
                  <tr key={u.id}>
                    <td>
                      <div className="user-cell">
                        <div className="avatar" style={{ width: 34, height: 34, fontSize: 12 }}>
                          {(u.name || '?').split(' ').map((p) => p[0]).join('').slice(0, 2)}
                        </div>
                        <div>
                          <div className="user-cell-name">{u.name}</div>
                          <div className="user-cell-email">{u.email}</div>
                        </div>
                      </div>
                    </td>
                    <td>{u.position || '-'}</td>
                    <td>{u.department || '-'}</td>
                    <td>{ROLE_LABELS[u.role] || u.role}</td>
                    <td>{u.status === 'active' ? 'Активен' : 'Заблокирован'}</td>
                    <td>
                      <div style={{ display: 'flex', gap: 6 }}>
                        <button className="btn-icon" title="Редактировать" onClick={() => openEdit(u)}><Pencil size={14} /></button>
                        <button className="btn-icon" title="Блок/разблок" onClick={() => toggleStatus(u.id)}><Lock size={14} /></button>
                        {isAdminOrSuper && !isSuperAdmin && u.role === 'intern' ? (
                          <button className="btn-icon" title="Заявка на перевод" onClick={() => sendPromotion(u)}><Send size={14} /></button>
                        ) : null}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {showModal ? (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title">{editUser ? 'Редактирование пользователя' : 'Новый пользователь'}</div>
              <button className="btn-icon" onClick={() => setShowModal(false)}><X size={18} /></button>
            </div>
            <div className="modal-body">
              <div className="grid-2">
                <div className="form-group">
                  <label className="form-label">Имя</label>
                  <input className="form-input" value={form.name} onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))} />
                </div>
                <div className="form-group">
                  <label className="form-label">Email</label>
                  <input className="form-input" value={form.email} onChange={(e) => setForm((prev) => ({ ...prev, email: e.target.value }))} />
                </div>
              </div>
              <div className="grid-2" style={{ marginTop: 10 }}>
                <div className="form-group">
                  <label className="form-label">Отдел</label>
                  <select className="form-select" value={form.department} onChange={(e) => setForm((prev) => ({ ...prev, department: e.target.value }))}>
                    <option value="">-</option>
                    {departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">Должность</label>
                  <select className="form-select" value={form.position} onChange={(e) => setForm((prev) => ({ ...prev, position: e.target.value }))}>
                    <option value="">-</option>
                    {positions.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                  </select>
                </div>
              </div>
              <div className="grid-2" style={{ marginTop: 10 }}>
                <div className="form-group">
                  <label className="form-label">Роль</label>
                  <select className="form-select" value={form.role} onChange={(e) => setForm((prev) => ({ ...prev, role: e.target.value }))}>
                    <option value="intern">Стажёр</option>
                    <option value="employee">Сотрудник</option>
                    <option value="projectmanager">Проект-менеджер</option>
                    <option value="admin">Администратор</option>
                    {isSuperAdmin ? <option value="superadmin">Суперадмин</option> : null}
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">Пароль {editUser ? '(опционально)' : ''}</label>
                  <input className="form-input" type="password" value={form.password} onChange={(e) => setForm((prev) => ({ ...prev, password: e.target.value }))} />
                </div>
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setShowModal(false)}>Отмена</button>
              <button className="btn btn-primary" onClick={saveUser}>Сохранить</button>
            </div>
          </div>
        </div>
      ) : null}
    </MainLayout>
  );
}

import { useEffect, useMemo, useState } from 'react';
import { Plus, Search, Pencil, Lock, Send, Check, Ban, X } from 'lucide-react';
import MainLayout from '../../layouts/MainLayout';
import { useAuth } from '../../context/AuthContext';
import {
  usersAPI,
  departmentsAPI,
  subdivisionsAPI,
  promotionRequestsAPI,
} from '../../api/auth';

const ROLE_LABELS = {
  intern: 'Стажер',
  employee: 'Сотрудник',
  projectmanager: 'Тимлид',
  department_head: 'Руководитель отдела',
  admin: 'Админ',
  superadmin: 'Суперадмин',
};

const EMPTY_FORM = {
  name: '',
  email: '',
  department: '',
  subdivision: '',
  manager: '',
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
    position: raw.subdivision_name || raw.position_name || '',
    positionId: raw.position || null,
    subdivisionId: raw.subdivision || null,
    subdivisionName: raw.subdivision_name || '',
    managerId: raw.manager || null,
    managerName: raw.manager_name || '',
    status: raw.is_active ? 'active' : 'blocked',
  };
}

function fixedSubdivisionLabelByRole(role) {
  if (role === 'projectmanager') return 'Тимлид';
  if (role === 'department_head') return 'Руководитель';
  if (role === 'admin') return 'Админ';
  return '';
}

export default function AdminUsers() {
  const { user, isSuperAdmin } = useAuth();
  const [users, setUsers] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [subdivisions, setSubdivisions] = useState([]);
  const [promotionRequests, setPromotionRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [editUser, setEditUser] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState('');

  const isAdminOrSuper = isSuperAdmin || user?.role === 'admin' || user?.role === 'department_head';
  const canAssignAdminRoles = isSuperAdmin || user?.role === 'admin';
  const isDepartmentHead = user?.role === 'department_head';
  const ownDepartmentId = user?.department ? String(user.department) : '';

  const loadAll = async () => {
    setLoading(true);
    setError('');
    try {
      const [usersRes, depRes, subRes, promotionRes] = await Promise.all([
        usersAPI.list(),
        departmentsAPI.list(),
        subdivisionsAPI.list({ is_active: true }),
        promotionRequestsAPI.list(),
      ]);
      setUsers((Array.isArray(usersRes.data) ? usersRes.data : []).map(mapUser));
      setDepartments(Array.isArray(depRes.data) ? depRes.data : []);
      setSubdivisions(Array.isArray(subRes.data) ? subRes.data : []);
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
      subdivision: target.subdivisionId || '',
      manager: target.managerId || '',
      role: target.role || 'intern',
      password: '',
    });
    setShowModal(true);
  };

  const saveUser = async () => {
    if (!form.name || !form.email) return;
    const name = splitName(form.name);
    let departmentPayload = form.department || null;
    if (isDepartmentHead) {
      if (form.role === 'intern') departmentPayload = null;
      else if (form.role === 'employee' || form.role === 'projectmanager') departmentPayload = ownDepartmentId || null;
    }
    const supportsSubdivision = form.role === 'intern' || form.role === 'employee';
    const payload = {
      username: form.email,
      email: form.email,
      first_name: name.first_name,
      last_name: name.last_name,
      department: departmentPayload,
      position: null,
      subdivision: supportsSubdivision ? (form.subdivision || null) : null,
      manager: form.role === 'projectmanager' ? null : (form.manager || null),
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
        reason: 'Заявка на перевод стажера в сотрудники.',
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

  const managerOptions = useMemo(() => {
    const effectiveDepartment = isDepartmentHead
      ? ((form.role === 'employee' || form.role === 'projectmanager') ? ownDepartmentId : '')
      : form.department;
    return users.filter((u) => {
      if (u.role !== 'projectmanager') return false;
      if (!effectiveDepartment) return true;
      return Number(u.departmentId) === Number(effectiveDepartment);
    });
  }, [users, form.department, form.role, isDepartmentHead, ownDepartmentId]);

  const subdivisionOptions = useMemo(() => {
    const effectiveDepartment = isDepartmentHead
      ? ((form.role === 'employee' || form.role === 'projectmanager') ? ownDepartmentId : (form.department || ownDepartmentId))
      : form.department;
    if (!effectiveDepartment) return subdivisions;
    return subdivisions.filter((s) => Number(s.department_id) === Number(effectiveDepartment));
  }, [subdivisions, form.department, form.role, isDepartmentHead, ownDepartmentId]);

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
                  <select
                    className="form-select"
                    value={
                      isDepartmentHead
                        ? ((form.role === 'employee' || form.role === 'projectmanager') ? ownDepartmentId : '')
                        : form.department
                    }
                    onChange={(e) => setForm((prev) => ({ ...prev, department: e.target.value }))}
                    disabled={isDepartmentHead}
                  >
                    <option value="">-</option>
                    {departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">Подотдел</label>
                  {form.role === 'intern' || form.role === 'employee' ? (
                    <select
                      className="form-select"
                      value={form.subdivision}
                      onChange={(e) => setForm((prev) => ({ ...prev, subdivision: e.target.value }))}
                    >
                      <option value="">-</option>
                      {subdivisionOptions.map((s) => (
                        <option key={s.id} value={s.id}>{s.name}</option>
                      ))}
                    </select>
                  ) : (
                    <input className="form-input" value={fixedSubdivisionLabelByRole(form.role) || '-'} disabled />
                  )}
                </div>
              </div>
              <div className="grid-2" style={{ marginTop: 10 }}>
                <div className="form-group">
                  <label className="form-label">Роль</label>
                  <select
                    className="form-select"
                    value={form.role}
                    onChange={(e) => {
                      const nextRole = e.target.value;
                      setForm((prev) => ({
                        ...prev,
                        role: nextRole,
                        manager: nextRole === 'projectmanager' ? '' : prev.manager,
                        subdivision: (nextRole === 'intern' || nextRole === 'employee') ? prev.subdivision : '',
                      }));
                    }}
                  >
                    <option value="intern">Стажер</option>
                    <option value="employee">Сотрудник</option>
                    <option value="projectmanager">Тимлид</option>
                    {canAssignAdminRoles ? <option value="department_head">Руководитель отдела</option> : null}
                    {canAssignAdminRoles ? <option value="admin">Админ</option> : null}
                    {isSuperAdmin ? <option value="superadmin">Суперадмин</option> : null}
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">Пароль {editUser ? '(опционально)' : ''}</label>
                  <input className="form-input" type="password" value={form.password} onChange={(e) => setForm((prev) => ({ ...prev, password: e.target.value }))} />
                </div>
              </div>
              <div className="grid-2" style={{ marginTop: 10 }}>
                <div className="form-group">
                  <label className="form-label">Руководитель (Тимлид)</label>
                  <select
                    className="form-select"
                    value={form.manager}
                    onChange={(e) => setForm((prev) => ({ ...prev, manager: e.target.value }))}
                    disabled={form.role === 'projectmanager'}
                  >
                    <option value="">-</option>
                    {managerOptions.map((m) => (
                      <option key={m.id} value={m.id}>{m.name}</option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">Текущий руководитель</label>
                  <input
                    className="form-input"
                    value={editUser?.managerName || '-'}
                    disabled
                  />
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

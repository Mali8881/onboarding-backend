import { useRef, useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import MainLayout from '../../layouts/MainLayout';
import { Plus, Trash2, Camera, Save, Check } from 'lucide-react';

const ROLE_META = {
  intern: { label: 'Стажер', color: '#2563EB', bg: 'linear-gradient(135deg,#DBEAFE,#EDE9FE)' },
  employee: { label: 'Сотрудник', color: '#16A34A', bg: 'linear-gradient(135deg,#D1FAE5,#DBEAFE)' },
  projectmanager: { label: 'Проект-менеджер', color: '#7C3AED', bg: 'linear-gradient(135deg,#EDE9FE,#FEE2E2)' },
  department_head: { label: 'Руководитель отдела', color: '#0EA5E9', bg: 'linear-gradient(135deg,#DBEAFE,#CFFAFE)' },
  admin: { label: 'Админ', color: '#EA580C', bg: 'linear-gradient(135deg,#FED7AA,#FEF9C3)' },
  superadmin: { label: 'Суперадминистратор', color: '#BE123C', bg: 'linear-gradient(135deg,#FECDD3,#FED7AA)' },
};

const DEPARTMENTS = ['Разработка', 'Отдел маркетинга', 'Отдел холодных продаж', 'HR', 'Управление', 'Логистика', 'ОКК'];
const POSITIONS = ['Frontend-разработчик', 'Backend-разработчик', 'Стажер', 'SMM-специалист', 'Проект-менеджер', 'Менеджер продаж', 'HR-менеджер', 'Руководитель отдела', 'Суперадминистратор'];

function OrgSection() {
  const [departments, setDepts] = useState(DEPARTMENTS.map((n, i) => ({ id: i + 1, name: n })));
  const [positions, setPos] = useState(POSITIONS.map((n, i) => ({ id: i + 1, name: n, dept: DEPARTMENTS[i % DEPARTMENTS.length] })));
  const [tab, setTab] = useState('depts');
  const [newDept, setND] = useState('');
  const [newPos, setNP] = useState('');
  const [newPD, setNPD] = useState(DEPARTMENTS[0]);
  const [saved, setSaved] = useState(false);

  const addDept = () => {
    if (!newDept.trim()) return;
    setDepts((d) => [...d, { id: Date.now(), name: newDept.trim() }]);
    setND('');
  };

  const addPos = () => {
    if (!newPos.trim()) return;
    setPos((p) => [...p, { id: Date.now(), name: newPos.trim(), dept: newPD }]);
    setNP('');
  };

  const save = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="card" style={{ marginTop: 20 }}>
      <div className="card-header" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span className="card-title">Структура компании</span>
        <button className="btn btn-primary btn-sm" onClick={save} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          {saved ? <><Check size={14} /> Сохранено</> : <><Save size={14} /> Сохранить</>}
        </button>
      </div>
      <div className="card-body">
        <div className="tabs" style={{ marginBottom: 16 }}>
          <button className={`tab-btn ${tab === 'depts' ? 'active' : ''}`} onClick={() => setTab('depts')}>Отделы ({departments.length})</button>
          <button className={`tab-btn ${tab === 'pos' ? 'active' : ''}`} onClick={() => setTab('pos')}>Должности ({positions.length})</button>
        </div>

        {tab === 'depts' && (
          <>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2,1fr)', gap: 8, marginBottom: 16 }}>
              {departments.map((d) => (
                <div key={d.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 12px', background: 'var(--gray-50)', borderRadius: 'var(--radius)', border: '1px solid var(--gray-200)' }}>
                  <span style={{ fontSize: 13, fontWeight: 500 }}>{d.name}</span>
                  <button onClick={() => setDepts((ds) => ds.filter((x) => x.id !== d.id))} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--danger)', padding: 2 }}><Trash2 size={13} /></button>
                </div>
              ))}
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <input className="form-input" placeholder="Название нового отдела" value={newDept} onChange={(e) => setND(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && addDept()} style={{ flex: 1 }} />
              <button className="btn btn-primary btn-sm" onClick={addDept}><Plus size={14} /> Добавить</button>
            </div>
          </>
        )}

        {tab === 'pos' && (
          <>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2,1fr)', gap: 8, marginBottom: 16 }}>
              {positions.map((p) => (
                <div key={p.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 12px', background: 'var(--gray-50)', borderRadius: 'var(--radius)', border: '1px solid var(--gray-200)' }}>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 500 }}>{p.name}</div>
                    <div style={{ fontSize: 11, color: 'var(--gray-400)' }}>{p.dept}</div>
                  </div>
                  <button onClick={() => setPos((ps) => ps.filter((x) => x.id !== p.id))} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--danger)', padding: 2 }}><Trash2 size={13} /></button>
                </div>
              ))}
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <input className="form-input" placeholder="Название должности" value={newPos} onChange={(e) => setNP(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && addPos()} style={{ flex: 1 }} />
              <select className="form-select" value={newPD} onChange={(e) => setNPD(e.target.value)} style={{ width: 180 }}>
                {departments.map((d) => <option key={d.id}>{d.name}</option>)}
              </select>
              <button className="btn btn-primary btn-sm" onClick={addPos}><Plus size={14} /> Добавить</button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

const STATIC_DEPARTMENT = 'IT Department';

const makeInitialForm = (u) => ({
  name: u?.name || '',
  email: u?.email || '',
  telegram: u?.telegram || '',
  phone: u?.phone || '',
});

export default function Profile() {
  const { user, updateUser } = useAuth();
  const meta = ROLE_META[user?.role] || ROLE_META.intern;
  const positionLabel = user?.roleLabel || meta.label || user?.position_name || user?.position || '—';
  const fileRef = useRef();

  const [form, setForm] = useState(() => makeInitialForm(user));
  const [avatar, setAvatar] = useState(user?.photo || null);
  const [saved, setSaved] = useState(false);
  const [errors, setErrors] = useState({});
  const [isEditing, setIsEditing] = useState(false);

  const validate = () => {
    const e = {};
    if (!form.name.trim()) e.name = 'Обязательное поле';
    if (!form.email.trim()) e.email = 'Обязательное поле';
    if (form.email.trim() && !/^\S+@\S+\.\S+$/.test(form.email.trim())) e.email = 'Введите корректный email';
    return e;
  };

  const handleSave = (e) => {
    e.preventDefault();
    const e2 = validate();
    if (Object.keys(e2).length) {
      setErrors(e2);
      return;
    }
    setErrors({});
    updateUser?.({
      name: form.name,
      email: form.email,
      telegram: form.telegram,
      phone: form.phone,
      ...(avatar ? { photo: avatar } : {}),
    });
    setIsEditing(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  };

  const handleAvatar = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => setAvatar(ev.target.result);
    reader.readAsDataURL(file);
  };

  const initials = form.name.split(' ').map((p) => p[0]).join('').slice(0, 2).toUpperCase() || '??';

  return (
    <MainLayout title="Личный кабинет">
      <div style={{ maxWidth: 760 }}>
        <div className="page-header">
          <div>
            <div className="page-title">Личный кабинет</div>
            <div className="page-subtitle">Управляйте своими данными и настройками</div>
          </div>
        </div>

        <div className="card">
          <div style={{ height: 100, background: meta.bg, borderRadius: '12px 12px 0 0', position: 'relative' }}>
            <div style={{ position: 'absolute', top: 12, right: 16, background: meta.color, color: 'white', fontSize: 12, fontWeight: 600, padding: '4px 12px', borderRadius: 20 }}>
              {meta.label}
            </div>
          </div>

          <div className="card-body" style={{ paddingTop: 0 }}>
            <div style={{ display: 'flex', alignItems: 'flex-end', gap: 16, marginTop: -36, marginBottom: 24 }}>
              <div style={{ position: 'relative', flexShrink: 0 }}>
                <div className="avatar" style={{ width: 72, height: 72, fontSize: 24, border: '3px solid white', boxShadow: 'var(--shadow)', background: avatar ? 'transparent' : meta.color, overflow: 'hidden' }}>
                  {avatar ? <img src={avatar} alt="avatar" style={{ width: '100%', height: '100%', objectFit: 'cover' }} /> : initials}
                </div>
                {isEditing && (
                  <>
                    <button
                      type="button"
                      onClick={() => fileRef.current?.click()}
                      style={{ position: 'absolute', bottom: 0, right: 0, width: 24, height: 24, borderRadius: '50%', background: meta.color, border: '2px solid white', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                    >
                      <Camera size={11} color="white" />
                    </button>
                    <input ref={fileRef} type="file" accept="image/*" style={{ display: 'none' }} onChange={handleAvatar} />
                  </>
                )}
              </div>
              <div style={{ marginBottom: 4 }}>
                <div style={{ fontWeight: 700, fontSize: 16 }}>{form.name || '—'}</div>
                <div style={{ fontSize: 13, color: 'var(--gray-500)' }}>{positionLabel} · {STATIC_DEPARTMENT}</div>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12, marginBottom: 24, background: 'var(--gray-50)', borderRadius: 'var(--radius)', padding: '14px 16px' }}>
              {[
                { label: 'Логин', value: user?.login || user?.username || '—' },
                { label: 'Email', value: form.email || '—' },
                { label: 'Дата найма', value: user?.hireDate || user?.hire_date || '—' },
              ].map((item) => (
                <div key={item.label}>
                  <div style={{ fontSize: 11, color: 'var(--gray-400)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 4 }}>{item.label}</div>
                  <div style={{ fontSize: 13, fontWeight: 500 }}>{item.value}</div>
                </div>
              ))}
            </div>

            <form onSubmit={handleSave}>
              <div style={{ fontSize: 15, fontWeight: 700, marginBottom: 16 }}>Персональные данные</div>

              <div className="form-group" style={{ marginBottom: 16 }}>
                <label className="form-label">ФИО <span style={{ color: 'var(--danger)' }}>*</span></label>
                <input
                  className={`form-input ${errors.name ? 'input-error' : ''}`}
                  value={form.name}
                  onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                  placeholder="Фамилия Имя Отчество"
                  disabled={!isEditing}
                />
                {errors.name && <div style={{ fontSize: 12, color: 'var(--danger)', marginTop: 4 }}>{errors.name}</div>}
              </div>

              <div className="grid-2" style={{ marginBottom: 16 }}>
                <div className="form-group">
                  <label className="form-label">Отдел</label>
                  <input className="form-input" value={STATIC_DEPARTMENT} disabled />
                </div>
                <div className="form-group">
                  <label className="form-label">Должность</label>
                  <input className="form-input" value={positionLabel} disabled />
                </div>
              </div>

              <div className="form-group" style={{ marginBottom: 16 }}>
                <label className="form-label">Email <span style={{ color: 'var(--danger)' }}>*</span></label>
                <input
                  className={`form-input ${errors.email ? 'input-error' : ''}`}
                  value={form.email}
                  onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                  placeholder="email@example.com"
                  disabled={!isEditing}
                />
                {errors.email && <div style={{ fontSize: 12, color: 'var(--danger)', marginTop: 4 }}>{errors.email}</div>}
              </div>

              <div className="grid-2" style={{ marginBottom: 24 }}>
                <div className="form-group">
                  <label className="form-label">Telegram</label>
                  <input className="form-input" value={form.telegram} onChange={(e) => setForm((f) => ({ ...f, telegram: e.target.value }))} placeholder="@username" disabled={!isEditing} />
                </div>
                <div className="form-group">
                  <label className="form-label">Телефон</label>
                  <input className="form-input" value={form.phone} onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))} placeholder="+996 ..." disabled={!isEditing} />
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
                {isEditing ? (
                  <>
                    <button
                      type="button"
                      className="btn btn-secondary"
                      onClick={() => {
                        setForm(makeInitialForm(user));
                        setAvatar(user?.photo || null);
                        setErrors({});
                        setIsEditing(false);
                      }}
                    >
                      Сбросить
                    </button>
                    <button type="submit" className="btn btn-primary" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      {saved ? <><Check size={15} /> Сохранено!</> : <><Save size={15} /> Сохранить изменения</>}
                    </button>
                  </>
                ) : (
                  <button
                    type="button"
                    className="btn btn-primary"
                    onClick={() => setIsEditing(true)}
                  >
                    Редактировать
                  </button>
                )}
              </div>
            </form>
          </div>
        </div>

        {user?.role === 'intern' && (
          <div className="card" style={{ marginTop: 20 }}>
            <div className="card-header">
              <span className="card-title">Перевод в сотрудники</span>
            </div>
            <div className="card-body">
              <div style={{ fontSize: 13, color: 'var(--gray-600)' }}>
                Процесс перевода ведет администратор: после завершения стажировки он отправляет запрос суперадминистратору на подтверждение роли сотрудника.
              </div>
            </div>
          </div>
        )}

        {user?.role === 'superadmin' && <OrgSection />}
      </div>
    </MainLayout>
  );
}


import { useState } from 'react';
import MainLayout from '../../layouts/MainLayout';
import { Shield, Lock, Database, Activity, RefreshCw, AlertTriangle } from 'lucide-react';
import {
  addOfficeNetwork,
  getCurrentNetworkHint,
  getOfficeNetworks,
  isValidCIDR,
  removeOfficeNetwork,
  setCurrentNetworkHint,
  toggleOfficeNetwork,
} from '../../utils/officeNetwork';

export default function AdminSystem() {
  const [settings, setSettings] = useState({
    sessionTimeout: '60',
    maxLoginAttempts: '5',
    passwordMinLength: '8',
    requireUppercase: true,
    requireNumbers: true,
    twoFactor: false,
  });
  const [saved, setSaved] = useState(false);
  const [networks, setNetworks] = useState(getOfficeNetworks);
  const [netForm, setNetForm] = useState({ name: '', cidr: '', active: true });
  const [networkError, setNetworkError] = useState('');
  const [networkHint, setNetworkHintState] = useState(getCurrentNetworkHint());

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const toggle = (key) => setSettings(s => ({ ...s, [key]: !s[key] }));
  const setNetworkHint = (value) => {
    setNetworkHintState(value);
    setCurrentNetworkHint(value);
  };

  const handleAddNetwork = () => {
    const name = netForm.name.trim();
    const cidr = netForm.cidr.trim();
    if (!name || !cidr) {
      setNetworkError('Заполните название и CIDR.');
      return;
    }
    if (!isValidCIDR(cidr)) {
      setNetworkError('Неверный CIDR. Пример: 203.0.113.0/24');
      return;
    }
    setNetworks(addOfficeNetwork({ name, cidr, active: netForm.active }));
    setNetForm({ name: '', cidr: '', active: true });
    setNetworkError('');
  };

  const handleToggleNetwork = (id) => {
    setNetworks(toggleOfficeNetwork(id));
  };

  const handleRemoveNetwork = (id) => {
    setNetworks(removeOfficeNetwork(id));
  };

  const activeCount = networks.filter((n) => n.active).length;

  const AUDIT_LOG = [
    { id: 1, action: 'Создан пользователь', actor: 'Мария К.', target: 'Иванов Иван', date: '20 фев. 2026, 14:32' },
    { id: 2, action: 'Изменена роль', actor: 'Мария К.', target: 'Алексей П. → Администратор', date: '19 фев. 2026, 11:05' },
    { id: 3, action: 'Деактивирован пользователь', actor: 'Иван С.', target: 'Дмитрий К.', date: '18 фев. 2026, 09:20' },
    { id: 4, action: 'Добавлен регламент', actor: 'Елена М.', target: 'Кодекс корпоративной этики', date: '17 фев. 2026, 16:45' },
    { id: 5, action: 'Изменены настройки безопасности', actor: 'Мария К.', target: 'Система', date: '15 фев. 2026, 10:00' },
  ];

  return (
    <MainLayout title="Админ-панель · Система и безопасность">
      <div className="page-header">
        <div>
          <div className="page-title">Система и безопасность</div>
          <div className="page-subtitle">Настройки безопасности и системные параметры платформы</div>
        </div>
      </div>

      <div className="grid-2" style={{ gap: 20, marginBottom: 20 }}>
        {/* Security settings */}
        <div className="card">
          <div className="card-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}><Shield size={16} color="var(--primary)" /><span className="card-title">Настройки безопасности</span></div>
          </div>
          <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div className="form-group">
              <label className="form-label">Таймаут сессии (минуты)</label>
              <input className="form-input" type="number" value={settings.sessionTimeout}
                onChange={e => setSettings(s => ({ ...s, sessionTimeout: e.target.value }))} />
            </div>
            <div className="form-group">
              <label className="form-label">Макс. попыток входа</label>
              <input className="form-input" type="number" value={settings.maxLoginAttempts}
                onChange={e => setSettings(s => ({ ...s, maxLoginAttempts: e.target.value }))} />
            </div>
            <div className="form-group">
              <label className="form-label">Минимальная длина пароля</label>
              <input className="form-input" type="number" value={settings.passwordMinLength}
                onChange={e => setSettings(s => ({ ...s, passwordMinLength: e.target.value }))} />
            </div>

            {[
              { key: 'requireUppercase', label: 'Требовать заглавные буквы' },
              { key: 'requireNumbers', label: 'Требовать цифры в пароле' },
              { key: 'twoFactor', label: 'Двухфакторная аутентификация' },
            ].map(({ key, label }) => (
              <div key={key} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 13 }}>{label}</span>
                <div
                  style={{
                    width: 44, height: 24, borderRadius: 12, cursor: 'pointer', transition: 'background 0.2s',
                    background: settings[key] ? 'var(--primary)' : 'var(--gray-300)', position: 'relative'
                  }}
                  onClick={() => toggle(key)}
                >
                  <div style={{
                    position: 'absolute', top: 2, left: settings[key] ? 22 : 2,
                    width: 20, height: 20, background: 'white', borderRadius: '50%', transition: 'left 0.2s'
                  }} />
                </div>
              </div>
            ))}

            <button className="btn btn-primary" onClick={handleSave} style={{ marginTop: 4 }}>
              {saved ? '✓ Сохранено' : 'Сохранить настройки'}
            </button>
          </div>
        </div>

        {/* System info */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div className="card">
            <div className="card-body">
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
                <Database size={18} color="var(--primary)" />
                <span style={{ fontWeight: 700 }}>Состояние системы</span>
              </div>
              {[
                { label: 'Статус', value: '● Работает', color: 'var(--success)' },
                { label: 'Версия', value: 'v1.0.0' },
                { label: 'Последнее обновление', value: '20 фев. 2026' },
                { label: 'Активных сессий', value: '12' },
              ].map(({ label, value, color }) => (
                <div key={label} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid var(--gray-100)', fontSize: 13 }}>
                  <span style={{ color: 'var(--gray-500)' }}>{label}</span>
                  <span style={{ fontWeight: 500, color: color || 'var(--gray-800)' }}>{value}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="card">
            <div className="card-body">
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
                <AlertTriangle size={18} color="var(--warning)" />
                <span style={{ fontWeight: 700 }}>Опасная зона</span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                <button className="btn btn-secondary" style={{ justifyContent: 'flex-start', gap: 8 }}>
                  <RefreshCw size={14} /> Сбросить кэш системы
                </button>
                <button className="btn" style={{ background: 'var(--danger-light)', color: 'var(--danger)', border: 'none', justifyContent: 'flex-start', gap: 8 }}>
                  <Lock size={14} /> Принудительный выход всех пользователей
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <span className="card-title">Офисные сети (Whitelist)</span>
        </div>
        <div className="card-body" style={{ display: 'grid', gap: 14 }}>
          <div style={{ fontSize: 13, color: 'var(--gray-500)' }}>
            Только пользователи из активных офисных сетей смогут выполнить отметку прихода/ухода в режиме "Офис".
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr auto auto', gap: 10, alignItems: 'end' }}>
            <div className="form-group">
              <label className="form-label">Название</label>
              <input
                className="form-input"
                placeholder="Главный офис"
                value={netForm.name}
                onChange={(e) => setNetForm((f) => ({ ...f, name: e.target.value }))}
              />
            </div>
            <div className="form-group">
              <label className="form-label">CIDR</label>
              <input
                className="form-input"
                placeholder="203.0.113.0/24"
                value={netForm.cidr}
                onChange={(e) => setNetForm((f) => ({ ...f, cidr: e.target.value }))}
              />
            </div>
            <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, marginBottom: 10 }}>
              <input
                type="checkbox"
                checked={netForm.active}
                onChange={(e) => setNetForm((f) => ({ ...f, active: e.target.checked }))}
              />
              Активна
            </label>
            <button type="button" className="btn btn-primary btn-sm" style={{ marginBottom: 8 }} onClick={handleAddNetwork}>
              Добавить
            </button>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 6 }}>
            <label className="form-label">Текущий IP для проверки (демо)</label>
            <input
              className="form-input"
              placeholder="192.168.1.10"
              value={networkHint}
              onChange={(e) => setNetworkHint(e.target.value)}
            />
          </div>

          {networkError && (
            <div style={{ fontSize: 12, color: 'var(--danger)' }}>{networkError}</div>
          )}

          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Название</th>
                  <th>CIDR</th>
                  <th>Статус</th>
                  <th>Действия</th>
                </tr>
              </thead>
              <tbody>
                {networks.map((n) => (
                  <tr key={n.id}>
                    <td>{n.name}</td>
                    <td>{n.cidr}</td>
                    <td>{n.active ? 'Активна' : 'Отключена'}</td>
                    <td>
                      <button type="button" className="btn btn-secondary btn-sm" onClick={() => handleToggleNetwork(n.id)}>
                        {n.active ? 'Выключить' : 'Включить'}
                      </button>
                      <button
                        type="button"
                        className="btn btn-sm"
                        style={{ marginLeft: 8, background: 'var(--danger-light)', color: 'var(--danger)', border: 'none' }}
                        onClick={() => handleRemoveNetwork(n.id)}
                      >
                        Удалить
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div style={{ fontSize: 12, color: 'var(--gray-500)' }}>
            Активных сетей: {activeCount}
          </div>
        </div>
      </div>

      {/* Audit log */}
      <div className="card">
        <div className="card-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}><Activity size={16} color="var(--primary)" /><span className="card-title">Журнал действий</span></div>
        </div>
        <div className="card-body" style={{ padding: 0 }}>
          <table className="table">
            <thead>
              <tr><th>Действие</th><th>Инициатор</th><th>Объект</th><th>Дата и время</th></tr>
            </thead>
            <tbody>
              {AUDIT_LOG.map(log => (
                <tr key={log.id}>
                  <td style={{ fontWeight: 500, fontSize: 13 }}>{log.action}</td>
                  <td style={{ fontSize: 13 }}>{log.actor}</td>
                  <td style={{ fontSize: 13, color: 'var(--gray-500)' }}>{log.target}</td>
                  <td style={{ fontSize: 12, color: 'var(--gray-400)' }}>{log.date}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </MainLayout>
  );
}

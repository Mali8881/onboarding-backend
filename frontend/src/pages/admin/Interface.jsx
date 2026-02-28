import { useEffect, useState } from 'react';
import MainLayout from '../../layouts/MainLayout';
import { Monitor, Type, Globe, Save } from 'lucide-react';
import { useLocale } from '../../context/LocaleContext';

const INTERFACE_SETTINGS_KEY = 'vpluse_interface_settings_v1';

const defaultSettings = {
  companyName: 'В Плюсе',
  companyTagline: 'Внутренняя корпоративная платформа',
  primaryColor: '#2563EB',
  defaultLang: 'ru',
  showWelcomeBanner: true,
  showTeamSection: true,
  showFeedbackForm: true,
  footerAddress: 'г. Бишкек, ул. Исанова 1',
  footerHours: 'Пн-Пт: 09:00 – 21:00',
  footerPhone: '+996 (555) 00-00-00',
};

function readSettings() {
  try {
    const raw = localStorage.getItem(INTERFACE_SETTINGS_KEY);
    if (!raw) return defaultSettings;
    return { ...defaultSettings, ...JSON.parse(raw) };
  } catch {
    return defaultSettings;
  }
}

export default function AdminInterface() {
  const { setLocale } = useLocale();
  const [settings, setSettings] = useState(readSettings);
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    localStorage.setItem(INTERFACE_SETTINGS_KEY, JSON.stringify(settings));
    setLocale(settings.defaultLang);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const toggle = (key) => setSettings(s => ({ ...s, [key]: !s[key] }));

  useEffect(() => {
    document.documentElement.style.setProperty('--primary', settings.primaryColor || '#2563EB');
  }, [settings.primaryColor]);

  return (
    <MainLayout title="Админ-панель · Интерфейс">
      <div className="page-header">
        <div>
          <div className="page-title">Настройки интерфейса</div>
          <div className="page-subtitle">Управление внешним видом и содержимым платформы</div>
        </div>
        <button className="btn btn-primary" onClick={handleSave}>
          <Save size={14} /> {saved ? '✓ Сохранено' : 'Сохранить'}
        </button>
      </div>

      <div className="grid-2" style={{ gap: 20 }}>
        {/* Branding */}
        <div className="card">
          <div className="card-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}><Type size={16} color="var(--primary)" /><span className="card-title">Брендинг</span></div>
          </div>
          <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div className="form-group">
              <label className="form-label">Название компании</label>
              <input className="form-input" value={settings.companyName} onChange={e => setSettings(s => ({ ...s, companyName: e.target.value }))} />
            </div>
            <div className="form-group">
              <label className="form-label">Подзаголовок</label>
              <input className="form-input" value={settings.companyTagline} onChange={e => setSettings(s => ({ ...s, companyTagline: e.target.value }))} />
            </div>
            <div className="form-group">
              <label className="form-label">Основной цвет</label>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <input type="color" value={settings.primaryColor} onChange={e => setSettings(s => ({ ...s, primaryColor: e.target.value }))}
                  style={{ width: 44, height: 36, border: '1px solid var(--gray-200)', borderRadius: 'var(--radius)', cursor: 'pointer', padding: 2 }} />
                <input className="form-input" value={settings.primaryColor} onChange={e => setSettings(s => ({ ...s, primaryColor: e.target.value }))} style={{ flex: 1 }} />
              </div>
            </div>
          </div>
        </div>

        {/* Localization */}
        <div className="card">
          <div className="card-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}><Globe size={16} color="var(--primary)" /><span className="card-title">Локализация</span></div>
          </div>
          <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div className="form-group">
              <label className="form-label">Язык по умолчанию</label>
              <select className="form-select" value={settings.defaultLang} onChange={e => setSettings(s => ({ ...s, defaultLang: e.target.value }))}>
                <option value="ru">Русский</option>
                <option value="en">English</option>
                <option value="kg">Кыргызча</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Адрес офиса</label>
              <input className="form-input" value={settings.footerAddress} onChange={e => setSettings(s => ({ ...s, footerAddress: e.target.value }))} />
            </div>
            <div className="form-group">
              <label className="form-label">Часы работы</label>
              <input className="form-input" value={settings.footerHours} onChange={e => setSettings(s => ({ ...s, footerHours: e.target.value }))} />
            </div>
            <div className="form-group">
              <label className="form-label">Телефон</label>
              <input className="form-input" value={settings.footerPhone} onChange={e => setSettings(s => ({ ...s, footerPhone: e.target.value }))} />
            </div>
          </div>
        </div>

        {/* Display options */}
        <div className="card">
          <div className="card-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}><Monitor size={16} color="var(--primary)" /><span className="card-title">Элементы интерфейса</span></div>
          </div>
          <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {[
              { key: 'showWelcomeBanner', label: 'Приветственный баннер на главной' },
              { key: 'showTeamSection', label: 'Блок "Наша команда"' },
              { key: 'showFeedbackForm', label: 'Форма обратной связи' },
            ].map(({ key, label }) => (
              <div key={key} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 13 }}>{label}</span>
                <div
                  style={{ width: 44, height: 24, borderRadius: 12, cursor: 'pointer', transition: 'background 0.2s', background: settings[key] ? 'var(--primary)' : 'var(--gray-300)', position: 'relative' }}
                  onClick={() => toggle(key)}
                >
                  <div style={{ position: 'absolute', top: 2, left: settings[key] ? 22 : 2, width: 20, height: 20, background: 'white', borderRadius: '50%', transition: 'left 0.2s' }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </MainLayout>
  );
}

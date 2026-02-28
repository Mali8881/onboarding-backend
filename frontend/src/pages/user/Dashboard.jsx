import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { X } from 'lucide-react';
import MainLayout from '../../layouts/MainLayout';
import { useAuth } from '../../context/AuthContext';
import { newsAPI, feedbackAPI } from '../../api/content';

const BANNERS = {
  intern: { title: 'Добро пожаловать в команду', action: 'Перейти к онбордингу', path: '/onboarding' },
  employee: { title: 'Рабочая панель сотрудника', action: 'Мой профиль', path: '/profile' },
  projectmanager: { title: 'Панель руководителя', action: 'Задачи команды', path: '/tasks' },
  admin: { title: 'Панель администратора', action: 'Открыть админку', path: '/admin/overview' },
  superadmin: { title: 'Панель суперадмина', action: 'Открыть админку', path: '/admin/overview' },
};

const FEEDBACK_TYPES = [
  { label: 'Предложение', value: 'suggestion' },
  { label: 'Жалоба', value: 'complaint' },
  { label: 'Отзыв', value: 'review' },
];

function toAbsoluteMedia(url) {
  if (!url) return '';
  if (url.startsWith('http://') || url.startsWith('https://')) return url;
  const apiBase = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
  const origin = apiBase.replace(/\/api\/?$/, '');
  return `${origin}${url.startsWith('/') ? '' : '/'}${url}`;
}

function stripHtml(input) {
  if (!input) return '';
  return String(input).replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
}

export default function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [news, setNews] = useState([]);
  const [newsLoading, setNewsLoading] = useState(true);
  const [selectedNews, setSelectedNews] = useState(null);
  const [fbType, setFbType] = useState('suggestion');
  const [fbText, setFbText] = useState('');
  const [fbMode, setFbMode] = useState('named');
  const [fbMsg, setFbMsg] = useState('');

  const banner = useMemo(() => BANNERS[user?.role] || BANNERS.employee, [user?.role]);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        setNewsLoading(true);
        const res = await newsAPI.list();
        if (!alive) return;
        const items = Array.isArray(res.data) ? res.data : [];
        setNews(
          items.map((n) => ({
            id: n.id,
            title: n.title,
            text: n.short_text || '',
            fullText: n.full_text || n.short_text || '',
            image: toAbsoluteMedia(n.image),
            date: n.published_at,
          }))
        );
      } catch {
        if (alive) setNews([]);
      } finally {
        if (alive) setNewsLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  const sendFeedback = async () => {
    const text = fbText.trim();
    if (!text) return;
    try {
      await feedbackAPI.create({
        type: fbType,
        text,
        full_name: fbMode === 'anonymous' ? '' : (user?.name || user?.username || ''),
        contact: fbMode === 'anonymous' ? '' : (user?.email || ''),
      });
      setFbText('');
      setFbType('suggestion');
      setFbMode('named');
      setFbMsg('Обращение отправлено.');
    } catch {
      setFbMsg('Не удалось отправить обращение.');
    }
    setTimeout(() => setFbMsg(''), 2500);
  };

  return (
    <MainLayout title="Главная">
      <div className="announcement-banner">
        <div>
          <div className="announcement-title">{banner.title}</div>
          <button className="btn" style={{ marginTop: 12 }} onClick={() => navigate(banner.path)}>
            {banner.action}
          </button>
        </div>
      </div>

      <div style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 17, fontWeight: 700, marginBottom: 16 }}>Актуальные новости</h2>
        {newsLoading && <div className="card"><div className="card-body">Загрузка...</div></div>}
        {!newsLoading && (
          <div className="news-grid">
            {news.map((n) => (
              <div key={n.id} className="news-card" onClick={() => setSelectedNews(n)}>
                {n.image ? <img src={n.image} alt={n.title} className="news-card-img" /> : null}
                <div className="news-card-body">
                  <div className="news-card-title">{n.title}</div>
                  <div className="news-card-text">{n.text}</div>
                </div>
              </div>
            ))}
            {news.length === 0 && <div className="card"><div className="card-body">Новостей пока нет.</div></div>}
          </div>
        )}
      </div>

      <div className="card" style={{ maxWidth: 720 }}>
        <div className="card-body">
          <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 8 }}>Обратная связь</h3>
          <div className="form-group" style={{ marginBottom: 10 }}>
            <label className="form-label">Тип</label>
            <select className="form-select" value={fbType} onChange={(e) => setFbType(e.target.value)}>
              {FEEDBACK_TYPES.map((item) => (
                <option key={item.value} value={item.value}>{item.label}</option>
              ))}
            </select>
          </div>
          <div className="form-group" style={{ marginBottom: 10 }}>
            <label className="form-label">Сообщение</label>
            <textarea
              className="form-textarea"
              value={fbText}
              onChange={(e) => setFbText(e.target.value)}
              placeholder="Опишите обращение"
              style={{ minHeight: 80 }}
            />
          </div>
          <div className="form-group" style={{ marginBottom: 12 }}>
            <label className="form-label">Формат</label>
            <select className="form-select" value={fbMode} onChange={(e) => setFbMode(e.target.value)}>
              <option value="named">Неанонимно</option>
              <option value="anonymous">Анонимно</option>
            </select>
          </div>
          <button className="btn btn-primary" onClick={sendFeedback}>Отправить</button>
          {fbMsg ? <div style={{ marginTop: 8, fontSize: 12 }}>{fbMsg}</div> : null}
        </div>
      </div>

      {selectedNews ? (
        <div className="modal-overlay" onClick={() => setSelectedNews(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 860, width: 'calc(100vw - 32px)' }}>
            <div className="modal-header">
              <div className="modal-title">{selectedNews.title}</div>
              <button className="btn-icon" onClick={() => setSelectedNews(null)}><X size={16} /></button>
            </div>
            <div className="modal-body">
              {selectedNews.image ? (
                <img src={selectedNews.image} alt={selectedNews.title} style={{ width: '100%', maxHeight: 280, objectFit: 'cover', borderRadius: 8, marginBottom: 12 }} />
              ) : null}
              <p style={{ margin: 0, lineHeight: 1.6 }}>{stripHtml(selectedNews.fullText || selectedNews.text)}</p>
            </div>
          </div>
        </div>
      ) : null}
    </MainLayout>
  );
}

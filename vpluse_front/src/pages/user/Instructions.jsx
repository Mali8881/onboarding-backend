import { useEffect, useState } from 'react';
import { BookOpen, ExternalLink, Download } from 'lucide-react';
import MainLayout from '../../layouts/MainLayout';
import { instructionsAPI } from '../../api/content';

function toAbsoluteMedia(url) {
  if (!url) return '';
  if (url.startsWith('http://') || url.startsWith('https://')) return url;
  const apiBase = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
  const origin = apiBase.replace(/\/api\/?$/, '');
  return `${origin}${url.startsWith('/') ? '' : '/'}${url}`;
}

const TYPE_LABELS = {
  text: 'Текст',
  link: 'Ссылка',
  file: 'Файл',
};

export default function Instructions() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        setLoading(true);
        const res = await instructionsAPI.list();
        if (!alive) return;
        const list = Array.isArray(res.data) ? res.data : [];
        setItems(
          list.map((i) => ({
            id: i.id,
            language: i.language,
            type: i.type,
            content: i.type === 'text' ? i.content : toAbsoluteMedia(i.content),
            updatedAt: i.updated_at,
          }))
        );
      } catch {
        if (alive) setItems([]);
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  return (
    <MainLayout title="Инструкция по платформе">
      <div style={{ maxWidth: 900 }}>
        <div className="page-header">
          <div>
            <div className="page-title">Инструкция по платформе</div>
            <div className="page-subtitle">Данные загружаются из backend</div>
          </div>
        </div>

        {loading ? (
          <div className="card"><div className="card-body">Загрузка...</div></div>
        ) : (
          <div className="card">
            <div className="card-body">
              <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                {items.map((item) => (
                  <div key={item.id} style={{ display: 'flex', gap: 14 }}>
                    <div style={{ width: 36, height: 36, borderRadius: 'var(--radius)', background: 'var(--primary-light)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                      <BookOpen size={16} color="var(--primary)" />
                    </div>
                    <div style={{ width: '100%' }}>
                      <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 4 }}>
                        {TYPE_LABELS[item.type] || item.type} ({item.language || 'ru'})
                      </div>
                      {item.type === 'text' ? (
                        <div style={{ fontSize: 13, color: 'var(--gray-600)', lineHeight: 1.6 }}>{item.content}</div>
                      ) : (
                        <div style={{ display: 'flex', gap: 8 }}>
                          <a className="btn btn-outline btn-sm" href={item.content} target="_blank" rel="noreferrer">
                            <ExternalLink size={13} /> Открыть
                          </a>
                          {item.type === 'file' ? (
                            <a className="btn btn-primary btn-sm" href={item.content} target="_blank" rel="noreferrer" download>
                              <Download size={13} /> Скачать
                            </a>
                          ) : null}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
                {items.length === 0 ? <div style={{ color: 'var(--gray-500)' }}>Инструкции пока не найдены.</div> : null}
              </div>
            </div>
          </div>
        )}
      </div>
    </MainLayout>
  );
}

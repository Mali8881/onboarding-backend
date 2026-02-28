import { useEffect, useMemo, useState } from 'react';
import { Download, ExternalLink } from 'lucide-react';
import MainLayout from '../../layouts/MainLayout';
import { regulationsAPI } from '../../api/content';

function toAbsoluteMedia(url) {
  if (!url) return '';
  if (url.startsWith('http://') || url.startsWith('https://')) return url;
  const apiBase = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
  const origin = apiBase.replace(/\/api\/?$/, '');
  return `${origin}${url.startsWith('/') ? '' : '/'}${url}`;
}

function detectExt(url) {
  if (!url) return '';
  const clean = url.split('?')[0];
  const i = clean.lastIndexOf('.');
  if (i === -1) return '';
  return clean.slice(i + 1).toLowerCase();
}

export default function Regulations() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        setLoading(true);
        const res = await regulationsAPI.list();
        if (!alive) return;
        const list = Array.isArray(res.data) ? res.data : [];
        setItems(
          list.map((r) => {
            const content = toAbsoluteMedia(r.content);
            const ext = detectExt(content);
            return {
              id: r.id,
              title: r.title,
              description: r.description || '',
              action: r.action || (r.type === 'link' ? 'open' : 'download'),
              content,
              ext: ext || (r.type === 'link' ? 'link' : 'file'),
            };
          })
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

  const sorted = useMemo(() => items.slice(), [items]);

  return (
    <MainLayout title="Регламенты компании">
      <div className="page-header">
        <div>
          <div className="page-title">Внутренние регламенты и инструкции</div>
          <div className="page-subtitle">Список документов из backend</div>
        </div>
      </div>

      {loading ? (
        <div className="card"><div className="card-body">Загрузка...</div></div>
      ) : (
        <div className="reg-grid">
          {sorted.map((reg) => (
            <div key={reg.id} className="reg-card">
              <div className="reg-title">{reg.title}</div>
              <div className="reg-desc">{reg.description || 'Без описания'}</div>
              <div className="reg-action" style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {reg.action === 'open' ? (
                  <a className="btn btn-outline btn-sm" href={reg.content || '#'} target="_blank" rel="noreferrer">
                    <ExternalLink size={13} /> Открыть
                  </a>
                ) : (
                  <>
                    <a className="btn btn-outline btn-sm" href={reg.content || '#'} target="_blank" rel="noreferrer">
                      <ExternalLink size={13} /> Просмотреть
                    </a>
                    <a className="btn btn-primary btn-sm" href={reg.content || '#'} target="_blank" rel="noreferrer" download>
                      <Download size={13} /> Скачать {reg.ext ? reg.ext.toUpperCase() : ''}
                    </a>
                  </>
                )}
              </div>
            </div>
          ))}
          {sorted.length === 0 ? (
            <div className="card"><div className="card-body">Регламентов пока нет.</div></div>
          ) : null}
        </div>
      )}
    </MainLayout>
  );
}

import { useEffect, useMemo, useState } from 'react';
import { Pencil, Plus, Trash2 } from 'lucide-react';
import MainLayout from '../../layouts/MainLayout';
import { instructionsAPI, newsAPI, regulationsAPI } from '../../api/content';

const emptyNews = { title: '', full_text: '', language: 'ru' };
const emptyReg = { title: '', description: '', type: 'link', url: '' };

export default function AdminContent() {
  const [tab, setTab] = useState('news');
  const [news, setNews] = useState([]);
  const [regs, setRegs] = useState([]);
  const [instructions, setInstructions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [newsForm, setNewsForm] = useState(emptyNews);
  const [newsEditId, setNewsEditId] = useState(null);

  const [regForm, setRegForm] = useState(emptyReg);
  const [regEditId, setRegEditId] = useState(null);

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const [newsRes, regRes, instructionsRes] = await Promise.all([
        newsAPI.list(),
        regulationsAPI.list(),
        instructionsAPI.list(),
      ]);
      setNews(Array.isArray(newsRes.data) ? newsRes.data : []);
      setRegs(Array.isArray(regRes.data) ? regRes.data : []);
      setInstructions(Array.isArray(instructionsRes.data) ? instructionsRes.data : []);
    } catch (e) {
      setError(e.response?.data?.detail || 'Не удалось загрузить контент.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const stats = useMemo(() => ({
    news: news.length,
    regs: regs.length,
    instructions: instructions.length,
  }), [news, regs, instructions]);

  const saveNews = async () => {
    if (!newsForm.title.trim()) return;
    const payload = {
      ...newsForm,
      published_at: new Date().toISOString(),
      is_active: true,
    };
    try {
      if (newsEditId) await newsAPI.update(newsEditId, payload);
      else await newsAPI.create(payload);
      setNewsForm(emptyNews);
      setNewsEditId(null);
      await load();
    } catch (e) {
      setError(e.response?.data?.detail || 'Ошибка сохранения новости.');
    }
  };

  const saveReg = async () => {
    if (!regForm.title.trim()) return;
    const payload = {
      title: regForm.title,
      description: regForm.description,
      type: regForm.type,
      external_url: regForm.type === 'link' ? regForm.url : '',
      is_active: true,
    };
    try {
      if (regEditId) await regulationsAPI.update(regEditId, payload);
      else await regulationsAPI.create(payload);
      setRegForm(emptyReg);
      setRegEditId(null);
      await load();
    } catch (e) {
      setError(e.response?.data?.detail || 'Ошибка сохранения регламента.');
    }
  };

  return (
    <MainLayout title="Администрирование">
      <div className="page-header">
        <div>
          <div className="page-title">Управление контентом</div>
          <div className="page-subtitle">Новости, регламенты и инструкции</div>
        </div>
      </div>

      {error && <div className="card" style={{ marginBottom: 12 }}><div className="card-body" style={{ color: '#b91c1c' }}>{error}</div></div>}
      {loading && <div className="card"><div className="card-body">Загрузка...</div></div>}

      {!loading && (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 14 }}>
            <Stat title="Новости" value={stats.news} />
            <Stat title="Регламенты" value={stats.regs} />
            <Stat title="Инструкции" value={stats.instructions} />
          </div>

          <div className="tabs">
            <button className={`tab-btn ${tab === 'news' ? 'active' : ''}`} onClick={() => setTab('news')}>Новости</button>
            <button className={`tab-btn ${tab === 'regulations' ? 'active' : ''}`} onClick={() => setTab('regulations')}>Регламенты</button>
            <button className={`tab-btn ${tab === 'instructions' ? 'active' : ''}`} onClick={() => setTab('instructions')}>Инструкции</button>
          </div>

          {tab === 'news' && (
            <>
              <div className="card" style={{ marginBottom: 12 }}>
                <div className="card-body" style={{ display: 'grid', gap: 10 }}>
                  <input className="form-input" placeholder="Заголовок" value={newsForm.title} onChange={(e) => setNewsForm((f) => ({ ...f, title: e.target.value }))} />
                  <textarea className="form-textarea" placeholder="Текст новости" value={newsForm.full_text} onChange={(e) => setNewsForm((f) => ({ ...f, full_text: e.target.value }))} />
                  <div style={{ display: 'flex', gap: 8 }}>
                    <button className="btn btn-primary btn-sm" onClick={saveNews}><Plus size={13} /> {newsEditId ? 'Сохранить' : 'Добавить'}</button>
                    {newsEditId && <button className="btn btn-secondary btn-sm" onClick={() => { setNewsEditId(null); setNewsForm(emptyNews); }}>Отмена</button>}
                  </div>
                </div>
              </div>
              <DataTable
                rows={news}
                columns={[
                  { key: 'title', label: 'ЗАГОЛОВОК' },
                  { key: 'published_at', label: 'ДАТА' },
                ]}
                onEdit={(item) => {
                  setNewsEditId(item.id);
                  setNewsForm({ title: item.title || '', full_text: item.full_text || '', language: item.language || 'ru' });
                }}
                onDelete={async (item) => {
                  await newsAPI.delete(item.id);
                  await load();
                }}
              />
            </>
          )}

          {tab === 'regulations' && (
            <>
              <div className="card" style={{ marginBottom: 12 }}>
                <div className="card-body" style={{ display: 'grid', gap: 10 }}>
                  <input className="form-input" placeholder="Название" value={regForm.title} onChange={(e) => setRegForm((f) => ({ ...f, title: e.target.value }))} />
                  <textarea className="form-textarea" placeholder="Описание" value={regForm.description} onChange={(e) => setRegForm((f) => ({ ...f, description: e.target.value }))} />
                  <select className="form-select" value={regForm.type} onChange={(e) => setRegForm((f) => ({ ...f, type: e.target.value }))}>
                    <option value="link">Ссылка</option>
                    <option value="file">Файл</option>
                  </select>
                  {regForm.type === 'link' && (
                    <input className="form-input" placeholder="https://..." value={regForm.url} onChange={(e) => setRegForm((f) => ({ ...f, url: e.target.value }))} />
                  )}
                  <div style={{ display: 'flex', gap: 8 }}>
                    <button className="btn btn-primary btn-sm" onClick={saveReg}><Plus size={13} /> {regEditId ? 'Сохранить' : 'Добавить'}</button>
                    {regEditId && <button className="btn btn-secondary btn-sm" onClick={() => { setRegEditId(null); setRegForm(emptyReg); }}>Отмена</button>}
                  </div>
                </div>
              </div>
              <DataTable
                rows={regs}
                columns={[
                  { key: 'title', label: 'НАЗВАНИЕ' },
                  { key: 'type', label: 'ТИП' },
                  { key: 'created_at', label: 'СОЗДАНО' },
                ]}
                onEdit={(item) => {
                  setRegEditId(item.id);
                  setRegForm({
                    title: item.title || '',
                    description: item.description || '',
                    type: item.type || 'link',
                    url: item.external_url || '',
                  });
                }}
                onDelete={async (item) => {
                  await regulationsAPI.delete(item.id);
                  await load();
                }}
              />
            </>
          )}

          {tab === 'instructions' && (
            <DataTable
              rows={instructions}
              columns={[
                { key: 'title', label: 'ЗАГОЛОВОК' },
                { key: 'language', label: 'ЯЗЫК' },
                { key: 'updated_at', label: 'ОБНОВЛЕНО' },
              ]}
              hideActions
            />
          )}
        </>
      )}
    </MainLayout>
  );
}

function Stat({ title, value }) {
  return (
    <div className="card">
      <div className="card-body">
        <div style={{ fontSize: 12, color: 'var(--gray-500)' }}>{title}</div>
        <div style={{ fontSize: 24, fontWeight: 800 }}>{value}</div>
      </div>
    </div>
  );
}

function DataTable({ rows, columns, onEdit, onDelete, hideActions = false }) {
  return (
    <div className="card">
      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              {columns.map((c) => <th key={c.key}>{c.label}</th>)}
              {!hideActions && <th>ДЕЙСТВИЯ</th>}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id}>
                {columns.map((c) => (
                  <td key={`${row.id}-${c.key}`}>{String(row[c.key] ?? '').slice(0, 120) || '-'}</td>
                ))}
                {!hideActions && (
                  <td>
                    <div style={{ display: 'flex', gap: 4 }}>
                      <button className="btn-icon" onClick={() => onEdit?.(row)}><Pencil size={13} /></button>
                      <button className="btn-icon" style={{ color: 'var(--danger)' }} onClick={() => onDelete?.(row)}><Trash2 size={13} /></button>
                    </div>
                  </td>
                )}
              </tr>
            ))}
            {rows.length === 0 && (
              <tr><td colSpan={columns.length + (hideActions ? 0 : 1)}>Данных пока нет.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

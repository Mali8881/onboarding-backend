const FEEDBACK_KEY = 'vpluse_feedback_tickets_v1';

const INITIAL_FEEDBACK = [
  { id: 1, type: 'Предложение', text: 'Было бы здорово добавить возможность экспортировать отчёты в Excel.', user: 'Алексей П.', userRole: 'intern', isAnonymous: false, date: '20 фев. 2026', status: 'new' },
  { id: 2, type: 'Жалоба', text: 'Иногда система медленно загружается в первой половине дня.', user: 'Анонимно', userRole: 'employee', isAnonymous: true, date: '18 фев. 2026', status: 'in_progress' },
  { id: 3, type: 'Вопрос', text: 'Когда будет обновлён онбординг для нового потока?', user: 'Дмитрий К.', userRole: 'intern', isAnonymous: false, date: '15 фев. 2026', status: 'resolved' },
  { id: 4, type: 'Жалоба', text: 'Руководитель поздно согласует отчёты, это тормозит работу.', user: 'Анонимно', userRole: 'intern', isAnonymous: true, date: '12 фев. 2026', status: 'resolved' },
  { id: 5, type: 'Жалоба', text: 'В пиковое время зависает открытие карточек задач.', user: 'Айбек У.', userRole: 'employee', isAnonymous: false, date: '11 фев. 2026', status: 'new' },
];

const readStore = () => {
  try {
    const raw = localStorage.getItem(FEEDBACK_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
};

const writeStore = (items) => localStorage.setItem(FEEDBACK_KEY, JSON.stringify(items));

export const listFeedbackTickets = () => {
  const existing = readStore();
  if (Array.isArray(existing)) return existing;
  writeStore(INITIAL_FEEDBACK);
  return INITIAL_FEEDBACK;
};

export const createFeedbackTicket = ({ type, text, user, userRole, isAnonymous = false }) => {
  const items = listFeedbackTickets();
  const next = {
    id: Date.now(),
    type,
    text,
    user: isAnonymous ? 'Анонимно' : user,
    userRole,
    isAnonymous,
    date: new Date().toLocaleDateString('ru-RU', { day: '2-digit', month: 'short', year: 'numeric' }),
    status: 'new',
  };
  const updated = [next, ...items];
  writeStore(updated);
  return next;
};

export const updateFeedbackStatus = (id, status) => {
  const items = listFeedbackTickets();
  const updated = items.map(i => (i.id === id ? { ...i, status } : i));
  writeStore(updated);
  return updated;
};

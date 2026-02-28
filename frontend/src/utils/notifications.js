import { listFeedbackTickets } from './feedbackStore';
import { getScheduleRequests } from './scheduleApproval';
import { getAttendanceStore, getTodayKey } from './attendance';

const PROMOTION_REQUESTS_KEY = 'vpluse_promotion_requests';

const readPromotionRequests = () => {
  try {
    const raw = localStorage.getItem(PROMOTION_REQUESTS_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
};

const seenKey = (userId) => `vpluse_notifications_seen_${userId}`;

const readSeen = (userId) => {
  try {
    const raw = localStorage.getItem(seenKey(userId));
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
};

export const markAllNotificationsRead = (userId, ids) => {
  if (!userId) return;
  localStorage.setItem(seenKey(userId), JSON.stringify(ids));
};

export const getNotificationsForUser = (user) => {
  if (!user?.id) return [];
  const items = [];

  const promotion = readPromotionRequests();
  const scheduleRequests = getScheduleRequests();
  const feedback = listFeedbackTickets();
  const attendance = getAttendanceStore();
  const todayKey = getTodayKey();

  if (user.role === 'superadmin') {
    promotion.filter(r => r.status === 'pending').forEach(r => {
      items.push({
        id: `promotion:${r.id}`,
        type: 'promotion',
        title: 'Заявка на перевод стажёра',
        text: `${r.userName} ожидает подтверждения роли сотрудника`,
        ts: r.createdAt || '',
      });
    });
    scheduleRequests.filter(r => r.status === 'pending').forEach(r => {
      items.push({
        id: `schedule:${r.id}`,
        type: 'schedule',
        title: 'Заявка на график',
        text: `${r.userName}: ${r.schedule?.name || 'Новый график'}`,
        ts: r.createdAt || '',
      });
    });
    feedback.filter(f => f.type === 'Жалоба').forEach(f => {
      items.push({
        id: `complaint:${f.id}`,
        type: 'complaint',
        title: 'Жалоба (история)',
        text: `${f.user}: ${f.text}`,
        ts: f.date || '',
      });
    });
  }

  if (user.role === 'admin') {
    feedback
      .filter(f => f.type === 'Жалоба' && ['intern', 'employee', 'projectmanager'].includes(f.userRole))
      .forEach(f => {
        items.push({
          id: `complaint:${f.id}`,
          type: 'complaint',
          title: 'Новая жалоба',
          text: `${f.user}: ${f.text}`,
          ts: f.date || '',
        });
      });
  }

  const own = attendance?.[String(user.id)]?.[todayKey];
  if (own?.lateNotifiedAt && !own?.checkIn) {
    items.push({
      id: `late:${user.id}:${todayKey}`,
      type: 'late',
      title: 'Просрочка отметки',
      text: 'Вы не отметили приход вовремя',
      ts: own.lateNotifiedAt,
    });
  }

  return items;
};

export const getUnreadCountForUser = (user) => {
  const items = getNotificationsForUser(user);
  const seen = new Set(readSeen(user?.id));
  return items.filter(i => !seen.has(i.id)).length;
};


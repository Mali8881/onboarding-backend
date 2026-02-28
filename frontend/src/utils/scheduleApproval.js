const REQUESTS_KEY = 'vpluse_schedule_requests_v1';
const ASSIGNMENTS_KEY = 'vpluse_schedule_assignments_v1';

const readJSON = (key) => {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
};

const writeJSON = (key, data) => {
  localStorage.setItem(key, JSON.stringify(data));
};

export const getScheduleRequests = () => readJSON(REQUESTS_KEY);

export const hasPendingScheduleRequest = (userId) => {
  const all = getScheduleRequests();
  return all.some(r => r.userId === userId && r.status === 'pending');
};

export const createScheduleRequest = (payload) => {
  const all = getScheduleRequests();
  const item = {
    id: Date.now(),
    status: 'pending',
    createdAt: new Date().toLocaleString('ru-RU'),
    ...payload,
  };
  all.unshift(item);
  writeJSON(REQUESTS_KEY, all);
  return item;
};

export const decideScheduleRequest = (requestId, status, reviewerName = '') => {
  const all = getScheduleRequests();
  const updated = all.map(r => (
    r.id === requestId
      ? { ...r, status, reviewedAt: new Date().toLocaleString('ru-RU'), reviewerName }
      : r
  ));
  writeJSON(REQUESTS_KEY, updated);
  return updated.find(r => r.id === requestId) || null;
};

export const getScheduleAssignments = () => readJSON(ASSIGNMENTS_KEY);

export const getAssignedScheduleForUser = (userId) => {
  const all = getScheduleAssignments();
  return all.find(x => x.userId === userId) || null;
};

export const setAssignedSchedule = ({ userId, schedule, approvedBy }) => {
  const all = getScheduleAssignments();
  const rest = all.filter(x => x.userId !== userId);
  const item = {
    userId,
    schedule,
    approvedBy,
    approvedAt: new Date().toLocaleString('ru-RU'),
  };
  rest.push(item);
  writeJSON(ASSIGNMENTS_KEY, rest);
  return item;
};


const STORAGE_KEY = 'vpluse_attendance_v1';

const readStore = () => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
};

const writeStore = (store) => {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
};

export const getTodayKey = () => {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, '0');
  const d = String(now.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
};

export const getAttendanceStore = () => readStore();

export const getUserAttendanceForDate = (userId, dateKey = getTodayKey()) => {
  const store = readStore();
  return store?.[String(userId)]?.[dateKey] || null;
};

export const setCheckIn = (userId, at = new Date().toISOString(), meta = null) => {
  const dateKey = getTodayKey();
  const store = readStore();
  const uid = String(userId);
  if (!store[uid]) store[uid] = {};
  const current = store[uid][dateKey] || {};
  if (!current.checkIn) {
    current.checkIn = at;
  }
  if (!current.status) {
    current.status = 'present';
  }
  if (meta && typeof meta === 'object') {
    current.checkMeta = {
      ...(current.checkMeta || {}),
      ...meta,
    };
  }
  store[uid][dateKey] = current;
  writeStore(store);
  return current;
};

export const setCheckOut = (userId, at = new Date().toISOString(), meta = null) => {
  const dateKey = getTodayKey();
  const store = readStore();
  const uid = String(userId);
  if (!store[uid]) store[uid] = {};
  const current = store[uid][dateKey] || {};
  if (!current.checkIn) {
    current.checkIn = at;
  }
  current.checkOut = at;
  current.status = 'present';
  if (meta && typeof meta === 'object') {
    current.checkMeta = {
      ...(current.checkMeta || {}),
      ...meta,
    };
  }
  store[uid][dateKey] = current;
  writeStore(store);
  return current;
};

export const markLateNotified = (userId, at = new Date().toISOString()) => {
  const dateKey = getTodayKey();
  const store = readStore();
  const uid = String(userId);
  if (!store[uid]) store[uid] = {};
  const current = store[uid][dateKey] || {};
  current.lateNotifiedAt = at;
  if (!current.status) current.status = 'late';
  store[uid][dateKey] = current;
  writeStore(store);
  return current;
};

export const isLateWithoutCheckIn = (userId, scheduleStart = '09:00', graceMinutes = 20) => {
  const [hh, mm] = scheduleStart.split(':').map(Number);
  const now = new Date();
  const threshold = new Date(now);
  threshold.setHours(hh, mm + graceMinutes, 0, 0);
  if (now < threshold) return false;
  const today = getUserAttendanceForDate(userId);
  return !today?.checkIn;
};

export const wasLateNotifiedToday = (userId) => {
  const today = getUserAttendanceForDate(userId);
  return Boolean(today?.lateNotifiedAt);
};

const CUSTOM_USERS_KEY = 'vpluse_custom_users_v1';
const CHANGED_EVENT = 'vpluse:mock-users-changed';

const readJSON = () => {
  try {
    const raw = localStorage.getItem(CUSTOM_USERS_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
};

const writeJSON = (items) => {
  localStorage.setItem(CUSTOM_USERS_KEY, JSON.stringify(items));
};

export const listCustomMockUsers = () => readJSON();

export const upsertCustomMockUser = (user) => {
  const items = readJSON();
  const idx = items.findIndex(u => u.id === user.id || u.email === user.email);
  if (idx >= 0) items[idx] = { ...items[idx], ...user };
  else items.unshift(user);
  writeJSON(items);
  window.dispatchEvent(new Event(CHANGED_EVENT));
};

export const MOCK_USERS_CHANGED_EVENT = CHANGED_EVENT;


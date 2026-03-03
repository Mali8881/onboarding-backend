import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_URL || '/api';
const CSRF_METHODS = ['post', 'put', 'patch', 'delete'];

function getCookie(name) {
  if (typeof document === 'undefined') return null;
  const prefix = `${name}=`;
  const chunks = document.cookie ? document.cookie.split(';') : [];
  for (let i = 0; i < chunks.length; i += 1) {
    const part = chunks[i].trim();
    if (part.startsWith(prefix)) {
      return decodeURIComponent(part.slice(prefix.length));
    }
  }
  return null;
}

const api = axios.create({
  baseURL: BASE_URL,
  withCredentials: true,
});

// Attach token automatically
api.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  if (CSRF_METHODS.includes(String(config.method || '').toLowerCase())) {
    const csrfToken = getCookie('csrftoken');
    if (csrfToken) config.headers['X-CSRFToken'] = csrfToken;
  }
  if (config.data instanceof FormData) {
    delete config.headers['Content-Type'];
  } else if (!config.headers['Content-Type']) {
    config.headers['Content-Type'] = 'application/json';
  }
  return config;
});

// Auto-refresh on 401
api.interceptors.response.use(
  res => res,
  async error => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      const refresh = localStorage.getItem('refresh_token');
      if (refresh) {
        try {
          const { data } = await axios.post(`${BASE_URL}/auth/token/refresh/`, { refresh });
          localStorage.setItem('access_token', data.access);
          original.headers.Authorization = `Bearer ${data.access}`;
          return api(original);
        } catch {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
        }
      }
    }
    return Promise.reject(error);
  }
);

export default api;

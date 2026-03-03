import { createContext, useContext, useState, useEffect } from 'react';
import { authAPI } from '../api/auth';
import { listCustomMockUsers, MOCK_USERS_CHANGED_EVENT } from '../utils/mockUsers';

const AuthContext = createContext(null);

// в”Ђв”Ђ РҐР°СЂРґ-РєРѕРґ РґР»СЏ СЂРµР¶РёРјР° Р±РµР· backend (USE_MOCK=true) в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
const USE_MOCK = false; // РџРµСЂРµРєР»СЋС‡Рё РІ true РґР»СЏ Р»РѕРєР°Р»СЊРЅС‹С… РјРѕРєРѕРІ

export const HARDCODED_USERS = [
  {
    id: 1, login: 'alexey', username: 'alexey', password: '1234',
    role: 'intern', roleLabel: 'РЎС‚Р°Р¶С‘СЂ',
    name: 'РђР»РµРєСЃРµР№ РџРµС‚СЂРѕРІ', first_name: 'РђР»РµРєСЃРµР№', last_name: 'РџРµС‚СЂРѕРІ',
    department: 1, department_name: 'Р Р°Р·СЂР°Р±РѕС‚РєР°',
    subdivision: 'Frontend',
    subdivision_name: 'Frontend',
    position: 9, position_name: 'РЎС‚Р°Р¶С‘СЂ',
    phone: '+996 555 123 456', telegram: '@alex_petrov',
    email: 'alex.p@vpluse.kg', hireDate: '27.05.2024',
  },
  {
    id: 2, login: 'aibek', username: 'aibek', password: '1234',
    role: 'employee', roleLabel: 'РЎРѕС‚СЂСѓРґРЅРёРє',
    name: 'РђР№Р±РµРє РЈСЃСѓРїРѕРІ', first_name: 'РђР№Р±РµРє', last_name: 'РЈСЃСѓРїРѕРІ',
    department: 3, department_name: 'РћС‚РґРµР» С…РѕР»РѕРґРЅС‹С… РїСЂРѕРґР°Р¶',
    subdivision: 'РҐРѕР»РѕРґРЅС‹Рµ Р·РІРѕРЅРєРё',
    subdivision_name: 'РҐРѕР»РѕРґРЅС‹Рµ Р·РІРѕРЅРєРё',
    position: 6, position_name: 'РњРµРЅРµРґР¶РµСЂ РїСЂРѕРґР°Р¶',
    phone: '+996 700 200 300', telegram: '@aibek_u',
    email: 'aibek.u@vpluse.kg', hireDate: '01.03.2024',
  },
  {
    id: 3, login: 'sultan', username: 'sultan', password: '1234',
    role: 'projectmanager', roleLabel: 'РџСЂРѕРµРєС‚-РјРµРЅРµРґР¶РµСЂ',
    name: 'РЎСѓР»С‚Р°РЅР°Р»РёРµРІ РњР°РєСЃР°С‚', first_name: 'РњР°РєСЃР°С‚', last_name: 'РЎСѓР»С‚Р°РЅР°Р»РёРµРІ',
    department: 2, department_name: 'РћС‚РґРµР» РјР°СЂРєРµС‚РёРЅРіР°',
    subdivision: 'Digital',
    subdivision_name: 'Digital',
    position: 7, position_name: 'РџСЂРѕРµРєС‚-РјРµРЅРµРґР¶РµСЂ',
    phone: '+996 999 555 194', telegram: '@sultan_m',
    email: 'sultan.m@vpluse.kg', hireDate: '27.05.2024',
  },
  {
    id: 10, login: 'elena.m', username: 'elena.m', password: '1234',
    role: 'employee', roleLabel: 'РЎРѕС‚СЂСѓРґРЅРёРє',
    name: 'Р•Р»РµРЅР° Рњ.', first_name: 'Р•Р»РµРЅР°', last_name: 'Рњ.',
    department: 2, department_name: 'РћС‚РґРµР» РјР°СЂРєРµС‚РёРЅРіР°',
    subdivision: 'Digital',
    subdivision_name: 'Digital',
    position: 6, position_name: 'РњР°СЂРєРµС‚РѕР»РѕРі',
    phone: '+996 700 101 202', telegram: '@elena_marketing',
    email: 'elena.m@vpluse.kg', hireDate: '04.04.2024',
  },
  {
    id: 11, login: 'azamat.k', username: 'azamat.k', password: '1234',
    role: 'intern', roleLabel: 'РЎС‚Р°Р¶С‘СЂ',
    name: 'РђР·Р°РјР°С‚ Рљ.', first_name: 'РђР·Р°РјР°С‚', last_name: 'Рљ.',
    department: 2, department_name: 'РћС‚РґРµР» РјР°СЂРєРµС‚РёРЅРіР°',
    subdivision: 'Digital',
    subdivision_name: 'Digital',
    position: 9, position_name: 'РЎС‚Р°Р¶С‘СЂ',
    phone: '+996 700 303 404', telegram: '@azamat_intern',
    email: 'azamat.k@vpluse.kg', hireDate: '10.02.2026',
  },
  {
    id: 4, login: 'ivan', username: 'ivan', password: '1234',
    role: 'projectmanager', roleLabel: 'Р СѓРєРѕРІРѕРґРёС‚РµР»СЊ',
    name: 'РРІР°РЅ РЎ.', first_name: 'РРІР°РЅ', last_name: 'РЎ.',
    department: 5, department_name: 'РЈРїСЂР°РІР»РµРЅРёРµ',
    subdivision: 'РћРїРµСЂР°С†РёРѕРЅРЅРѕРµ СѓРїСЂР°РІР»РµРЅРёРµ',
    subdivision_name: 'РћРїРµСЂР°С†РёРѕРЅРЅРѕРµ СѓРїСЂР°РІР»РµРЅРёРµ',
    position: 8, position_name: 'Р СѓРєРѕРІРѕРґРёС‚РµР»СЊ',
    phone: '+996 555 200 100', telegram: '@ivan_sales',
    email: 'ivan.s@vpluse.kg', hireDate: '19.03.2024',
  },
  {
    id: 5, login: 'maria', username: 'maria', password: '1234',
    role: 'superadmin', roleLabel: 'РЎСѓРїРµСЂР°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂ',
    name: 'РњР°СЂРёСЏ Рљ.', first_name: 'РњР°СЂРёСЏ', last_name: 'Рљ.',
    department: 5, department_name: 'РЈРїСЂР°РІР»РµРЅРёРµ',
    subdivision: 'РђРґРјРёРЅРёСЃС‚СЂРёСЂРѕРІР°РЅРёРµ',
    subdivision_name: 'РђРґРјРёРЅРёСЃС‚СЂРёСЂРѕРІР°РЅРёРµ',
    position: 9, position_name: 'РЎСѓРїРµСЂР°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂ',
    phone: '+996 555 600 500', telegram: '@maria_k',
    email: 'maria.k@vpluse.kg', hireDate: '19.03.2024',
  },
  {
    id: 9, login: 'admin', username: 'admin', password: '1234',
    role: 'admin', roleLabel: 'РђРґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂ',
    name: 'РђРґРјРёРЅ Рђ.', first_name: 'РђРґРјРёРЅ', last_name: 'Рђ.',
    department: 5, department_name: 'РЈРїСЂР°РІР»РµРЅРёРµ',
    subdivision: 'РђРґРјРёРЅРёСЃС‚СЂРёСЂРѕРІР°РЅРёРµ',
    subdivision_name: 'РђРґРјРёРЅРёСЃС‚СЂРёСЂРѕРІР°РЅРёРµ',
    position: 10, position_name: 'РђРґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂ',
    phone: '+996 555 900 100', telegram: '@admin_full',
    email: 'admin@vpluse.kg', hireDate: '20.03.2024',
  },
];

const ROLE_LABELS = {
  intern: 'Стажер',
  employee: 'Сотрудник',
  projectmanager: 'Проект-менеджер',
  department_head: 'Руководитель отдела',
  admin: 'Админ',
  superadmin: 'Суперадмин',
};

function normalizeMockUser(raw) {
  const login = raw.login || raw.username || raw.email || '';
  return {
    id: raw.id,
    login,
    username: raw.username || login,
    password: raw.password || '1234',
    role: raw.role || 'intern',
    roleLabel: raw.roleLabel || ROLE_LABELS[raw.role] || 'РЎС‚Р°Р¶С‘СЂ',
    name: raw.name || [raw.first_name, raw.last_name].filter(Boolean).join(' ') || login,
    first_name: raw.first_name || '',
    last_name: raw.last_name || '',
    department: raw.department || '',
    department_name: raw.department_name || raw.department || '',
    subdivision: raw.subdivision || '',
    subdivision_name: raw.subdivision_name || raw.subdivision || '',
    position: raw.position || '',
    position_name: raw.position_name || raw.position || '',
    phone: raw.phone || '',
    telegram: raw.telegram || '',
    email: raw.email || '',
    hireDate: raw.hireDate || raw.hire_date || '',
  };
}

function getAllMockUsers() {
  const custom = listCustomMockUsers();
  const byEmail = new Map();
  [...HARDCODED_USERS, ...custom].forEach((u) => {
    const key = (u.email || u.login || u.username || String(u.id)).toLowerCase();
    byEmail.set(key, normalizeMockUser(u));
  });
  return Array.from(byEmail.values());
}

function normalizeUser(raw) {
  return {
    id: raw.id,
    username: raw.username,
    login: raw.username,
    name: raw.full_name || `${raw.first_name} ${raw.last_name}`.trim() || raw.username,
    email: raw.email,
    role: raw.role,
    roleLabel: raw.role_label,
    department: raw.department,
    department_name: raw.department_name,
    subdivision: raw.subdivision,
    subdivision_name: raw.subdivision_name,
    position: raw.position,
    position_name: raw.position_name,
    phone: raw.phone || '',
    telegram: raw.telegram || '',
    hireDate: raw.hire_date || '',
  };
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(false);
  const [bootstrapped, setBootstrapped] = useState(false);
  const [mockUsers, setMockUsers] = useState(getAllMockUsers());

  useEffect(() => {
    const refresh = () => setMockUsers(getAllMockUsers());
    window.addEventListener(MOCK_USERS_CHANGED_EVENT, refresh);
    window.addEventListener('storage', refresh);
    return () => {
      window.removeEventListener(MOCK_USERS_CHANGED_EVENT, refresh);
      window.removeEventListener('storage', refresh);
    };
  }, []);

  // Restore session on mount
  useEffect(() => {
    if (USE_MOCK) { setBootstrapped(true); return; }
    const token = localStorage.getItem('access_token');
    if (token) {
      authAPI.getMe()
        .then(res => setUser(normalizeUser(res.data)))
        .catch(() => {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
        })
        .finally(() => setBootstrapped(true));
    } else {
      setBootstrapped(true);
    }
  }, []);

  const login = async (loginVal, password) => {
    setLoading(true);
    try {
      if (USE_MOCK) {
        await new Promise(r => setTimeout(r, 400));
        const found = getAllMockUsers().find(
          u =>
            [u.login, u.username, u.email]
              .filter(Boolean)
              .some(v => v.toLowerCase() === loginVal.trim().toLowerCase()) &&
            u.password === password
        );
        if (!found) throw new Error('РќРµРІРµСЂРЅС‹Р№ Р»РѕРіРёРЅ РёР»Рё РїР°СЂРѕР»СЊ');
        setUser(normalizeMockUser(found));
        return found;
      } else {
        const res = await authAPI.login(loginVal, password);
        const { access, refresh, user: userData } = res.data;
        localStorage.setItem('access_token', access);
        localStorage.setItem('refresh_token', refresh);
        const normalized = normalizeUser(userData);
        setUser(normalized);
        return normalized;
      }
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    if (!USE_MOCK) {
      const refresh = localStorage.getItem('refresh_token');
      if (refresh) await authAPI.logout(refresh).catch(() => {});
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
    }
    setUser(null);
  };

  const updateUser = (data) => setUser(u => ({ ...u, ...data }));

  const isAdmin = user?.role === 'department_head' || user?.role === 'admin' || user?.role === 'superadmin';
  const isSuperAdmin = user?.role === 'superadmin';
  const isIntern = user?.role === 'intern';

  if (!bootstrapped) return null;

  return (
    <AuthContext.Provider value={{
      user, login, logout, updateUser, loading,
      isAdmin, isSuperAdmin, isIntern, USE_MOCK, mockUsers,
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);



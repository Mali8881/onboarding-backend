import { createContext, useContext, useMemo, useState } from 'react';

const LOCALE_KEY = 'vpluse_locale_v1';
const SUPPORTED = ['ru', 'en', 'kg'];

const DICT = {
  ru: {
    'lang.ru': 'RU',
    'lang.en': 'EN',
    'lang.kg': 'KG',

    'header.welcome': 'Добро пожаловать',
    'header.notifications': 'Уведомления',
    'header.read': 'Прочитано',
    'header.noEvents': 'Новых событий нет.',
    'header.profile': 'Профиль',
    'header.logout': 'Выйти',

    'sidebar.section.my': 'МОИ РАЗДЕЛЫ',
    'sidebar.section.manage': 'УПРАВЛЕНИЕ',
    'sidebar.section.system': 'СИСТЕМА',
    'sidebar.home': 'Главная',
    'sidebar.tasks': 'Задачи',
    'sidebar.myTasks': 'Мои задачи',
    'sidebar.teamTasks': 'Задачи команды',
    'sidebar.salary': 'Зарплата',
    'sidebar.company': 'Компания',
    'sidebar.regulations': 'Регламенты',
    'sidebar.schedule': 'График работы',
    'sidebar.instructions': 'Инструкция',
    'sidebar.overview': 'Обзор',
    'sidebar.users': 'Пользователи',
    'sidebar.roles': 'Роли и права',
    'sidebar.content': 'Контент',
    'sidebar.onboarding': 'Онбординг / Отчеты',
    'sidebar.workSchedules': 'График работы сотрудников',
    'sidebar.feedback': 'Обратная связь',
    'sidebar.systemSecurity': 'Система / Безопасность',
    'sidebar.interface': 'Интерфейс',
    'sidebar.hideSection': 'СКРЫТИЕ РАЗДЕЛОВ',
    'sidebar.hideToggle': 'Скрыть разделы',
    'sidebar.collapse': 'Свернуть меню',
  },
  en: {
    'lang.ru': 'RU',
    'lang.en': 'EN',
    'lang.kg': 'KG',

    'header.welcome': 'Welcome',
    'header.notifications': 'Notifications',
    'header.read': 'Mark read',
    'header.noEvents': 'No new events.',
    'header.profile': 'Profile',
    'header.logout': 'Logout',

    'sidebar.section.my': 'MY SECTIONS',
    'sidebar.section.manage': 'MANAGEMENT',
    'sidebar.section.system': 'SYSTEM',
    'sidebar.home': 'Home',
    'sidebar.tasks': 'Tasks',
    'sidebar.myTasks': 'My tasks',
    'sidebar.teamTasks': 'Team tasks',
    'sidebar.salary': 'Salary',
    'sidebar.company': 'Company',
    'sidebar.regulations': 'Regulations',
    'sidebar.schedule': 'Work schedule',
    'sidebar.instructions': 'Instructions',
    'sidebar.overview': 'Overview',
    'sidebar.users': 'Users',
    'sidebar.roles': 'Roles & permissions',
    'sidebar.content': 'Content',
    'sidebar.onboarding': 'Onboarding / Reports',
    'sidebar.workSchedules': 'Work schedules',
    'sidebar.feedback': 'Feedback',
    'sidebar.systemSecurity': 'System / Security',
    'sidebar.interface': 'Interface',
    'sidebar.hideSection': 'HIDDEN SECTIONS',
    'sidebar.hideToggle': 'Hide sections',
    'sidebar.collapse': 'Collapse menu',
  },
  kg: {
    'lang.ru': 'RU',
    'lang.en': 'EN',
    'lang.kg': 'KG',

    'header.welcome': 'Кош келиңиз',
    'header.notifications': 'Билдирмелер',
    'header.read': 'Окулган',
    'header.noEvents': 'Жаңы окуялар жок.',
    'header.profile': 'Профиль',
    'header.logout': 'Чыгуу',

    'sidebar.section.my': 'МЕНИН БӨЛҮМДӨРҮМ',
    'sidebar.section.manage': 'БАШКАРУУ',
    'sidebar.section.system': 'СИСТЕМА',
    'sidebar.home': 'Башкы бет',
    'sidebar.tasks': 'Тапшырмалар',
    'sidebar.myTasks': 'Менин тапшырмаларым',
    'sidebar.teamTasks': 'Команданын тапшырмалары',
    'sidebar.salary': 'Айлык',
    'sidebar.company': 'Компания',
    'sidebar.regulations': 'Регламенттер',
    'sidebar.schedule': 'Иш графиги',
    'sidebar.instructions': 'Нускама',
    'sidebar.overview': 'Сереп',
    'sidebar.users': 'Колдонуучулар',
    'sidebar.roles': 'Ролдор жана укуктар',
    'sidebar.content': 'Контент',
    'sidebar.onboarding': 'Онбординг / Отчеттор',
    'sidebar.workSchedules': 'Иш графиктери',
    'sidebar.feedback': 'Кайтарым байланыш',
    'sidebar.systemSecurity': 'Система / Коопсуздук',
    'sidebar.interface': 'Интерфейс',
    'sidebar.hideSection': 'ЖАШЫРУУ БӨЛҮМҮ',
    'sidebar.hideToggle': 'Бөлүмдөрдү жашыруу',
    'sidebar.collapse': 'Менюну жыйноо',
  },
};

const PHRASES = {
  en: {
    'Главная': 'Home',
    'Онбординг': 'Onboarding',
    'Инструкция': 'Instructions',
    'Регламенты': 'Regulations',
    'Компания': 'Company',
    'График работы': 'Work schedule',
    'Мои задачи': 'My tasks',
    'Зарплата': 'Salary',
    'Обратная связь': 'Feedback',
  },
  kg: {
    'Главная': 'Башкы бет',
    'Онбординг': 'Онбординг',
    'Инструкция': 'Нускама',
    'Регламенты': 'Регламенттер',
    'Компания': 'Компания',
    'График работы': 'Иш графиги',
    'Мои задачи': 'Менин тапшырмаларым',
    'Зарплата': 'Айлык',
    'Обратная связь': 'Кайтарым байланыш',
  },
};

const LocaleContext = createContext(null);

function getInitialLocale() {
  try {
    const raw = localStorage.getItem(LOCALE_KEY) || 'ru';
    return SUPPORTED.includes(raw) ? raw : 'ru';
  } catch {
    return 'ru';
  }
}

export function LocaleProvider({ children }) {
  const [locale, setLocaleState] = useState(getInitialLocale);

  const setLocale = (next) => {
    const normalized = SUPPORTED.includes(next) ? next : 'ru';
    setLocaleState(normalized);
    try {
      localStorage.setItem(LOCALE_KEY, normalized);
    } catch {
      // ignore storage errors
    }
  };

  const t = (key, fallback = '') => {
    const hit = DICT[locale]?.[key];
    if (hit) return hit;
    return fallback || key;
  };

  const tr = (text) => {
    if (!text || locale === 'ru') return text;
    return PHRASES[locale]?.[text] || text;
  };

  const value = useMemo(() => ({ locale, setLocale, t, tr, supported: SUPPORTED }), [locale]);

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export function useLocale() {
  return useContext(LocaleContext);
}

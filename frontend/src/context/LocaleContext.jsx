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
    'sidebar.onboarding': 'Онбординг / Отчёты',
    'sidebar.workSchedules': 'Графики работы',
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
    'Войти': 'Sign in',
    'Логин': 'Login',
    'Пароль': 'Password',
    'Забыли пароль?': 'Forgot password?',
    'Сохранить': 'Save',
    'Создать': 'Create',
    'Фильтры': 'Filters',
    'Назад': 'Back',
    'Одобрить': 'Approve',
    'Отклонить': 'Reject',
    'Удалить': 'Delete',
    'Редактировать': 'Edit',
    'Поиск': 'Search',
    'Введите для поиска': 'Type to search',
    'Статус': 'Status',
    'Сотрудник': 'Employee',
    'Сотрудники': 'Employees',
    'Пользователь': 'User',
    'Пользователи': 'Users',
    'Роль': 'Role',
    'Должность': 'Position',
    'Отдел': 'Department',
    'Подразделение': 'Subdivision',
    'Главная': 'Home',
    'Регламенты': 'Regulations',
    'Инструкция': 'Instructions',
    'График работы': 'Work schedule',
    'Мой график': 'My schedule',
    'Компания': 'Company',
    'Профиль': 'Profile',
    'Зарплата': 'Salary',
    'Мои задачи': 'My tasks',
    'Обзор': 'Overview',
    'Контент': 'Content',
    'Обратная связь': 'Feedback',
    'Графики работы': 'Work schedules',
    'Графики пользователей': 'User schedules',
    'Недельные планы работы': 'Weekly work plans',
    'Календарь недельного плана': 'Weekly plan calendar',
    'Начало недели': 'Week start',
    'Часы в офисе': 'Office hours',
    'Часы онлайн': 'Online hours',
    'Кем проверено': 'Reviewed by',
    'Обновлено': 'Updated at',
    'Подробности': 'Details',
    'Рабочие дни': 'Work days',
    'Онлайн дни': 'Online days',
    'Утвержденный недельный план': 'Approved weekly plan',
    'Время утверждения недельного плана': 'Approval time',
    'Ничего не найдено': 'Nothing found',
    'Пользователи не найдены': 'Users not found',
    'Нет заявок на одобрение.': 'No approval requests.',
    'График': 'Schedule',
    'Утвержден': 'Approved',
    'Время запроса': 'Requested at',
    'Короткий перерыв 15 минут': '15-minute break',
    'Очистить перерывы': 'Clear breaks',
    'Короткие перерывы не добавлены': 'No short breaks added',
    'Начало': 'From',
    'Конец': 'To',
    'Формат': 'Mode',
    'Офис': 'Office',
    'Онлайн': 'Online',
    'Выходной': 'Day off',
    'Часы': 'Hours',
    'Детали сотрудника': 'Employee details',
    'Раздел доступен для админа/суперадмина.': 'Section available for admin/superadmin.',
    'Настройки интерфейса': 'Interface settings',
    'Настройки безопасности': 'Security settings',
    'Система / Безопасность': 'System / Security',
    'Интерфейс': 'Interface',
  },
  kg: {
    'Войти': 'Кирүү',
    'Логин': 'Логин',
    'Пароль': 'Сырсөз',
    'Забыли пароль?': 'Сырсөздү унуттуңузбу?',
    'Сохранить': 'Сактоо',
    'Создать': 'Түзүү',
    'Фильтры': 'Чыпкалар',
    'Назад': 'Артка',
    'Одобрить': 'Бекитүү',
    'Отклонить': 'Четке кагуу',
    'Удалить': 'Өчүрүү',
    'Редактировать': 'Түзөтүү',
    'Поиск': 'Издөө',
    'Введите для поиска': 'Издөө үчүн жазыңыз',
    'Статус': 'Статус',
    'Сотрудник': 'Кызматкер',
    'Сотрудники': 'Кызматкерлер',
    'Пользователь': 'Колдонуучу',
    'Пользователи': 'Колдонуучулар',
    'Роль': 'Роль',
    'Должность': 'Кызмат орду',
    'Отдел': 'Бөлүм',
    'Подразделение': 'Багыт',
    'Главная': 'Башкы бет',
    'Регламенты': 'Регламенттер',
    'Инструкция': 'Нускама',
    'График работы': 'Иш графиги',
    'Мой график': 'Менин графигим',
    'Компания': 'Компания',
    'Профиль': 'Профиль',
    'Зарплата': 'Айлык',
    'Мои задачи': 'Менин тапшырмаларым',
    'Обзор': 'Сереп',
    'Контент': 'Контент',
    'Обратная связь': 'Кайтарым байланыш',
    'Графики работы': 'Иш графиктери',
    'Графики пользователей': 'Колдонуучунун графиктери',
    'Недельные планы работы': 'Жумалык иш пландары',
    'Календарь недельного плана': 'Жумалык план календары',
    'Начало недели': 'Аптанын башталышы',
    'Часы в офисе': 'Офистеги сааттар',
    'Часы онлайн': 'Онлайн сааттар',
    'Кем проверено': 'Текшерген',
    'Обновлено': 'Жаңыртылды',
    'Подробности': 'Толугураак',
    'Рабочие дни': 'Иш күндөрү',
    'Онлайн дни': 'Онлайн күндөр',
    'Утвержденный недельный план': 'Бекитилген жумалык план',
    'Время утверждения недельного плана': 'Бекитилген убакыт',
    'Ничего не найдено': 'Эч нерсе табылган жок',
    'Пользователи не найдены': 'Колдонуучулар табылган жок',
    'Нет заявок на одобрение.': 'Бекитүүгө арыздар жок.',
    'График': 'График',
    'Утвержден': 'Бекитилген',
    'Время запроса': 'Сурам убактысы',
    'Короткий перерыв 15 минут': '15 мүнөттүк тыныгуу',
    'Очистить перерывы': 'Тыныгууларды тазалоо',
    'Короткие перерывы не добавлены': 'Кыска тыныгуулар кошулган эмес',
    'Начало': 'Башы',
    'Конец': 'Аягы',
    'Формат': 'Формат',
    'Офис': 'Офис',
    'Онлайн': 'Онлайн',
    'Выходной': 'Дем алыш',
    'Часы': 'Сааттар',
    'Детали сотрудника': 'Кызматкердин маалыматы',
    'Раздел доступен для админа/суперадмина.': 'Бөлүм админ/суперадмин үчүн жеткиликтүү.',
    'Настройки интерфейса': 'Интерфейс жөндөөлөрү',
    'Настройки безопасности': 'Коопсуздук жөндөөлөрү',
    'Система / Безопасность': 'Система / Коопсуздук',
    'Интерфейс': 'Интерфейс',
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

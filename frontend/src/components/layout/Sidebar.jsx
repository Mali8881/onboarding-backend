import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useLocale } from '../../context/LocaleContext';
import {
  Home, BookOpen, Calendar, User, BookMarked,
  Users, Shield, FileText, ClipboardCheck,
  LayoutGrid, Settings, ChevronLeft, ChevronRight,
  GraduationCap, MessageSquare, CheckSquare, Wallet,
} from 'lucide-react';

const NAV_INTERN = [
  { label: 'Главная',       icon: Home,          path: '/dashboard' },
  { label: 'Онбординг',     icon: GraduationCap, path: '/onboarding' },
  { label: 'Регламенты',    icon: BookMarked,    path: '/regulations' },
  { label: 'График работы', icon: Calendar,      path: '/schedule' },
  { label: 'Инструкция',    icon: BookOpen,      path: '/instructions' },
];

const NAV_EMPLOYEE = [
  { label: 'Главная',       icon: Home,          path: '/dashboard' },
  { label: 'Мои задачи',    icon: CheckSquare,   path: '/tasks' },
  { label: 'Зарплата',      icon: Wallet,        path: '/salary' },
  { label: 'Компания',      icon: Users,         path: '/company' },
  { label: 'Регламенты',    icon: BookMarked,    path: '/regulations' },
  { label: 'График работы', icon: Calendar,      path: '/schedule' },
  { label: 'Инструкция',    icon: BookOpen,      path: '/instructions' },
];

const NAV_PM = [
  { label: 'Главная',        icon: Home,          path: '/dashboard' },
  { label: 'Задачи команды', icon: CheckSquare,   path: '/tasks' },
  { label: 'Онбординг / Отчёты', icon: GraduationCap, path: '/admin/onboarding' },
  { label: 'Зарплата',       icon: Wallet,        path: '/salary' },
  { label: 'Компания',       icon: Users,         path: '/company' },
  { label: 'Регламенты',     icon: BookMarked,    path: '/regulations' },
  { label: 'График работы',  icon: Calendar,      path: '/schedule' },
  { label: 'Инструкция',     icon: BookOpen,      path: '/instructions' },
];

const NAV_ADMIN = [
  { section: 'МОИ РАЗДЕЛЫ' },
  { label: 'Главная',            icon: Home,          path: '/dashboard' },
  { label: 'Задачи',             icon: CheckSquare,   path: '/tasks' },
  { label: 'Компания',           icon: Users,         path: '/company' },
  { label: 'График работы',      icon: Calendar,      path: '/schedule' },
  { label: 'Регламенты',         icon: BookMarked,    path: '/regulations' },
  { label: 'Зарплата',           icon: Wallet,        path: '/salary' },
  { section: 'УПРАВЛЕНИЕ' },
  { label: 'Обзор',              icon: LayoutGrid,    path: '/admin/overview' },
  { label: 'Пользователи',       icon: Users,         path: '/admin/users' },
  { label: 'Контент',            icon: FileText,      path: '/admin/content' },
  { label: 'График работы сотрудников', icon: Calendar, path: '/admin/schedules' },
  { label: 'Обратная связь',     icon: MessageSquare, path: '/admin/feedback' },
];

const NAV_SUPERADMIN = [
  { section: 'МОИ РАЗДЕЛЫ' },
  { label: 'Главная',                icon: Home,          path: '/dashboard' },
  { label: 'Задачи',                 icon: CheckSquare,   path: '/tasks' },
  { label: 'Компания',               icon: Users,         path: '/company' },
  { label: 'График работы',          icon: Calendar,      path: '/schedule' },
  { section: 'УПРАВЛЕНИЕ' },
  { label: 'Обзор',                  icon: LayoutGrid,    path: '/admin/overview' },
  { label: 'Пользователи',           icon: Users,         path: '/admin/users' },
  { label: 'Роли и права',           icon: Shield,        path: '/admin/roles' },
  { label: 'Зарплаты',               icon: Wallet,        path: '/salary' },
  { label: 'Контент',                icon: FileText,      path: '/admin/content' },
  { label: 'График работы сотрудников', icon: Calendar,    path: '/admin/schedules' },
  { label: 'Обратная связь',         icon: MessageSquare, path: '/admin/feedback' },
  { section: 'СИСТЕМА' },
  { label: 'Система / Безопасность', icon: Settings,      path: '/admin/system' },
  { label: 'Интерфейс',              icon: LayoutGrid,    path: '/admin/interface' },
];

const ROLE_COLORS = {
  intern:         '#2563EB',
  employee:       '#16A34A',
  projectmanager: '#7C3AED',
  admin:          '#EA580C',
  superadmin:     '#BE123C',
};

const NAV_MAP = {
  intern:         NAV_INTERN,
  employee:       NAV_EMPLOYEE,
  projectmanager: NAV_PM,
  admin:          NAV_ADMIN,
  superadmin:     NAV_SUPERADMIN,
};

export default function Sidebar() {
  const { user } = useAuth();
  const { t } = useLocale();
  const navigate = useNavigate();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);
  const [hideMenuPanelOpen, setHideMenuPanelOpen] = useState(false);

  const canCustomizeHide = user?.role === 'admin' || user?.role === 'projectmanager' || user?.role === 'employee';
  const baseNav = NAV_MAP[user?.role] || NAV_INTERN;
  const nav = canCustomizeHide
    ? baseNav.filter(item => item.path !== '/regulations' && item.path !== '/instructions')
    : baseNav;

  const handleHome = () => {
    if (user?.role === 'admin' || user?.role === 'superadmin') navigate('/admin/overview');
    else navigate('/dashboard');
  };

  const translateNav = (label) => {
    const map = {
      'Главная': 'sidebar.home',
      'Задачи': 'sidebar.tasks',
      'Мои задачи': 'sidebar.myTasks',
      'Задачи команды': 'sidebar.teamTasks',
      'Мой график': 'sidebar.schedule',
      'Зарплата': 'sidebar.salary',
      'Компания': 'sidebar.company',
      'Регламенты': 'sidebar.regulations',
      'График работы': 'sidebar.schedule',
      'Инструкция': 'sidebar.instructions',
      'Обзор': 'sidebar.overview',
      'Пользователи': 'sidebar.users',
      'Роли и права': 'sidebar.roles',
      'Контент': 'sidebar.content',
      'Онбординг / Отчёты': 'sidebar.onboarding',
      'Графики работы': 'sidebar.workSchedules',
      'График работы сотрудников': 'sidebar.workSchedules',
      'Обратная связь': 'sidebar.feedback',
      'Система / Безопасность': 'sidebar.systemSecurity',
      'Интерфейс': 'sidebar.interface',
    };
    return t(map[label] || '', label);
  };

  const translateSection = (section) => {
    if (section === 'МОИ РАЗДЕЛЫ') return t('sidebar.section.my', section);
    if (section === 'УПРАВЛЕНИЕ') return t('sidebar.section.manage', section);
    if (section === 'СИСТЕМА') return t('sidebar.section.system', section);
    return section;
  };

  return (
    <aside className={`sidebar ${collapsed ? 'collapsed' : ''}`}>
      <div className="sidebar-logo" style={{ cursor: 'pointer' }} onClick={handleHome}>
        <div className="sidebar-logo-icon">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="20 6 9 17 4 12" />
          </svg>
        </div>
        {!collapsed && <span className="sidebar-logo-text">В Плюсе</span>}
      </div>

      <nav className="sidebar-nav">
        {nav.map((item, i) => {
          if (item.section) {
            if (collapsed) return null;
            return <div key={i} className="nav-section-label">{translateSection(item.section)}</div>;
          }
          const Icon = item.icon;
          const isActive = location.pathname === item.path ||
            (item.path !== '/dashboard' && item.path !== '/' && location.pathname.startsWith(item.path));
          return (
            <div key={item.path + item.label}
              className={`nav-item ${isActive ? 'active' : ''}`}
              onClick={() => navigate(item.path)}
              title={collapsed ? translateNav(item.label) : ''}>
              <Icon className="nav-item-icon" size={17} />
              {!collapsed && <span className="nav-item-label">{translateNav(item.label)}</span>}
            </div>
          );
        })}
        {canCustomizeHide && !collapsed && (
          <>
            <div className="nav-section-label">{t('sidebar.hideSection', 'СКРЫТИЕ РАЗДЕЛОВ')}</div>
            <div
              className="nav-item"
              onClick={() => setHideMenuPanelOpen(v => !v)}
              title="Свернуть/развернуть блок скрытия"
            >
              {hideMenuPanelOpen ? <ChevronLeft className="nav-item-icon" size={17} /> : <ChevronRight className="nav-item-icon" size={17} />}
              <span className="nav-item-label">
                {t('sidebar.hideToggle', 'Скрыть разделы')}
              </span>
            </div>
            {hideMenuPanelOpen && (
              <>
                <div
                  className="nav-item"
                  onClick={() => navigate('/regulations')}
                  title="Открыть Регламенты"
                >
                  <BookMarked className="nav-item-icon" size={17} />
                  <span className="nav-item-label">
                    Регламенты
                  </span>
                </div>
                <div
                  className="nav-item"
                  onClick={() => navigate('/instructions')}
                  title="Открыть Инструкция"
                >
                  <BookOpen className="nav-item-icon" size={17} />
                  <span className="nav-item-label">
                    Инструкция
                  </span>
                </div>
              </>
            )}
          </>
        )}
      </nav>

      <div className="sidebar-footer">
        <button className="collapse-btn" onClick={() => setCollapsed(c => !c)}>
          {collapsed
            ? <ChevronRight size={16} />
            : <><ChevronLeft size={16} /><span>{t('sidebar.collapse', 'Свернуть меню')}</span></>
          }
        </button>
      </div>
    </aside>
  );
}

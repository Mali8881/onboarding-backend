import Sidebar from '../components/layout/Sidebar';
import Header from '../components/layout/Header';

export default function MainLayout({ children, title }) {
  return (
    <div className="app-shell">
      <Sidebar />
      <div className="main-wrap">
        <Header title={title} />
        <main className="main-content">
          {children}
        </main>
      </div>
    </div>
  );
}

import React, { useEffect, useState } from 'react';
import { NavLink, Outlet, useParams } from 'react-router-dom';
import { LayoutDashboard, Files, MessageSquare, Menu, X } from 'lucide-react';
import './DashboardShell.css';
import { repositoriesApi, type Repository } from '../../api/repositories';

interface NavItemProps {
  to: string;
  icon: React.ReactNode;
  label: string;
  onClick?: () => void;
  disabled?: boolean;
}

const NavItem: React.FC<NavItemProps> = ({ to, icon, label, onClick, disabled }) => disabled ? (
  <span className="nav-item nav-item-disabled" aria-disabled="true" title={`${label} is not available yet`}>
    <span className="nav-item-icon" aria-hidden="true">{icon}</span>
    {label}
  </span>
) : (
  <NavLink
    to={to}
    className={({ isActive }) =>
      ['nav-item', isActive ? 'nav-item-active' : ''].filter(Boolean).join(' ')
    }
    onClick={onClick}
    end={false}
    aria-current="page"
  >
    <span className="nav-item-icon" aria-hidden="true">
      {icon}
    </span>
    {label}
  </NavLink>
);

export const DashboardShell: React.FC = () => {
  const { repoId } = useParams<{ repoId: string }>();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [repository, setRepository] = useState<Repository | null>(null);

  useEffect(() => {
    if (!repoId) return;
    const controller = new AbortController();
    repositoriesApi.monitorUntilReady(repoId, {
      signal: controller.signal,
      onStatus: setRepository,
    }).catch(() => undefined);
    return () => controller.abort();
  }, [repoId]);

  const base = `/dashboard/${repoId}`;
  const closeSidebar = () => setSidebarOpen(false);

  return (
    <div className="shell">
      {/* Mobile overlay */}
      <div
        className={`sidebar-overlay ${sidebarOpen ? 'sidebar-open' : ''}`}
        onClick={closeSidebar}
        aria-hidden="true"
      />

      {/* Sidebar */}
      <aside
        className={`sidebar ${sidebarOpen ? 'sidebar-open' : ''}`}
        aria-label="Primary navigation"
      >
        {/* Identity Block */}
        <div className="sidebar-identity">
          <img src="/favicon.svg" alt="CodeAtlas" className="sidebar-logo-mark" aria-hidden="true" />
          <span className="sidebar-wordmark">CodeAtlas</span>
        </div>

        {/* Primary Navigation */}
        <nav className="sidebar-nav" aria-label="Dashboard pages">
          <NavItem
            to={`${base}/overview`}
            icon={<LayoutDashboard size={16} />}
            label="Overview"
            onClick={closeSidebar}
          />
          <NavItem
            to={`${base}/files`}
            icon={<Files size={16} />}
            label="Files"
            disabled={repository === null || (!repository.files_ready && repository.status !== 'ready')}
            onClick={closeSidebar}
          />
          <NavItem
            to={`${base}/chat`}
            icon={<MessageSquare size={16} />}
            label="Chat"
            disabled={repository === null || repository.status !== 'ready'}
            onClick={closeSidebar}
          />
        </nav>
      </aside>

      {/* Content Area */}
      <div className="shell-content">
        {/* Mobile top bar */}
        <header className="mobile-topbar">
          <button
            className="mobile-nav-toggle"
            aria-label={sidebarOpen ? 'Close navigation' : 'Open navigation'}
            aria-expanded={sidebarOpen}
            onClick={() => setSidebarOpen((v) => !v)}
          >
            {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
          <span style={{ fontSize: 'var(--text-nav)', fontWeight: 'var(--weight-semibold)', color: 'var(--text-primary)' }}>
            CodeAtlas
          </span>
        </header>

        {/* Page content */}
        <main
          id="main-content"
          style={{ flex: 1, overflow: 'auto', display: 'flex', flexDirection: 'column' }}
        >
          <Outlet />
        </main>
      </div>
    </div>
  );
};

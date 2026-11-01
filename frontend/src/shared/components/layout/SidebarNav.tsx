import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Files, MessageSquare, PanelLeftClose, PanelLeftOpen, Unlink } from 'lucide-react';
import type { Repository } from '../../../features/repositories/types';

interface SidebarNavProps {
  base: string;
  repository: Repository | null;
  collapsed: boolean;
  onToggleCollapse: () => void;
  onUnlink: () => void;
  unlinking: boolean;
  onNavigate?: () => void;
}

export const SidebarNav: React.FC<SidebarNavProps> = ({
  base,
  repository,
  collapsed,
  onToggleCollapse,
  onUnlink,
  unlinking,
  onNavigate,
}) => {
  const isReady = repository?.status === 'ready';
  const filesReady = repository?.files_ready || isReady;

  return (
    <aside className={`sidebar ${collapsed ? 'sidebar-collapsed' : ''}`} aria-label="Primary navigation">
      <div className="sidebar-identity">
        <div className="sidebar-brand">
          <img src="/favicon.svg" alt="CodeAtlas" className="sidebar-logo-mark" />
          {!collapsed && <span className="sidebar-wordmark">CodeAtlas</span>}
        </div>
        <button
          type="button"
          className="sidebar-rail-toggle"
          onClick={onToggleCollapse}
          title={collapsed ? 'Expand sidebar' : 'Collapse to rail'}
        >
          {collapsed ? <PanelLeftOpen size={16} /> : <PanelLeftClose size={16} />}
        </button>
      </div>

      <nav className="sidebar-nav" aria-label="Dashboard pages">
        <NavLink
          to={`${base}/overview`}
          className={({ isActive }) => ['nav-item', isActive ? 'nav-item-active' : ''].filter(Boolean).join(' ')}
          onClick={onNavigate}
          title="Overview"
        >
          <span className="nav-item-icon"><LayoutDashboard size={16} /></span>
          {!collapsed && <span>Overview</span>}
        </NavLink>

        {filesReady ? (
          <NavLink
            to={`${base}/files`}
            className={({ isActive }) => ['nav-item', isActive ? 'nav-item-active' : ''].filter(Boolean).join(' ')}
            onClick={onNavigate}
            title="Files"
          >
            <span className="nav-item-icon"><Files size={16} /></span>
            {!collapsed && <span>Files</span>}
          </NavLink>
        ) : (
          <span className="nav-item nav-item-disabled" title="Files processing...">
            <span className="nav-item-icon"><Files size={16} /></span>
            {!collapsed && <span>Files</span>}
          </span>
        )}

        {isReady ? (
          <NavLink
            to={`${base}/chat`}
            className={({ isActive }) => ['nav-item', isActive ? 'nav-item-active' : ''].filter(Boolean).join(' ')}
            onClick={onNavigate}
            title="Chat"
          >
            <span className="nav-item-icon"><MessageSquare size={16} /></span>
            {!collapsed && <span>Chat</span>}
          </NavLink>
        ) : (
          <span className="nav-item nav-item-disabled" title="Chat unlocks when indexing finishes">
            <span className="nav-item-icon"><MessageSquare size={16} /></span>
            {!collapsed && <span>Chat</span>}
          </span>
        )}
      </nav>

      <div className="sidebar-footer">
        <button
          type="button"
          className="sidebar-unlink-btn"
          onClick={onUnlink}
          disabled={unlinking}
          title="Unlink repository"
        >
          <Unlink size={14} />
          {!collapsed && <span>{unlinking ? 'Unlinking...' : 'Unlink'}</span>}
        </button>
      </div>
    </aside>
  );
};

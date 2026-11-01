import React from 'react';
import { Menu, X, GitBranch, ArrowUpRight } from 'lucide-react';
import type { Repository } from '../../../features/repositories/types';

interface WorkspaceHeaderProps {
  repository: Repository | null;
  sidebarOpen: boolean;
  onToggleSidebar: () => void;
}

export const WorkspaceHeader: React.FC<WorkspaceHeaderProps> = ({
  repository,
  sidebarOpen,
  onToggleSidebar,
}) => {
  const isReady = repository?.status === 'ready';
  const repoName = repository?.name || 'Repository';
  const owner = repository?.owner || '';

  return (
    <header className="workspace-header">
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <button
          className="mobile-nav-toggle"
          onClick={onToggleSidebar}
          aria-label={sidebarOpen ? 'Close navigation' : 'Open navigation'}
        >
          {sidebarOpen ? <X size={18} /> : <Menu size={18} />}
        </button>
        <div className="workspace-breadcrumbs">
          <span>Workspace</span>
          <span style={{ opacity: 0.4 }}>/</span>
          {owner && <span>{owner}</span>}
          {owner && <span style={{ opacity: 0.4 }}>/</span>}
          <span className="workspace-repo-title">{repoName}</span>
        </div>
      </div>

      <div className="workspace-actions">
        {repository?.branch && (
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            <GitBranch size={12} /> {repository.branch}
          </span>
        )}
        <span className={`workspace-status-badge ${isReady ? 'status-ready' : ''}`}>
          <span style={{
            width: 6,
            height: 6,
            borderRadius: '50%',
            backgroundColor: isReady ? 'var(--success)' : 'var(--warning)',
          }} />
          {repository?.status || 'connecting'}
        </span>
        {repository?.url && (
          <a
            href={repository.url}
            target="_blank"
            rel="noreferrer"
            style={{ color: 'var(--text-muted)', display: 'flex', alignItems: 'center' }}
            title="Open on GitHub"
          >
            <ArrowUpRight size={15} />
          </a>
        )}
      </div>
    </header>
  );
};

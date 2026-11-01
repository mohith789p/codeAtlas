import React from 'react';
import { GitBranch, Star, GitFork, ExternalLink, Unlink } from 'lucide-react';
import type { Repository } from '../../repositories/types';
import './OverviewHeader.css';

interface OverviewHeaderProps {
  repo: Repository;
  onUnlink: () => void;
  unlinking: boolean;
}

function initials(name: string): string {
  return name.split(/[\s._-]/).map((p) => p[0]).join('').toUpperCase().slice(0, 2);
}

function formatNumber(n: number): string {
  return n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n);
}

export const OverviewHeader: React.FC<OverviewHeaderProps> = ({ repo, onUnlink, unlinking }) => {
  const isReady = repo.status === 'ready';
  const name = repo.name || 'Repository';

  return (
    <div className="overview-header">
      <div className="overview-header-main">
        <div className="overview-title-row">
          <div className="overview-repo-avatar">{initials(name)}</div>
          <h1 className="overview-repo-name">{name}</h1>
          <span className={`overview-meta-pill ${isReady ? 'status-ready' : ''}`}>
            <span style={{
              width: 6,
              height: 6,
              borderRadius: '50%',
              backgroundColor: isReady ? 'var(--success)' : 'var(--warning)',
            }} />
            {repo.status || 'indexing'}
          </span>
          {repo.branch && (
            <span className="overview-meta-pill">
              <GitBranch size={12} /> {repo.branch}
            </span>
          )}
          {repo.stars !== undefined && repo.stars > 0 && (
            <span className="overview-meta-pill">
              <Star size={12} /> {formatNumber(repo.stars)}
            </span>
          )}
          {repo.forks !== undefined && repo.forks > 0 && (
            <span className="overview-meta-pill">
              <GitFork size={12} /> {formatNumber(repo.forks)}
            </span>
          )}
        </div>
      </div>

      <div className="overview-actions">
        {repo.url && (
          <a
            href={repo.url}
            target="_blank"
            rel="noreferrer"
            className="overview-meta-pill"
            style={{ textDecoration: 'none' }}
          >
            <ExternalLink size={13} />
            <span>GitHub</span>
          </a>
        )}
        <button
          type="button"
          className="btn-ghost-danger"
          onClick={onUnlink}
          disabled={unlinking}
        >
          <Unlink size={13} />
          <span>{unlinking ? 'Unlinking…' : 'Unlink'}</span>
        </button>
      </div>
    </div>
  );
};

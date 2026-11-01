import React from 'react';
import type { Repository } from '../../repositories/types';
import './RepoDetailsGrid.css';

interface RepoDetailsGridProps {
  repo: Repository;
}

function formatDate(val?: string): string {
  if (!val) return '—';
  const d = new Date(val);
  return Number.isNaN(d.getTime()) ? '—' : d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
}

export const RepoDetailsGrid: React.FC<RepoDetailsGridProps> = ({ repo }) => (
  <div className="details-grid">
    <div className="details-card">
      <h3 className="lang-card-title">About this Repository</h3>
      <p className="details-desc">
        {repo.description || 'No description provided by the repository.'}
      </p>
      {repo.topics && repo.topics.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '4px' }}>
          {repo.topics.map((t) => (
            <span
              key={t}
              style={{
                fontSize: '0.75rem',
                padding: '2px 8px',
                borderRadius: '12px',
                background: 'rgba(124, 58, 237, 0.1)',
                color: 'var(--accent-violet-soft)',
                border: '1px solid rgba(124, 58, 237, 0.2)',
              }}
            >
              #{t}
            </span>
          ))}
        </div>
      )}
    </div>

    <div className="details-card">
      <h3 className="lang-card-title">Repository Specs</h3>
      <div className="meta-keyvalue-row">
        <span className="meta-key">Default Branch</span>
        <span className="meta-val">{repo.branch || repo.default_branch || 'main'}</span>
      </div>
      <div className="meta-keyvalue-row">
        <span className="meta-key">License</span>
        <span className="meta-val">{repo.repository_metadata?.license_name || 'None detected'}</span>
      </div>
      <div className="meta-keyvalue-row">
        <span className="meta-key">Last Synced</span>
        <span className="meta-val">{formatDate(repo.processing?.last_indexed_at || (repo as any).processing_stats?.last_indexed_at || repo.pushed_at || repo.created_at)}</span>
      </div>
      <div className="meta-keyvalue-row" style={{ borderBottom: 'none' }}>
        <span className="meta-key">Visibility</span>
        <span className="meta-val">{repo.visibility || repo.repository_metadata?.visibility || 'Public'}</span>
      </div>
    </div>
  </div>
);

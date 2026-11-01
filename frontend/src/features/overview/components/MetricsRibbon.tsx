import React from 'react';
import { HardDrive, Files, CalendarPlus, History } from 'lucide-react';
import type { Repository } from '../../repositories/types';
import './MetricsRibbon.css';

interface MetricsRibbonProps {
  repo: Repository;
}

function formatSize(kb?: number): string {
  if (kb === undefined || kb === null || kb <= 0) return '—';
  if (kb >= 1024 * 1024) return `${(kb / (1024 * 1024)).toFixed(2)} GB`;
  if (kb >= 1024) return `${(kb / 1024).toFixed(1)} MB`;
  return `${kb.toLocaleString()} KB`;
}

function formatDate(val?: string): string {
  if (!val) return '—';
  const d = new Date(val);
  return Number.isNaN(d.getTime())
    ? '—'
    : d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function formatCount(val: number | undefined, status?: string): string {
  if (val !== undefined && val !== null) {
    return val.toLocaleString();
  }
  if (status === 'ready') return '0';
  return status === 'queued' || status === 'downloading' ? 'Pending' : 'Indexing…';
}

export const MetricsRibbon: React.FC<MetricsRibbonProps> = ({ repo }) => {
  const sizeKb = repo.size_kb || (repo.repository_metadata as any)?.size_kb || (repo as any).size;

  const fileCount =
    repo.files ||
    repo.processing?.files_total ||
    repo.processing_stats?.files_total ||
    repo.stats?.files ||
    repo.repository_metadata?.file_paths?.length;

  const createdDate =
    repo.repository_metadata?.github_created_at ||
    repo.created_at;

  const updatedDate =
    repo.repository_metadata?.pushed_at ||
    repo.repository_metadata?.github_updated_at ||
    repo.pushed_at ||
    repo.updated_at;

  return (
    <div className="metrics-ribbon">
      <div className="metric-card">
        <div className="metric-label">
          <HardDrive size={14} />
          <span>Project Size</span>
        </div>
        <div className="metric-value">{formatSize(sizeKb)}</div>
        <div className="metric-subtext">Total repository footprint</div>
      </div>

      <div className="metric-card">
        <div className="metric-label">
          <Files size={14} />
          <span>Total Files</span>
        </div>
        <div className="metric-value">{formatCount(fileCount, repo.status)}</div>
        <div className="metric-subtext">Source files analyzed</div>
      </div>

      <div className="metric-card">
        <div className="metric-label">
          <CalendarPlus size={14} />
          <span>Created in Git</span>
        </div>
        <div className="metric-value" style={{ fontSize: '1.125rem', paddingTop: '4px' }}>
          {formatDate(createdDate)}
        </div>
        <div className="metric-subtext">Initial git repository creation</div>
      </div>

      <div className="metric-card">
        <div className="metric-label">
          <History size={14} />
          <span>Updated in Git</span>
        </div>
        <div className="metric-value" style={{ fontSize: '1.125rem', paddingTop: '4px' }}>
          {formatDate(updatedDate)}
        </div>
        <div className="metric-subtext">Latest commit / push to git</div>
      </div>
    </div>
  );
};

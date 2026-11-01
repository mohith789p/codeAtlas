import React from 'react';
import { GitBranch, Clock, ArrowRight } from 'lucide-react';
import './RecentRepos.css';

interface RecentRepoItem {
  id: string;
  name: string;
  owner?: string;
  branch?: string;
}

interface RecentReposProps {
  onSelect: (item: RecentRepoItem) => void;
}

export const RecentRepos: React.FC<RecentReposProps> = ({ onSelect }) => {
  const [recents, setRecents] = React.useState<RecentRepoItem[]>([]);

  React.useEffect(() => {
    try {
      const stored = localStorage.getItem('codeatlas:recent_repos');
      if (stored) {
        setRecents(JSON.parse(stored).slice(0, 3));
      }
    } catch {
      // ignore
    }
  }, []);

  if (recents.length === 0) return null;

  return (
    <div className="recent-repos-card">
      <div className="recent-repos-header" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
        <Clock size={12} />
        <span>Recent Repositories</span>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
        {recents.map((r) => (
          <button
            key={r.id}
            type="button"
            className="recent-repo-item"
            onClick={() => onSelect(r)}
          >
            <span style={{ fontWeight: 'var(--weight-medium)', color: 'var(--text-primary)' }}>
              {r.owner ? `${r.owner}/${r.name}` : r.name}
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              {r.branch && <span><GitBranch size={11} /> {r.branch}</span>}
              <ArrowRight size={13} />
            </span>
          </button>
        ))}
      </div>
    </div>
  );
};

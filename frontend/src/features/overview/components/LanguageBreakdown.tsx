import React from 'react';
import type { Repository } from '../../repositories/types';
import './LanguageBreakdown.css';

const LANG_COLORS: Record<string, string> = {
  TypeScript: '#3178c6',
  JavaScript: '#f7df1e',
  Python: '#3572A5',
  Rust: '#dea584',
  Go: '#00ADD8',
  Java: '#b07219',
  'C++': '#f34b7d',
  C: '#555555',
  'C#': '#178600',
  Ruby: '#701516',
  PHP: '#4F5D95',
  Swift: '#F05138',
  Kotlin: '#A97BFF',
  HTML: '#e34c26',
  CSS: '#563d7c',
  Shell: '#89e051',
  Other: '#646b84',
};

interface LanguageBreakdownProps {
  repo: Repository;
}

export const LanguageBreakdown: React.FC<LanguageBreakdownProps> = ({ repo }) => {
  const rawLangs = repo.languages && Object.keys(repo.languages).length > 0
    ? repo.languages
    : (repo.repository_metadata?.languages && Object.keys(repo.repository_metadata.languages).length > 0
      ? repo.repository_metadata.languages
      : null);

  const primary = repo.primary_language || repo.language;
  const languages: Record<string, number> = rawLangs || (primary ? { [primary]: 100 } : { 'General': 100 });
  const total = Object.values(languages).reduce((acc, val) => acc + val, 0) || 1;

  const entries = Object.entries(languages)
    .map(([lang, count]) => {
      const normalized = lang.charAt(0).toUpperCase() + lang.slice(1).toLowerCase();
      const color = LANG_COLORS[lang] || LANG_COLORS[normalized] || '#7c3aed';
      return {
        lang,
        count,
        pct: Math.max(1, Math.round((count / total) * 100)),
        color,
      };
    })
    .sort((a, b) => b.count - a.count);

  return (
    <div className="lang-breakdown-card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3 className="lang-card-title">Languages & Stack</h3>
        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          {primary ? `Primary: ${primary}` : `${entries.length} detected`}
        </span>
      </div>

      <div className="lang-bar-container">
        {entries.map(({ lang, pct, color }) => (
          <div
            key={lang}
            className="lang-bar-segment"
            style={{ width: `${pct}%`, backgroundColor: color }}
            title={`${lang}: ${pct}%`}
          />
        ))}
      </div>

      <div className="lang-legend-grid">
        {entries.map(({ lang, pct, color }) => (
          <div key={lang} className="lang-legend-item">
            <span className="lang-legend-dot" style={{ backgroundColor: color }} />
            <span>{lang}</span>
            <span className="lang-legend-pct">{pct}%</span>
          </div>
        ))}
      </div>
    </div>
  );
};
